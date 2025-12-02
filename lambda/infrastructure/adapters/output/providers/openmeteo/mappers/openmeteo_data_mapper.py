"""
OpenMeteo Data Mapper - Transforma dados da API Open-Meteo para entities
LOCALIZAÇÃO: infrastructure (transforma dados externos → domínio)
"""
from typing import Dict, Any, List
from datetime import datetime

from domain.entities.daily_forecast import DailyForecast
from domain.entities.hourly_forecast import HourlyForecast
from domain.entities.weather import Weather
from domain.helpers.rainfall_calculator import calculate_rainfall_intensity
from domain.constants import Weather as WeatherConstants
from shared.config.logger_config import get_logger

logger = get_logger(child=True)


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
                    precip_hours=precip_hours[i] if i < len(precip_hours) else 0.0
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
        precip = hourly.get('precipitation', [])
        precip_prob = hourly.get('precipitation_probability', [])
        humidity = hourly.get('relative_humidity_2m', [])
        wind_speed = hourly.get('wind_speed_10m', [])
        wind_dir = hourly.get('wind_direction_10m', [])
        clouds = hourly.get('cloud_cover', [])
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
                    weather_code=weather_code,
                    description=OpenMeteoDataMapper.get_wmo_description(weather_code)
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
        city_name: str
    ) -> Weather:
        """
        Converte HourlyForecast para Weather entity
        Usado quando OpenMeteo é fonte de dados atuais
        
        Args:
            hourly_forecast: Primeiro item do forecast hourly
            city_id: ID da cidade
            city_name: Nome da cidade
        
        Returns:
            Weather entity
        """
        return Weather(
            city_id=city_id,
            city_name=city_name,
            timestamp=datetime.fromisoformat(hourly_forecast.timestamp),
            temperature=hourly_forecast.temperature,
            humidity=float(hourly_forecast.humidity),
            wind_speed=hourly_forecast.wind_speed,
            wind_direction=hourly_forecast.wind_direction,
            rain_probability=float(hourly_forecast.precipitation_probability),
            rain_1h=hourly_forecast.precipitation,
            rain_accumulated_day=0.0,  # Calculado externamente se necessário
            description=hourly_forecast.description,
            feels_like=0.0,  # OpenMeteo não fornece
            pressure=0.0,  # OpenMeteo não fornece
            visibility=10000.0,  # Valor padrão (10km)
            clouds=float(hourly_forecast.cloud_cover),
            weather_alert=[],  # Gerados externamente
            weather_code=hourly_forecast.weather_code,
            temp_min=0.0,  # Calculado externamente
            temp_max=0.0  # Calculado externamente
        )
    
    @staticmethod
    def get_wmo_description(weather_code: int) -> str:
        """
        Retorna descrição PT-BR para código WMO
        
        Args:
            weather_code: Código WMO
        
        Returns:
            Descrição em português
        """
        return WeatherConstants.WMO_DESCRIPTIONS.get(
            weather_code,
            "Condição desconhecida"
        )
