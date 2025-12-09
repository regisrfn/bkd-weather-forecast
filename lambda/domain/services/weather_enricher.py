"""Weather Enricher - Enriquece Weather entities com dados horários mais precisos"""
from typing import List, Optional
from datetime import datetime
from zoneinfo import ZoneInfo

from domain.entities.weather import Weather
from domain.entities.hourly_forecast import HourlyForecast
from domain.constants import App
from shared.config.logger_config import get_logger

logger = get_logger(child=True)


class WeatherEnricher:
    """
    Enriquece Weather entities combinando dados de múltiplas fontes
    """
    
    @staticmethod
    def enrich_with_hourly_data(
        base_weather: Weather,
        hourly_forecasts: List[HourlyForecast],
        target_datetime: Optional[datetime] = None
    ) -> Weather:
        """
        Enriquece Weather base com dados hourly do OpenMeteo
        
        ESTRATÉGIA:
        1. Mantém dados já presentes (visibility, pressure, feels_like)
        2. Substitui apenas dados que OpenMeteo tem mais precisos na hora exata
        3. Merge de alertas sem duplicatas
        
        Args:
            base_weather: Weather base já calculado
            hourly_forecasts: Lista de HourlyForecast do OpenMeteo
            target_datetime: Datetime alvo (None = agora)
        
        Returns:
            Weather enriquecido
        """
        if not hourly_forecasts:
            logger.warning("Nenhum forecast hourly disponível para enrichment")
            return base_weather
        
        # Encontrar hora mais próxima
        brasil_tz = ZoneInfo(App.TIMEZONE)
        
        if target_datetime is None:
            ref_dt = datetime.now(tz=brasil_tz)
        elif target_datetime.tzinfo is not None:
            ref_dt = target_datetime.astimezone(brasil_tz)
        else:
            ref_dt = target_datetime.replace(tzinfo=brasil_tz)
        
        # Buscar forecast mais próximo (passado ou futuro)
        closest_forecast = None
        min_diff = float('inf')
        
        for forecast in hourly_forecasts:
            forecast_dt = datetime.fromisoformat(forecast.timestamp)
            if forecast_dt.tzinfo is None:
                forecast_dt = forecast_dt.replace(tzinfo=brasil_tz)
            
            diff = abs((forecast_dt - ref_dt).total_seconds())
            if diff < min_diff:
                min_diff = diff
                closest_forecast = forecast
        
        if not closest_forecast:
            logger.warning("Não foi possível encontrar forecast mais próximo")
            return base_weather
        
        # Criar timestamp enriquecido com timezone correto
        enriched_timestamp = datetime.fromisoformat(closest_forecast.timestamp)
        if enriched_timestamp.tzinfo is None:
            enriched_timestamp = enriched_timestamp.replace(tzinfo=brasil_tz)
        
        # Criar Weather enriquecido mantendo dados já disponíveis
        enriched = Weather(
            city_id=base_weather.city_id,
            city_name=base_weather.city_name,
            # Dados ENRICHED do OpenMeteo (mais precisos)
            timestamp=enriched_timestamp,
            temperature=closest_forecast.temperature,
            humidity=float(closest_forecast.humidity),
            wind_speed=closest_forecast.wind_speed,
            wind_direction=closest_forecast.wind_direction,
            rain_probability=float(closest_forecast.precipitation_probability),
            rain_1h=closest_forecast.precipitation,
            clouds=float(closest_forecast.cloud_cover),
            weather_code=closest_forecast.weather_code,
            description=closest_forecast.description,
            # Dados mantidos do provider base (OpenMeteo não fornece)
            feels_like=base_weather.feels_like,
            pressure=base_weather.pressure,
            visibility=base_weather.visibility,
            rain_accumulated_day=base_weather.rain_accumulated_day,
            temp_min=base_weather.temp_min,
            temp_max=base_weather.temp_max,
            weather_alert=base_weather.weather_alert.copy()  # Cópia para não modificar original
        )
        
        logger.info("Weather enriched com dados hourly do OpenMeteo")
        return enriched
    
    @staticmethod
    def merge_alerts(
        base_weather: Weather,
        additional_alerts: List
    ) -> Weather:
        """
        Merge de alertas de múltiplas fontes sem duplicatas
        
        Args:
            base_weather: Weather com alertas base
            additional_alerts: Alertas adicionais para merge
        
        Returns:
            Weather com alertas merged
        """
        if not additional_alerts:
            return base_weather
        
        # Set de códigos existentes
        existing_codes = {alert.code for alert in base_weather.weather_alert}
        
        # Adicionar apenas alertas novos
        for alert in additional_alerts:
            if alert.code not in existing_codes:
                base_weather.weather_alert.append(alert)
                existing_codes.add(alert.code)
        
        logger.info(
            f"Merged alerts: {len(base_weather.weather_alert)} total "
            f"(+{len(additional_alerts)} novos candidatos)"
        )
        
        return base_weather
