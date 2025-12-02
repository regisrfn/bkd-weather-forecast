"""
Testes de Regras de Negócio Críticas - Rain Alert Service
Foco em descobrir bugs e validar lógica complexa
"""
import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

from domain.services.rain_alert_service import RainAlertService, RainAlertInput
from domain.alerts.primitives import AlertSeverity, RAIN_INTENSITY_REFERENCE


class TestRainIntensityCalculation:
    """Testes para cálculo de intensidade de chuva"""
    
    def test_zero_precipitation_returns_zero_intensity(self):
        """REGRA: Se rain_1h = 0, intensidade DEVE ser 0, independente da probabilidade"""
        intensity = RainAlertService.compute_rainfall_intensity(
            rain_prob=100.0,  # 100% de probabilidade
            rain_1h=0.0       # MAS 0mm de chuva
        )
        assert intensity == 0.0, "Zero precipitação deve resultar em zero intensidade"
    
    def test_intensity_maxes_at_100(self):
        """REGRA: Intensidade nunca deve ultrapassar 100"""
        intensity = RainAlertService.compute_rainfall_intensity(
            rain_prob=100.0,
            rain_1h=1000.0  # Valor absurdo
        )
        assert intensity == 100.0, "Intensidade deve ser limitada em 100"
    
    def test_intensity_formula_correctness(self):
        """REGRA: Fórmula = (rain_1h * rain_prob/100) / REFERENCE * 100"""
        # Exemplo: 15mm/h a 50% de probabilidade
        # = (15 * 0.5) / 30 * 100
        # = 7.5 / 30 * 100
        # = 0.25 * 100
        # = 25
        intensity = RainAlertService.compute_rainfall_intensity(
            rain_prob=50.0,
            rain_1h=15.0
        )
        expected = (15.0 * 0.5) / RAIN_INTENSITY_REFERENCE * 100.0
        assert intensity == expected, f"Fórmula incorreta: {intensity} != {expected}"
    
    def test_low_probability_reduces_intensity(self):
        """REGRA: Baixa probabilidade deve reduzir intensidade significativamente"""
        high_prob = RainAlertService.compute_rainfall_intensity(
            rain_prob=90.0,
            rain_1h=10.0
        )
        low_prob = RainAlertService.compute_rainfall_intensity(
            rain_prob=10.0,
            rain_1h=10.0
        )
        assert low_prob < high_prob / 5, "Baixa probabilidade deve reduzir intensidade drasticamente"


