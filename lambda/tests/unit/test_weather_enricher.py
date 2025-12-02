"""
Testes Unitários - WeatherEnricher
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from domain.alerts.primitives import WeatherAlert, AlertSeverity
from domain.entities.hourly_forecast import HourlyForecast
from domain.entities.weather import Weather
from domain.services.weather_enricher import WeatherEnricher


def _base_weather() -> Weather:
    return Weather(
        city_id="1",
        city_name="Test City",
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=ZoneInfo("UTC")),
        temperature=30.0,
        humidity=50,
        wind_speed=5.0,
        rain_probability=10.0,
        rain_1h=0.0,
        description="base",
        feels_like=32.0,
        pressure=1015.0,
        visibility=9000,
        rain_accumulated_day=3.0,
        temp_min=28.0,
        temp_max=33.0,
        weather_alert=[],
    )


def test_enrich_with_closest_hourly_forecast():
    base = _base_weather()
    forecasts = [
        HourlyForecast(
            timestamp="2024-01-01T10:00:00-03:00",
            temperature=20.0,
            precipitation=0.0,
            precipitation_probability=5,
            rainfall_intensity=0.0,
            humidity=40,
            wind_speed=8.0,
            wind_direction=90,
            cloud_cover=10,
            weather_code=1,
            description="cool",
        ),
        HourlyForecast(
            timestamp="2024-01-01T12:15:00-03:00",
            temperature=22.5,
            precipitation=0.3,
            precipitation_probability=25,
            rainfall_intensity=0.0,
            humidity=60,
            wind_speed=12.0,
            wind_direction=135,
            cloud_cover=80,
            weather_code=61,
            description="rain coming",
        ),
    ]
    target = datetime(2024, 1, 1, 12, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))

    enriched = WeatherEnricher.enrich_with_hourly_data(base, forecasts, target)

    # Campos substituídos pelo forecast mais próximo
    assert enriched.temperature == 22.5
    assert enriched.humidity == 60
    assert enriched.wind_speed == 12.0
    assert enriched.wind_direction == 135
    assert enriched.rain_probability == 25
    assert enriched.rain_1h == 0.3
    assert enriched.description == "rain coming"
    assert enriched.weather_code == 61
    # Campos preservados do base_weather
    assert enriched.feels_like == base.feels_like
    assert enriched.pressure == base.pressure
    assert enriched.visibility == base.visibility
    assert enriched.rain_accumulated_day == base.rain_accumulated_day
    assert enriched.temp_min == base.temp_min
    assert enriched.temp_max == base.temp_max


def test_enrich_returns_base_when_no_hourly():
    base = _base_weather()
    result = WeatherEnricher.enrich_with_hourly_data(base, [], None)
    assert result is base


def test_merge_alerts_deduplicates_codes():
    base = _base_weather()
    existing = WeatherAlert(
        code="RAIN",
        severity=AlertSeverity.INFO,
        description="rain",
        timestamp=datetime.now(tz=ZoneInfo("UTC")),
    )
    base.weather_alert = [existing]

    new_alerts = [
        existing,
        WeatherAlert(
            code="WIND",
            severity=AlertSeverity.ALERT,
            description="vento",
            timestamp=datetime.now(tz=ZoneInfo("UTC")),
        ),
    ]

    merged = WeatherEnricher.merge_alerts(base, new_alerts)
    codes = {a.code for a in merged.weather_alert}
    assert codes == {"RAIN", "WIND"}
    assert len(merged.weather_alert) == 2

