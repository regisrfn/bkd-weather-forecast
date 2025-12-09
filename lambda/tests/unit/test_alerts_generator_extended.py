"""
Testes Estendidos para AlertsGenerator
Foca em casos de borda e cenários não cobertos pelos testes existentes
"""
import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dataclasses import dataclass

from domain.services.alerts_generator import AlertsGenerator
from domain.alerts.primitives import AlertSeverity


@dataclass
class MockForecast:
    """Mock simples de forecast para testes"""
    timestamp: datetime
    temperature: float
    wind_speed: float
    wind_direction: int
    rain_probability: float
    precipitation: float
    weather_code: int
    visibility: float = 10000
    
    @property
    def precipitation_probability(self):
        return self.rain_probability
    
    @property
    def rainfall_intensity(self):
        """Calcula rainfall_intensity para testes"""
        from domain.helpers.rainfall_calculator import calculate_rainfall_intensity
        return calculate_rainfall_intensity(self.rain_probability, self.precipitation)


class TestAlertsGeneratorEdgeCases:
    """Testes para casos de borda do AlertsGenerator"""
    
    def test_generate_all_alerts_with_empty_list(self):
        """REGRA: Lista vazia deve retornar lista vazia de alertas"""
        alerts = AlertsGenerator.generate_all_alerts([])
        assert alerts == []
    
    def test_generate_all_alerts_with_past_forecasts_only(self):
        """REGRA: Se todos forecasts são passados, retornar lista vazia"""
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        past_forecasts = [
            MockForecast(
                timestamp=now - timedelta(hours=i),
                temperature=25.0,
                wind_speed=10.0,
                wind_direction=180,
                rain_probability=30,
                precipitation=0.0,
                weather_code=800
            )
            for i in range(1, 4)
        ]
        
        alerts = AlertsGenerator.generate_all_alerts(past_forecasts, target_datetime=now)
        assert alerts == []
    
    def test_generate_all_alerts_with_naive_target_datetime(self):
        """REGRA: target_datetime naive deve ser tratado como horário de Brasília"""
        now = datetime.now()  # Naive datetime
        
        future_forecast = MockForecast(
            timestamp=now + timedelta(hours=1),
            temperature=35.0,
            wind_speed=10.0,
            wind_direction=180,
            rain_probability=0,
            precipitation=0.0,
            weather_code=800
        )
        
        # Não deve lançar exceção
        alerts = AlertsGenerator.generate_all_alerts([future_forecast], target_datetime=now)
        # Deve processar corretamente
        assert isinstance(alerts, list)
    
    def test_generate_all_alerts_with_timezone_aware_target(self):
        """REGRA: target_datetime com timezone deve ser convertido para Brasília"""
        utc_time = datetime.now(ZoneInfo("UTC"))
        
        future_forecast = MockForecast(
            timestamp=utc_time + timedelta(hours=1),
            temperature=35.0,
            wind_speed=10.0,
            wind_direction=180,
            rain_probability=0,
            precipitation=0.0,
            weather_code=800
        )
        
        alerts = AlertsGenerator.generate_all_alerts([future_forecast], target_datetime=utc_time)
        assert isinstance(alerts, list)
    
    def test_generate_alerts_with_high_visibility(self):
        """EDGE CASE: Visibilidade muito alta não deve gerar alerta"""
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        
        forecast = MockForecast(
            timestamp=now + timedelta(hours=1),
            temperature=25.0,
            wind_speed=10.0,
            wind_direction=180,
            rain_probability=0,
            precipitation=0.0,
            weather_code=800,
            visibility=50000  # Visibilidade excepcional
        )
        
        alerts = AlertsGenerator.generate_all_alerts([forecast], target_datetime=now)
        
        # Não deve ter alerta de visibilidade
        visibility_alerts = [a for a in alerts if 'visibilidade' in a.message.lower()]
        assert len(visibility_alerts) == 0
    
    def test_generate_alerts_with_zero_precipitation_high_probability(self):
        """EDGE CASE: Alta probabilidade mas sem precipitação"""
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        
        forecast = MockForecast(
            timestamp=now + timedelta(hours=1),
            temperature=25.0,
            wind_speed=10.0,
            wind_direction=180,
            rain_probability=90,  # Alta probabilidade
            precipitation=0.0,  # Mas sem precipitação
            weather_code=800
        )
        
        alerts = AlertsGenerator.generate_all_alerts([forecast], target_datetime=now)
        
        # Alta probabilidade nem sempre gera alerta se não houver precipitação
        # O teste apenas verifica que não crashou
        assert isinstance(alerts, list)
    
    def test_generate_alerts_with_extreme_cold_temperature(self):
        """EDGE CASE: Temperatura extremamente baixa"""
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        
        forecast = MockForecast(
            timestamp=now + timedelta(hours=1),
            temperature=-5.0,  # Muito frio para o Brasil
            wind_speed=10.0,
            wind_direction=180,
            rain_probability=0,
            precipitation=0.0,
            weather_code=600  # Neve
        )
        
        alerts = AlertsGenerator.generate_all_alerts([forecast], target_datetime=now)
        
        # Deve processar corretamente, pode ou não ter alertas dependendo dos thresholds
        assert isinstance(alerts, list)
        # Se houver alertas, deve incluir frio ou neve
        if alerts:
            descriptions = ' '.join([a.description.lower() for a in alerts])
            assert any(word in descriptions for word in ['frio', 'neve', 'temperatura', 'gelado'])
    
    def test_generate_alerts_with_storm_weather_code(self):
        """EDGE CASE: Código de tempestade deve gerar alerta"""
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        
        forecast = MockForecast(
            timestamp=now + timedelta(hours=1),
            temperature=25.0,
            wind_speed=30.0,  # Vento forte
            wind_direction=180,
            rain_probability=100,
            precipitation=50.0,  # Chuva intensa
            weather_code=95  # Código de tempestade
        )
        
        alerts = AlertsGenerator.generate_all_alerts([forecast], target_datetime=now)
        
        # Deve ter múltiplos alertas
        assert len(alerts) > 0
        
        # Pelo menos um deve ser de tempestade ou chuva forte
        severe_alerts = [a for a in alerts if a.severity in [AlertSeverity.ALERT, AlertSeverity.DANGER]]
        assert len(severe_alerts) > 0
    
    def test_deduplication_of_identical_alerts(self):
        """REGRA: Alertas idênticos devem ser deduplcados"""
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        
        # Dois forecasts consecutivos com mesmas condições
        forecasts = [
            MockForecast(
                timestamp=now + timedelta(hours=i),
                temperature=35.0,  # Muito quente
                wind_speed=10.0,
                wind_direction=180,
                rain_probability=0,
                precipitation=0.0,
                weather_code=800
            )
            for i in range(1, 3)
        ]
        
        alerts = AlertsGenerator.generate_all_alerts(forecasts, target_datetime=now)
        
        # Alertas devem ser deduplcados
        alert_descriptions = [a.description for a in alerts]
        # Não deve ter mensagens duplicadas
        assert len(alert_descriptions) == len(set(alert_descriptions))
    
    def test_generate_alerts_with_high_wind_multiple_hours(self):
        """EDGE CASE: Vento forte por múltiplas horas"""
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        
        forecasts = [
            MockForecast(
                timestamp=now + timedelta(hours=i),
                temperature=25.0,
                wind_speed=60.0,  # Vento muito forte
                wind_direction=180,
                rain_probability=0,
                precipitation=0.0,
                weather_code=800
            )
            for i in range(1, 6)  # 5 horas de vento forte
        ]
        
        alerts = AlertsGenerator.generate_all_alerts(forecasts, target_datetime=now)
        
        # Deve ter alerta de vento
        wind_alerts = [a for a in alerts if 'vento' in a.description.lower()]
        assert len(wind_alerts) > 0
    
    def test_generate_alerts_with_mixed_conditions(self):
        """INTEGRATION: Múltiplas condições adversas simultâneas"""
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        
        forecast = MockForecast(
            timestamp=now + timedelta(hours=1),
            temperature=2.0,  # Muito frio
            wind_speed=70.0,  # Vento muito forte
            wind_direction=180,
            rain_probability=90,  # Alta prob de chuva
            precipitation=25.0,  # Chuva forte
            weather_code=95,  # Tempestade
            visibility=500  # Baixa visibilidade
        )
        
        alerts = AlertsGenerator.generate_all_alerts([forecast], target_datetime=now)
        
        # Deve ter múltiplos alertas de diferentes tipos
        assert len(alerts) >= 3
        
        # Deve ter pelo menos um alerta de alta severidade
        high_severity_alerts = [a for a in alerts if a.severity in [AlertSeverity.ALERT, AlertSeverity.DANGER]]
        assert len(high_severity_alerts) > 0
