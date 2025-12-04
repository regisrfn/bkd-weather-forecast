"""
Async Use Case: Get City Weather
100% async implementation - Refatorado para usar providers desacoplados
"""
import asyncio
from typing import Optional
from datetime import datetime
from ddtrace import tracer

from domain.entities.weather import Weather
from domain.exceptions import CityNotFoundException, CoordinatesNotFoundException
from application.ports.output.weather_provider_port import IWeatherProvider
from domain.services.alerts_generator import AlertsGenerator
from application.ports.input.get_city_weather_port import IGetCityWeatherUseCase
from application.ports.output.city_repository_port import ICityRepository
from infrastructure.adapters.output.providers.openmeteo.openmeteo_provider import OpenMeteoProvider
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
        
        # Fetch hourly and daily data once, reuse for current weather + alerts
        # Fetch in parallel
        hourly_task = self.weather_provider.get_hourly_forecast(
            latitude=city.latitude,
            longitude=city.longitude,
            city_id=city.id,
            hours=168  # 7 dias - usado para current weather + alertas
        )
        
        daily_task = self.weather_provider.get_daily_forecast(
            latitude=city.latitude,
            longitude=city.longitude,
            city_id=city.id,
            days=16  # 16 dias para consistência de cache entre rotas
        )
        
        hourly_forecasts, daily_forecasts = await asyncio.gather(hourly_task, daily_task)
        
        # Extrair current weather dos dados hourly já buscados
        weather = OpenMeteoProvider.extract_current_weather_from_hourly(
            hourly_forecasts=hourly_forecasts,
            daily_forecasts=daily_forecasts if daily_forecasts else None,
            city_id=city.id,
            city_name=city.name,
            target_datetime=target_datetime
        )
        
        # Gerar alertas usando dados já buscados
        alerts = await AlertsGenerator.generate_alerts_for_weather(
            hourly_forecasts=hourly_forecasts if hourly_forecasts else [],
            daily_forecasts=daily_forecasts if daily_forecasts else [],
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
