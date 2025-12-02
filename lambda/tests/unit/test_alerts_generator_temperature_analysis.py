"""
Testes para análise de temperatura no AlertsGenerator
Foca em cobrir _analyze_temperature_trends_optimized e casos de borda
"""
import os
import sys
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from domain.services.alerts_generator import AlertsGenerator
from domain.alerts.primitives import WeatherAlert, AlertSeverity
from domain.entities.hourly_forecast import HourlyForecast


def _hourly(ts_str: str, temp: float = 25.0) -> HourlyForecast:
    """Helper para criar HourlyForecast"""
    return HourlyForecast(
        timestamp=ts_str,
        temperature=temp,
        precipitation=0.0,
        precipitation_probability=0.0,
        humidity=60,
        wind_speed=5.0,
        wind_direction=180,
        cloud_cover=20,
        weather_code=0,
        description="clear",
    )


class TestAlertsGeneratorTemperatureAnalysis:
    """Testa análise de temperatura e casos especiais"""

    def test_analyze_temperature_trends_multiple_days(self):
        """Deve analisar tendências em múltiplos dias"""
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        
        forecasts = [
            _hourly((now + timedelta(days=0, hours=12)).isoformat(), temp=30.0),
            _hourly((now + timedelta(days=1, hours=12)).isoformat(), temp=32.0),
            _hourly((now + timedelta(days=2, hours=12)).isoformat(), temp=20.0),  # Drop 12°C
            _hourly((now + timedelta(days=3, hours=12)).isoformat(), temp=33.0),  # Rise 13°C
        ]
        
        result = AlertsGenerator.generate_alerts_next_days(forecasts, target_datetime=now)
        
        codes = {a.code for a in result}
        # Deve ter TEMP_DROP e TEMP_RISE
        assert "TEMP_DROP" in codes
        assert "TEMP_RISE" in codes

    def test_temperature_variation_exactly_8_degrees(self):
        """Deve gerar alerta com variação exatamente no threshold"""
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        
        forecasts = [
            _hourly((now + timedelta(hours=12)).isoformat(), temp=25.0),
            _hourly((now + timedelta(days=1, hours=12)).isoformat(), temp=17.0),  # Exatamente -8°C
        ]
        
        result = AlertsGenerator.generate_alerts_next_days(forecasts, target_datetime=now)
        
        temp_alerts = [a for a in result if a.code == "TEMP_DROP"]
        assert len(temp_alerts) > 0
        assert temp_alerts[0].details["variation_c"] == -8.0

    def test_no_alerts_for_single_day(self):
        """Não deve gerar alertas de temperatura com apenas 1 dia de dados"""
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        
        forecasts = [
            _hourly((now + timedelta(hours=i)).isoformat(), temp=25.0)
            for i in range(1, 24)
        ]
        
        result = AlertsGenerator.generate_alerts_next_days(forecasts, target_datetime=now)
        
        temp_alerts = [a for a in result if "TEMP" in a.code]
        assert len(temp_alerts) == 0

    def test_parse_timestamp_with_different_formats(self):
        """Deve parsear timestamps em diferentes formatos"""
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        
        # Testar com datetime direto
        forecasts = [_hourly((now + timedelta(hours=12)).isoformat(), temp=25.0)]
        result = AlertsGenerator.generate_alerts_next_days(forecasts, target_datetime=now)
        assert isinstance(result, list)

    def test_generate_all_alerts_with_custom_target(self):
        """Deve usar target_datetime customizado"""
        custom_date = datetime(2024, 6, 15, 12, 0, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
        
        forecasts = [
            _hourly("2024-06-15T14:00:00-03:00", temp=35.0),
            _hourly("2024-06-16T14:00:00-03:00", temp=22.0),
        ]
        
        result = AlertsGenerator.generate_all_alerts(forecasts, target_datetime=custom_date)
        
        temp_alerts = [a for a in result if a.code == "TEMP_DROP"]
        assert len(temp_alerts) > 0

    def test_extreme_temperature_variations(self):
        """Deve lidar com variações extremas de temperatura"""
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        
        forecasts = [
            _hourly((now + timedelta(hours=12)).isoformat(), temp=40.0),
            _hourly((now + timedelta(days=1, hours=12)).isoformat(), temp=5.0),  # -35°C!
        ]
        
        result = AlertsGenerator.generate_alerts_next_days(forecasts, target_datetime=now)
        
        temp_drop = [a for a in result if a.code == "TEMP_DROP"]
        assert len(temp_drop) > 0
        assert abs(temp_drop[0].details["variation_c"]) >= 30.0

    def test_gradual_temperature_change(self):
        """Não deve gerar alerta para mudanças graduais pequenas"""
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        
        # Mudança gradual de 1°C por dia
        forecasts = []
        for day in range(7):
            temp = 25.0 + day  # 25, 26, 27, 28, 29, 30, 31
            forecasts.append(_hourly((now + timedelta(days=day, hours=12)).isoformat(), temp=temp))
        
        result = AlertsGenerator.generate_alerts_next_days(forecasts, target_datetime=now)
        
        temp_alerts = [a for a in result if "TEMP" in a.code and ("DROP" in a.code or "RISE" in a.code)]
        assert len(temp_alerts) == 0

    def test_multiple_temperature_swings(self):
        """Deve escolher a maior variação quando há múltiplas oscilações"""
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        
        forecasts = [
            _hourly((now + timedelta(days=0, hours=12)).isoformat(), temp=30.0),
            _hourly((now + timedelta(days=1, hours=12)).isoformat(), temp=22.0),  # -8°C
            _hourly((now + timedelta(days=2, hours=12)).isoformat(), temp=29.0),  # +7°C
            _hourly((now + timedelta(days=3, hours=12)).isoformat(), temp=15.0),  # -14°C (maior)
        ]
        
        result = AlertsGenerator.generate_alerts_next_days(forecasts, target_datetime=now)
        
        temp_drop = [a for a in result if a.code == "TEMP_DROP"]
        # Deve ter apenas 1 (deduplicado), com a maior variação
        assert len(temp_drop) == 1
        assert abs(temp_drop[0].details["variation_c"]) >= 14.0

    def test_temperature_rise_severity(self):
        """Alerta TEMP_RISE deve ter severidade WARNING"""
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        
        forecasts = [
            _hourly((now + timedelta(hours=12)).isoformat(), temp=20.0),
            _hourly((now + timedelta(days=1, hours=12)).isoformat(), temp=35.0),
        ]
        
        result = AlertsGenerator.generate_alerts_next_days(forecasts, target_datetime=now)
        
        temp_rise = [a for a in result if a.code == "TEMP_RISE"]
        assert len(temp_rise) > 0
        assert temp_rise[0].severity == AlertSeverity.WARNING

    def test_temperature_drop_severity(self):
        """Alerta TEMP_DROP deve ter severidade INFO"""
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        
        forecasts = [
            _hourly((now + timedelta(hours=12)).isoformat(), temp=35.0),
            _hourly((now + timedelta(days=1, hours=12)).isoformat(), temp=20.0),
        ]
        
        result = AlertsGenerator.generate_alerts_next_days(forecasts, target_datetime=now)
        
        temp_drop = [a for a in result if a.code == "TEMP_DROP"]
        assert len(temp_drop) > 0
        assert temp_drop[0].severity == AlertSeverity.INFO

    def test_days_between_in_details(self):
        """Details deve incluir days_between"""
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        
        forecasts = [
            _hourly((now + timedelta(days=0, hours=12)).isoformat(), temp=30.0),
            _hourly((now + timedelta(days=2, hours=12)).isoformat(), temp=18.0),  # 2 dias depois
        ]
        
        result = AlertsGenerator.generate_alerts_next_days(forecasts, target_datetime=now)
        
        temp_drop = [a for a in result if a.code == "TEMP_DROP"]
        assert len(temp_drop) > 0
        assert "days_between" in temp_drop[0].details
        assert temp_drop[0].details["days_between"] == 2

    def test_temperature_analysis_with_naive_datetime(self):
        """Deve funcionar com datetime naive (sem timezone)"""
        naive_dt = datetime(2024, 7, 1, 12, 0, 0)
        
        forecasts = [
            _hourly("2024-07-01T14:00:00-03:00", temp=32.0),
            _hourly("2024-07-02T14:00:00-03:00", temp=20.0),
        ]
        
        result = AlertsGenerator.generate_alerts_next_days(forecasts, target_datetime=naive_dt)
        
        temp_alerts = [a for a in result if "TEMP" in a.code]
        assert len(temp_alerts) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
