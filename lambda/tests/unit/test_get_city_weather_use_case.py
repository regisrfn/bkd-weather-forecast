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


@pytest.mark.asyncio
async def test_execute_success(use_case, city_repository, weather_provider, sample_city, sample_weather):
    city_repository.get_by_id.return_value = sample_city
    weather_provider.get_current_weather.return_value = sample_weather

    target = datetime(2025, 11, 27, 15, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))

    result = await use_case.execute("3543204", target)

    assert isinstance(result, Weather)
    assert result.city_id == "3543204"
    assert result.city_name == "Ribeirão Preto"
    weather_provider.get_current_weather.assert_awaited_once_with(
        latitude=sample_city.latitude,
        longitude=sample_city.longitude,
        city_id=sample_city.id,
        city_name=sample_city.name,
        target_datetime=target
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
    weather_provider.get_current_weather.side_effect = RuntimeError("provider boom")

    with pytest.raises(RuntimeError):
        await use_case.execute(sample_city.id)

