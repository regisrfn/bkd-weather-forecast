"""Open-Meteo Provider - Implementação do provider para Open-Meteo API"""

from typing import Optional, List
from datetime import datetime
from ddtrace import tracer

from application.ports.output.weather_provider_port import IWeatherProvider
from domain.entities.weather import Weather
from domain.entities.daily_forecast import DailyForecast
from domain.entities.hourly_forecast import HourlyForecast
from domain.constants import API, Cache
from infrastructure.adapters.output.providers.openmeteo.mappers import OpenMeteoDataMapper
from infrastructure.adapters.output.cache.async_dynamodb_cache import AsyncDynamoDBCache, get_async_cache
from infrastructure.adapters.output.http.aiohttp_session_manager import get_aiohttp_session_manager


class OpenMeteoProvider(IWeatherProvider):
    """
    Provider para Open-Meteo Forecast API
    
    Características:
    - API gratuita sem rate limits agressivos
    - Previsões diárias de até 16 dias
    - Previsões horárias de até 168 horas (7 dias)
    - Dados astronômicos (nascer/pôr do sol, fase lua)
    - Cache DynamoDB com TTL de 1 hora
    - 100% async com aiohttp
    """
    
    def __init__(
        self,
        cache: Optional[AsyncDynamoDBCache] = None
    ):
        """
        Inicializa provider
        
        Args:
            cache: Cache DynamoDB async (usa factory se None)
        """
        self.base_url = API.OPENMETEO_BASE_URL
        self.cache = cache or get_async_cache()
        
        # Usar gerenciador centralizado de sessão HTTP
        self.session_manager = get_aiohttp_session_manager(
            total_timeout=API.HTTP_TIMEOUT_TOTAL,
            connect_timeout=API.HTTP_TIMEOUT_CONNECT,
            sock_read_timeout=API.HTTP_TIMEOUT_READ,
            limit=API.HTTP_CONNECTION_LIMIT,
            limit_per_host=API.HTTP_CONNECTION_LIMIT_PER_HOST,
            ttl_dns_cache=API.DNS_CACHE_TTL
        )
    
    @property
    def provider_name(self) -> str:
        return "OpenMeteo"
    
    @property
    def supports_current_weather(self) -> bool:
        return True  # Via hourly data
    
    @property
    def supports_daily_forecast(self) -> bool:
        return True
    
    @property
    def supports_hourly_forecast(self) -> bool:
        return True
    
    async def get_current_weather(
        self,
        latitude: float,
        longitude: float,
        city_id: str,
        city_name: str,
        target_datetime: Optional[datetime] = None
    ) -> Weather:
        """
        OpenMeteo fornece dados atuais via hourly forecast
        Busca forecast hourly e extrai hora mais próxima
        """
        hourly_forecasts = await self.get_hourly_forecast(
            latitude=latitude,
            longitude=longitude,
            city_id=city_id,
            hours=24  # Apenas próximas 24h para current
        )
        
        if not hourly_forecasts:
            raise ValueError("Nenhuma previsão horária disponível no OpenMeteo")
        
        # Converter primeiro hourly para Weather entity
        return OpenMeteoDataMapper.map_hourly_to_weather(
            hourly_forecast=hourly_forecasts[0],
            city_id=city_id,
            city_name=city_name
        )
    
    @tracer.wrap(resource="openmeteo.get_daily_forecast")
    async def get_daily_forecast(
        self,
        latitude: float,
        longitude: float,
        city_id: str,
        days: int = 16
    ) -> List[DailyForecast]:
        """
        Busca previsões diárias do Open-Meteo
        
        Flow:
        1. Tenta cache DynamoDB (prefix: openmeteo_)
        2. Se MISS: chama API Open-Meteo (async HTTP)
        3. Salva no cache (TTL 1h)
        4. Processa e retorna List[DailyForecast]
        """
        if days < 1 or days > 16:
            raise ValueError(f"days deve estar entre 1 e 16, recebeu {days}")
        
        cache_key = f"{Cache.PREFIX_OPENMETEO_DAILY}{city_id}"
        
        # 🔍 Tentar cache primeiro
        data = None
        if self.cache and self.cache.is_enabled():
            data = await self.cache.get(cache_key)
        
        # 📡 Cache MISS: chamar API
        if data is None:
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
                'forecast_days': days
            }
            
            session = await self.session_manager.get_session()
            
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
            
            # 💾 Salvar no cache
            if self.cache and self.cache.is_enabled():
                await self.cache.set(cache_key, data, ttl_seconds=Cache.TTL_OPENMETEO_DAILY)
        
        # 🔄 Processar dados usando mapper de infrastructure
        return OpenMeteoDataMapper.map_daily_response_to_forecasts(data)
    
    @tracer.wrap(resource="openmeteo.get_hourly_forecast")
    async def get_hourly_forecast(
        self,
        latitude: float,
        longitude: float,
        city_id: str,
        hours: int = 168
    ) -> List[HourlyForecast]:
        """
        Busca previsões horárias do Open-Meteo
        
        Flow:
        1. Tenta cache DynamoDB (prefix: openmeteo_hourly_)
        2. Se MISS: chama API Open-Meteo (async HTTP)
        3. Salva no cache (TTL 1h)
        4. Processa e retorna List[HourlyForecast]
        """
        cache_key = f"{Cache.PREFIX_OPENMETEO_HOURLY}{city_id}"
        
        # 🔍 Tentar cache primeiro
        data = None
        if self.cache and self.cache.is_enabled():
            data = await self.cache.get(cache_key)
        
        # 📡 Cache MISS: chamar API
        if data is None:
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
                'forecast_days': min(16, (hours // 24) + 1)
            }
            
            session = await self.session_manager.get_session()
            
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
            
            # 💾 Salvar no cache
            if self.cache and self.cache.is_enabled():
                await self.cache.set(cache_key, data, ttl_seconds=Cache.TTL_OPENMETEO_HOURLY)
        
        # 🔄 Processar dados usando mapper de infrastructure
        return OpenMeteoDataMapper.map_hourly_response_to_forecasts(data, max_hours=hours)


# Factory singleton
_provider_instance = None


def get_openmeteo_provider(
    cache: Optional[AsyncDynamoDBCache] = None
) -> OpenMeteoProvider:
    """
    Factory para obter singleton do provider
    Reutiliza entre invocações Lambda (warm starts)
    """
    global _provider_instance
    
    if _provider_instance is None:
        _provider_instance = OpenMeteoProvider(cache=cache)
    
    return _provider_instance
