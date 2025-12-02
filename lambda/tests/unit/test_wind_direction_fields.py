"""
Testes Unitários - Validação dos Campos de Direção do Vento
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from domain.entities.hourly_forecast import HourlyForecast
from domain.entities.weather import Weather


class TestWindDirectionFields:
    """Valida uso correto dos campos de direção do vento"""

    def test_hourly_forecast_uses_wind_direction_10m(self):
        hourly = HourlyForecast(
            timestamp="2024-01-01T00:00:00-03:00",
            temperature=25.0,
            precipitation=0.0,
            precipitation_probability=10,
            rainfall_intensity=0.0,
            humidity=70,
            wind_speed=15.0,
            wind_direction=225,
            cloud_cover=30,
            weather_code=2,
        )

        assert hourly.wind_direction == 225
        api_response = hourly.to_api_response()
        assert api_response["windDirection"] == 225

    def test_weather_entity_has_wind_direction(self):
        weather = Weather(
            city_id="123",
            city_name="Test City",
            timestamp=datetime.now(tz=ZoneInfo("UTC")),
            temperature=28.5,
            humidity=65,
            wind_speed=20.0,
            wind_direction=135,
            rain_probability=25.0,
            rain_1h=0.5,
            rain_accumulated_day=2.5,
            description="Partly cloudy",
            feels_like=30.0,
            pressure=1013,
            visibility=10000,
            clouds=40,
            weather_alert=[],
            weather_code=801,
            temp_min=22.0,
            temp_max=32.0,
        )

        assert weather.wind_direction == 135
        assert weather.to_api_response()["windDirection"] == 135

    @pytest.mark.parametrize("degrees", [0, 45, 90, 135, 180, 225, 270, 315, 360])
    def test_wind_direction_range_validation(self, degrees):
        hourly = HourlyForecast(
            timestamp="2024-01-01T00:00:00-03:00",
            temperature=25.0,
            precipitation=0.0,
            precipitation_probability=10,
            rainfall_intensity=0.0,
            humidity=70,
            wind_speed=15.0,
            wind_direction=degrees,
            cloud_cover=30,
            weather_code=2,
        )
        assert 0 <= hourly.wind_direction <= 360

