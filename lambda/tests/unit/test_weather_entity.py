"""
Testes Unitários - Weather Entity (foco em serialização e métricas)
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from domain.alerts.primitives import AlertSeverity, WeatherAlert
from domain.entities.weather import Weather
from domain.constants import WeatherCondition


def test_to_api_response_converts_timezone_and_rounds():
    ts = datetime(2025, 11, 20, 15, 0)  # naive -> assume UTC antes de converter
    weather = Weather(
        city_id="3543204",
        city_name="Ribeirão Preto",
        timestamp=ts,
        temperature=28.56,
        humidity=65.4,
        wind_speed=15.24,
        rain_probability=45.0,
        rain_1h=2.55,
        rain_accumulated_day=3.21,
        description="céu limpo",
        feels_like=29.01,
        pressure=1013.7,
        visibility=9876.5,
        clouds=63.2,
        temp_min=21.11,
        temp_max=30.99,
    )

    api_response = weather.to_api_response()

    assert api_response["timestamp"].startswith("2025-11-20T12:00:00-03:00")
    assert api_response["temperature"] == 28.6
    assert api_response["humidity"] == 65.4
    assert api_response["windSpeed"] == 15.2
    assert api_response["rainVolumeHour"] == 2.5
    assert api_response["dailyRainAccumulation"] == 3.2
    assert api_response["feelsLike"] == 29.0
    assert api_response["pressure"] == 1013.7
    assert api_response["visibility"] == 9876
    assert api_response["cloudsDescription"] == "Nublado"


@pytest.mark.parametrize(
    "rain_1h, rain_prob, expected",
    [
        (0.0, 100.0, 0),
        (30.0, 100.0, 100),
        (15.0, 50.0, 1),
        (10.0, 60.0, 4),
    ],
)
def test_rainfall_intensity_metric(rain_1h, rain_prob, expected):
    weather = Weather(
        city_id="1",
        city_name="Test",
        timestamp=datetime.now(),
        temperature=20,
        humidity=80,
        wind_speed=5,
        rain_probability=rain_prob,
        rain_1h=rain_1h,
    )
    assert weather.rainfall_intensity == expected


def test_clouds_description_edges():
    base = dict(
        city_id="1",
        city_name="Test",
        timestamp=datetime.now(tz=ZoneInfo("UTC")),
        temperature=20,
        humidity=80,
        wind_speed=5,
    )
    assert Weather(clouds=5, rain_probability=0, rain_1h=0, **base).clouds_description == "Céu limpo"
    assert Weather(clouds=30, rain_probability=0, rain_1h=0, **base).clouds_description == "Parcialmente nublado"
    assert Weather(clouds=90, rain_probability=0, rain_1h=0, **base).clouds_description == "Céu encoberto"


def test_to_api_response_serializes_alerts():
    alert = WeatherAlert(
        code="STORM",
        severity=AlertSeverity.DANGER,
        description="Tempestade",
        timestamp=datetime(2025, 1, 1, 12, tzinfo=ZoneInfo("UTC")),
        details={"windSpeedKmh": 80},
    )
    weather = Weather(
        city_id="1",
        city_name="Alert City",
        timestamp=datetime.now(tz=ZoneInfo("UTC")),
        temperature=22,
        humidity=70,
        wind_speed=10,
        rain_probability=0,
        rain_1h=0,
        weather_alert=[alert],
    )

    resp = weather.to_api_response()
    assert resp["weatherAlert"] == [alert.to_dict()]


def test_weather_code_drizzle_with_intensity_rounding():
    weather = Weather(
        city_id="3543204",
        city_name="Ribeirão do Sul",
        timestamp=datetime.now(tz=ZoneInfo("America/Sao_Paulo")),
        temperature=20.0,
        humidity=80.0,
        wind_speed=5.0,
        rain_probability=70.0,
        rain_1h=0.6,  # ~1 de intensidade composta
        visibility=10000.0,
        clouds=90.0
    )

    assert weather.rainfall_intensity == 1  # arredondado
    assert weather.weather_code == WeatherCondition.LIGHT_DRIZZLE
    assert "Garoa" in weather.description
