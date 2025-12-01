"""
Testes Unitários - AsyncOpenMeteoRepository (Hourly)
Testa o novo método get_hourly_forecast
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from infrastructure.adapters.output.async_openmeteo_repository import AsyncOpenMeteoRepository
from domain.entities.hourly_forecast import HourlyForecast


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
    repo = AsyncOpenMeteoRepository(cache=mock_cache)
    return repo


@pytest.fixture
def mock_hourly_response():
    """Mock de resposta da API Open-Meteo para hourly forecast"""
    return {
        "hourly": {
            "time": [
                "2025-12-01T00:00",
                "2025-12-01T01:00",
                "2025-12-01T02:00"
            ],
            "temperature_2m": [22.5, 21.8, 21.2],
            "precipitation": [0.0, 0.2, 0.5],
            "precipitation_probability": [10, 20, 30],
            "relative_humidity_2m": [75, 78, 80],
            "wind_speed_10m": [8.5, 9.2, 10.0],
            "wind_direction_10m": [180, 185, 190],
            "cloud_cover": [40, 45, 50],
            "weather_code": [1, 2, 3]
        }
    }


class TestGetHourlyForecast:
    """Testes para método get_hourly_forecast"""
    
    @pytest.mark.asyncio
    async def test_get_hourly_forecast_success(self, repository, mock_cache, mock_hourly_response):
        """Deve buscar previsões horárias com sucesso"""
        # Mock da sessão HTTP
        with patch.object(repository.session_manager, 'get_session') as mock_session:
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(return_value=mock_hourly_response)
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            
            mock_http_session = MagicMock()
            mock_http_session.get = MagicMock(return_value=mock_response)
            mock_session.return_value = mock_http_session
            
            # Executar
            forecasts = await repository.get_hourly_forecast(
                city_id="3543204",
                latitude=-22.8125,
                longitude=-50.1856,
                forecast_hours=72
            )
            
            # Validações
            assert len(forecasts) == 3
            assert all(isinstance(f, HourlyForecast) for f in forecasts)
            
            # Validar primeiro forecast
            first = forecasts[0]
            assert first.timestamp == "2025-12-01T00:00"
            assert first.temperature == 22.5
            assert first.precipitation == 0.0
            assert first.precipitation_probability == 10
            assert first.humidity == 75
            assert first.wind_speed == 8.5
            assert first.wind_direction == 180
            assert first.cloud_cover == 40
            assert first.weather_code == 1
            
            # Verificar cache save foi chamado com TTL de 1h (3600s)
            mock_cache.set.assert_called_once()
            call_args = mock_cache.set.call_args
            assert call_args[1]['ttl_seconds'] == 3600
    
    @pytest.mark.asyncio
    async def test_get_hourly_forecast_from_cache(self, repository, mock_cache, mock_hourly_response):
        """Deve buscar do cache quando disponível"""
        # Mock cache hit
        mock_cache.get = AsyncMock(return_value=mock_hourly_response)
        
        # Executar
        forecasts = await repository.get_hourly_forecast(
            city_id="3543204",
            latitude=-22.8125,
            longitude=-50.1856
        )
        
        # Validações
        assert len(forecasts) == 3
        
        # Cache deve ter sido consultado
        mock_cache.get.assert_called_once()
        
        # API não deve ter sido chamada (cache hit)
        mock_cache.set.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_hourly_forecast_limits_hours(self, repository, mock_cache):
        """Deve limitar número de horas processadas"""
        # Mock com muitas horas
        many_hours_response = {
            "hourly": {
                "time": [f"2025-12-01T{h:02d}:00" for h in range(24)],
                "temperature_2m": [20.0 + h for h in range(24)],
                "precipitation": [0.0] * 24,
                "precipitation_probability": [10] * 24,
                "relative_humidity_2m": [70] * 24,
                "wind_speed_10m": [10.0] * 24,
                "wind_direction_10m": [180] * 24,
                "cloud_cover": [40] * 24,
                "weather_code": [1] * 24
            }
        }
        
        with patch.object(repository.session_manager, 'get_session') as mock_session:
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(return_value=many_hours_response)
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            
            mock_http_session = MagicMock()
            mock_http_session.get = MagicMock(return_value=mock_response)
            mock_session.return_value = mock_http_session
            
            # Executar com limite de 12 horas
            forecasts = await repository.get_hourly_forecast(
                city_id="3543204",
                latitude=-22.8125,
                longitude=-50.1856,
                forecast_hours=12
            )
            
            # Deve ter apenas 12 horas
            assert len(forecasts) == 12
    
    @pytest.mark.asyncio
    async def test_get_hourly_forecast_handles_missing_data(self, repository, mock_cache):
        """Deve usar valores padrão quando dados faltarem"""
        incomplete_response = {
            "hourly": {
                "time": ["2025-12-01T00:00"],
                "temperature_2m": [22.5],
                # Faltam alguns campos
                "precipitation": [],
                "precipitation_probability": [],
                "relative_humidity_2m": [],
                "wind_speed_10m": [10.0],
                "wind_direction_10m": [],
                "cloud_cover": [],
                "weather_code": []
            }
        }
        
        with patch.object(repository.session_manager, 'get_session') as mock_session:
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(return_value=incomplete_response)
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            
            mock_http_session = MagicMock()
            mock_http_session.get = MagicMock(return_value=mock_response)
            mock_session.return_value = mock_http_session
            
            # Executar
            forecasts = await repository.get_hourly_forecast(
                city_id="3543204",
                latitude=-22.8125,
                longitude=-50.1856
            )
            
            # Deve ter 1 forecast com valores padrão para campos faltantes
            assert len(forecasts) == 1
            forecast = forecasts[0]
            assert forecast.temperature == 22.5
            assert forecast.wind_speed == 10.0
            # Campos faltantes devem ter valores padrão
            assert forecast.precipitation == 0.0
            assert forecast.precipitation_probability == 0
            assert forecast.humidity == 0
            assert forecast.wind_direction == 0
            assert forecast.cloud_cover == 0
            assert forecast.weather_code == 0


class TestCacheTTLUpdate:
    """Testes para validar que o cache TTL foi atualizado"""
    
    @pytest.mark.asyncio
    async def test_daily_forecast_cache_ttl_is_1h(self, repository, mock_cache):
        """Deve usar TTL de 1h (3600s) para daily forecasts"""
        mock_daily_response = {
            "daily": {
                "time": ["2025-12-01"],
                "temperature_2m_max": [30.0],
                "temperature_2m_min": [20.0],
                "precipitation_sum": [5.0],
                "precipitation_probability_mean": [50.0],
                "wind_speed_10m_max": [15.0],
                "wind_direction_10m_dominant": [180],
                "uv_index_max": [7.0],
                "sunrise": ["06:00"],
                "sunset": ["18:00"],
                "precipitation_hours": [3.0]
            }
        }
        
        with patch.object(repository.session_manager, 'get_session') as mock_session:
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(return_value=mock_daily_response)
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            
            mock_http_session = MagicMock()
            mock_http_session.get = MagicMock(return_value=mock_response)
            mock_session.return_value = mock_http_session
            
            # Executar
            await repository.get_extended_forecast(
                city_id="3543204",
                latitude=-22.8125,
                longitude=-50.1856
            )
            
            # Verificar que cache.set foi chamado com TTL de 1h
            mock_cache.set.assert_called_once()
            call_args = mock_cache.set.call_args
            assert call_args[1]['ttl_seconds'] == 3600
