"""
Async Use Case: Get City Weather
100% async implementation with aioboto3 + aiohttp
"""
from typing import Optional
from datetime import datetime
from ddtrace import tracer

from domain.entities.weather import Weather
from domain.exceptions import CityNotFoundException, CoordinatesNotFoundException
from application.ports.input.get_city_weather_port import IGetCityWeatherUseCase
from application.ports.output.city_repository_port import ICityRepository
from infrastructure.adapters.output.async_weather_repository import AsyncOpenWeatherRepository
from shared.config.logger_config import get_logger

logger = get_logger(child=True)


class AsyncGetCityWeatherUseCase(IGetCityWeatherUseCase):
    """Async use case: Get weather data for a single city"""
    
    def __init__(
        self,
        city_repository: ICityRepository,
        weather_repository: AsyncOpenWeatherRepository
    ):
        self.city_repository = city_repository
        self.weather_repository = weather_repository
    
    @tracer.wrap(resource="use_case.async_get_city_weather")
    async def execute(self, city_id: str, target_datetime: Optional[datetime] = None) -> Weather:
        """
        Execute use case asynchronously
        
        Args:
            city_id: City ID
            target_datetime: Specific datetime for forecast (optional)
        
        Returns:
            Weather entity with forecast data
        
        Raises:
            CityNotFoundException: If city not found
            CoordinatesNotFoundException: If city has no coordinates
        """
        # Get city (sync - in-memory lookup)
        city = self.city_repository.get_by_id(city_id)
        if not city:
            raise CityNotFoundException(
                f"City not found",
                details={"city_id": city_id}
            )
        
        # Validate coordinates
        if not city.has_coordinates():
            raise CoordinatesNotFoundException(
                f"City has no coordinates",
                details={"city_id": city_id, "city_name": city.name}
            )
        
        # Get weather data (ASYNC - HTTP + DynamoDB)
        weather = await self.weather_repository.get_current_weather(
            city.id,
            city.latitude,
            city.longitude,
            city.name,
            target_datetime
        )
        
        return weather
