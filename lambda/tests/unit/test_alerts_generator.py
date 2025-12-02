"""
Testes Unitários - AlertsGenerator
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from domain.alerts.primitives import WeatherAlert, AlertSeverity
from domain.entities.hourly_forecast import HourlyForecast
from domain.services import alerts_generator
from domain.services.alerts_generator import AlertsGenerator


def _hourly(ts: str, temp: float = 25.0, code: int = 61) -> HourlyForecast:
    return HourlyForecast(
        timestamp=ts,
        temperature=temp,
        precipitation=1.0,
        precipitation_probability=80,
        humidity=60,
        wind_speed=10.0,
        wind_direction=180,
        cloud_cover=50,
        weather_code=code,
        description="chuva",
    )


def test_generate_all_alerts_deduplicates_and_sets_rain_end(monkeypatch):
    forecasts = [
        _hourly("2024-01-01T10:00:00-03:00"),
        _hourly("2024-01-01T11:00:00-03:00"),
    ]

    def fake_generate_alerts(*, weather_code, rain_prob, wind_speed, forecast_time, **kwargs):
        return [
            WeatherAlert(
                code="HEAVY_RAIN",
                severity=AlertSeverity.ALERT,
                description="chuva forte",
                timestamp=forecast_time,
                details={"rain_prob": rain_prob},
            )
        ]

    monkeypatch.setattr(alerts_generator.WeatherAlertOrchestrator, "generate_alerts", fake_generate_alerts)

    alerts = AlertsGenerator.generate_all_alerts(forecasts, target_datetime=datetime(2024, 1, 1, 9, tzinfo=ZoneInfo("America/Sao_Paulo")))

    assert len(alerts) == 1  # dedupe pelo code
    rain_alert = alerts[0]
    assert rain_alert.code == "HEAVY_RAIN"
    assert "rain_ends_at" in rain_alert.details
    assert rain_alert.details["rain_ends_at"].endswith("12:00:00-03:00")


def test_generate_all_alerts_includes_temperature_trends(monkeypatch):
    forecasts = [
        _hourly("2024-01-01T09:00:00-03:00", temp=32.0, code=1),
        _hourly("2024-01-02T09:00:00-03:00", temp=20.0, code=1),
        _hourly("2024-01-03T09:00:00-03:00", temp=35.0, code=1),
    ]

    # Evitar alertas básicos interferindo
    monkeypatch.setattr(alerts_generator.WeatherAlertOrchestrator, "generate_alerts", lambda **_: [])

    alerts = AlertsGenerator.generate_all_alerts(
        forecasts,
        target_datetime=datetime(2023, 12, 31, 12, tzinfo=ZoneInfo("America/Sao_Paulo")),
    )
    codes = {a.code for a in alerts}
    assert "TEMP_DROP" in codes
    assert "TEMP_RISE" in codes


def test_generate_all_alerts_returns_empty_for_past_forecasts(monkeypatch):
    monkeypatch.setattr(alerts_generator.WeatherAlertOrchestrator, "generate_alerts", lambda **_: [])
    past_forecast = _hourly("2020-01-01T00:00:00-03:00")

    result = AlertsGenerator.generate_all_alerts([past_forecast], target_datetime=datetime(2024, 1, 1, tzinfo=ZoneInfo("America/Sao_Paulo")))
    assert result == []