class TestRainAlertGeneration:
    """Testes para geração de alertas de chuva"""
    
    def test_no_alert_for_zero_rain_and_low_probability(self):
        """REGRA: Sem chuva + baixa probabilidade = sem alerta"""
        data = RainAlertInput(
            weather_code=800,  # Céu limpo
            rain_prob=10.0,
            rain_1h=0.0,
            forecast_time=datetime.now(ZoneInfo("UTC"))
        )
        alerts = RainAlertService.generate_alerts(data)
        assert len(alerts) == 0, "Não deve gerar alerta para condições secas"
    
    def test_storm_alert_for_thunderstorm_code(self):
        """REGRA: Código 95-99 (WMO) OU 200-299 (OWM) = tempestade"""
        # WMO thunderstorm
        data_wmo = RainAlertInput(
            weather_code=95,
            rain_prob=80.0,
            rain_1h=15.0,
            forecast_time=datetime.now(ZoneInfo("UTC"))
        )
        alerts_wmo = RainAlertService.generate_alerts(data_wmo)
        assert any(a.code == "STORM" for a in alerts_wmo), "WMO 95 deve gerar STORM"
        
        # OpenWeather thunderstorm
        data_owm = RainAlertInput(
            weather_code=201,
            rain_prob=80.0,
            rain_1h=15.0,
            forecast_time=datetime.now(ZoneInfo("UTC"))
        )
        alerts_owm = RainAlertService.generate_alerts(data_owm)
        assert any(a.code == "STORM" for a in alerts_owm), "OWM 201 deve gerar STORM"
    
    def test_heavy_rain_threshold_60_intensity(self):
        """REGRA: Intensidade >= 60 = HEAVY_RAIN"""
        # Calcular rain_1h para atingir intensidade 60
        # 60 = (rain_1h * 100) / 30 * 100
        # rain_1h = 60 * 30 / 100 / 100 = 18mm
        data = RainAlertInput(
            weather_code=500,
            rain_prob=100.0,
            rain_1h=18.0,
            forecast_time=datetime.now(ZoneInfo("UTC"))
        )
        alerts = RainAlertService.generate_alerts(data)
        assert any(a.code == "HEAVY_RAIN" for a in alerts), "60+ intensidade deve ser HEAVY_RAIN"
        assert any(a.severity == AlertSeverity.ALERT for a in alerts), "HEAVY_RAIN deve ser ALERT"
    
    def test_moderate_rain_threshold_25_intensity(self):
        """REGRA: Intensidade 25-59 = MODERATE_RAIN"""
        # 25 = (rain_1h * 100) / 30 * 100
        # rain_1h = 7.5mm
        data = RainAlertInput(
            weather_code=500,
            rain_prob=100.0,
            rain_1h=7.5,
            forecast_time=datetime.now(ZoneInfo("UTC"))
        )
        alerts = RainAlertService.generate_alerts(data)
        assert any(a.code == "MODERATE_RAIN" for a in alerts), "25-59 intensidade deve ser MODERATE_RAIN"
        assert any(a.severity == AlertSeverity.WARNING for a in alerts), "MODERATE_RAIN deve ser WARNING"
    
    def test_light_rain_threshold_10_intensity(self):
        """REGRA: Intensidade 10-24 = LIGHT_RAIN"""
        # 10 = (rain_1h * 100) / 30 * 100
        # rain_1h = 3mm
        data = RainAlertInput(
            weather_code=500,
            rain_prob=100.0,
            rain_1h=3.0,
            forecast_time=datetime.now(ZoneInfo("UTC"))
        )
        alerts = RainAlertService.generate_alerts(data)
        assert any(a.code == "LIGHT_RAIN" for a in alerts), "10-24 intensidade deve ser LIGHT_RAIN"
    
    def test_drizzle_threshold_1_intensity(self):
        """REGRA: Intensidade 1-9 = DRIZZLE"""
        # 1 = (rain_1h * 100) / 30 * 100
        # rain_1h = 0.3mm
        data = RainAlertInput(
            weather_code=500,
            rain_prob=100.0,
            rain_1h=0.3,
            forecast_time=datetime.now(ZoneInfo("UTC"))
        )
        alerts = RainAlertService.generate_alerts(data)
        assert any(a.code == "DRIZZLE" for a in alerts), "1-9 intensidade deve ser DRIZZLE"
    
    def test_fallback_alert_for_high_probability_no_volume(self):
        """REGRA: Alta probabilidade (70%+) com código de chuva mas sem volume = RAIN_EXPECTED"""
        data = RainAlertInput(
            weather_code=500,  # Código de chuva
            rain_prob=80.0,    # Alta probabilidade
            rain_1h=0.0,       # Mas sem volume medido
            forecast_time=datetime.now(ZoneInfo("UTC"))
        )
        alerts = RainAlertService.generate_alerts(data)
        assert any(a.code == "RAIN_EXPECTED" for a in alerts), "Alta prob sem volume deve gerar RAIN_EXPECTED"
    
    def test_no_fallback_for_low_probability(self):
        """REGRA: Baixa probabilidade não deve gerar fallback mesmo com código de chuva"""
        data = RainAlertInput(
            weather_code=500,
            rain_prob=30.0,  # Baixa
            rain_1h=0.0,
            forecast_time=datetime.now(ZoneInfo("UTC"))
        )
        alerts = RainAlertService.generate_alerts(data)
        assert len(alerts) == 0, "Baixa probabilidade sem volume não deve gerar alerta"
    
    def test_alert_details_include_probability(self):
        """REGRA: Todos os alertas devem incluir probability_percent nos detalhes"""
        data = RainAlertInput(
            weather_code=500,
            rain_prob=75.5,
            rain_1h=5.0,
            forecast_time=datetime.now(ZoneInfo("UTC"))
        )
        alerts = RainAlertService.generate_alerts(data)
        assert len(alerts) > 0, "Deve gerar pelo menos um alerta"
        for alert in alerts:
            assert "probability_percent" in alert.details, "Deve incluir probabilidade"
            assert alert.details["probability_percent"] == 75.5, "Probabilidade deve estar correta"
    
    def test_alert_details_include_rain_volume_when_present(self):
        """REGRA: Alertas com chuva devem incluir rain_mm_h nos detalhes"""
        data = RainAlertInput(
            weather_code=500,
            rain_prob=80.0,
            rain_1h=12.5,
            forecast_time=datetime.now(ZoneInfo("UTC"))
        )
        alerts = RainAlertService.generate_alerts(data)
        assert len(alerts) > 0, "Deve gerar alerta"
        # Pelo menos um alerta deve ter rain_mm_h
        has_volume = any("rain_mm_h" in a.details for a in alerts)
        assert has_volume, "Deve incluir volume de chuva quando presente"


