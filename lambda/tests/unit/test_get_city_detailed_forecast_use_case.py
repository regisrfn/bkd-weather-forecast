"""
Testes Unitários - GetCityDetailedForecastUseCase
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from application.use_cases.get_city_detailed_forecast_use_case import GetCityDetailedForecastUseCase
from domain.alerts.primitives import WeatherAlert, AlertSeverity
from domain.entities.city import City
from domain.entities.daily_forecast import DailyForecast
from domain.entities.hourly_forecast import HourlyForecast
from domain.entities.weather import Weather
from domain.exceptions import CityNotFoundException
from domain.services import alerts_generator


def _make_city() -> City:
    return City(
        id="3543204",
        name="Ribeirão Preto",
        state="SP",
        region="Sudeste",
        latitude=-21.1704,
        longitude=-47.8103
    )


def _make_weather() -> Weather:
    return Weather(
        city_id="3543204",
        city_name="Ribeirão Preto",
        timestamp=datetime(2025, 11, 27, 15, 0, tzinfo=ZoneInfo("UTC")),
        temperature=28.0,
        humidity=60,
        wind_speed=12.0,
        rain_probability=10.0,
        description="céu limpo",
    )


def _make_daily() -> list[DailyForecast]:
    return [
        DailyForecast(
            date="2025-11-28",
            temp_min=20.0,
            temp_max=30.0,
            precipitation_mm=2.0,
            rain_probability=20.0,
                rainfall_intensity=0.0,
            wind_speed_max=15.0,
            wind_direction=90,
            uv_index=7.5,
            sunrise="06:00",
            sunset="18:00",
            precipitation_hours=1.0,
        )
    ]


def _make_hourly() -> list[HourlyForecast]:
    return [
        HourlyForecast(
            timestamp="2025-11-27T15:00:00-03:00",
            temperature=27.0,
            precipitation=0.2,
            precipitation_probability=15,
            rainfall_intensity=0.0,
            humidity=55,
            wind_speed=10.0,
            wind_direction=180,
            cloud_cover=20,
            weather_code=1,
            description="Claro",
        )
    ]


@pytest.fixture
def city_repository():
    return MagicMock()


@pytest.fixture
def weather_provider():
    provider = MagicMock()
    provider.provider_name = "OpenMeteoMock"
    provider.get_daily_forecast = AsyncMock()
    provider.get_hourly_forecast = AsyncMock()
    return provider


def _build_use_case(city_repository, weather_provider):
    return GetCityDetailedForecastUseCase(
        city_repository=city_repository,
        weather_provider=weather_provider,
    )


@pytest.mark.asyncio
async def test_execute_success_enriches_and_merges_alerts(city_repository, weather_provider):
    """
    Testa que o use case:
    - Chama os providers hourly e daily
    - Retorna ExtendedForecast com dados
    - Inclui daily e hourly forecasts
    """
    city_repository.get_by_id.return_value = _make_city()

    weather_provider.get_daily_forecast.return_value = _make_daily()
    weather_provider.get_hourly_forecast.return_value = _make_hourly()

    use_case = _build_use_case(city_repository, weather_provider)
    result = await use_case.execute("3543204")

    # Verificar estrutura do resultado
    assert result.current_weather is not None
    assert result.current_weather.city_id == "3543204"
    assert result.extended_available is True
    assert len(result.daily_forecasts) > 0
    assert len(result.hourly_forecasts) > 0
    
    weather_provider.get_daily_forecast.assert_called_once()
    weather_provider.get_hourly_forecast.assert_called_once()


@pytest.mark.asyncio
async def test_execute_continues_without_daily_data(monkeypatch, city_repository, weather_provider):
    city_repository.get_by_id.return_value = _make_city()
    weather_provider.get_daily_forecast.side_effect = RuntimeError("daily boom")
    weather_provider.get_hourly_forecast.return_value = _make_hourly()

    monkeypatch.setattr(
        alerts_generator.AlertsGenerator,
        "generate_alerts_for_weather",
        AsyncMock(return_value=[]),
    )

    use_case = _build_use_case(city_repository, weather_provider)
    result = await use_case.execute("3543204")

    assert result.extended_available is False
    assert result.daily_forecasts == []
    assert result.hourly_forecasts


@pytest.mark.asyncio
async def test_execute_raises_when_city_missing(city_repository, weather_provider):
    city_repository.get_by_id.return_value = None
    use_case = _build_use_case(city_repository, weather_provider)

    with pytest.raises(CityNotFoundException):
        await use_case.execute("0000000")
