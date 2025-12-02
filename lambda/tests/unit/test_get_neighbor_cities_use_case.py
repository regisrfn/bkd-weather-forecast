"""
Testes Unitários - AsyncGetNeighborCitiesUseCase (nova arquitetura)
"""
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from application.use_cases.get_neighbor_cities_use_case import AsyncGetNeighborCitiesUseCase
from domain.entities.city import City, NeighborCity
from domain.exceptions import CityNotFoundException, CoordinatesNotFoundException, InvalidRadiusException


@pytest.fixture
def city_repository():
    repo = MagicMock()
    return repo


@pytest.fixture
def use_case(city_repository):
    return AsyncGetNeighborCitiesUseCase(city_repository=city_repository)


@pytest.fixture
def center_city():
    return City(
        id="3543204",
        name="Ribeirão do Sul",
        state="SP",
        region="Sudeste",
        latitude=-22.7572,
        longitude=-49.9439
    )


@pytest.fixture
def nearby_cities():
    return [
        City(
            id="3550506",
            name="São Pedro do Turvo",
            state="SP",
            region="Sudeste",
            latitude=-22.8978,
            longitude=-49.7433
        ),
        City(
            id="3513504",
            name="Chavantes",
            state="SP",
            region="Sudeste",
            latitude=-23.0392,
            longitude=-49.7089
        ),
    ]


@pytest.fixture
def far_city():
    return City(
        id="3304557",
        name="Rio de Janeiro",
        state="RJ",
        region="Sudeste",
        latitude=-22.9068,
        longitude=-43.1729
    )


@pytest.mark.asyncio
async def test_execute_success_filters_and_sorts(use_case, city_repository, center_city, nearby_cities, far_city):
    city_repository.get_by_id.return_value = center_city
    city_repository.get_with_coordinates.return_value = [center_city] + nearby_cities + [far_city]

    result = await use_case.execute(center_city.id, 120.0)

    city_repository.get_with_coordinates.assert_called_once()
    assert result["centerCity"] == center_city
    assert all(isinstance(n, NeighborCity) for n in result["neighbors"])
    assert {n.city.id for n in result["neighbors"]} == {c.id for c in nearby_cities}
    distances = [n.distance for n in result["neighbors"]]
    assert distances == sorted(distances)


@pytest.mark.asyncio
async def test_execute_invalid_radius_raises(use_case, city_repository, center_city):
    city_repository.get_by_id.return_value = center_city
    with pytest.raises(InvalidRadiusException):
        await use_case.execute(center_city.id, 0.5)


@pytest.mark.asyncio
async def test_execute_city_not_found(use_case, city_repository):
    city_repository.get_by_id.return_value = None
    with pytest.raises(CityNotFoundException):
        await use_case.execute("0000000", 10.0)


@pytest.mark.asyncio
async def test_execute_missing_coordinates(use_case, city_repository):
    city_repository.get_by_id.return_value = City(
        id="1",
        name="Sem Coords",
        state="SP",
        region="Sudeste",
        latitude=None,
        longitude=None
    )
    with pytest.raises(CoordinatesNotFoundException):
        await use_case.execute("1", 10.0)


@pytest.mark.asyncio
async def test_execute_handles_no_neighbors(use_case, city_repository, center_city):
    city_repository.get_by_id.return_value = center_city
    city_repository.get_with_coordinates.return_value = [center_city]

    result = await use_case.execute(center_city.id, 20.0)

    assert result["neighbors"] == []

