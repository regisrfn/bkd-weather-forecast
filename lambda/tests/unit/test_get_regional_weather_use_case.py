"""
Testes Unitários - GetRegionalWeatherUseCase
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from infrastructure.adapters.output.providers.openmeteo.openmeteo_provider import OpenMeteoProvider
from application.use_cases.get_regional_weather_use_case import GetRegionalWeatherUseCase
from domain.entities.city import City
from domain.entities.weather import Weather
from domain.exceptions import CoordinatesNotFoundException


@pytest.fixture
def city_repository():
    return MagicMock()


@pytest.fixture
def weather_provider():
    provider = MagicMock()
    provider.provider_name = "MockProvider"
    provider.get_hourly_forecast = AsyncMock()
    provider.get_daily_forecast = AsyncMock()
    provider.extract_current_weather_from_hourly = OpenMeteoProvider.extract_current_weather_from_hourly
    return provider


@pytest.fixture
def use_case(city_repository, weather_provider):
    return GetRegionalWeatherUseCase(city_repository, weather_provider)


def _make_city(city_id: str, lat: float, lon: float) -> City:
    return City(
        id=city_id,
        name=f"City {city_id}",
        state="SP",
        region="Sudeste",
        latitude=lat,
        longitude=lon
    )


def _make_weather(city_id: str) -> Weather:
    return Weather(
        city_id=city_id,
        city_name=f"City {city_id}",
        timestamp=datetime.now(tz=ZoneInfo("UTC")),
        temperature=25.0,
        humidity=60,
        wind_speed=10.0
    )


@pytest.mark.asyncio
async def test_execute_returns_only_successful_results(use_case, city_repository, weather_provider):
    from domain.entities.hourly_forecast import HourlyForecast
    from domain.entities.daily_forecast import DailyForecast
    
    city_ids = ["1", "2", "missing"]
    city_repository.get_by_id.side_effect = [
        _make_city("1", -10, -50),  # Cidade 1 - sucesso
        _make_city("2", -11, -51),  # Cidade 2 - vai falhar no provider
        None  # Cidade "missing" - falha no repositório (não chama provider)
    ]
    
    # Mock hourly and daily forecasts
    sample_hourly = HourlyForecast(
        timestamp="2025-11-27T15:00:00",
        temperature=25.0,
        precipitation=0.0,
        precipitation_probability=30,
        rainfall_intensity=0.0,
        humidity=60,
        wind_speed=10.0,
        wind_direction=180,
        cloud_cover=20
    )
    
    sample_daily = DailyForecast(
        date="2025-11-27",
        temp_min=18.0,
        temp_max=32.0,
        precipitation_mm=0.0,
        rain_probability=30.0,
        rainfall_intensity=0.0,
        wind_speed_max=10.0,
        wind_direction=180,
        uv_index=8.0,
        sunrise="06:00:00",
        sunset="18:30:00",
        precipitation_hours=0.0
    )
    
    # Mock para retornar dados válidos sempre que chamado
    # Cada cidade que não falhar no repositório receberá esses dados
    # Forçar falha apenas na cidade 2
    async def mock_hourly(latitude, longitude, city_id, hours):
        if city_id == "2":
            raise RuntimeError("provider failure")
        return [sample_hourly]
    
    async def mock_daily(latitude, longitude, city_id, days):
        if city_id == "2":
            raise RuntimeError("provider failure")
        return [sample_daily]
    
    weather_provider.get_hourly_forecast = AsyncMock(side_effect=mock_hourly)
    weather_provider.get_daily_forecast = AsyncMock(side_effect=mock_daily)

    result = await use_case.execute(city_ids)

    assert len(result) == 1
    assert result[0].city_id == "1"
    weather_provider.get_hourly_forecast.assert_awaited()
    weather_provider.get_daily_forecast.assert_awaited()


@pytest.mark.asyncio
async def test_execute_raises_when_city_missing_coordinates(use_case, city_repository):
    bad_city = _make_city("3", None, None)
    city_repository.get_by_id.return_value = bad_city

    result = await use_case.execute([bad_city.id])
    assert result == []


@pytest.mark.asyncio
async def test_execute_sets_daily_aggregates(use_case, city_repository, weather_provider):
    from domain.entities.hourly_forecast import HourlyForecast
    from domain.entities.daily_forecast import DailyForecast

    city_repository.get_by_id.return_value = _make_city("9", -10, -50)

    hourly_forecasts = [
        HourlyForecast(
            timestamp="2025-11-27T12:00:00",
            temperature=25.0,
            precipitation=1.0,
            precipitation_probability=50,
            rainfall_intensity=20.0,
            humidity=60,
            wind_speed=12.0,
            wind_direction=100,
            cloud_cover=20
        ),
        HourlyForecast(
            timestamp="2025-11-27T15:00:00",
            temperature=26.0,
            precipitation=3.0,
            precipitation_probability=70,
            rainfall_intensity=60.0,
            humidity=58,
            wind_speed=15.0,
            wind_direction=120,
            cloud_cover=40
        ),
    ]

    daily_forecast = DailyForecast(
        date="2025-11-27",
        temp_min=18.0,
        temp_max=32.0,
        precipitation_mm=10.0,
        rain_probability=80.0,
        rainfall_intensity=70.0,
        wind_speed_max=25.0,
        wind_direction=180,
        uv_index=9.0,
        sunrise="06:00:00",
        sunset="18:30:00",
        precipitation_hours=4.0
    )

    weather_provider.get_hourly_forecast = AsyncMock(return_value=hourly_forecasts)
    weather_provider.get_daily_forecast = AsyncMock(return_value=[daily_forecast])

    target_dt = datetime(2025, 11, 27, 10, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    result = await use_case.execute(["9"], target_dt)

    assert len(result) == 1
    aggregates = result[0].daily_aggregates
    assert aggregates is not None
    assert aggregates.date == "2025-11-27"
    assert aggregates.rain_volume == pytest.approx(10.0)
    assert aggregates.rain_intensity_max == pytest.approx(70.0)
    assert aggregates.rain_probability_max == pytest.approx(80.0)
    assert aggregates.wind_speed_max == pytest.approx(25.0)
    assert aggregates.temp_min == pytest.approx(18.0)
    assert aggregates.temp_max == pytest.approx(32.0)
