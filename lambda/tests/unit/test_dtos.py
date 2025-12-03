"""
Testes dos DTOs de Request e Response
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from application.dtos.requests import (
    GetWeatherRequest,
    GetDetailedForecastRequest,
    GetRegionalWeatherRequest,
    GetNeighborCitiesRequest
)
from application.dtos.responses import (
    WeatherResponse,
    ExtendedForecastResponse,
    RegionalWeatherResponse,
    NeighborCitiesResponse
)
from domain.entities.weather import Weather
from domain.entities.extended_forecast import ExtendedForecast
from domain.entities.city import City, NeighborCity


class TestRequestDTOs:
    """Testes para Request DTOs"""
    
    def test_get_weather_request_creation(self):
        """Testa criação de GetWeatherRequest com datetime"""
        timestamp = datetime(2024, 1, 1, 12, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
        request = GetWeatherRequest(city_id="3448439", target_datetime=timestamp)
        
        assert request.city_id == "3448439"
        assert request.target_datetime == timestamp
    
    def test_get_weather_request_without_datetime(self):
        """Testa criação de GetWeatherRequest sem datetime"""
        request = GetWeatherRequest(city_id="3448439")
        
        assert request.city_id == "3448439"
        assert request.target_datetime is None
    
    def test_get_detailed_forecast_request_creation(self):
        """Testa criação de GetDetailedForecastRequest"""
        request = GetDetailedForecastRequest(city_id="3448439")
        
        assert request.city_id == "3448439"
    
    def test_get_regional_weather_request_creation(self):
        """Testa criação de GetRegionalWeatherRequest"""
        request = GetRegionalWeatherRequest(center_city_id="3448439", radius_km=50.0)
        
        assert request.center_city_id == "3448439"
        assert request.radius_km == 50.0
    
    def test_get_neighbor_cities_request_creation(self):
        """Testa criação de GetNeighborCitiesRequest"""
        request = GetNeighborCitiesRequest(center_city_id="3448439", radius_km=50.0)
        
        assert request.center_city_id == "3448439"
        assert request.radius_km == 50.0


class TestResponseDTOs:
    """Testes para Response DTOs"""
    
    def test_weather_response_from_entity(self):
        """Testa WeatherResponse.from_entity"""
        weather = Weather(
            city_id="3448439",
            city_name="São Paulo",
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=ZoneInfo("America/Sao_Paulo")),
            temperature=25.0,
            humidity=70.0,
            wind_speed=10.0,
            wind_direction=180,
            rain_probability=30.0,
            rain_1h=0.0,
            description="Céu limpo",
            feels_like=24.0,
            pressure=1013.0,
            visibility=10000.0,
            clouds=20.0,
            weather_code=800
        )
        
        response = WeatherResponse.from_entity(weather)
        
        assert isinstance(response, WeatherResponse)
        assert response.city_id == "3448439"
        assert response.city_name == "São Paulo"
        assert response.temperature == 25.0
    
    def test_weather_response_to_dict(self):
        """Testa WeatherResponse.to_dict"""
        weather = Weather(
            city_id="3448439",
            city_name="São Paulo",
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=ZoneInfo("America/Sao_Paulo")),
            temperature=25.0,
            humidity=70.0,
            wind_speed=10.0,
            wind_direction=180,
            rain_probability=30.0,
            rain_1h=0.0,
            description="Céu limpo",
            feels_like=24.0,
            pressure=1013.0,
            visibility=10000.0,
            clouds=20.0,
            weather_code=800
        )
        
        response = WeatherResponse.from_entity(weather)
        result = response.to_dict()
        
        assert isinstance(result, dict)
        assert result["cityId"] == "3448439"
        assert result["cityName"] == "São Paulo"
        assert result["temperature"] == 25.0
    
    def test_extended_forecast_response_from_entity(self):
        """Testa ExtendedForecastResponse.from_entity"""
        forecast = ExtendedForecast(
            city_id="3448439",
            city_name="São Paulo",
            city_state="SP",
            current_weather=Weather(
                city_id="3448439",
                city_name="São Paulo",
                timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=ZoneInfo("America/Sao_Paulo")),
                temperature=25.0,
                humidity=70.0,
                wind_speed=10.0,
                wind_direction=180,
                rain_probability=30.0,
                rain_1h=0.0,
                description="Céu limpo",
                feels_like=24.0,
                pressure=1013.0,
                visibility=10000.0,
                clouds=20.0,
                weather_code=800
            ),
            daily_forecasts=[],
            hourly_forecasts=[]
        )
        
        response = ExtendedForecastResponse.from_entity(forecast)
        
        assert isinstance(response, ExtendedForecastResponse)
        assert response.city_id == "3448439"
        assert response.city_name == "São Paulo"
        assert response.city_state == "SP"
        assert response.extended_available is True
    
    def test_extended_forecast_response_to_dict(self):
        """Testa ExtendedForecastResponse.to_dict"""
        forecast = ExtendedForecast(
            city_id="3448439",
            city_name="São Paulo",
            city_state="SP",
            current_weather=Weather(
                city_id="3448439",
                city_name="São Paulo",
                timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=ZoneInfo("America/Sao_Paulo")),
                temperature=25.0,
                humidity=70.0,
                wind_speed=10.0,
                wind_direction=180,
                rain_probability=30.0,
                rain_1h=0.0,
                description="Céu limpo",
                feels_like=24.0,
                pressure=1013.0,
                visibility=10000.0,
                clouds=20.0,
                weather_code=800
            ),
            daily_forecasts=[],
            hourly_forecasts=[]
        )
        
        response = ExtendedForecastResponse.from_entity(forecast)
        result = response.to_dict()
        
        assert isinstance(result, dict)
        assert result["cityId"] == "3448439"
        assert "currentWeather" in result
    
    def test_regional_weather_response_from_weather_list(self):
        """Testa RegionalWeatherResponse.from_weather_list"""
        weather_list = [
            Weather(
                city_id="3448439",
                city_name="São Paulo",
                timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=ZoneInfo("America/Sao_Paulo")),
                temperature=25.0,
                humidity=70.0,
                wind_speed=10.0,
                wind_direction=180,
                rain_probability=30.0,
                rain_1h=0.0,
                description="Céu limpo",
                feels_like=24.0,
                pressure=1013.0,
                visibility=10000.0,
                clouds=20.0,
                weather_code=800
            )
        ]
        
        response = RegionalWeatherResponse.from_weather_list(
            weather_list=weather_list,
            center_city_id="3448439",
            radius_km=50.0
        )
        
        assert isinstance(response, RegionalWeatherResponse)
        assert response.center_city_id == "3448439"
        assert response.radius_km == 50.0
        assert response.total_cities == 1
    
    def test_regional_weather_response_to_dict(self):
        """Testa RegionalWeatherResponse.to_dict"""
        weather_list = [
            Weather(
                city_id="3448439",
                city_name="São Paulo",
                timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=ZoneInfo("America/Sao_Paulo")),
                temperature=25.0,
                humidity=70.0,
                wind_speed=10.0,
                wind_direction=180,
                rain_probability=30.0,
                rain_1h=0.0,
                description="Céu limpo",
                feels_like=24.0,
                pressure=1013.0,
                visibility=10000.0,
                clouds=20.0,
                weather_code=800
            )
        ]
        
        response = RegionalWeatherResponse.from_weather_list(
            weather_list=weather_list,
            center_city_id="3448439",
            radius_km=50.0
        )
        result = response.to_dict()
        
        assert isinstance(result, list)
        assert len(result) == 1
    
    def test_neighbor_cities_response_from_cities(self):
        """Testa NeighborCitiesResponse.from_cities"""
        city = City(
            id="3448439",
            name="São Paulo",
            state="SP",
            region="Sudeste",
            latitude=-23.5505,
            longitude=-46.6333
        )
        neighbor = NeighborCity(city=city, distance=10.5)
        
        response = NeighborCitiesResponse.from_cities(
            cities=[neighbor],
            center_city_id="3448439",
            radius_km=50.0
        )
        
        assert isinstance(response, NeighborCitiesResponse)
        assert response.center_city_id == "3448439"
        assert response.radius_km == 50.0
        assert response.total_cities == 1
    
    def test_neighbor_cities_response_to_dict(self):
        """Testa NeighborCitiesResponse.to_dict"""
        city = City(
            id="3448439",
            name="São Paulo",
            state="SP",
            region="Sudeste",
            latitude=-23.5505,
            longitude=-46.6333
        )
        neighbor = NeighborCity(city=city, distance=10.5)
        
        response = NeighborCitiesResponse.from_cities(
            cities=[neighbor],
            center_city_id="3448439",
            radius_km=50.0
        )
        result = response.to_dict()
        
        assert isinstance(result, list)
        assert len(result) == 1
