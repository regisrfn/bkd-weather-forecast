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
            
            # 💾 Salvar no cache (async, TTL 6h = 21600 segundos)
            if self.cache and self.cache.is_enabled():
                await self.cache.set(cache_key, data, ttl_seconds=21600)
        
        # 🔄 Processar dados e retornar List[DailyForecast]
        return self._process_daily_data(data)
    
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
                forecast = DailyForecast.from_openmeteo_data(
                    date=dates[i],
                    temp_max=temp_max[i] if i < len(temp_max) else 0.0,
                    temp_min=temp_min[i] if i < len(temp_min) else 0.0,
                    precipitation=precipitation[i] if i < len(precipitation) else 0.0,
                    rain_prob=rain_prob[i] if i < len(rain_prob) else 0.0,
                    wind_speed=wind_speed[i] if i < len(wind_speed) else 0.0,
                    wind_direction=int(wind_direction[i]) if i < len(wind_direction) else 0,
                    uv_index=uv_index[i] if i < len(uv_index) else 0.0,
                    sunrise=sunrise[i] if i < len(sunrise) else "06:00",
                    sunset=sunset[i] if i < len(sunset) else "18:00",
                    precip_hours=precip_hours[i] if i < len(precip_hours) else 0.0
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
