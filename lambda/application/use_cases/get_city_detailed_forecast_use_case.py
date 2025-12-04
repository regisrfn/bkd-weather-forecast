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
from infrastructure.adapters.output.providers.openmeteo.openmeteo_provider import OpenMeteoProvider
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
        
        # Execute TWO API calls in parallel (ASYNC - sem GIL)
        # Strategy: Open-Meteo ONLY - Fetch once, reuse data
        try:
            # Task 1: Hourly forecasts (168h = 7 dias, reutilizado para tudo)
            hourly_task = self.hourly_forecast_provider.get_hourly_forecast(
                latitude=city.latitude,
                longitude=city.longitude,
                city_id=city.id,
                hours=168  # Fetch once: current weather + API response + alerts
            )
            
            # Task 2: Daily forecasts (16 dias para resposta da API)
            daily_task = self.daily_forecast_provider.get_daily_forecast(
                latitude=city.latitude,
                longitude=city.longitude,
                city_id=city.id,
                days=16
            )
            
            # Await both tasks concurrently
            results = await asyncio.gather(
                hourly_task,
                daily_task,
                return_exceptions=True  # Continue even if one fails
            )
            
            hourly_forecasts_full = results[0]  # 168 horas
            daily_forecasts = results[1]  # 16 dias
            
            # Validate hourly_forecasts (critical - must succeed)
            if isinstance(hourly_forecasts_full, Exception):
                logger.error("Failed to fetch hourly forecasts", error=str(hourly_forecasts_full))
                raise hourly_forecasts_full
            
            # Validate daily_forecasts
            if isinstance(daily_forecasts, Exception):
                logger.error("Failed to fetch daily forecasts", error=str(daily_forecasts))
                daily_forecasts = []
            
            # Handle errors
            extended_available = True
            
            if not daily_forecasts:
                logger.warning("No daily forecasts available")
                extended_available = False
            
            # Extrair current weather dos dados hourly já buscados (sem nova chamada)
            current_weather = OpenMeteoProvider.extract_current_weather_from_hourly(
                hourly_forecasts=hourly_forecasts_full,
                daily_forecasts=daily_forecasts if daily_forecasts else None,
                city_id=city.id,
                city_name=city.name,
                target_datetime=target_datetime
            )
            
            # Gerar alertas usando dados já buscados (sem nova chamada)
            alerts = await AlertsGenerator.generate_alerts_for_weather(
                hourly_forecasts=hourly_forecasts_full,  # Passa dados completos, função decide o uso
                daily_forecasts=daily_forecasts if daily_forecasts else [],  # Passa dados completos
                target_datetime=target_datetime,
                days_limit=7
            )
            
            if alerts:
                object.__setattr__(current_weather, 'weather_alert', alerts)
            
            # Slice hourly para resposta da API (48h)
            hourly_forecasts = hourly_forecasts_full[:48] if hourly_forecasts_full else []
            
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
