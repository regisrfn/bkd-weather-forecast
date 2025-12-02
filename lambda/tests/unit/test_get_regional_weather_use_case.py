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
    provider.get_current_weather = AsyncMock()
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
    city_ids = ["1", "2", "missing"]
    city_repository.get_by_id.side_effect = [
        _make_city("1", -10, -50),
        _make_city("2", -11, -51),
        None
    ]
    weather_provider.get_current_weather.side_effect = [
        _make_weather("1"),
        RuntimeError("provider failure")
    ]

    result = await use_case.execute(city_ids)

    assert len(result) == 1
    assert result[0].city_id == "1"
    weather_provider.get_current_weather.assert_awaited()


@pytest.mark.asyncio
async def test_execute_raises_when_city_missing_coordinates(use_case, city_repository):
    bad_city = _make_city("3", None, None)
    city_repository.get_by_id.return_value = bad_city

    result = await use_case.execute([bad_city.id])
    assert result == []
