"""
Testes Unitários - AsyncGetCityWeatherUseCase
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import pytest
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import AsyncMock, MagicMock

from application.use_cases.async_get_city_weather import AsyncGetCityWeatherUseCase
from domain.entities.city import City
from domain.entities.weather import Weather
from domain.exceptions import CityNotFoundException, CoordinatesNotFoundException


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
    return AsyncGetCityWeatherUseCase(
        city_repository=mock_city_repository,
        weather_repository=mock_weather_repository
    )


@pytest.fixture
def sample_city():
    """Cidade de exemplo"""
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
    """Weather entity de exemplo"""
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
class TestAsyncGetCityWeatherUseCase:
    """Testes para AsyncGetCityWeatherUseCase"""
    
    async def test_execute_success(
        self,
        use_case,
        mock_city_repository,
        mock_weather_repository,
        sample_city,
        sample_weather
    ):
        """Testa execução com sucesso"""
        mock_city_repository.get_by_id.return_value = sample_city
        mock_weather_repository.get_current_weather = AsyncMock(return_value=sample_weather)
        
        target_dt = datetime(2025, 11, 27, 15, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
        
        result = await use_case.execute("3543204", target_dt)
        
        assert isinstance(result, Weather)
        assert result.city_id == "3543204"
        assert result.city_name == "Ribeirão Preto"
        assert result.temperature == 28.5
        
        mock_city_repository.get_by_id.assert_called_once_with("3543204")
        mock_weather_repository.get_current_weather.assert_called_once()
    
    async def test_execute_without_target_datetime(
        self,
        use_case,
        mock_city_repository,
        mock_weather_repository,
        sample_city,
        sample_weather
    ):
        """Testa execução sem data alvo (próxima previsão)"""
        mock_city_repository.get_by_id.return_value = sample_city
        mock_weather_repository.get_current_weather = AsyncMock(return_value=sample_weather)
        
        result = await use_case.execute("3543204", None)
        
        assert isinstance(result, Weather)
        assert result.city_name == "Ribeirão Preto"
        
        # Verifica que foi chamado
        mock_weather_repository.get_current_weather.assert_called_once()
    
    async def test_execute_city_not_found(
        self,
        use_case,
        mock_city_repository
    ):
        """Testa exceção quando cidade não encontrada"""
        mock_city_repository.get_by_id.return_value = None
        
        with pytest.raises(CityNotFoundException) as exc_info:
            await use_case.execute("9999999")
        
        assert "City not found" in str(exc_info.value)
        assert exc_info.value.details["city_id"] == "9999999"
    
    async def test_execute_city_without_coordinates(
        self,
        use_case,
        mock_city_repository
    ):
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
            await use_case.execute("3543204")
        
        assert "City has no coordinates" in str(exc_info.value)
        assert exc_info.value.details["city_id"] == "3543204"
    
    async def test_execute_with_future_date(
        self,
        use_case,
        mock_city_repository,
        mock_weather_repository,
        sample_city,
        sample_weather
    ):
        """Testa execução com data futura (além do limite)"""
        mock_city_repository.get_by_id.return_value = sample_city
        mock_weather_repository.get_current_weather = AsyncMock(return_value=sample_weather)
        
        # Data além do dia 5
        target_dt = datetime(2025, 12, 10, 12, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
        
        result = await use_case.execute("3543204", target_dt)
        
        # Deve retornar com sucesso (última previsão)
        assert isinstance(result, Weather)
        assert result.city_name == "Ribeirão Preto"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
