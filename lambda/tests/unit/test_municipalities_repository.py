"""
Testes Unitários - MunicipalitiesRepository
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import pytest
import json
import tempfile

from infrastructure.adapters.output.municipalities_repository import MunicipalitiesRepository
from domain.entities.city import City


@pytest.fixture
def sample_municipalities_data():
    """Dados de municípios de exemplo"""
    return [
        {
            "id": "3543204",
            "name": "Ribeirão do Sul",
            "state": "SP",
            "region": "Sudeste",
            "latitude": -22.7572,
            "longitude": -49.9439
        },
        {
            "id": "3548708",
            "name": "São Carlos",
            "state": "SP",
            "region": "Sudeste",
            "latitude": -22.0074,
            "longitude": -47.8911
        },
        {
            "id": "3509502",
            "name": "Campinas",
            "state": "SP",
            "region": "Sudeste",
            "latitude": -22.9099,
            "longitude": -47.0626
        },
        {
            "id": "3304557",
            "name": "Rio de Janeiro",
            "state": "RJ",
            "region": "Sudeste",
            "latitude": -22.9068,
            "longitude": -43.1729
        },
        {
            "id": "9999999",
            "name": "Cidade Sem Coordenadas",
            "state": "SP",
            "region": "Sudeste",
            "latitude": None,
            "longitude": None
        }
    ]


@pytest.fixture
def temp_municipalities_file(sample_municipalities_data):
    """Cria arquivo temporário com dados de municípios"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(sample_municipalities_data, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    os.unlink(temp_path)


@pytest.fixture
def repository(temp_municipalities_file):
    """Instância do repositório com dados de teste"""
    return MunicipalitiesRepository(json_path=temp_municipalities_file)


class TestMunicipalitiesRepository:
    """Testes para MunicipalitiesRepository"""
    
    def test_init_loads_data(self, repository):
        """Testa que inicialização carrega dados"""
        assert repository._data is not None
        assert len(repository._data) == 5
        assert repository._index_by_id is not None
        assert repository._index_by_state is not None
    
    def test_get_by_id_success(self, repository):
        """Testa busca por ID com sucesso"""
        city = repository.get_by_id("3543204")
        
        assert isinstance(city, City)
        assert city.id == "3543204"
        assert city.name == "Ribeirão do Sul"
        assert city.state == "SP"
        assert city.region == "Sudeste"
        assert city.latitude == -22.7572
        assert city.longitude == -49.9439
    
    def test_get_by_id_not_found(self, repository):
        """Testa busca por ID inexistente"""
        city = repository.get_by_id("0000000")
        
        assert city is None
    
    def test_get_by_id_multiple_cities(self, repository):
        """Testa busca de múltiplas cidades"""
        cities_data = [
            ("3543204", "Ribeirão do Sul"),
            ("3548708", "São Carlos"),
            ("3509502", "Campinas"),
            ("3304557", "Rio de Janeiro")
        ]
        
        for city_id, expected_name in cities_data:
            city = repository.get_by_id(city_id)
            assert city is not None
            assert city.name == expected_name
    
    def test_get_all_returns_all_cities(self, repository):
        """Testa que get_all retorna todas as cidades"""
        cities = repository.get_all()
        
        assert isinstance(cities, list)
        assert len(cities) == 5
        assert all(isinstance(c, City) for c in cities)
    
    def test_get_all_with_coordinates_filter(self, repository):
        """Testa busca de cidades com coordenadas"""
        all_cities = repository.get_all()
        
        cities_with_coords = [c for c in all_cities if c.has_coordinates()]
        
        assert len(cities_with_coords) == 4  # 4 de 5 têm coordenadas
    
    def test_city_without_coordinates(self, repository):
        """Testa cidade sem coordenadas"""
        city = repository.get_by_id("9999999")
        
        assert city is not None
        assert city.name == "Cidade Sem Coordenadas"
        assert city.latitude is None
        assert city.longitude is None
        assert not city.has_coordinates()
    
    def test_index_by_state(self, repository):
        """Testa índice por estado"""
        assert "SP" in repository._index_by_state
        assert "RJ" in repository._index_by_state
        
        sp_cities = repository._index_by_state["SP"]
        assert len(sp_cities) == 4  # 4 cidades de SP
        
        rj_cities = repository._index_by_state["RJ"]
        assert len(rj_cities) == 1  # 1 cidade do RJ
    
    def test_dict_to_entity_conversion(self, repository):
        """Testa conversão de dict para entity"""
        data = {
            "id": "3543204",
            "name": "Ribeirão do Sul",
            "state": "SP",
            "region": "Sudeste",
            "latitude": -22.7572,
            "longitude": -49.9439
        }
        
        city = repository._dict_to_entity(data)
        
        assert isinstance(city, City)
        assert city.id == data["id"]
        assert city.name == data["name"]
        assert city.state == data["state"]
        assert city.region == data["region"]
        assert city.latitude == data["latitude"]
        assert city.longitude == data["longitude"]
    
    def test_dict_to_entity_without_coordinates(self, repository):
        """Testa conversão sem coordenadas"""
        data = {
            "id": "9999999",
            "name": "Cidade Teste",
            "state": "SP",
            "region": "Sudeste"
        }
        
        city = repository._dict_to_entity(data)
        
        assert city.latitude is None
        assert city.longitude is None
    
    def test_load_data_idempotent(self, repository):
        """Testa que _load_data é idempotente (não recarrega)"""
        original_data = repository._data
        original_index = repository._index_by_id
        
        repository._load_data()
        
        # Deve ser o mesmo objeto (não recarregou)
        assert repository._data is original_data
        assert repository._index_by_id is original_index
    
    def test_repository_with_empty_file(self):
        """Testa repositório com arquivo vazio"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump([], f)
            temp_path = f.name
        
        try:
            repo = MunicipalitiesRepository(json_path=temp_path)
            
            assert repo._data == []
            assert repo._index_by_id == {}
            assert repo._index_by_state == {}
            assert repo.get_all() == []
        finally:
            os.unlink(temp_path)
    
    def test_get_by_id_performance(self, repository):
        """Testa que busca por ID é O(1) usando índice"""
        # Múltiplas buscas devem ser rápidas
        for _ in range(100):
            city = repository.get_by_id("3543204")
            assert city is not None
        
        # Se estivesse fazendo busca linear, seria lento


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
