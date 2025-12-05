"""
OpenMeteo Data Mapper - Transforma dados da API Open-Meteo para entities
LOCALIZAÇÃO: infrastructure (transforma dados externos → domínio)
"""
from typing import Dict, Any, List
from datetime import datetime
import math

from domain.entities.daily_forecast import DailyForecast
from domain.entities.hourly_forecast import HourlyForecast
from domain.entities.weather import Weather
from domain.helpers.rainfall_calculator import calculate_rainfall_intensity
from domain.constants import Weather as WeatherConstants
from shared.config.logger_config import get_logger

logger = get_logger(child=True)


def calculate_feels_like(temp: float, humidity: float, wind_speed: float) -> float:
    """
    Calcula sensação térmica (feels like) usando Heat Index ou Wind Chill
    
    Args:
        temp: Temperatura em °C
        humidity: Umidade relativa em %
        wind_speed: Velocidade do vento em km/h
    
    Returns:
        Temperatura aparente em °C
    """
    # Para temperaturas altas (> 27°C): usar Heat Index
    if temp > 27:
        # Fórmula simplificada do Heat Index
        # HI = T + 0.5555 × (VP - 10)
        # onde VP = 6.112 × e^(17.67 × T / (T + 243.5)) × (RH / 100)
        
        vapor_pressure = 6.112 * math.exp((17.67 * temp) / (temp + 243.5)) * (humidity / 100)
        heat_index = temp + 0.5555 * (vapor_pressure - 10)
        return round(heat_index, 1)
    
    # Para temperaturas baixas (< 10°C) com vento: usar Wind Chill
    elif temp < 10 and wind_speed > 4.8:
        # Fórmula Wind Chill (ajustada para km/h)
        # WC = 13.12 + 0.6215×T - 11.37×V^0.16 + 0.3965×T×V^0.16
        
        v_power = math.pow(wind_speed, 0.16)
        wind_chill = 13.12 + (0.6215 * temp) - (11.37 * v_power) + (0.3965 * temp * v_power)
        return round(wind_chill, 1)
    
    # Para temperaturas moderadas: retornar temperatura real
    return temp


