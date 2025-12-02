"""OpenWeather Provider - Implementação do provider para OpenWeather One Call API 3.0"""

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
    Provider para OpenWeather One Call API 3.0
    
    Características:
    - Current weather detalhado (visibility, pressure, feels_like, uvi)
    - Previsões horárias de 48 horas
    - Previsões diárias de 8 dias (temp, pop, uvi, sunrise/sunset, moon_phase)
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
        return True  # One Call suporta até 8 dias
    
    @property
    def supports_hourly_forecast(self) -> bool:
        return True  # One Call suporta até 48 horas
    
    @tracer.wrap(resource="openweather.get_current_weather")
    async def get_current_weather(
        self,
        latitude: float,
        longitude: float,
        city_id: str,
        city_name: str,
        target_datetime: Optional[datetime] = None,
        include_daily_alerts: bool = False
    ) -> Weather:
        """
        Busca dados meteorológicos atuais do OpenWeather One Call API 3.0
        
        Flow:
        1. Tenta cache DynamoDB (async)
        2. Se MISS: chama One Call API (async HTTP)
        3. Salva no cache (TTL 3h)
        4. Processa campo 'current' e retorna Weather entity
        
        Args:
            latitude: Latitude da cidade
            longitude: Longitude da cidade
            city_id: ID da cidade
            city_name: Nome da cidade
            target_datetime: Datetime específico (opcional)
            include_daily_alerts: Se True, inclui alertas de médio prazo (8 dias)
        
        Returns:
            Weather entity completo
        """
        cache_key = f"{Cache.PREFIX_OPENWEATHER}{city_id}"
        
        # 🔍 Tentar cache primeiro
        data = None
        if self.cache and self.cache.is_enabled():
            data = await self.cache.get(cache_key)
        
        # 📡 Cache MISS: chamar One Call API
        if data is None:
            url = f"{self.base_url}/onecall"
            params = {
                'lat': latitude,
                'lon': longitude,
                'appid': self.api_key,
                'units': 'metric',
                'lang': 'pt_br',
                'exclude': 'minutely,alerts'  # Incluir hourly e daily para temp_min/max
            }
            
            session = await self.session_manager.get_session()
            
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
            
            # 💾 Salvar no cache
            if self.cache and self.cache.is_enabled():
                await self.cache.set(cache_key, data, ttl_seconds=Cache.TTL_OPENWEATHER)
        
        # 🔄 Processar dados usando mapper de infrastructure
        return OpenWeatherDataMapper.map_onecall_current_to_weather(
            data=data,
            city_id=city_id,
            city_name=city_name,
            target_datetime=target_datetime,
            include_daily_alerts=include_daily_alerts
        )
    
    @tracer.wrap(resource="openweather.get_daily_forecast")
    async def get_daily_forecast(
        self,
        latitude: float,
        longitude: float,
        city_id: str,
        days: int = 8
    ) -> List[DailyForecast]:
        """
        Busca previsões diárias do OpenWeather One Call API 3.0
        
        Flow:
        1. Valida days (máximo 8)
        2. Tenta cache DynamoDB
        3. Se MISS: chama One Call API
        4. Processa campo 'daily' e retorna lista de DailyForecast
        
        Args:
            latitude: Latitude da cidade
            longitude: Longitude da cidade
            city_id: ID da cidade (para cache)
            days: Número de dias (1-8, padrão 8)
        
        Returns:
            Lista de DailyForecast (até 8 dias)
        
        Raises:
            ValueError: Se days > 8
        """
        if days < 1 or days > 8:
            raise ValueError(f"OpenWeather One Call suporta até 8 dias, recebeu {days}")
        
        cache_key = f"{Cache.PREFIX_OPENWEATHER}{city_id}_daily"
        
        # 🔍 Tentar cache primeiro
        data = None
        if self.cache and self.cache.is_enabled():
            data = await self.cache.get(cache_key)
        
        # 📡 Cache MISS: chamar One Call API
        if data is None:
            url = f"{self.base_url}/onecall"
            params = {
                'lat': latitude,
                'lon': longitude,
                'appid': self.api_key,
                'units': 'metric',
                'lang': 'pt_br',
                'exclude': 'current,minutely,hourly,alerts'
            }
            
            session = await self.session_manager.get_session()
            
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
            
            # 💾 Salvar no cache
            if self.cache and self.cache.is_enabled():
                await self.cache.set(cache_key, data, ttl_seconds=Cache.TTL_OPENWEATHER)
        
        # 🔄 Processar dados
        return OpenWeatherDataMapper.map_onecall_daily_to_forecasts(data, max_days=days)
    
    @tracer.wrap(resource="openweather.get_hourly_forecast")
    async def get_hourly_forecast(
        self,
        latitude: float,
        longitude: float,
        city_id: str,
        hours: int = 48
    ) -> List[HourlyForecast]:
        """
        Busca previsões horárias do OpenWeather One Call API 3.0
        
        Flow:
        1. Valida hours (máximo 48)
        2. Tenta cache DynamoDB
        3. Se MISS: chama One Call API
        4. Processa campo 'hourly' e retorna lista de HourlyForecast
        
        Args:
            latitude: Latitude da cidade
            longitude: Longitude da cidade
            city_id: ID da cidade (para cache)
            hours: Número de horas (1-48, padrão 48)
        
        Returns:
            Lista de HourlyForecast (até 48 horas)
        
        Raises:
            ValueError: Se hours > 48
        """
        if hours < 1 or hours > 48:
            raise ValueError(f"OpenWeather One Call suporta até 48 horas, recebeu {hours}")
        
        cache_key = f"{Cache.PREFIX_OPENWEATHER}{city_id}_hourly"
        
        # 🔍 Tentar cache primeiro
        data = None
        if self.cache and self.cache.is_enabled():
            data = await self.cache.get(cache_key)
        
        # 📡 Cache MISS: chamar One Call API
        if data is None:
            url = f"{self.base_url}/onecall"
            params = {
                'lat': latitude,
                'lon': longitude,
                'appid': self.api_key,
                'units': 'metric',
                'lang': 'pt_br',
                'exclude': 'current,minutely,daily,alerts'
            }
            
            session = await self.session_manager.get_session()
            
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
            
            # 💾 Salvar no cache
            if self.cache and self.cache.is_enabled():
                await self.cache.set(cache_key, data, ttl_seconds=Cache.TTL_OPENWEATHER)
        
        # 🔄 Processar dados
        return OpenWeatherDataMapper.map_onecall_hourly_to_forecasts(data, max_hours=hours)


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
