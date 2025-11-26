"""
Unit tests for AsyncGetRegionalWeatherUseCase - Complete Coverage
Tests for _parse_cached_weather and _fetch_cities_from_api
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from zoneinfo import ZoneInfo

from application.use_cases.get_regional_weather import AsyncGetRegionalWeatherUseCase
from domain.entities.city import City
from domain.entities.weather import Weather


@pytest.fixture
def sample_cached_data():
    """Sample cached weather data"""
    return {
        'list': [
            {
                'dt': 1700000000,
                'main': {
                    'temp': 25.0,
                    'feels_like': 26.0,
                    'humidity': 65,
                    'pressure': 1013
                },
                'weather': [{'id': 800, 'description': 'clear sky'}],
                'wind': {'speed': 3.5},
                'pop': 0.1,
                'visibility': 10000,
                'clouds': {'all': 10},
                'rain': {'3h': 0.3}
            }
        ]
    }


@pytest.fixture
def mock_city_repository():
    """Mock city repository"""
    repo = Mock()
    
    city1 = City(id='3550308', name='São Paulo', state='SP', region='Sudeste', latitude=-23.5505, longitude=-46.6333)
    city2 = City(id='3304557', name='Rio de Janeiro', state='RJ', region='Sudeste', latitude=-22.9068, longitude=-43.1729)
    city_no_coords = City(id='9999999', name='City Without Coords', state='XX', region='North', latitude=None, longitude=None)
    
    def get_by_id_side_effect(city_id):
        if city_id == '3550308':
            return city1
        elif city_id == '3304557':
            return city2
        elif city_id == '9999999':
            return city_no_coords
        return None
    
    repo.get_by_id.side_effect = get_by_id_side_effect
    return repo


@pytest.fixture
def mock_weather_repository():
    """Mock weather repository"""
    repo = AsyncMock()
    return repo


@pytest.fixture
def use_case(mock_city_repository, mock_weather_repository):
    """Use case instance"""
    return AsyncGetRegionalWeatherUseCase(
        city_repository=mock_city_repository,
        weather_repository=mock_weather_repository
    )


class TestParseCachedWeather:
    """Tests for _parse_cached_weather method"""
    
    def test_parse_cached_weather_success(self, use_case, sample_cached_data, mock_city_repository):
        """Test successful parsing of cached weather data"""
        city = City(id='3550308', name='São Paulo', state='SP', region='Sudeste', latitude=-23.5505, longitude=-46.6333)
        
        # Mock _select_forecast to return first item
        use_case.weather_repository._select_forecast = Mock(return_value=sample_cached_data['list'][0])
        use_case.weather_repository._collect_all_alerts = Mock(return_value=[])
        use_case.weather_repository._get_daily_temp_extremes = Mock(return_value=(20.0, 30.0))
        
        result = use_case._parse_cached_weather(sample_cached_data, city, None)
        
        assert result is not None
        assert isinstance(result, Weather)
        assert result.city_id == '3550308'
        assert result.city_name == 'São Paulo'
        assert result.temperature == 25.0
        assert result.humidity == 65
    
    def test_parse_cached_weather_no_forecast(self, use_case, sample_cached_data, mock_city_repository):
        """Test parsing when no forecast is selected"""
        city = City(id='3550308', name='São Paulo', state='SP', region='Sudeste', latitude=-23.5505, longitude=-46.6333)
        
        # Mock _select_forecast to return None
        use_case.weather_repository._select_forecast = Mock(return_value=None)
        
        result = use_case._parse_cached_weather(sample_cached_data, city, None)
        
        assert result is None
    
    def test_parse_cached_weather_with_target_datetime(self, use_case, sample_cached_data, mock_city_repository):
        """Test parsing with specific target datetime"""
        city = City(id='3550308', name='São Paulo', state='SP', region='Sudeste', latitude=-23.5505, longitude=-46.6333)
        target_dt = datetime(2025, 12, 1, 12, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
        
        use_case.weather_repository._select_forecast = Mock(return_value=sample_cached_data['list'][0])
        use_case.weather_repository._collect_all_alerts = Mock(return_value=['RAIN'])
        use_case.weather_repository._get_daily_temp_extremes = Mock(return_value=(18.0, 28.0))
        
        result = use_case._parse_cached_weather(sample_cached_data, city, target_dt)
        
        assert result is not None
        assert result.weather_alert == ['RAIN']
        assert result.temp_min == 18.0
        assert result.temp_max == 28.0


class TestFetchCitiesFromAPI:
    """Tests for _fetch_cities_from_api method"""
    
    @pytest.mark.asyncio
    async def test_fetch_cities_from_api_success(self, use_case, mock_city_repository):
        """Test successful API fetch for multiple cities"""
        city_ids = ['3550308', '3304557']
        
        # Mock weather data
        weather1 = Weather(
            city_id='3550308',
            city_name='São Paulo',
            timestamp=datetime.now(ZoneInfo("UTC")),
            temperature=25.0,
            humidity=65,
            wind_speed=10.0,
            rain_probability=10.0
        )
        
        weather2 = Weather(
            city_id='3304557',
            city_name='Rio de Janeiro',
            timestamp=datetime.now(ZoneInfo("UTC")),
            temperature=28.0,
            humidity=70,
            wind_speed=8.0,
            rain_probability=15.0
        )
        
        # Mock get_current_weather_with_cache_data
        async def mock_get_weather(city_id, lat, lon, name, target_dt):
            if city_id == '3550308':
                return (weather1, f'cache_key_{city_id}', {'data': 'mock1'})
            else:
                return (weather2, f'cache_key_{city_id}', {'data': 'mock2'})
        
        use_case.weather_repository.get_current_weather_with_cache_data = AsyncMock(side_effect=mock_get_weather)
        use_case.weather_repository.batch_save_weather_to_cache = AsyncMock()
        
        result = await use_case._fetch_cities_from_api(city_ids, None)
        
        assert len(result) == 2
        assert all(isinstance(w, Weather) for w in result)
        use_case.weather_repository.batch_save_weather_to_cache.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_cities_from_api_with_failures(self, use_case, mock_city_repository):
        """Test API fetch with some failures"""
        city_ids = ['3550308', 'invalid_id', '3304557']
        
        weather1 = Weather(
            city_id='3550308',
            city_name='São Paulo',
            timestamp=datetime.now(ZoneInfo("UTC")),
            temperature=25.0,
            humidity=65,
            wind_speed=10.0,
            rain_probability=10.0
        )
        
        # Mock get_current_weather_with_cache_data - city 2 fails
        async def mock_get_weather(city_id, lat, lon, name, target_dt):
            if city_id == '3550308':
                return (weather1, f'cache_key_{city_id}', {'data': 'mock1'})
            raise Exception("API error")
        
        use_case.weather_repository.get_current_weather_with_cache_data = AsyncMock(side_effect=mock_get_weather)
        use_case.weather_repository.batch_save_weather_to_cache = AsyncMock()
        
        result = await use_case._fetch_cities_from_api(city_ids, None)
        
        # Should return only successful fetch
        assert len(result) == 1
        assert result[0].city_id == '3550308'
    
    @pytest.mark.asyncio
    async def test_fetch_cities_from_api_city_without_coordinates(self, use_case, mock_city_repository):
        """Test API fetch skips cities without coordinates"""
        city_ids = ['9999999']  # City without coordinates
        
        use_case.weather_repository.get_current_weather_with_cache_data = AsyncMock()
        use_case.weather_repository.batch_save_weather_to_cache = AsyncMock()
        
        result = await use_case._fetch_cities_from_api(city_ids, None)
        
        assert len(result) == 0
        # Should not call API for cities without coordinates
        use_case.weather_repository.get_current_weather_with_cache_data.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_fetch_cities_from_api_city_not_found(self, use_case, mock_city_repository):
        """Test API fetch skips cities not found in repository"""
        city_ids = ['nonexistent']
        
        use_case.weather_repository.get_current_weather_with_cache_data = AsyncMock()
        use_case.weather_repository.batch_save_weather_to_cache = AsyncMock()
        
        result = await use_case._fetch_cities_from_api(city_ids, None)
        
        assert len(result) == 0
        use_case.weather_repository.get_current_weather_with_cache_data.assert_not_called()


class TestFetchAllCities:
    """Tests for _fetch_all_cities method"""
    
    @pytest.mark.asyncio
    async def test_fetch_all_cities_all_from_cache(self, use_case, mock_city_repository, sample_cached_data):
        """Test when all cities are found in cache"""
        city_ids = ['3550308', '3304557']
        
        # Mock batch_get_weather_from_cache to return data for all
        cache_results = {
            '3550308': sample_cached_data,
            '3304557': sample_cached_data
        }
        use_case.weather_repository.batch_get_weather_from_cache = AsyncMock(return_value=cache_results)
        
        # Mock _select_forecast and related methods
        use_case.weather_repository._select_forecast = Mock(return_value=sample_cached_data['list'][0])
        use_case.weather_repository._collect_all_alerts = Mock(return_value=[])
        use_case.weather_repository._get_daily_temp_extremes = Mock(return_value=(20.0, 30.0))
        
        result = await use_case._fetch_all_cities(city_ids, None)
        
        assert len(result) == 2
        # Should not fetch from API if all in cache
        use_case.weather_repository.batch_get_weather_from_cache.assert_called_once_with(city_ids)
    
    @pytest.mark.asyncio
    async def test_fetch_all_cities_mixed_cache_and_api(self, use_case, mock_city_repository, sample_cached_data):
        """Test when some cities are in cache and others need API fetch"""
        city_ids = ['3550308', '3304557']
        
        # Only first city in cache
        cache_results = {'3550308': sample_cached_data}
        use_case.weather_repository.batch_get_weather_from_cache = AsyncMock(return_value=cache_results)
        
        # Mock cache hit parsing
        use_case.weather_repository._select_forecast = Mock(return_value=sample_cached_data['list'][0])
        use_case.weather_repository._collect_all_alerts = Mock(return_value=[])
        use_case.weather_repository._get_daily_temp_extremes = Mock(return_value=(20.0, 30.0))
        
        # Mock API fetch for cache miss
        weather2 = Weather(
            city_id='3304557',
            city_name='Rio de Janeiro',
            timestamp=datetime.now(ZoneInfo("UTC")),
            temperature=28.0,
            humidity=70,
            wind_speed=8.0,
            rain_probability=15.0
        )
        
        use_case.weather_repository.get_current_weather_with_cache_data = AsyncMock(
            return_value=(weather2, 'cache_key', {'data': 'mock'})
        )
        use_case.weather_repository.batch_save_weather_to_cache = AsyncMock()
        
        result = await use_case._fetch_all_cities(city_ids, None)
        
        assert len(result) == 2
        # Should fetch only cache miss from API
        use_case.weather_repository.get_current_weather_with_cache_data.assert_called_once()
