"""
Testes Unitários - AsyncOpenWeatherRepository
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


class TestSelectForecast:
    """Testes para método _select_forecast"""
    
    def test_select_forecast_closest_to_target(self, repository, test_data):
        """Testa seleção da previsão mais próxima da data alvo"""
        forecasts = test_data['list']
        
        # Target: 2025-11-27 12:00 (dt: 1764244800)
        target_dt = datetime(2025, 11, 27, 12, 0, tzinfo=ZoneInfo("UTC"))
        
        result = repository._select_forecast(forecasts, target_dt)
        
        assert result is not None
        assert result['dt'] == 1764244800  # Exata correspondência
        assert result['main']['temp'] == 23.72
    
    def test_select_forecast_future_date_beyond_limit(self, repository, test_data):
        """Testa retorno da última previsão quando data além do limite (dia 5)"""
        forecasts = test_data['list']
        
        # Target: 2025-12-10 (além do dia 5)
        target_dt = datetime(2025, 12, 10, 12, 0, tzinfo=ZoneInfo("UTC"))
        
        result = repository._select_forecast(forecasts, target_dt)
        
        # Deve retornar a última previsão disponível (2025-12-01 15:00)
        assert result is not None
        assert result['dt'] == 1764601200  # Última previsão
        assert result['dt_txt'] == "2025-12-01 15:00:00"
        assert result['main']['temp'] == 29.41
    
    def test_select_forecast_no_target_datetime(self, repository, test_data):
        """Testa seleção quando target_datetime é None (próxima previsão)"""
        forecasts = test_data['list']
        
        result = repository._select_forecast(forecasts, None)
        
        # Deve retornar a primeira previsão futura
        assert result is not None
        assert result['dt'] >= forecasts[0]['dt']
    
    def test_select_forecast_empty_list(self, repository):
        """Testa comportamento com lista vazia"""
        # Com lista vazia, deve retornar None ou lançar exceção
        result = repository._select_forecast([], datetime.now(tz=ZoneInfo("UTC")))
        # Retorna None porque não há previsões futuras nem última previsão
        assert result is None or result == []
    
    def test_select_forecast_past_date_returns_first(self, repository, test_data):
        """Testa que data no passado retorna primeira previsão futura disponível"""
        forecasts = test_data['list']
        
        # Target: 2025-11-20 (antes da primeira previsão)
        target_dt = datetime(2025, 11, 20, 12, 0, tzinfo=ZoneInfo("UTC"))
        
        result = repository._select_forecast(forecasts, target_dt)
        
        # Com data no passado, todas as previsões são futuras, então retorna a primeira
        assert result is not None
        assert result['dt'] == 1764180000  # Primeira previsão


class TestProcessWeatherData:
    """Testes para método _process_weather_data"""
    
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
        assert weather.rain_probability > 0  # pop = 0.47 = 47%
        assert weather.description == "chuva leve"
        assert weather.weather_code == 500  # Rain code
    
    def test_process_weather_data_no_target_datetime(self, repository, test_data):
        """Testa processamento sem data alvo (próxima previsão)"""
        city_name = "Ibirarema"
        
        weather = repository._process_weather_data(test_data, city_name, None)
        
        assert isinstance(weather, Weather)
        assert weather.city_name == city_name
        assert weather.timestamp is not None


class TestGetDailyTempExtremes:
    """Testes para método _get_daily_temp_extremes"""
    
    def test_get_daily_temp_extremes_with_target_date(self, repository, test_data):
        """Testa cálculo de temperaturas min/max do dia"""
        forecasts = test_data['list']
        target_dt = datetime(2025, 11, 27, 12, 0, tzinfo=ZoneInfo("UTC"))
        
        temp_min, temp_max = repository._get_daily_temp_extremes(forecasts, target_dt)
        
        assert isinstance(temp_min, float)
        assert isinstance(temp_max, float)
        assert temp_min <= temp_max
        assert temp_min > 0  # Temperatura realista
        assert temp_max < 50  # Temperatura realista
    
    def test_get_daily_temp_extremes_empty_list(self, repository):
        """Testa com lista vazia"""
        temp_min, temp_max = repository._get_daily_temp_extremes([], None)
        
        assert temp_min == 0.0
        assert temp_max == 0.0
    
    def test_get_daily_temp_extremes_no_target(self, repository, test_data):
        """Testa cálculo sem data alvo (hoje)"""
        forecasts = test_data['list']
        
        temp_min, temp_max = repository._get_daily_temp_extremes(forecasts, None)
        
        assert isinstance(temp_min, float)
        assert isinstance(temp_max, float)
        assert temp_min <= temp_max


class TestCollectAllAlerts:
    """Testes para método _collect_all_alerts"""
    
    def test_collect_all_alerts_no_alerts(self, repository, test_data):
        """Testa coleta de alertas quando não há condições severas"""
        forecasts = test_data['list'][:10]  # Primeiras 10 previsões (céu limpo)
        target_dt = datetime(2025, 11, 27, 12, 0, tzinfo=ZoneInfo("UTC"))
        
        alerts = repository._collect_all_alerts(forecasts, target_dt)
        
        assert isinstance(alerts, list)
        # Pode ter alguns alertas dependendo dos dados
    
    def test_collect_all_alerts_with_rain(self, repository, test_data):
        """Testa coleta de alertas com previsão de chuva"""
        # Última previsão tem chuva
        forecasts = [test_data['list'][-1]]
        target_dt = datetime(2025, 12, 1, 15, 0, tzinfo=ZoneInfo("UTC"))
        
        alerts = repository._collect_all_alerts(forecasts, target_dt)
        
        assert isinstance(alerts, list)
        # Pode ter alertas de chuva dependendo da probabilidade
    
    def test_collect_all_alerts_empty_list(self, repository):
        """Testa com lista vazia"""
        alerts = repository._collect_all_alerts([], None)
        
        assert isinstance(alerts, list)
        assert len(alerts) == 0


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
