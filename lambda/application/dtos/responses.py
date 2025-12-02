"""Response DTOs - Contratos de saída dos use cases"""

from dataclasses import dataclass
from typing import List, Dict, Any
from datetime import datetime
from zoneinfo import ZoneInfo

from domain.entities.weather import Weather
from domain.entities.city import City
from domain.entities.extended_forecast import ExtendedForecast
from domain.constants import App


@dataclass
class WeatherResponse:
    """Response com dados meteorológicos de uma cidade"""
    city_id: str
    city_name: str
    timestamp: str  # ISO 8601
    temperature: float
    humidity: float
    wind_speed: float
    wind_direction: int
    rain_probability: float
    rain_volume_hour: float
    daily_rain_accumulation: float
    description: str
    feels_like: float
    pressure: float
    visibility: float
    clouds: float
    clouds_description: str
    weather_alerts: List[Dict[str, Any]]
    temp_min: float
    temp_max: float
    rainfall_intensity: int
    
    @staticmethod
    def from_entity(weather: Weather) -> 'WeatherResponse':
        """
        Converte Weather entity para DTO de resposta
        
        Args:
            weather: Weather entity do domínio
        
        Returns:
            WeatherResponse DTO
        """
        
        # Converter timestamp para timezone Brasil
        brasil_tz = ZoneInfo(App.TIMEZONE)
        if weather.timestamp.tzinfo is not None:
            timestamp_brasil = weather.timestamp.astimezone(brasil_tz)
        else:
            timestamp_brasil = weather.timestamp.replace(tzinfo=ZoneInfo("UTC")).astimezone(brasil_tz)
        
        return WeatherResponse(
            city_id=weather.city_id,
            city_name=weather.city_name,
            timestamp=timestamp_brasil.isoformat(),
            temperature=round(weather.temperature, 1),
            humidity=round(weather.humidity, 1),
            wind_speed=round(weather.wind_speed, 1),
            wind_direction=weather.wind_direction,
            rain_probability=round(weather.rain_probability, 1),
            rain_volume_hour=round(weather.rain_1h, 1),
            daily_rain_accumulation=round(weather.rain_accumulated_day, 1),
            description=weather.description,
            feels_like=round(weather.feels_like, 1),
            pressure=round(weather.pressure, 1),
            visibility=round(weather.visibility),
            clouds=round(weather.clouds, 1),
            clouds_description=weather.clouds_description,
            weather_alerts=[alert.to_dict() for alert in weather.weather_alert],
            temp_min=round(weather.temp_min, 1),
            temp_max=round(weather.temp_max, 1),
            rainfall_intensity=weather.rainfall_intensity
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário para resposta JSON"""
        return {
            'cityId': self.city_id,
            'cityName': self.city_name,
            'timestamp': self.timestamp,
            'temperature': self.temperature,
            'humidity': self.humidity,
            'windSpeed': self.wind_speed,
            'windDirection': self.wind_direction,
            'rainfallProbability': self.rain_probability,
            'rainVolumeHour': self.rain_volume_hour,
            'dailyRainAccumulation': self.daily_rain_accumulation,
            'description': self.description,
            'feelsLike': self.feels_like,
            'pressure': self.pressure,
            'visibility': self.visibility,
            'clouds': self.clouds,
            'cloudsDescription': self.clouds_description,
            'weatherAlert': self.weather_alerts,
            'tempMin': self.temp_min,
            'tempMax': self.temp_max,
            'rainfallIntensity': self.rainfall_intensity
        }


@dataclass
class ExtendedForecastResponse:
    """Response com previsão detalhada (current + daily + hourly)"""
    city_id: str
    city_name: str
    city_state: str
    current_weather: Dict[str, Any]
    daily_forecasts: List[Dict[str, Any]]
    hourly_forecasts: List[Dict[str, Any]]
    extended_available: bool
    
    @staticmethod
    def from_entity(extended_forecast: ExtendedForecast) -> 'ExtendedForecastResponse':
        """
        Converte ExtendedForecast entity para DTO
        
        Args:
            extended_forecast: ExtendedForecast entity do domínio
        
        Returns:
            ExtendedForecastResponse DTO
        """
        return ExtendedForecastResponse(
            city_id=extended_forecast.city_id,
            city_name=extended_forecast.city_name,
            city_state=extended_forecast.city_state,
            current_weather=extended_forecast.current_weather.to_api_response(),
            daily_forecasts=[df.to_api_response() for df in extended_forecast.daily_forecasts],
            hourly_forecasts=[hf.to_api_response() for hf in extended_forecast.hourly_forecasts],
            extended_available=extended_forecast.extended_available
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário para resposta JSON"""
        return {
            'cityId': self.city_id,
            'cityName': self.city_name,
            'cityState': self.city_state,
            'currentWeather': self.current_weather,
            'dailyForecasts': self.daily_forecasts,
            'hourlyForecasts': self.hourly_forecasts,
            'extendedAvailable': self.extended_available
        }


@dataclass
class RegionalWeatherResponse:
    """Response com clima de múltiplas cidades"""
    weather_list: List[Dict[str, Any]]
    center_city_id: str
    radius_km: float
    total_cities: int
    
    @staticmethod
    def from_weather_list(
        weather_list: List[Weather],
        center_city_id: str,
        radius_km: float
    ) -> 'RegionalWeatherResponse':
        """
        Converte lista de Weather entities para DTO
        
        Args:
            weather_list: Lista de Weather entities
            center_city_id: ID da cidade central
            radius_km: Raio usado
        
        Returns:
            RegionalWeatherResponse DTO
        """
        return RegionalWeatherResponse(
            weather_list=[w.to_api_response() for w in weather_list],
            center_city_id=center_city_id,
            radius_km=radius_km,
            total_cities=len(weather_list)
        )
    
    def to_dict(self) -> List[Dict[str, Any]]:
        """Converte para lista de dicionários (formato legado)"""
        return self.weather_list


@dataclass
class NeighborCitiesResponse:
    """Response com cidades vizinhas"""
    cities: List[Dict[str, Any]]
    center_city_id: str
    radius_km: float
    total_cities: int
    
    @staticmethod
    def from_cities(
        cities: List[City],
        center_city_id: str,
        radius_km: float
    ) -> 'NeighborCitiesResponse':
        """
        Converte lista de City entities para DTO
        
        Args:
            cities: Lista de City entities
            center_city_id: ID da cidade central
            radius_km: Raio usado
        
        Returns:
            NeighborCitiesResponse DTO
        """
        return NeighborCitiesResponse(
            cities=[c.to_dict() for c in cities],
            center_city_id=center_city_id,
            radius_km=radius_km,
            total_cities=len(cities)
        )
    
    def to_dict(self) -> List[Dict[str, Any]]:
        """Converte para lista de dicionários"""
        return self.cities
