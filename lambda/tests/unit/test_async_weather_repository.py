"""
Testes Unitários - AsyncOpenWeatherRepository (Refactored)
Tests now focus on API communication and cache coordination
Helper methods are tested separately in their own test files
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import pytest
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import AsyncMock, MagicMock, patch
from infrastructure.adapters.output.async_weather_repository import AsyncOpenWeatherRepository
from domain.entities.weather import Weather


@pytest.fixture
def test_data():
    """Carrega test-data.json"""
    test_data_path = os.path.join(os.path.dirname(__file__), 'test-data.json')
    with open(test_data_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def mock_cache():
    """Mock do cache DynamoDB"""
    cache = MagicMock()
    cache.is_enabled.return_value = True
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    return cache


@pytest.fixture
def repository(mock_cache):
    """Instância do repositório com mock de cache"""
    repo = AsyncOpenWeatherRepository(
        api_key="test_api_key",
        cache=mock_cache
    )
    return repo


class TestProcessWeatherData:
    """Testes para método _process_weather_data (delegation to processor)"""
    
    def test_process_weather_data_success(self, repository, test_data):
        """Testa processamento de dados de clima com sucesso"""
        city_name = "Ibirarema"
        target_dt = datetime(2025, 11, 27, 15, 0, tzinfo=ZoneInfo("UTC"))
        
        weather = repository._process_weather_data(test_data, city_name, target_dt)
        
        assert isinstance(weather, Weather)
        assert weather.city_name == city_name
        assert weather.temperature > 0
        assert 0 <= weather.humidity <= 100
        assert weather.wind_speed >= 0
        assert 0 <= weather.rain_probability <= 100
        assert isinstance(weather.description, str)
        assert isinstance(weather.weather_alert, list)
    
    def test_process_weather_data_with_rain(self, repository, test_data):
        """Testa processamento de previsão com chuva"""
        city_name = "Ibirarema"
        # Última previsão tem chuva (dt: 1764601200)
        target_dt = datetime(2025, 12, 1, 15, 0, tzinfo=ZoneInfo("UTC"))
        
        weather = repository._process_weather_data(test_data, city_name, target_dt)
        
        assert isinstance(weather, Weather)
        assert weather.rain_probability > 0
        assert weather.description == "chuva leve"
        assert weather.weather_code == 500
    
    def test_process_weather_data_no_target_datetime(self, repository, test_data):
        """Testa processamento sem data alvo (próxima previsão)"""
        city_name = "Ibirarema"
        
        weather = repository._process_weather_data(test_data, city_name, None)
        
        assert isinstance(weather, Weather)
        assert weather.city_name == city_name
        assert weather.timestamp is not None


@pytest.mark.asyncio
class TestAsyncMethods:
    """Testes para métodos assíncronos"""
    
    async def test_batch_save_weather_to_cache_success(self, repository, mock_cache):
        """Testa salvamento em batch no cache"""
        weather_data_list = [
            ("key1", {"data": "value1"}),
            ("key2", {"data": "value2"})
        ]
        
        mock_cache.batch_set = AsyncMock(return_value={"key1": True, "key2": True})
        
        results = await repository.batch_save_weather_to_cache(weather_data_list)
        
        assert results == {"key1": True, "key2": True}
        mock_cache.batch_set.assert_called_once()
    
    async def test_batch_save_weather_cache_disabled(self, repository, mock_cache):
        """Testa salvamento quando cache está desabilitado"""
        mock_cache.is_enabled.return_value = False
        
        weather_data_list = [("key1", {"data": "value1"})]
        
        results = await repository.batch_save_weather_to_cache(weather_data_list)
        
        assert results == {"key1": False}
    
    async def test_batch_get_weather_from_cache(self, repository, mock_cache):
        """Testa busca em batch no cache"""
        city_ids = ["3543204", "3548708"]
        expected_results = {
            "3543204": {"temp": 25.0},
            "3548708": {"temp": 28.0}
        }
        
        mock_cache.batch_get = AsyncMock(return_value=expected_results)
        
        results = await repository.batch_get_weather_from_cache(city_ids)
        
        assert results == expected_results
        mock_cache.batch_get.assert_called_once_with(city_ids)
    
    async def test_batch_get_weather_cache_disabled(self, repository, mock_cache):
        """Testa busca quando cache está desabilitado"""
        mock_cache.is_enabled.return_value = False
        
        results = await repository.batch_get_weather_from_cache(["3543204"])
        
        assert results == {}


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

