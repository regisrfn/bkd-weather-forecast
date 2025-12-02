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
    
    Estratégia Híbrida 16 dias:
    - OpenWeather One Call 3.0: current + hourly (48h) + daily (8 dias)
    - Open-Meteo: daily (16 dias) como complemento
    - Combina: OpenWeather dias 1-8 + Open-Meteo dias 9-16
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
    
    def _combine_daily_forecasts(
        self,
        openweather_forecasts: any,
        openmeteo_forecasts: any
    ) -> List[DailyForecast]:
        """
        Combina previsões daily: OpenWeather (dias 1-8) + Open-Meteo (dias 9-16)
        
        Estratégia:
        1. Se OpenWeather OK: usa dias 1-8 do OpenWeather
        2. Complementa com dias 9-16 do Open-Meteo
        3. Se OpenWeather falhar: usa todos 16 dias do Open-Meteo
        
        Args:
            openweather_forecasts: Lista de 8 DailyForecast ou Exception
            openmeteo_forecasts: Lista de 16 DailyForecast ou Exception
        
        Returns:
            Lista combinada de até 16 DailyForecast
        """
        # Se ambos falharam, retornar lista vazia
        if isinstance(openweather_forecasts, Exception) and isinstance(openmeteo_forecasts, Exception):
            logger.error(
                "Both OpenWeather and Open-Meteo daily forecasts failed",
                ow_error=str(openweather_forecasts),
                om_error=str(openmeteo_forecasts)
            )
            return []
        
        # Se apenas Open-Meteo disponível, usar todos 16 dias
        if isinstance(openweather_forecasts, Exception):
            logger.warning(
                "OpenWeather daily failed, using Open-Meteo 16 days",
                error=str(openweather_forecasts)
            )
            return openmeteo_forecasts if not isinstance(openmeteo_forecasts, Exception) else []
        
        # Se apenas OpenWeather disponível, usar os 8 dias
        if isinstance(openmeteo_forecasts, Exception):
            logger.warning(
                "Open-Meteo daily failed, using OpenWeather 8 days only",
                error=str(openmeteo_forecasts)
            )
            return openweather_forecasts if not isinstance(openweather_forecasts, Exception) else []
        
        # Ambos OK: combinar OpenWeather (1-8) + Open-Meteo (9-16)
        # Criar mapa de datas do Open-Meteo
        openmeteo_by_date = {forecast.date: forecast for forecast in openmeteo_forecasts}
        
        # Pegar dias 1-8 do OpenWeather
        combined = list(openweather_forecasts[:8])
        
        # Adicionar dias 9-16 do Open-Meteo que não estão no OpenWeather
        used_dates = {forecast.date for forecast in combined}
        
        for forecast in openmeteo_forecasts:
            if forecast.date not in used_dates:
                combined.append(forecast)
                if len(combined) >= 16:
                    break
        
        logger.info(
            f"Combined daily forecasts: {len(combined)} days "
            f"(OpenWeather: {len(openweather_forecasts)}, Open-Meteo: {len([f for f in openmeteo_forecasts if f.date not in used_dates])} additional)"
        )
        
        return combined[:16]  # Garantir máximo 16 dias
    
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
        
        # Execute FOUR API calls in parallel (ASYNC - sem GIL)
        # Strategy: OpenWeather (8 days) + Open-Meteo (16 days) para combinar
        try:
            # Task 1: Current weather (com alertas de 8 dias para rota detalhada)
            current_task = self.current_weather_provider.get_current_weather(
                latitude=city.latitude,
                longitude=city.longitude,
                city_id=city.id,
                city_name=city.name,
                target_datetime=target_datetime,
                include_daily_alerts=True  # Inclui alertas de médio prazo (8 dias)
            )
            
            # Task 2: OpenWeather Daily forecasts (8 dias)
            openweather_daily_task = self.current_weather_provider.get_daily_forecast(
                latitude=city.latitude,
                longitude=city.longitude,
                city_id=city.id,
                days=8
            )
            
            # Task 3: Open-Meteo Daily forecasts (16 dias - para complementar)
            openmeteo_daily_task = self.daily_forecast_provider.get_daily_forecast(
                latitude=city.latitude,
                longitude=city.longitude,
                city_id=city.id,
                days=16
            )
            
            # Task 4: Hourly forecasts (48h OpenWeather)
            hourly_task = self.hourly_forecast_provider.get_hourly_forecast(
                latitude=city.latitude,
                longitude=city.longitude,
                city_id=city.id,
                hours=48
            )
            
            # Await all four tasks concurrently
            results = await asyncio.gather(
                current_task,
                openweather_daily_task,
                openmeteo_daily_task,
                hourly_task,
                return_exceptions=True  # Continue even if one fails
            )
            
            current_weather = results[0]
            openweather_daily = results[1]
            openmeteo_daily = results[2]
            hourly_forecasts = results[3]
            
            # Combinar daily forecasts: OpenWeather (dias 1-8) + Open-Meteo (dias 9-16)
            daily_forecasts = self._combine_daily_forecasts(
                openweather_forecasts=openweather_daily,
                openmeteo_forecasts=openmeteo_daily
            )
            
            # Handle errors
            extended_available = True
            
            # Process current weather (critical - must succeed)
            if isinstance(current_weather, Exception):
                logger.error("Failed to fetch current weather", error=str(current_weather))
                raise current_weather
            
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
