"""
Async Use Case: Get City Detailed Forecast
Consolida dados atuais (Open-Meteo hourly prioritariamente) com previsões estendidas
"""
import asyncio
from typing import Optional
from datetime import datetime
from ddtrace import tracer

from domain.entities.extended_forecast import ExtendedForecast
from domain.exceptions import CityNotFoundException, CoordinatesNotFoundException
from application.ports.output.city_repository_port import ICityRepository
from infrastructure.adapters.output.async_weather_repository import AsyncOpenWeatherRepository
from infrastructure.adapters.output.async_openmeteo_repository import AsyncOpenMeteoRepository
from infrastructure.adapters.helpers.hourly_weather_processor import HourlyWeatherProcessor
from shared.config.logger_config import get_logger

logger = get_logger(child=True)


class AsyncGetCityDetailedForecastUseCase:
    """
    Async use case: Get detailed forecast with extended data
    
    Combina:
    - Open-Meteo Hourly: Dados atuais da hora mais próxima (PRIORITÁRIO)
    - OpenWeather: Fallback para dados atuais (se hourly falhar)
    - Open-Meteo Daily: Previsões diárias estendidas (16 dias)
    - Open-Meteo Hourly: Array de previsões horárias (168 horas)
    
    Executa chamadas em paralelo para otimizar latência.
    """
    
    def __init__(
        self,
        city_repository: ICityRepository,
        weather_repository: AsyncOpenWeatherRepository,
        openmeteo_repository: AsyncOpenMeteoRepository
    ):
        self.city_repository = city_repository
        self.weather_repository = weather_repository
        self.openmeteo_repository = openmeteo_repository
    
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
            latitude=city.latitude,
            longitude=city.longitude
        )
        
        # Execute THREE API calls in parallel (ASYNC - sem GIL)
        try:
            # Task 1: OpenWeather current weather (fallback)
            current_weather_task = self.weather_repository.get_current_weather(
                city.id,
                city.latitude,
                city.longitude,
                city.name,
                target_datetime
            )
            
            # Task 2: Open-Meteo daily forecasts
            extended_forecast_task = self.openmeteo_repository.get_extended_forecast(
                city.id,
                city.latitude,
                city.longitude,
                forecast_days=16
            )
            
            # Task 3: Open-Meteo hourly forecasts (NOVO)
            hourly_forecast_task = self.openmeteo_repository.get_hourly_forecast(
                city.id,
                city.latitude,
                city.longitude,
                forecast_hours=168
            )
            
            # Await all three tasks concurrently
            current_weather, daily_forecasts, hourly_forecasts = await asyncio.gather(
                current_weather_task,
                extended_forecast_task,
                hourly_forecast_task,
                return_exceptions=True  # Continue even if one fails
            )
            
            # Verificar se houve erros
            extended_available = True
            
            # Processar hourly forecasts
            if isinstance(hourly_forecasts, Exception):
                logger.warning(
                    "Failed to fetch hourly forecast from Open-Meteo",
                    error=str(hourly_forecasts)
                )
                hourly_forecasts = []
            
            # ENRIQUECER current weather com dados hourly (manter dados completos do OpenWeather)
            if hourly_forecasts and not isinstance(current_weather, Exception):
                try:
                    # Enriquecer com dados hourly mais precisos
                    enriched_weather = HourlyWeatherProcessor.enrich_weather_with_hourly(
                        base_weather=current_weather,
                        hourly_forecasts=hourly_forecasts,
                        target_datetime=target_datetime
                    )
                    
                    if enriched_weather:
                        logger.info("Enriched current weather with Open-Meteo hourly data")
                        current_weather = enriched_weather
                    else:
                        logger.warning("Failed to enrich with hourly data, using OpenWeather only")
                except Exception as e:
                    logger.warning(
                        "Failed to enrich current weather with hourly data, using OpenWeather only",
                        error=str(e)
                    )
            
            # Se current_weather falhou E não conseguimos usar hourly, propagar erro
            if isinstance(current_weather, Exception):
                logger.error("Failed to fetch current weather", error=str(current_weather))
                raise current_weather
            
            # Se Open-Meteo daily falhou, continuar apenas com dados atuais
            if isinstance(daily_forecasts, Exception):
                logger.warning(
                    "Failed to fetch extended forecast from Open-Meteo, continuing with current weather only",
                    error=str(daily_forecasts)
                )
                daily_forecasts = []
                extended_available = False
            
            # Consolidar em ExtendedForecast
            extended_forecast = ExtendedForecast(
                city_id=city.id,
                city_name=city.name,
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
                hourly_hours=len(hourly_forecasts) if not isinstance(hourly_forecasts, Exception) else 0
            )
            
            return extended_forecast
        
        except Exception as e:
            logger.error(
                "Failed to fetch detailed forecast",
                city_id=city_id,
                error=str(e)
            )
            raise
