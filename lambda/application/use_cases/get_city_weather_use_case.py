"""
Async Use Case: Get City Weather
100% async implementation - Refatorado para usar providers desacoplados
"""
from typing import Optional
from datetime import datetime
from ddtrace import tracer

from domain.entities.weather import Weather
from domain.exceptions import CityNotFoundException, CoordinatesNotFoundException
from application.ports.output.weather_provider_port import IWeatherProvider
from domain.services.alerts_generator import AlertsGenerator
from application.ports.input.get_city_weather_port import IGetCityWeatherUseCase
from application.ports.output.city_repository_port import ICityRepository
from shared.config.logger_config import get_logger

logger = get_logger(child=True)


class AsyncGetCityWeatherUseCase(IGetCityWeatherUseCase):
    """Async use case: Get weather data for a single city"""
    
    def __init__(
        self,
        city_repository: ICityRepository,
        weather_provider: IWeatherProvider
    ):
        self.city_repository = city_repository
        self.weather_provider = weather_provider
    
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
        
        # Get weather data (ASYNC - HTTP + DynamoDB via provider)
        weather = await self.weather_provider.get_current_weather(
            latitude=city.latitude,
            longitude=city.longitude,
            city_id=city.id,
            city_name=city.name,
            target_datetime=target_datetime
        )
        
        # Gerar alertas combinando hourly (48h) + daily (5 dias)
        from domain.services.alerts_generator import AlertsGenerator
        
        alerts = await AlertsGenerator.generate_alerts_for_weather(
            weather_provider=self.weather_provider,
            latitude=city.latitude,
            longitude=city.longitude,
            city_id=city.id,
            target_datetime=target_datetime,
            days_limit=7
        )
        
        if alerts:
            object.__setattr__(weather, 'weather_alert', alerts)
        
        logger.info(
            "Weather fetched successfully",
            city_id=city_id,
            provider=self.weather_provider.provider_name
        )
        
        return weather
