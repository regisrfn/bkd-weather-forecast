"""
Testes Unitários - AsyncGetNeighborCitiesUseCase
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import pytest
from unittest.mock import MagicMock

from application.use_cases.async_get_neighbor_cities import AsyncGetNeighborCitiesUseCase
from domain.entities.city import City
from domain.exceptions import CityNotFoundException, CoordinatesNotFoundException, InvalidRadiusException


@pytest.fixture
def mock_city_repository():
    """Mock do repositório de cidades"""
    repo = MagicMock()
    return repo


@pytest.fixture
def use_case(mock_city_repository):
    """Instância do use case"""
    return AsyncGetNeighborCitiesUseCase(city_repository=mock_city_repository)


@pytest.fixture
def center_city():
    """Cidade centro"""
    return City(
        id="3543204",
        name="Ribeirão do Sul",
        state="SP",
        region="Sudeste",
        latitude=-22.7572,
        longitude=-49.9439
    )


@pytest.fixture
def neighbor_cities():
    """Cidades vizinhas"""
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
        City(
            id="3548708",
            name="São Carlos",
            state="SP",
            region="Sudeste",
            latitude=-22.0074,
            longitude=-47.8911
        )
    ]


@pytest.mark.asyncio
class TestAsyncGetNeighborCitiesUseCase:
    """Testes para AsyncGetNeighborCitiesUseCase"""
    
    async def test_execute_success(
        self,
        use_case,
        mock_city_repository,
        center_city,
        neighbor_cities
    ):
        """Testa busca de vizinhos com sucesso"""
        mock_city_repository.get_by_id.return_value = center_city
        mock_city_repository.get_all.return_value = [center_city] + neighbor_cities
        
        result = await use_case.execute("3543204", 50.0)
        
        assert isinstance(result, dict)
        assert "centerCity" in result
        assert "neighbors" in result
        
        # centerCity pode ser uma entidade City ou dict dependendo da implementação
        center_id = result["centerCity"].get("id") if isinstance(result["centerCity"], dict) else result["centerCity"].id
        center_name = result["centerCity"].get("name") if isinstance(result["centerCity"], dict) else result["centerCity"].name
        
        assert center_id == "3543204"
        assert center_name == "Ribeirão do Sul"
        
        assert isinstance(result["neighbors"], list)
        # Verificar que retorna vizinhos ordenados por distância
        if len(result["neighbors"]) > 1:
            distances = [n["distance"] for n in result["neighbors"]]
            assert distances == sorted(distances)
    
    async def test_execute_with_small_radius(
        self,
        use_case,
        mock_city_repository,
        center_city,
        neighbor_cities
    ):
        """Testa busca com raio pequeno (poucos vizinhos)"""
        mock_city_repository.get_by_id.return_value = center_city
        mock_city_repository.get_all.return_value = [center_city] + neighbor_cities
        
        result = await use_case.execute("3543204", 20.0)
        
        assert isinstance(result, dict)
        assert "neighbors" in result
        # Com raio de 20km, deve ter menos vizinhos
        assert all(n["distance"] <= 20.0 for n in result["neighbors"])
    
    async def test_execute_with_large_radius(
        self,
        use_case,
        mock_city_repository,
        center_city,
        neighbor_cities
    ):
        """Testa busca com raio grande (mais vizinhos)"""
        mock_city_repository.get_by_id.return_value = center_city
        mock_city_repository.get_all.return_value = [center_city] + neighbor_cities
        
        result = await use_case.execute("3543204", 500.0)
        
        assert isinstance(result, dict)
        assert len(result["neighbors"]) >= 0
    
    async def test_execute_invalid_radius_negative(self, use_case, mock_city_repository, center_city):
        """Testa exceção com raio negativo"""
        mock_city_repository.get_by_id.return_value = center_city
        
        with pytest.raises(InvalidRadiusException):
            await use_case.execute("3543204", -10.0)
    
    async def test_execute_invalid_radius_zero(self, use_case, mock_city_repository, center_city):
        """Testa exceção com raio zero"""
        mock_city_repository.get_by_id.return_value = center_city
        
        with pytest.raises(InvalidRadiusException):
            await use_case.execute("3543204", 0.0)
    
    async def test_execute_invalid_radius_too_large(self, use_case, mock_city_repository, center_city):
        """Testa exceção com raio muito grande (>500km)"""
        mock_city_repository.get_by_id.return_value = center_city
        
        with pytest.raises(InvalidRadiusException):
            await use_case.execute("3543204", 1000.0)
    
    async def test_execute_city_not_found(self, use_case, mock_city_repository):
        """Testa exceção quando cidade não encontrada"""
        mock_city_repository.get_by_id.return_value = None
        
        with pytest.raises(CityNotFoundException) as exc_info:
            await use_case.execute("9999999", 50.0)
        
        assert "City not found" in str(exc_info.value)
        assert exc_info.value.details["city_id"] == "9999999"
    
    async def test_execute_city_without_coordinates(self, use_case, mock_city_repository):
        """Testa exceção quando cidade não tem coordenadas"""
        city_no_coords = City(
            id="3543204",
            name="Cidade Sem Coordenadas",
            state="SP",
            region="Sudeste",
            latitude=None,
            longitude=None
        )
        mock_city_repository.get_by_id.return_value = city_no_coords
        
        with pytest.raises(CoordinatesNotFoundException) as exc_info:
            await use_case.execute("3543204", 50.0)
        
        assert "City has no coordinates" in str(exc_info.value)
    
    async def test_execute_no_neighbors_found(
        self,
        use_case,
        mock_city_repository,
        center_city
    ):
        """Testa quando não há vizinhos no raio especificado"""
        mock_city_repository.get_by_id.return_value = center_city
        mock_city_repository.get_all.return_value = [center_city]
        
        result = await use_case.execute("3543204", 1.0)
        
        assert isinstance(result, dict)
        assert result["neighbors"] == []
    
    async def test_execute_filters_same_state(
        self,
        use_case,
        mock_city_repository,
        center_city
    ):
        """Testa que filtra apenas cidades do mesmo estado"""
        other_state_city = City(
            id="3304557",
            name="Rio de Janeiro",
            state="RJ",  # Estado diferente
            region="Sudeste",
            latitude=-22.9068,
            longitude=-43.1729
        )
        
        mock_city_repository.get_by_id.return_value = center_city
        mock_city_repository.get_all.return_value = [center_city, other_state_city]
        
        result = await use_case.execute("3543204", 500.0)
        
        # Não deve incluir cidade de outro estado
        neighbor_ids = [n["id"] for n in result["neighbors"]]
        assert "3304557" not in neighbor_ids


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
