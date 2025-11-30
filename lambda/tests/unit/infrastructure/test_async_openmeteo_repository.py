"""
Unit Tests: Async Open-Meteo Repository
"""
import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from infrastructure.adapters.output.async_openmeteo_repository import (
    AsyncOpenMeteoRepository,
    get_async_openmeteo_repository
)
from domain.entities.daily_forecast import DailyForecast


@pytest.fixture
def sample_openmeteo_response():
    """Load sample response from fixtures"""
    fixtures_path = Path(__file__).parent.parent.parent / 'fixtures' / 'openmeteo_sample_responses.json'
    with open(fixtures_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['sao_paulo']


@pytest.fixture
def repository():
    """Create repository instance without cache"""
    return AsyncOpenMeteoRepository(cache=None)


class TestAsyncOpenMeteoRepository:
    """Test suite for AsyncOpenMeteoRepository"""
    
    @pytest.mark.asyncio
    async def test_get_extended_forecast_success(self, repository, sample_openmeteo_response):
        """Test successful fetch of extended forecast"""
        # Mock aiohttp response
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value=sample_openmeteo_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()
        
        # Mock aiohttp session
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        
        # Mock session manager to return the mock session
        with patch.object(repository.session_manager, 'get_session', return_value=mock_session):
            result = await repository.get_extended_forecast(
                city_id='3550308',
                latitude=-23.5505,
                longitude=-46.6333,
                forecast_days=16
            )
        
        # Assertions
        assert len(result) == 16
        assert all(isinstance(f, DailyForecast) for f in result)
        
        # Verificar primeiro dia
        first_day = result[0]
        assert first_day.date == '2025-11-30'
        assert first_day.temp_max > 0
        assert first_day.temp_min > 0
        assert first_day.uv_index >= 0
    
    @pytest.mark.asyncio
    async def test_get_extended_forecast_invalid_days(self, repository):
        """Test error when forecast_days is invalid"""
        with pytest.raises(ValueError, match="forecast_days must be between 1 and 16"):
            await repository.get_extended_forecast(
                city_id='3550308',
                latitude=-23.5505,
                longitude=-46.6333,
                forecast_days=20  # Invalid
            )
    
    def test_process_daily_data(self, repository, sample_openmeteo_response):
        """Test data processing from API response"""
        result = repository._process_daily_data(sample_openmeteo_response)
        
        assert len(result) == 16
        assert all(isinstance(f, DailyForecast) for f in result)
        
        # Verificar estrutura de dados
        for forecast in result:
            assert hasattr(forecast, 'date')
            assert hasattr(forecast, 'temp_max')
            assert hasattr(forecast, 'temp_min')
            assert hasattr(forecast, 'uv_index')
            assert hasattr(forecast, 'sunrise')
            assert hasattr(forecast, 'sunset')
    
    def test_calculate_moon_phase(self):
        """Test moon phase calculation"""
        # Testar datas conhecidas
        assert 'Nova' in AsyncOpenMeteoRepository.calculate_moon_phase('2000-01-06')
        assert 'Lua' in AsyncOpenMeteoRepository.calculate_moon_phase('2025-11-30')
    
    def test_singleton_factory(self):
        """Test singleton pattern of factory"""
        instance1 = get_async_openmeteo_repository()
        instance2 = get_async_openmeteo_repository()
        
        assert instance1 is instance2
