"""
Async Use Case: Get City Detailed Forecast
Refatorado para usar providers desacoplados e serviços de domínio otimizados
"""
import asyncio
from typing import Optional
from datetime import datetime
from ddtrace import tracer

from domain.entities.extended_forecast import ExtendedForecast
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
    
    Combina dados de múltiplos providers:
    - Current weather (provider configurável)
    - Daily forecasts (provider com suporte daily)
    - Hourly forecasts (provider com suporte hourly)
    - Enriquecimento opcional entre providers
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
        try:
            # Task 1: Current weather
            current_task = self.current_weather_provider.get_current_weather(
                latitude=city.latitude,
                longitude=city.longitude,
                city_id=city.id,
                city_name=city.name,
                target_datetime=target_datetime
            )
            
            # Task 2: Daily forecasts
            daily_task = self.daily_forecast_provider.get_daily_forecast(
                latitude=city.latitude,
                longitude=city.longitude,
                city_id=city.id,
                days=16
            )
            
            # Task 3: Hourly forecasts
            hourly_task = self.hourly_forecast_provider.get_hourly_forecast(
                latitude=city.latitude,
                longitude=city.longitude,
                city_id=city.id,
                hours=168
            )
            
            # Await all three tasks concurrently
            current_weather, daily_forecasts, hourly_forecasts = await asyncio.gather(
                current_task,
                daily_task,
                hourly_task,
                return_exceptions=True  # Continue even if one fails
            )
            
            # Handle errors
            extended_available = True
            
            # Process current weather
            if isinstance(current_weather, Exception):
                logger.error("Failed to fetch current weather", error=str(current_weather))
                raise current_weather
            
            # Process daily forecasts
            if isinstance(daily_forecasts, Exception):
                logger.warning(
                    "Failed to fetch daily forecast, continuing with current only",
                    error=str(daily_forecasts)
                )
                daily_forecasts = []
                extended_available = False
            
            # Process hourly forecasts
            if isinstance(hourly_forecasts, Exception):
                logger.warning(
                    "Failed to fetch hourly forecast",
                    error=str(hourly_forecasts)
                )
                hourly_forecasts = []
            
            # Enrich current weather with hourly data if available and different providers
            if (hourly_forecasts and 
                not isinstance(hourly_forecasts, Exception) and
                self.current_weather_provider.provider_name != self.hourly_forecast_provider.provider_name):
                try:
                    enriched = WeatherEnricher.enrich_with_hourly_data(
                        base_weather=current_weather,
                        hourly_forecasts=hourly_forecasts,
                        target_datetime=target_datetime
                    )
                    if enriched:
                        current_weather = enriched
                        logger.info("Current weather enriched with hourly data")
                except Exception as e:
                    logger.warning(
                        "Failed to enrich current weather with hourly data",
                        error=str(e)
                    )
            
            # Generate enhanced alerts from hourly forecasts (next 7 days)
            # OpenMeteo alerts have PRIORITY over OpenWeather alerts (replace, not merge)
            if hourly_forecasts and not isinstance(hourly_forecasts, Exception):
                try:
                    # Usar generate_alerts_next_7days para alertas em tempo real
                    # (não usar target_datetime - queremos alertas dos próximos 7 dias a partir de AGORA)
                    openmeteo_alerts = AlertsGenerator.generate_alerts_next_7days(
                        forecasts=hourly_forecasts
                    )
                    
                    # OpenMeteo alerts REPLACE OpenWeather alerts (prioridade)
                    # Manter apenas alertas do OpenWeather que NÃO existem no OpenMeteo
                    if openmeteo_alerts:
                        openmeteo_codes = {alert.code for alert in openmeteo_alerts}
                        
                        # Filtrar alertas do OpenWeather (remover códigos duplicados)
                        openweather_unique = [
                            alert for alert in current_weather.weather_alert
                            if alert.code not in openmeteo_codes
                        ]
                        
                        # Substituir: OpenMeteo first, depois OpenWeather únicos
                        current_weather.weather_alert = openmeteo_alerts + openweather_unique
                        
                        logger.info(
                            f"Enhanced alerts: {len(current_weather.weather_alert)} total "
                            f"({len(openmeteo_alerts)} OpenMeteo + {len(openweather_unique)} OpenWeather)"
                        )
                        
                except Exception as e:
                    logger.warning(
                        "Failed to generate enhanced alerts from hourly data",
                        error=str(e)
                    )
            
            # Create ExtendedForecast
            extended_forecast = ExtendedForecast(
                city_id=city.id,
                city_name=city.name,
                city_state=city.state,
                current_weather=current_weather,
                daily_forecasts=daily_forecasts if not isinstance(daily_forecasts, Exception) else [],
                hourly_forecasts=hourly_forecasts if not isinstance(hourly_forecasts, Exception) else [],
                extended_available=extended_available
            )
            
            logger.info(
                "Detailed forecast fetched successfully",
                city_id=city_id,
                extended_available=extended_available,
                forecast_days=len(daily_forecasts) if not isinstance(daily_forecasts, Exception) else 0,
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
