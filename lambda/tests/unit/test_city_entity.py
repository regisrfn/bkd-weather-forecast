"""
Testes Unitários - Domain Entities (City)
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from domain.entities.city import City, NeighborCity


def test_city_creation():
    """Testa criação de entidade City"""
    city = City(
        id="3543204",
        name="Ribeirão Preto",
        state="SP",
        region="Sudeste",
        latitude=-21.1704,
        longitude=-47.8103
    )
    
    assert city.id == "3543204"
    assert city.name == "Ribeirão Preto"
    assert city.state == "SP"
    assert city.region == "Sudeste"
    assert city.latitude == -21.1704
    assert city.longitude == -47.8103


def test_city_has_coordinates():
    """Testa validação de coordenadas"""
    city_with_coords = City(
        id="3543204",
        name="Ribeirão Preto",
        state="SP",
        region="Sudeste",
        latitude=-21.1704,
        longitude=-47.8103
    )
    
    city_without_coords = City(
        id="9999999",
        name="Cidade Sem Coordenadas",
        state="SP",
        region="Sudeste",
        latitude=None,
        longitude=None
    )
    
    assert city_with_coords.has_coordinates() is True
    assert city_without_coords.has_coordinates() is False


def test_city_to_api_response():
    """Testa conversão de City para formato API"""
    city = City(
        id="3543204",
        name="Ribeirão Preto",
        state="SP",
        region="Sudeste",
        latitude=-21.1704,
        longitude=-47.8103
    )
    
    api_response = city.to_api_response()
    
    assert api_response['id'] == "3543204"
    assert api_response['name'] == "Ribeirão Preto"
    assert api_response['latitude'] == -21.1704
    assert api_response['longitude'] == -47.8103


def test_neighbor_city_creation():
    """Testa criação de NeighborCity"""
    city = City(
        id="3548708",
        name="São Carlos",
        state="SP",
        region="Sudeste",
        latitude=-22.0074,
        longitude=-47.8911
    )
    
    neighbor = NeighborCity(city=city, distance=95.5)
    
    assert neighbor.city.id == "3548708"
    assert neighbor.city.name == "São Carlos"
    assert neighbor.distance == 95.5


def test_neighbor_city_to_api_response():
    """Testa conversão de NeighborCity para formato API"""
    city = City(
        id="3548708",
        name="São Carlos",
        state="SP",
        region="Sudeste",
        latitude=-22.0074,
        longitude=-47.8911
    )
    
    neighbor = NeighborCity(city=city, distance=95.5)
    api_response = neighbor.to_api_response()
    
    assert api_response['id'] == "3548708"
    assert api_response['name'] == "São Carlos"
    assert api_response['distance'] == 95.5
    assert api_response['latitude'] == -22.0074
    assert api_response['longitude'] == -47.8911


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
