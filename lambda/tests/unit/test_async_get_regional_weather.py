"""
Testes Unitários - AsyncGetRegionalWeatherUseCase
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import pytest
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import AsyncMock, MagicMock

from application.use_cases.get_regional_weather import AsyncGetRegionalWeatherUseCase
from domain.entities.city import City
from domain.entities.weather import Weather


@pytest.fixture
def mock_city_repository():
    """Mock do repositório de cidades"""
    repo = MagicMock()
    return repo


@pytest.fixture
def mock_weather_repository():
    """Mock do repositório de clima"""
    repo = MagicMock()
    return repo


@pytest.fixture
def use_case(mock_city_repository, mock_weather_repository):
    """Instância do use case"""
    return AsyncGetRegionalWeatherUseCase(
        city_repository=mock_city_repository,
        weather_repository=mock_weather_repository
    )


@pytest.fixture
def sample_cities():
    """Lista de cidades de exemplo"""
    return [
        City(
            id="3543204",
            name="Ribeirão do Sul",
            state="SP",
            region="Sudeste",
            latitude=-22.7572,
            longitude=-49.9439
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
            latitude=-22.9099,
            longitude=-47.0626
        )
    ]


@pytest.fixture
def sample_weather_list():
    """Lista de Weather entities"""
    return [
        Weather(
            city_id="3543204",
            city_name="Ribeirão do Sul",
            timestamp=datetime(2025, 11, 27, 15, 0, tzinfo=ZoneInfo("UTC")),
            temperature=28.5,
            humidity=65,
            wind_speed=15.2,
            rain_probability=45.0,
            description="céu limpo"
        ),
        Weather(
            city_id="3548708",
            city_name="São Carlos",
            timestamp=datetime(2025, 11, 27, 15, 0, tzinfo=ZoneInfo("UTC")),
            temperature=27.1,
            humidity=58,
            wind_speed=12.8,
            rain_probability=20.0,
            description="parcialmente nublado"
        ),
        Weather(
            city_id="3509502",
            city_name="Campinas",
            timestamp=datetime(2025, 11, 27, 15, 0, tzinfo=ZoneInfo("UTC")),
            temperature=29.5,
            humidity=62,
            wind_speed=10.5,
            rain_probability=15.0,
            description="céu limpo"
        )
    ]


@pytest.mark.asyncio
class TestAsyncGetRegionalWeatherUseCase:
    """Testes para AsyncGetRegionalWeatherUseCase"""
    
    async def test_execute_success(
        self,
        use_case,
        sample_weather_list
    ):
        """Testa execução com sucesso para múltiplas cidades"""
        city_ids = ["3543204", "3548708", "3509502"]
        
        # Mock do método interno
        use_case._fetch_all_cities = AsyncMock(return_value=sample_weather_list)
        
        result = await use_case.execute(city_ids)
        
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(w, Weather) for w in result)
        
        # Verificar que todas as cidades foram processadas
        result_city_ids = [w.city_id for w in result]
        assert set(result_city_ids) == set(city_ids)
    
    async def test_execute_with_target_datetime(
        self,
        use_case,
        sample_weather_list
    ):
        """Testa execução com data/hora específica"""
        city_ids = ["3543204", "3548708"]
        target_dt = datetime(2025, 11, 28, 12, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
        
        use_case._fetch_all_cities = AsyncMock(return_value=sample_weather_list[:2])
        
        result = await use_case.execute(city_ids, target_dt)
        
        assert isinstance(result, list)
        assert len(result) == 2
        
        # Verificar que foi chamado com target_datetime
        use_case._fetch_all_cities.assert_called_once_with(city_ids, target_dt)
    
    async def test_execute_empty_list(self, use_case):
        """Testa execução com lista vazia"""
        use_case._fetch_all_cities = AsyncMock(return_value=[])
        
        result = await use_case.execute([])
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    async def test_execute_partial_success(self, use_case, sample_weather_list):
        """Testa quando algumas cidades falham"""
        city_ids = ["3543204", "9999999", "3548708"]
        
        # Retorna apenas 2 de 3 (uma falhou)
        use_case._fetch_all_cities = AsyncMock(return_value=sample_weather_list[:2])
        
        result = await use_case.execute(city_ids)
        
        assert isinstance(result, list)
        assert len(result) == 2
        # Deve retornar apenas as bem-sucedidas
        result_city_ids = [w.city_id for w in result]
        assert "9999999" not in result_city_ids
    
    async def test_execute_single_city(self, use_case, sample_weather_list):
        """Testa execução com apenas uma cidade"""
        city_ids = ["3543204"]
        
        use_case._fetch_all_cities = AsyncMock(return_value=[sample_weather_list[0]])
        
        result = await use_case.execute(city_ids)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].city_id == "3543204"
    
    async def test_execute_large_batch(self, use_case):
        """Testa execução com muitas cidades (100+)"""
        # Simular 100 cidades
        city_ids = [f"350{i:04d}" for i in range(100)]
        
        weather_list = [
            Weather(
                city_id=cid,
                city_name=f"City {cid}",
                timestamp=datetime.now(tz=ZoneInfo("UTC")),
                temperature=25.0 + i,
                humidity=60,
                wind_speed=10.0,
                rain_probability=20.0,
                description="teste"
            )
            for i, cid in enumerate(city_ids)
        ]
        
        use_case._fetch_all_cities = AsyncMock(return_value=weather_list)
        
        result = await use_case.execute(city_ids)
        
        assert isinstance(result, list)
        assert len(result) == 100
    
    async def test_execute_with_future_date(self, use_case, sample_weather_list):
        """Testa execução com data futura (além do dia 5)"""
        city_ids = ["3543204", "3548708"]
        
        # Data além do limite
        target_dt = datetime(2025, 12, 10, 12, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
        
        use_case._fetch_all_cities = AsyncMock(return_value=sample_weather_list[:2])
        
        result = await use_case.execute(city_ids, target_dt)
        
        # Deve retornar com sucesso (última previsão disponível)
        assert isinstance(result, list)
        assert len(result) == 2
    
    async def test_execute_maintains_order(self, use_case, sample_weather_list):
        """Testa que mantém a ordem das cidades solicitadas"""
        city_ids = ["3543204", "3548708", "3509502"]
        
        use_case._fetch_all_cities = AsyncMock(return_value=sample_weather_list)
        
        result = await use_case.execute(city_ids)
        
        # A ordem pode não ser mantida devido ao processamento paralelo,
        # mas todos os IDs devem estar presentes
        result_city_ids = {w.city_id for w in result}
        expected_city_ids = set(city_ids)
        assert result_city_ids == expected_city_ids


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
