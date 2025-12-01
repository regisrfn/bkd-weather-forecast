"""
Async Open-Meteo Repository - Repositório 100% assíncrono para Open-Meteo API
Complementa dados do OpenWeather com previsões estendidas de até 16 dias
"""
import os
import math
from datetime import datetime
from typing import List, Optional, Dict, Any
from ddtrace import tracer

from domain.entities.daily_forecast import DailyForecast
from infrastructure.adapters.cache.async_dynamodb_cache import AsyncDynamoDBCache, get_async_cache
from infrastructure.adapters.config.aiohttp_session_manager import get_aiohttp_session_manager
from shared.config.logger_config import get_logger

logger = get_logger(child=True)


class AsyncOpenMeteoRepository:
    """
    Repositório 100% assíncrono para Open-Meteo Forecast API
    
    Benefícios:
    - API gratuita sem rate limits agressivos
    - Previsões de até 16 dias
    - Dados complementares (UV index, nascer/pôr do sol)
    - Cache DynamoDB com TTL de 6 horas
    - 100% async com aiohttp (sem GIL)
    
    Estratégia de Cache:
    1. Busca cache DynamoDB por city_id (prefix: openmeteo_)
    2. Se MISS, chama Open-Meteo API (async HTTP)
    3. Salva resposta completa no cache (TTL 6h)
    4. Processa dados e retorna List[DailyForecast]
    """
    
    def __init__(
        self,
        cache: Optional[AsyncDynamoDBCache] = None
    ):
        """
        Inicializa repositório async
        
        Args:
            cache: Cache DynamoDB async (usa factory se None)
        """
        self.base_url = "https://api.open-meteo.com/v1"
        self.cache = cache or get_async_cache()
        
        # Usar gerenciador centralizado de sessão HTTP
        self.session_manager = get_aiohttp_session_manager(
            total_timeout=15,
            connect_timeout=5,
            sock_read_timeout=10,
            limit=100,
            limit_per_host=30,
            ttl_dns_cache=300
        )
    
    @tracer.wrap(resource="async_openmeteo.get_extended_forecast")
    async def get_extended_forecast(
        self,
        city_id: str,
        latitude: float,
        longitude: float,
        forecast_days: int = 16
    ) -> List[DailyForecast]:
        """
        Busca previsões diárias estendidas de forma ASSÍNCRONA
        
        Flow:
        1. Cache GET async (DynamoDB, prefix: openmeteo_{city_id})
        2. Se MISS: HTTP GET async (Open-Meteo API, sem GIL)
        3. Cache SET async (DynamoDB, TTL 6h)
        4. Parse e retorna List[DailyForecast]
        
        Args:
            city_id: ID da cidade (chave de cache)
            latitude: Latitude
            longitude: Longitude
            forecast_days: Número de dias de previsão (1-16)
        
        Returns:
            Lista de DailyForecast (até 16 dias)
        
        Raises:
            ValueError: Se forecast_days < 1 ou > 16
            aiohttp.ClientError: Se API falhar
        """
        if forecast_days < 1 or forecast_days > 16:
            raise ValueError(f"forecast_days must be between 1 and 16, got {forecast_days}")
        
        cache_key = f"openmeteo_{city_id}"
        
        # 🔍 Tentar cache primeiro (async, sem GIL)
        data = None
        if self.cache and self.cache.is_enabled():
            data = await self.cache.get(cache_key)
            if data:
                logger.info("Open-Meteo cache hit", cache_key=cache_key)
        
        # 📡 Cache MISS: chamar API (async HTTP, sem GIL)
        if data is None:
            logger.info("Open-Meteo cache miss, fetching from API", cache_key=cache_key)
            
            url = f"{self.base_url}/forecast"
            params = {
                'latitude': latitude,
                'longitude': longitude,
                'daily': ','.join([
                    'temperature_2m_max',
                    'temperature_2m_min',
                    'precipitation_sum',
                    'precipitation_probability_mean',
                    'wind_speed_10m_max',
                    'wind_direction_10m_dominant',
                    'uv_index_max',
                    'sunrise',
                    'sunset',
                    'precipitation_hours'
                ]),
                'timezone': 'America/Sao_Paulo',
                'forecast_days': forecast_days
            }
            
            session = await self.session_manager.get_session()
            
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
            
            # 💾 Salvar no cache (async, TTL 1h = 3600 segundos)
            if self.cache and self.cache.is_enabled():
                await self.cache.set(cache_key, data, ttl_seconds=3600)
        
        # 🔄 Processar dados e retornar List[DailyForecast]
        return self._process_daily_data(data)
    
    @tracer.wrap(resource="async_openmeteo.get_hourly_forecast")
    async def get_hourly_forecast(
        self,
        city_id: str,
        latitude: float,
        longitude: float,
        forecast_hours: int = 168  # 7 days = 168 hours
    ) -> List:
        """
        Busca previsões horárias do Open-Meteo de forma ASSÍNCRONA
        
        Flow:
        1. Cache GET async (DynamoDB, prefix: openmeteo_hourly_{city_id})
        2. Se MISS: HTTP GET async (Open-Meteo API, sem GIL)
        3. Cache SET async (DynamoDB, TTL 1h)
        4. Parse e retorna List[HourlyForecast]
        
        Args:
            city_id: ID da cidade (chave de cache)
            latitude: Latitude
            longitude: Longitude
            forecast_hours: Número de horas de previsão (default 168 = 7 dias)
        
        Returns:
            Lista de HourlyForecast (até 168 horas)
        
        Raises:
            aiohttp.ClientError: Se API falhar
        """
        from domain.entities.hourly_forecast import HourlyForecast
        
        cache_key = f"openmeteo_hourly_{city_id}"
        
        # 🔍 Tentar cache primeiro (async, sem GIL)
        data = None
        if self.cache and self.cache.is_enabled():
            data = await self.cache.get(cache_key)
            if data:
                logger.info("Open-Meteo hourly cache hit", cache_key=cache_key)
        
        # 📡 Cache MISS: chamar API (async HTTP, sem GIL)
        if data is None:
            logger.info("Open-Meteo hourly cache miss, fetching from API", cache_key=cache_key)
            
            url = f"{self.base_url}/forecast"
            params = {
                'latitude': latitude,
                'longitude': longitude,
                'hourly': ','.join([
                    'temperature_2m',
                    'precipitation',
                    'precipitation_probability',
                    'relative_humidity_2m',
                    'wind_speed_10m',
                    'wind_direction_10m',
                    'cloud_cover',
                    'weather_code'
                ]),
                'timezone': 'America/Sao_Paulo',
                'forecast_days': min(16, (forecast_hours // 24) + 1)
            }
            
            session = await self.session_manager.get_session()
            
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
            
            # 💾 Salvar no cache (async, TTL 1h = 3600 segundos)
            if self.cache and self.cache.is_enabled():
                await self.cache.set(cache_key, data, ttl_seconds=3600)
        
        # 🔄 Processar dados e retornar List[HourlyForecast]
        return self._process_hourly_data(data, forecast_hours)
    
    def _process_hourly_data(self, data: Dict[str, Any], max_hours: int) -> List:
        """
        Processa dados hourly da API Open-Meteo e retorna lista de HourlyForecast
        
        Args:
            data: Resposta completa da API Open-Meteo
            max_hours: Número máximo de horas a processar
        
        Returns:
            Lista de HourlyForecast parseados
        """
        from domain.entities.hourly_forecast import HourlyForecast
        
        hourly = data.get('hourly', {})
        
        times = hourly.get('time', [])
        temps = hourly.get('temperature_2m', [])
        precip = hourly.get('precipitation', [])
        precip_prob = hourly.get('precipitation_probability', [])
        humidity = hourly.get('relative_humidity_2m', [])
        wind_speed = hourly.get('wind_speed_10m', [])
        wind_dir = hourly.get('wind_direction_10m', [])
        clouds = hourly.get('cloud_cover', [])
        weather_codes = hourly.get('weather_code', [])
        
        forecasts = []
        for i in range(min(len(times), max_hours)):
            try:
                weather_code = int(weather_codes[i]) if i < len(weather_codes) else 0
                forecast = HourlyForecast(
                    timestamp=times[i],
                    temperature=temps[i] if i < len(temps) else 0.0,
                    precipitation=precip[i] if i < len(precip) else 0.0,
                    precipitation_probability=int(precip_prob[i]) if i < len(precip_prob) else 0,
                    humidity=int(humidity[i]) if i < len(humidity) else 0,
                    wind_speed=wind_speed[i] if i < len(wind_speed) else 0.0,
                    wind_direction=int(wind_dir[i]) if i < len(wind_dir) else 0,
                    cloud_cover=int(clouds[i]) if i < len(clouds) else 0,
                    weather_code=weather_code,
                    description=self._get_weather_description(weather_code)
                )
                forecasts.append(forecast)
            except Exception as e:
                logger.warning(f"Failed to parse hour {i}: {e}")
                continue
        
        return forecasts
    
    def _process_daily_data(self, data: Dict[str, Any]) -> List[DailyForecast]:
        """
        Processa dados da API Open-Meteo e retorna lista de DailyForecast
        
        Args:
            data: Resposta completa da API Open-Meteo
        
        Returns:
            Lista de DailyForecast parseados
        """
        daily = data.get('daily', {})
        
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
        
        # Iterar sobre todos os dias disponíveis
        for i in range(len(dates)):
            try:
                # Extrair valores com fallback para None
                t_max = temp_max[i] if i < len(temp_max) else None
                t_min = temp_min[i] if i < len(temp_min) else None
                precip = precipitation[i] if i < len(precipitation) else None
                r_prob = rain_prob[i] if i < len(rain_prob) else None
                w_speed = wind_speed[i] if i < len(wind_speed) else None
                w_dir = wind_direction[i] if i < len(wind_direction) else None
                uv = uv_index[i] if i < len(uv_index) else None
                sr = sunrise[i] if i < len(sunrise) else None
                ss = sunset[i] if i < len(sunset) else None
                p_hours = precip_hours[i] if i < len(precip_hours) else None
                
                # Pular dia se dados essenciais (temperaturas) forem None
                if t_max is None or t_min is None:
                    logger.warning(f"Skipping day {dates[i]}: missing temperature data (max={t_max}, min={t_min})")
                    continue
                
                # Usar 0.0 como fallback para dados opcionais (mas não None)
                forecast = DailyForecast.from_openmeteo_data(
                    date=dates[i],
                    temp_max=t_max,
                    temp_min=t_min,
                    precipitation=precip if precip is not None else 0.0,
                    rain_prob=r_prob if r_prob is not None else 0.0,
                    wind_speed=w_speed if w_speed is not None else 0.0,
                    wind_direction=int(w_dir) if w_dir is not None else 0,
                    uv_index=uv if uv is not None else 0.0,
                    sunrise=sr if sr is not None else "06:00",
                    sunset=ss if ss is not None else "18:00",
                    precip_hours=p_hours if p_hours is not None else 0.0
                )
                forecasts.append(forecast)
            except Exception as e:
                logger.warning(f"Failed to parse day {i}: {e}")
                continue
        
        return forecasts
    
    @staticmethod
    def calculate_moon_phase(date_str: str) -> str:
        """
        Calcula fase da lua baseado na data
        
        Algoritmo simplificado baseado em ciclo lunar de ~29.53 dias
        Referência: 2000-01-06 foi Lua Nova
        
        Args:
            date_str: Data no formato YYYY-MM-DD
        
        Returns:
            Nome da fase da lua em português
        """
        try:
            # Data de referência (Lua Nova conhecida)
            reference = datetime(2000, 1, 6)
            target = datetime.strptime(date_str, '%Y-%m-%d')
            
            # Calcular dias desde a referência
            days_since = (target - reference).days
            
            # Ciclo lunar médio: 29.53 dias
            lunar_cycle = 29.53
            
            # Posição no ciclo (0-1)
            phase = (days_since % lunar_cycle) / lunar_cycle
            
            # Determinar fase (8 fases principais)
            if phase < 0.0625:
                return "🌑 Lua Nova"
            elif phase < 0.1875:
                return "🌒 Lua Crescente"
            elif phase < 0.3125:
                return "🌓 Quarto Crescente"
            elif phase < 0.4375:
                return "🌔 Lua Gibosa Crescente"
            elif phase < 0.5625:
                return "🌕 Lua Cheia"
            elif phase < 0.6875:
                return "🌖 Lua Gibosa Minguante"
            elif phase < 0.8125:
                return "🌗 Quarto Minguante"
            else:
                return "🌘 Lua Minguante"
        except Exception as e:
            logger.warning(f"Failed to calculate moon phase: {e}")
            return "🌑 Lua"
    
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


# Factory singleton
_async_openmeteo_repository_instance = None


def get_async_openmeteo_repository(
    cache: Optional[AsyncDynamoDBCache] = None
) -> AsyncOpenMeteoRepository:
    """
    Factory to get async Open-Meteo repository singleton
    Reuses between Lambda invocations (warm starts)
    Sessão aiohttp é global e compartilhada
    
    Args:
        cache: Cache DynamoDB async
    
    Returns:
        AsyncOpenMeteoRepository instance
    """
    global _async_openmeteo_repository_instance
    
    if _async_openmeteo_repository_instance is None:
        _async_openmeteo_repository_instance = AsyncOpenMeteoRepository(cache=cache)
    
    return _async_openmeteo_repository_instance
