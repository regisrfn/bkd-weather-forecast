"""OpenWeather Provider - Implementação do provider para OpenWeatherMap API"""

from typing import Optional, List
from datetime import datetime
from ddtrace import tracer

from application.ports.output.weather_provider_port import IWeatherProvider
from domain.entities.weather import Weather
from domain.entities.daily_forecast import DailyForecast
from domain.entities.hourly_forecast import HourlyForecast
from domain.constants import API, Cache
from infrastructure.adapters.output.providers.openweather.mappers import OpenWeatherDataMapper
from infrastructure.adapters.output.cache.async_dynamodb_cache import AsyncDynamoDBCache, get_async_cache
from infrastructure.adapters.output.http.aiohttp_session_manager import get_aiohttp_session_manager


class OpenWeatherProvider(IWeatherProvider):
    """
    Provider para OpenWeatherMap Forecast API
    
    Características:
    - Previsões de 5 dias com intervalos de 3 horas
    - Dados atuais detalhados (visibility, pressure, feels_like)
    - Cache DynamoDB com TTL de 3 horas
    - 100% async com aiohttp
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        cache: Optional[AsyncDynamoDBCache] = None
    ):
        """
        Inicializa provider
        
        Args:
            api_key: OpenWeather API key (env se None)
            cache: Cache DynamoDB async (usa factory se None)
        
        Raises:
            ValueError: Se API key não configurada
        """
        self.api_key = api_key or API.OPENWEATHER_API_KEY
        if not self.api_key:
            raise ValueError("❌ OPENWEATHER_API_KEY não configurada")
        
        self.base_url = API.OPENWEATHER_BASE_URL
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
        return "OpenWeather"
    
    @property
    def supports_current_weather(self) -> bool:
        return True
    
    @property
    def supports_daily_forecast(self) -> bool:
        return False  # OpenWeather fornece dados 3h, não daily agregado
    
    @property
    def supports_hourly_forecast(self) -> bool:
        return False  # OpenWeather fornece 3h, não verdadeiro hourly
    
    @tracer.wrap(resource="openweather.get_current_weather")
    async def get_current_weather(
        self,
        latitude: float,
        longitude: float,
        city_id: str,
        city_name: str,
        target_datetime: Optional[datetime] = None
    ) -> Weather:
        """
        Busca dados meteorológicos do OpenWeather
        
        Flow:
        1. Tenta cache DynamoDB (async)
        2. Se MISS: chama API OpenWeather (async HTTP)
        3. Salva no cache (TTL 3h)
        4. Processa e retorna Weather entity
        """
        cache_key = f"{Cache.PREFIX_OPENWEATHER}{city_id}"
        
        # 🔍 Tentar cache primeiro
        data = None
        if self.cache and self.cache.is_enabled():
            data = await self.cache.get(cache_key)
        
        # 📡 Cache MISS: chamar API
        if data is None:
            url = f"{self.base_url}/forecast"
            params = {
                'lat': latitude,
                'lon': longitude,
                'appid': self.api_key,
                'units': 'metric',
                'lang': 'pt_br'
            }
            
            session = await self.session_manager.get_session()
            
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
            
            # 💾 Salvar no cache
            if self.cache and self.cache.is_enabled():
                await self.cache.set(cache_key, data, ttl_seconds=Cache.TTL_OPENWEATHER)
        
        # 🔄 Processar dados usando mapper de infrastructure
        return OpenWeatherDataMapper.map_forecast_response_to_weather(
            data=data,
            city_id=city_id,
            city_name=city_name,
            target_datetime=target_datetime
        )
    
    async def get_daily_forecast(
        self,
        latitude: float,
        longitude: float,
        city_id: str,
        days: int = 16
    ) -> List[DailyForecast]:
        """
        OpenWeather não suporta previsões daily agregadas
        """
        raise NotImplementedError(
            "OpenWeather não suporta previsões daily. Use OpenMeteoProvider."
        )
    
    async def get_hourly_forecast(
        self,
        latitude: float,
        longitude: float,
        city_id: str,
        hours: int = 168
    ) -> List[HourlyForecast]:
        """
        OpenWeather não suporta previsões horárias verdadeiras (apenas 3h)
        """
        raise NotImplementedError(
            "OpenWeather não suporta previsões hourly. Use OpenMeteoProvider."
        )


# Factory singleton
_provider_instance = None


def get_openweather_provider(
    api_key: Optional[str] = None,
    cache: Optional[AsyncDynamoDBCache] = None
) -> OpenWeatherProvider:
    """
    Factory para obter singleton do provider
    Reutiliza entre invocações Lambda (warm starts)
    """
    global _provider_instance
    
    if _provider_instance is None:
        _provider_instance = OpenWeatherProvider(api_key=api_key, cache=cache)
    
    return _provider_instance