class TestRainCodeClassification:
    """Testes para classificação de códigos de chuva"""
    
    @pytest.mark.parametrize("code", [80, 81, 82])
    def test_wmo_rain_shower_codes_are_recognized(self, code):
        """REGRA: Códigos WMO 80-82 devem ser reconhecidos como chuva"""
        data = RainAlertInput(
            weather_code=code,
            rain_prob=60.0,
            rain_1h=5.0,
            forecast_time=datetime.now(ZoneInfo("UTC"))
        )
        alerts = RainAlertService.generate_alerts(data)
        assert len(alerts) > 0, f"Código WMO {code} deve gerar alerta"
    
    @pytest.mark.parametrize("code", [95, 96, 99])
    def test_wmo_thunderstorm_codes_generate_storm_alert(self, code):
        """REGRA: Códigos WMO 95-99 devem gerar STORM com DANGER severity"""
        data = RainAlertInput(
            weather_code=code,
            rain_prob=80.0,
            rain_1h=15.0,
            forecast_time=datetime.now(ZoneInfo("UTC"))
        )
        alerts = RainAlertService.generate_alerts(data)
        storm_alerts = [a for a in alerts if a.code == "STORM"]
        assert len(storm_alerts) > 0, f"Código WMO {code} deve gerar STORM"
        assert storm_alerts[0].severity == AlertSeverity.DANGER
    
    @pytest.mark.parametrize("code", [200, 210, 230, 250])
    def test_owm_thunderstorm_codes_generate_storm_alert(self, code):
        """REGRA: Códigos OWM 200-299 devem gerar STORM"""
        data = RainAlertInput(
            weather_code=code,
            rain_prob=80.0,
            rain_1h=15.0,
            forecast_time=datetime.now(ZoneInfo("UTC"))
        )
        alerts = RainAlertService.generate_alerts(data)
        assert any(a.code == "STORM" for a in alerts), f"Código OWM {code} deve gerar STORM"
    
    @pytest.mark.parametrize("code", [502, 503, 504, 522, 531])
    def test_owm_heavy_rain_codes_with_high_volume(self, code):
        """REGRA: Códigos OWM de chuva forte com volume alto devem gerar alerta apropriado"""
        data = RainAlertInput(
            weather_code=code,
            rain_prob=100.0,  # 100% para maximizar intensidade
            rain_1h=30.0,     # 30mm/h = intensidade 100
            forecast_time=datetime.now(ZoneInfo("UTC"))
        )
        alerts = RainAlertService.generate_alerts(data)
        # Com intensidade 100, deve gerar HEAVY_RAIN
        assert len(alerts) > 0, f"Código {code} com volume alto deve gerar alerta"
        assert any(a.code == "HEAVY_RAIN" for a in alerts), \
            f"Volume muito alto (30mm/h a 100%) deve gerar HEAVY_RAIN para código {code}"
    
    def test_clear_sky_code_does_not_generate_alert(self):
        """REGRA: Código 800 (céu limpo) não deve gerar alerta mesmo com dados inconsistentes"""
        data = RainAlertInput(
            weather_code=800,  # Céu limpo (inconsistente com dados abaixo)
            rain_prob=10.0,
            rain_1h=0.5,
            forecast_time=datetime.now(ZoneInfo("UTC"))
        )
        alerts = RainAlertService.generate_alerts(data)
        # Intensidade muito baixa, não deve gerar
        assert len(alerts) == 0, "Código 800 com baixa intensidade não deve gerar alerta"


class TestEdgeCasesAndBoundaries:
    """Testes de casos extremos e limites"""
    
    def test_exactly_at_threshold_generates_alert(self):
        """REGRA: Valor exatamente no threshold deve gerar o alerta"""
        # Intensidade exatamente 10 (limite LIGHT_RAIN)
        data = RainAlertInput(
            weather_code=500,
            rain_prob=100.0,
            rain_1h=3.0,  # = 10 intensity
            forecast_time=datetime.now(ZoneInfo("UTC"))
        )
        alerts = RainAlertService.generate_alerts(data)
        assert any(a.code == "LIGHT_RAIN" for a in alerts), "Threshold exato deve gerar alerta"
    
    def test_just_below_threshold_does_not_upgrade(self):
        """REGRA: Valor abaixo do threshold não deve ser promovido"""
        # Intensidade 24.9 (abaixo de MODERATE_RAIN=25)
        data = RainAlertInput(
            weather_code=500,
            rain_prob=100.0,
            rain_1h=7.47,  # = 24.9 intensity
            forecast_time=datetime.now(ZoneInfo("UTC"))
        )
        alerts = RainAlertService.generate_alerts(data)
        assert all(a.code != "MODERATE_RAIN" for a in alerts), "Abaixo do threshold não deve promover"
    
    def test_negative_values_handled_gracefully(self):
        """REGRA: Valores negativos não devem causar crash"""
        data = RainAlertInput(
            weather_code=500,
            rain_prob=-10.0,  # Inválido mas não deve crashar
            rain_1h=-5.0,     # Inválido
            forecast_time=datetime.now(ZoneInfo("UTC"))
        )
        # Não deve crashar
        alerts = RainAlertService.generate_alerts(data)
        assert isinstance(alerts, list), "Deve retornar lista mesmo com valores inválidos"
    
    def test_extremely_high_values_capped(self):
        """REGRA: Valores absurdamente altos devem ser limitados"""
        data = RainAlertInput(
            weather_code=500,
            rain_prob=1000.0,  # Absurdo
            rain_1h=999.0,     # Absurdo
            forecast_time=datetime.now(ZoneInfo("UTC"))
        )
        intensity = RainAlertService.compute_rainfall_intensity(1000.0, 999.0)
        assert intensity == 100.0, "Intensidade deve ser limitada em 100"
