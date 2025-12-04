"""
Testes Unitários - AsyncGetCityWeatherUseCase (nova arquitetura)
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import AsyncMock, MagicMock

import pytest

# Garantir que o pacote lambda/ esteja no PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from application.use_cases.get_city_weather_use_case import AsyncGetCityWeatherUseCase
from domain.entities.city import City
from domain.entities.weather import Weather
from domain.exceptions import CityNotFoundException, CoordinatesNotFoundException


@pytest.fixture
def city_repository():
    repo = MagicMock()
    return repo


@pytest.fixture
def weather_provider():
    provider = MagicMock()
    provider.provider_name = "MockProvider"
    provider.supports_current_weather = True
    provider.get_current_weather = AsyncMock()
    provider.get_hourly_forecast = AsyncMock()
    provider.get_daily_forecast = AsyncMock()
    return provider


@pytest.fixture
def use_case(city_repository, weather_provider):
    return AsyncGetCityWeatherUseCase(
        city_repository=city_repository,
        weather_provider=weather_provider
    )


@pytest.fixture
def sample_city():
    return City(
        id="3543204",
        name="Ribeirão Preto",
        state="SP",
        region="Sudeste",
        latitude=-21.1704,
        longitude=-47.8103
    )


@pytest.fixture
def sample_weather():
    return Weather(
        city_id="3543204",
        city_name="Ribeirão Preto",
        timestamp=datetime(2025, 11, 27, 15, 0, tzinfo=ZoneInfo("UTC")),
        temperature=28.5,
        humidity=65,
        wind_speed=15.2,
        rain_probability=45.0,
        description="céu limpo"
    )


@pytest.fixture
def sample_hourly_forecast():
    from domain.entities.hourly_forecast import HourlyForecast
    return HourlyForecast(
        timestamp="2025-11-27T15:00:00",
        temperature=28.5,
        precipitation=0.0,
        precipitation_probability=45,
        rainfall_intensity=0.0,
        humidity=65,
        wind_speed=15.2,
        wind_direction=180,
        cloud_cover=20,
        weather_code=0,
        description="céu limpo"
    )


@pytest.fixture
def sample_daily_forecast():
    from domain.entities.daily_forecast import DailyForecast
    return DailyForecast(
        date="2025-11-27",
        temp_min=18.0,
        temp_max=32.0,
        precipitation_mm=0.0,
        rain_probability=45.0,
        rainfall_intensity=0.0,
        wind_speed_max=15.2,
        wind_direction=180,
        uv_index=8.5,
        sunrise="06:00:00",
        sunset="18:30:00",
        precipitation_hours=0.0
    )


@pytest.mark.asyncio
async def test_execute_success(use_case, city_repository, weather_provider, sample_city, sample_hourly_forecast, sample_daily_forecast):
    city_repository.get_by_id.return_value = sample_city
    weather_provider.get_hourly_forecast.return_value = [sample_hourly_forecast]
    weather_provider.get_daily_forecast.return_value = [sample_daily_forecast]

    target = datetime(2025, 11, 27, 15, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))

    result = await use_case.execute("3543204", target)

    assert isinstance(result, Weather)
    assert result.city_id == "3543204"
    assert result.city_name == "Ribeirão Preto"
    weather_provider.get_hourly_forecast.assert_awaited_once_with(
        latitude=sample_city.latitude,
        longitude=sample_city.longitude,
        city_id=sample_city.id,
        hours=168
    )
    weather_provider.get_daily_forecast.assert_awaited_once_with(
        latitude=sample_city.latitude,
        longitude=sample_city.longitude,
        city_id=sample_city.id,
        days=7
    )


@pytest.mark.asyncio
async def test_execute_city_not_found_raises(use_case, city_repository):
    city_repository.get_by_id.return_value = None

    with pytest.raises(CityNotFoundException):
        await use_case.execute("9999999")


@pytest.mark.asyncio
async def test_execute_missing_coordinates_raises(use_case, city_repository):
    city_without_coords = City(
        id="123",
        name="Sem Coordenadas",
        state="SP",
        region="Sudeste",
        latitude=None,
        longitude=None
    )
    city_repository.get_by_id.return_value = city_without_coords

    with pytest.raises(CoordinatesNotFoundException):
        await use_case.execute("123")


@pytest.mark.asyncio
async def test_execute_propagates_provider_error(use_case, city_repository, weather_provider, sample_city):
    city_repository.get_by_id.return_value = sample_city
    weather_provider.get_hourly_forecast.side_effect = RuntimeError("provider boom")

    with pytest.raises(RuntimeError):
        await use_case.execute(sample_city.id)

