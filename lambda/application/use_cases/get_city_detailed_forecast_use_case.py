"""
Async Use Case: Get City Detailed Forecast
Refatorado para usar One Call API 3.0 com estratégia híbrida para 16 dias
"""
import asyncio
from typing import Optional, List
from datetime import datetime
from ddtrace import tracer

from domain.entities.extended_forecast import ExtendedForecast
from domain.entities.daily_forecast import DailyForecast
from domain.exceptions import CityNotFoundException, CoordinatesNotFoundException
from application.ports.output.weather_provider_port import IWeatherProvider
from domain.services.weather_enricher import WeatherEnricher
from domain.services.alerts_generator import AlertsGenerator
from application.ports.output.city_repository_port import ICityRepository
from shared.config.logger_config import get_logger

logger = get_logger(child=True)


class GetCityDetailedForecastUseCase:
    """
    Async use case: Get detailed forecast with extended data
    
    Estratégia Open-Meteo Only:
    - Open-Meteo: current + hourly (48h) + daily (16 dias)
    - Uma única fonte de dados consistente
    """
    
    def __init__(
        self,
        city_repository: ICityRepository,
        current_weather_provider: IWeatherProvider,
        daily_forecast_provider: IWeatherProvider,
        hourly_forecast_provider: IWeatherProvider
    ):
        self.city_repository = city_repository
        self.current_weather_provider = current_weather_provider
        self.daily_forecast_provider = daily_forecast_provider
        self.hourly_forecast_provider = hourly_forecast_provider
    
    @tracer.wrap(resource="use_case.async_get_city_detailed_forecast")
    async def execute(
        self,
        city_id: str,
        target_datetime: Optional[datetime] = None
    ) -> ExtendedForecast:
        """
        Execute use case asynchronously com chamadas em paralelo
        
        Args:
            city_id: City ID
            target_datetime: Datetime específico para dados atuais (opcional)
        
        Returns:
            ExtendedForecast entity com dados consolidados
        
        Raises:
            CityNotFoundException: Se cidade não encontrada
            CoordinatesNotFoundException: Se cidade não tem coordenadas
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
        
        logger.info(
            "Fetching detailed forecast",
            city_id=city_id,
            city_name=city.name,
            current_provider=self.current_weather_provider.provider_name,
            daily_provider=self.daily_forecast_provider.provider_name,
            hourly_provider=self.hourly_forecast_provider.provider_name
        )
        
        # Execute THREE API calls in parallel (ASYNC - sem GIL)
        # Strategy: Open-Meteo ONLY (16 days)
        try:
            # Task 1: Current weather (com alertas de 16 dias para rota detalhada)
            current_task = self.current_weather_provider.get_current_weather(
                latitude=city.latitude,
                longitude=city.longitude,
                city_id=city.id,
                city_name=city.name,
                target_datetime=target_datetime,
                include_daily_alerts=True  # Inclui alertas de médio prazo (16 dias)
            )
            
            # Task 2: Open-Meteo Daily forecasts (16 dias)
            daily_task = self.daily_forecast_provider.get_daily_forecast(
                latitude=city.latitude,
                longitude=city.longitude,
                city_id=city.id,
                days=16
            )
            
            # Task 3: Hourly forecasts (48h para resposta da API)
            hourly_task = self.hourly_forecast_provider.get_hourly_forecast(
                latitude=city.latitude,
                longitude=city.longitude,
                city_id=city.id,
                hours=48
            )
            
            # Await all three tasks concurrently
            results = await asyncio.gather(
                current_task,
                daily_task,
                hourly_task,
                return_exceptions=True  # Continue even if one fails
            )
            
            current_weather = results[0]
            daily_forecasts = results[1]
            hourly_forecasts = results[2]
            
            # Validate daily_forecasts
            if isinstance(daily_forecasts, Exception):
                logger.error("Failed to fetch daily forecasts", error=str(daily_forecasts))
                daily_forecasts = []
            
            # Handle errors
            extended_available = True
            
            # Process current weather (critical - must succeed)
            if isinstance(current_weather, Exception):
                logger.error("Failed to fetch current weather", error=str(current_weather))
                raise current_weather
            
            # Gerar alertas para current weather usando hourly (2 dias) + daily (5 dias)
            from domain.services.alerts_generator import AlertsGenerator
            
            alerts = await AlertsGenerator.generate_alerts_for_weather(
                weather_provider=self.current_weather_provider,
                latitude=city.latitude,
                longitude=city.longitude,
                city_id=city.id,
                target_datetime=target_datetime,
                days_limit=7
            )
            
            if alerts:
                object.__setattr__(current_weather, 'weather_alert', alerts)
            
            # Daily forecasts já foram combinados
            if not daily_forecasts:
                logger.warning("No daily forecasts available")
                extended_available = False
            
            # Process hourly forecasts
            if isinstance(hourly_forecasts, Exception):
                logger.warning(
                    "Failed to fetch hourly forecast",
                    error=str(hourly_forecasts)
                )
                hourly_forecasts = []
            
            # Create ExtendedForecast
            extended_forecast = ExtendedForecast(
                city_id=city.id,
                city_name=city.name,
                city_state=city.state,
                current_weather=current_weather,
                daily_forecasts=daily_forecasts,
                hourly_forecasts=hourly_forecasts if not isinstance(hourly_forecasts, Exception) else [],
                extended_available=extended_available
            )
            
            logger.info(
                "Detailed forecast fetched successfully",
                city_id=city_id,
                extended_available=extended_available,
                forecast_days=len(daily_forecasts),
                hourly_hours=len(hourly_forecasts) if not isinstance(hourly_forecasts, Exception) else 0,
                total_alerts=len(current_weather.weather_alert)
            )
            
            return extended_forecast
        
        except Exception as e:
            logger.error(
                "Failed to fetch detailed forecast",
                city_id=city_id,
                error=str(e)
            )
            raise