class OpenMeteoDataMapper:
    """
    Mapper para transformar respostas da API Open-Meteo em entities de domínio
    
    Responsabilidade: Traduzir formato Open-Meteo → Domain entities
    Localização: Infrastructure (conhece detalhes da API externa)
    """
    
    @staticmethod
    def map_daily_response_to_forecasts(data: Dict[str, Any]) -> List[DailyForecast]:
        """
        Mapeia resposta /forecast (daily) da API Open-Meteo para DailyForecast entities
        OTIMIZADO: Validação antecipada e processamento eficiente
        
        Args:
            data: Resposta raw da API Open-Meteo (daily endpoint)
        
        Returns:
            Lista de DailyForecast entities
        """
        daily = data.get('daily', {})
        
        # Extrair arrays (mais eficiente que acessar dict repetidamente)
        dates = daily.get('time', [])
        temp_max = daily.get('temperature_2m_max', [])
        temp_min = daily.get('temperature_2m_min', [])
        apparent_temp_max = daily.get('apparent_temperature_max', [])
        apparent_temp_min = daily.get('apparent_temperature_min', [])
        precipitation = daily.get('precipitation_sum', [])
        rain_prob = daily.get('precipitation_probability_mean', [])
        wind_speed = daily.get('wind_speed_10m_max', [])
        wind_direction = daily.get('wind_direction_10m_dominant', [])
        uv_index = daily.get('uv_index_max', [])
        sunrise = daily.get('sunrise', [])
        sunset = daily.get('sunset', [])
        precip_hours = daily.get('precipitation_hours', [])
        
        forecasts = []
        
        for i, date in enumerate(dates):
            try:
                # Validação early-exit (dados essenciais)
                t_max = temp_max[i] if i < len(temp_max) else None
                t_min = temp_min[i] if i < len(temp_min) else None
                
                if t_max is None or t_min is None:
                    logger.warning(f"Dia {date}: temperaturas ausentes, pulando")
                    continue
                
                # Criar forecast com fallbacks para dados opcionais
                forecast = DailyForecast.from_openmeteo_data(
                    date=date,
                    temp_max=t_max,
                    temp_min=t_min,
                    precipitation=precipitation[i] if i < len(precipitation) else 0.0,
                    rain_prob=rain_prob[i] if i < len(rain_prob) else 0.0,
                    wind_speed=wind_speed[i] if i < len(wind_speed) else 0.0,
                    wind_direction=int(wind_direction[i]) if i < len(wind_direction) and wind_direction[i] is not None else 0,
                    uv_index=uv_index[i] if i < len(uv_index) else 0.0,
                    sunrise=sunrise[i] if i < len(sunrise) else "06:00",
                    sunset=sunset[i] if i < len(sunset) else "18:00",
                    precip_hours=precip_hours[i] if i < len(precip_hours) else 0.0,
                    apparent_temp_min=apparent_temp_min[i] if i < len(apparent_temp_min) else None,
                    apparent_temp_max=apparent_temp_max[i] if i < len(apparent_temp_max) else None
                )
                forecasts.append(forecast)
                
            except Exception as e:
                logger.warning(f"Falha ao processar dia {i}: {e}")
                continue
        
        return forecasts
    
    @staticmethod
    def map_hourly_response_to_forecasts(
        data: Dict[str, Any],
        max_hours: int
    ) -> List[HourlyForecast]:
        """
        Mapeia resposta /forecast (hourly) da API Open-Meteo para HourlyForecast entities
        OTIMIZADO: Slice limit e processamento eficiente
        
        Args:
            data: Resposta raw da API Open-Meteo (hourly endpoint)
            max_hours: Número máximo de horas a retornar
        
        Returns:
            Lista de HourlyForecast entities (até max_hours)
        """
        hourly = data.get('hourly', {})
        
        # Extrair arrays
        times = hourly.get('time', [])
        temps = hourly.get('temperature_2m', [])
        apparent_temps = hourly.get('apparent_temperature', [])
        precip = hourly.get('precipitation', [])
        precip_prob = hourly.get('precipitation_probability', [])
        humidity = hourly.get('relative_humidity_2m', [])
        wind_speed = hourly.get('wind_speed_10m', [])
        wind_dir = hourly.get('wind_direction_10m', [])
        clouds = hourly.get('cloud_cover', [])
        pressure = hourly.get('pressure_msl', [])
        visibility_data = hourly.get('visibility', [])
        uv_index = hourly.get('uv_index', [])
        is_day = hourly.get('is_day', [])
        weather_codes = hourly.get('weather_code', [])
        
        # Limitar ao número máximo de horas
        limit = min(len(times), max_hours)
        
        forecasts = []
        for i in range(limit):
            try:
                weather_code = int(weather_codes[i]) if i < len(weather_codes) else 0
                precipitation_mm = precip[i] if i < len(precip) else 0.0
                precipitation_prob = int(precip_prob[i]) if i < len(precip_prob) else 0
                
                # Calcular rainfall_intensity
                rainfall_intensity = calculate_rainfall_intensity(precipitation_prob, precipitation_mm)
                
                forecast = HourlyForecast(
                    timestamp=times[i],
                    temperature=temps[i] if i < len(temps) else 0.0,
                    precipitation=precipitation_mm,
                    precipitation_probability=precipitation_prob,
                    rainfall_intensity=rainfall_intensity,
                    humidity=int(humidity[i]) if i < len(humidity) else 0,
                    wind_speed=wind_speed[i] if i < len(wind_speed) else 0.0,
                    wind_direction=int(wind_dir[i]) if i < len(wind_dir) else 0,
                    cloud_cover=int(clouds[i]) if i < len(clouds) else 0,
                    pressure=pressure[i] if i < len(pressure) else None,
                    visibility=visibility_data[i] if i < len(visibility_data) else None,
                    uv_index=uv_index[i] if i < len(uv_index) else None,
                    is_day=int(is_day[i]) if i < len(is_day) else None,
                    apparent_temperature=apparent_temps[i] if i < len(apparent_temps) else None,
                    weather_code=0,  # Será calculado pela entidade via classify_weather_condition
                    description=""  # Será calculado pela entidade via classify_weather_condition
                )
                forecasts.append(forecast)
                
            except Exception as e:
                logger.warning(f"Falha ao processar hora {i}: {e}")
                continue
        
        return forecasts
    
    @staticmethod
    def map_hourly_to_weather(
        hourly_forecast: HourlyForecast,
        city_id: str,
        city_name: str,
        temp_min: float = 0.0,
        temp_max: float = 0.0,
        rain_accumulated_day: float = 0.0
    ) -> Weather:
        """
        Converte HourlyForecast para Weather entity
        Usado quando OpenMeteo é fonte de dados atuais
        
        Args:
            hourly_forecast: Primeiro item do forecast hourly
            city_id: ID da cidade
            city_name: Nome da cidade
            temp_min: Temperatura mínima do dia (opcional)
            temp_max: Temperatura máxima do dia (opcional)
            rain_accumulated_day: Precipitação acumulada do dia (opcional)
        
        Returns:
            Weather entity
        """
        from zoneinfo import ZoneInfo
        
        # Usar apparent_temperature da API se disponível, senão calcular
        if hourly_forecast.apparent_temperature is not None:
            feels_like_calc = hourly_forecast.apparent_temperature
        else:
            feels_like_calc = calculate_feels_like(
                hourly_forecast.temperature,
                float(hourly_forecast.humidity),
                hourly_forecast.wind_speed
            )
        
        # Usar pressure e visibility da API, com fallbacks para valores padrão
        pressure_value = hourly_forecast.pressure if hourly_forecast.pressure is not None else 1013.0
        visibility_value = hourly_forecast.visibility if hourly_forecast.visibility is not None else 10000.0
        
        # Converter timestamp para datetime com timezone
        timestamp_dt = datetime.fromisoformat(hourly_forecast.timestamp)
        if timestamp_dt.tzinfo is None:
            timestamp_dt = timestamp_dt.replace(tzinfo=ZoneInfo("America/Sao_Paulo"))
        
        # Determinar is_day a partir do hourly_forecast (OpenMeteo fornece esse campo)
        is_day_value = True  # Default
        if hourly_forecast.is_day is not None:
            is_day_value = bool(hourly_forecast.is_day)
        
        return Weather(
            city_id=city_id,
            city_name=city_name,
            timestamp=timestamp_dt,
            temperature=hourly_forecast.temperature,
            humidity=float(hourly_forecast.humidity),
            wind_speed=hourly_forecast.wind_speed,
            wind_direction=hourly_forecast.wind_direction,
            rain_probability=float(hourly_forecast.precipitation_probability),
            rain_1h=hourly_forecast.precipitation,
            rain_accumulated_day=rain_accumulated_day,
            description="",  # Será calculado pela entidade via classify_weather_condition
            feels_like=feels_like_calc,
            pressure=pressure_value,
            visibility=visibility_value,
            clouds=float(hourly_forecast.cloud_cover),
            weather_alert=[],  # Gerados externamente
            weather_code=0,  # Será calculado pela entidade via classify_weather_condition
            temp_min=temp_min,
            temp_max=temp_max,
            is_day=is_day_value
        )
