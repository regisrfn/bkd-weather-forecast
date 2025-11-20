"""
Testes Unitários - Use Case GetNeighborCities
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambda'))

import pytest
from unittest.mock import Mock
from application.use_cases.get_neighbor_cities import GetNeighborCitiesUseCase
from domain.entities.city import City


class MockCityRepository:
    """Mock do repositório de cidades para testes"""
    
    def get_by_id(self, city_id: str):
        if city_id == "3543204":
            return City(
                id="3543204",
                name="Ribeirão Preto",
                state="SP",
                region="Sudeste",
                latitude=-21.1704,
                longitude=-47.8103
            )
        return None
    
    def get_with_coordinates(self):
        return [
            City(
                id="3543204",
                name="Ribeirão Preto",
                state="SP",
                region="Sudeste",
                latitude=-21.1704,
                longitude=-47.8103
            ),
            City(
                id="3548708",
                name="São Carlos",
                state="SP",
                region="Sudeste",
                latitude=-22.0074,
                longitude=-47.8911
            ),
            City(
                id="3509502",
                name="Campinas",
                state="SP",
                region="Sudeste",
                latitude=-22.9056,
                longitude=-47.0608
            )
        ]


def test_get_neighbor_cities_success():
    """Testa busca de vizinhos com sucesso"""
    repository = MockCityRepository()
    use_case = GetNeighborCitiesUseCase(repository)
    
    result = use_case.execute("3543204", radius=150)
    
    assert 'centerCity' in result
    assert 'neighbors' in result
    assert result['centerCity'].id == "3543204"
    assert result['centerCity'].name == "Ribeirão Preto"
    assert isinstance(result['neighbors'], list)
    # Deve ter pelo menos 1 vizinho (São Carlos está a ~95km)
    assert len(result['neighbors']) >= 1


def test_get_neighbor_cities_city_not_found():
    """Testa erro quando cidade não encontrada"""
    repository = MockCityRepository()
    use_case = GetNeighborCitiesUseCase(repository)
    
    with pytest.raises(ValueError, match="não encontrada"):
        use_case.execute("9999999", radius=50)


def test_get_neighbor_cities_invalid_radius():
    """Testa erro com raio inválido"""
    repository = MockCityRepository()
    use_case = GetNeighborCitiesUseCase(repository)
    
    with pytest.raises(ValueError, match="Raio deve estar entre"):
        use_case.execute("3543204", radius=1000)  # Raio muito grande


def test_get_neighbor_cities_sorting():
    """Testa ordenação dos vizinhos por distância"""
    repository = MockCityRepository()
    use_case = GetNeighborCitiesUseCase(repository)
    
    result = use_case.execute("3543204", radius=150)
    neighbors = result['neighbors']
    
    # Verificar se está ordenado por distância crescente
    for i in range(len(neighbors) - 1):
        assert neighbors[i].distance <= neighbors[i + 1].distance


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
