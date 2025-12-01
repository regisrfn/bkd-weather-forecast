"""
Hourly Weather Processor - Processa dados horários do Open-Meteo
Extrai current weather da hora mais próxima e converte para Weather entity
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Optional

from domain.entities.weather import Weather
from domain.entities.hourly_forecast import HourlyForecast
from shared.config.logger_config import get_logger

logger = get_logger(child=True)


class HourlyWeatherProcessor:
    """
    Processa dados horários do Open-Meteo para enriquecer Weather entities
    com dados mais precisos mantendo campos completos do OpenWeather
    """
    
    @staticmethod
    def enrich_weather_with_hourly(
        base_weather: Weather,
        hourly_forecasts: List[HourlyForecast],
        target_datetime: Optional[datetime] = None
    ) -> Optional[Weather]:
        """
        Enriquece Weather entity do OpenWeather com dados hourly do Open-Meteo
        
        Strategy:
        1. Mantém TODOS os dados do OpenWeather (visibility, pressure, feels_like, etc)
        2. Sobrescreve apenas campos disponíveis no hourly (temperatura, vento, precipitação)
        3. Busca hora mais próxima para dados mais precisos
        
        Args:
            base_weather: Weather entity do OpenWeather (base completa)
            hourly_forecasts: Lista de previsões horárias do Open-Meteo
            target_datetime: Datetime alvo (None = próxima hora)
        
        Returns:
            Weather entity enriquecido ou None se não houver dados hourly válidos
        """
        if not hourly_forecasts:
            logger.warning("Empty hourly forecasts list")
            return None
        
        # Encontrar hora mais próxima
        closest_forecast = HourlyWeatherProcessor._find_closest_hourly(
            hourly_forecasts,
            target_datetime or base_weather.timestamp
        )
        
        if closest_forecast is None:
            logger.warning("No valid hourly forecast found")
            return None
        
        # Parse timestamp do hourly
        hourly_timestamp = datetime.fromisoformat(closest_forecast.timestamp)
        if hourly_timestamp.tzinfo is None:
            hourly_timestamp = hourly_timestamp.replace(tzinfo=ZoneInfo("America/Sao_Paulo"))
        
        # Calcular dados diários a partir do hourly
        daily_rain_accumulation = HourlyWeatherProcessor._calculate_daily_rain_accumulation(
            hourly_forecasts,
            hourly_timestamp
        )
        
        temp_min, temp_max = HourlyWeatherProcessor._calculate_daily_temp_extremes(
            hourly_forecasts,
            hourly_timestamp
        )
        
        # Gerar alertas atualizados com dados hourly
        weather_alerts = Weather.get_weather_alert(
            weather_code=closest_forecast.weather_code,
            rain_prob=float(closest_forecast.precipitation_probability),
            wind_speed=closest_forecast.wind_speed,
            forecast_time=hourly_timestamp,
            rain_1h=closest_forecast.precipitation,
            temperature=closest_forecast.temperature,
            visibility=base_weather.visibility  # Manter do OpenWeather
        )
        
        # ENRIQUECER: Criar novo Weather mantendo dados completos do OpenWeather
        return Weather(
            city_id=base_weather.city_id,
            city_name=base_weather.city_name,
            timestamp=hourly_timestamp,  # Atualizar para hora mais próxima
            # Dados HOURLY (Open-Meteo) - mais precisos
            temperature=closest_forecast.temperature,
            humidity=float(closest_forecast.humidity),
            wind_speed=closest_forecast.wind_speed,
            wind_direction=closest_forecast.wind_direction,
            rain_probability=float(closest_forecast.precipitation_probability),
            rain_1h=closest_forecast.precipitation,
            rain_accumulated_day=daily_rain_accumulation,
            clouds=float(closest_forecast.cloud_cover),
            weather_code=closest_forecast.weather_code,
            temp_min=temp_min,
            temp_max=temp_max,
            weather_alert=weather_alerts,
            # Dados OPENWEATHER (manter) - campos que Open-Meteo não fornece
            description=HourlyWeatherProcessor._get_weather_description(closest_forecast.weather_code),
            feels_like=base_weather.feels_like,  # ✅ Mantém do OpenWeather
            pressure=base_weather.pressure,      # ✅ Mantém do OpenWeather
            visibility=base_weather.visibility   # ✅ Mantém do OpenWeather
        )
    
    @staticmethod
    def _find_closest_hourly(
        hourly_forecasts: List[HourlyForecast],
        target_datetime: datetime
    ) -> Optional[HourlyForecast]:
        """
        Encontra a previsão horária mais próxima do datetime alvo
        
        Args:
            hourly_forecasts: Lista de previsões horárias
            target_datetime: Datetime de referência
        
        Returns:
            HourlyForecast mais próximo ou None
        """
        # Garantir timezone
        if target_datetime.tzinfo is None:
            reference_datetime = target_datetime.replace(tzinfo=ZoneInfo("America/Sao_Paulo"))
        else:
            reference_datetime = target_datetime.astimezone(ZoneInfo("America/Sao_Paulo"))
        
        closest_forecast = None
        min_diff = float('inf')
        
        for forecast in hourly_forecasts:
            try:
                forecast_time = datetime.fromisoformat(forecast.timestamp)
                if forecast_time.tzinfo is None:
                    forecast_time = forecast_time.replace(tzinfo=ZoneInfo("America/Sao_Paulo"))
                else:
                    forecast_time = forecast_time.astimezone(ZoneInfo("America/Sao_Paulo"))
                
                diff = abs((forecast_time - reference_datetime).total_seconds())
                
                if diff < min_diff:
                    min_diff = diff
                    closest_forecast = forecast
            except Exception as e:
                logger.warning(f"Failed to parse forecast timestamp {forecast.timestamp}: {e}")
                continue
        
        return closest_forecast
    
    @staticmethod
    def _calculate_daily_rain_accumulation(
        hourly_forecasts: List[HourlyForecast],
        target_timestamp: datetime
    ) -> float:
        """
        Calcula acumulado de chuva do dia a partir das previsões horárias
        
        Args:
            hourly_forecasts: Lista de previsões horárias
            target_timestamp: Timestamp de referência
        
        Returns:
            Acumulado de chuva do dia em mm
        """
        target_date = target_timestamp.date()
        total_rain = 0.0
        
        for forecast in hourly_forecasts:
            try:
                forecast_time = datetime.fromisoformat(forecast.timestamp)
                if forecast_time.tzinfo is None:
                    forecast_time = forecast_time.replace(tzinfo=ZoneInfo("America/Sao_Paulo"))
                
                if forecast_time.date() == target_date:
                    total_rain += forecast.precipitation
            except Exception as e:
                logger.warning(f"Failed to process forecast for rain calculation: {e}")
                continue
        
        return total_rain
    
    @staticmethod
    def _calculate_daily_temp_extremes(
        hourly_forecasts: List[HourlyForecast],
        target_timestamp: datetime
    ) -> tuple:
        """
        Calcula temperaturas mínima e máxima do dia
        
        Args:
            hourly_forecasts: Lista de previsões horárias
            target_timestamp: Timestamp de referência
        
        Returns:
            Tuple (temp_min, temp_max)
        """
        target_date = target_timestamp.date()
        temperatures = []
        
        for forecast in hourly_forecasts:
            try:
                forecast_time = datetime.fromisoformat(forecast.timestamp)
                if forecast_time.tzinfo is None:
                    forecast_time = forecast_time.replace(tzinfo=ZoneInfo("America/Sao_Paulo"))
                
                if forecast_time.date() == target_date:
                    temperatures.append(forecast.temperature)
            except Exception as e:
                logger.warning(f"Failed to process forecast for temp calculation: {e}")
                continue
        
        if not temperatures:
            return (0.0, 0.0)
        
        return (min(temperatures), max(temperatures))
    
    @staticmethod
    def _get_weather_description(weather_code: int) -> str:
        """
        Converte WMO weather code para descrição em português
        
        WMO Weather interpretation codes (WW):
        0: Céu limpo
        1-3: Mainly clear, partly cloudy, and overcast
        45-48: Fog
        51-57: Drizzle
        61-67: Rain
        71-77: Snow
        80-82: Rain showers
        85-86: Snow showers
        95-99: Thunderstorm
        
        Args:
            weather_code: WMO weather code
        
        Returns:
            Descrição em português
        """
        descriptions = {
            0: "Céu limpo",
            1: "Principalmente limpo",
            2: "Parcialmente nublado",
            3: "Nublado",
            45: "Neblina",
            48: "Nevoeiro com geada",
            51: "Garoa leve",
            53: "Garoa moderada",
            55: "Garoa intensa",
            56: "Garoa congelante leve",
            57: "Garoa congelante intensa",
            61: "Chuva leve",
            63: "Chuva moderada",
            65: "Chuva forte",
            66: "Chuva congelante leve",
            67: "Chuva congelante forte",
            71: "Neve leve",
            73: "Neve moderada",
            75: "Neve forte",
            77: "Grãos de neve",
            80: "Pancadas de chuva leves",
            81: "Pancadas de chuva moderadas",
            82: "Pancadas de chuva fortes",
            85: "Pancadas de neve leves",
            86: "Pancadas de neve fortes",
            95: "Tempestade",
            96: "Tempestade com granizo leve",
            99: "Tempestade com granizo forte"
        }
        
        return descriptions.get(weather_code, "Condição desconhecida")
