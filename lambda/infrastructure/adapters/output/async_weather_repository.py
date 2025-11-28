"""
Async Weather Repository - 100% assíncrono com aiohttp + aioboto3
SEM GIL - Verdadeiro paralelismo I/O para 100+ cidades simultâneas

Refactored to follow clean architecture principles:
- Delegates data processing to WeatherDataProcessor
- Delegates alert analysis to WeatherAlertsAnalyzer
- Delegates date filtering to DateFilterHelper
- Focuses only on API communication and cache coordination
"""
import os
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from ddtrace import tracer
from aws_lambda_powertools import Logger

from domain.entities.weather import Weather
from application.ports.output.weather_repository_port import IWeatherRepository
from infrastructure.adapters.cache.async_dynamodb_cache import AsyncDynamoDBCache, get_async_cache
from infrastructure.adapters.config.aiohttp_session_manager import get_aiohttp_session_manager
from infrastructure.adapters.helpers.weather_data_processor import WeatherDataProcessor

logger = Logger(child=True)


class AsyncOpenWeatherRepository(IWeatherRepository):
    """
    Repositório 100% assíncrono para OpenWeatherMap Forecast API
    
    Benefícios:
    - SEM GIL: Verdadeiro paralelismo I/O
    - 100+ requisições HTTP simultâneas (aiohttp)
    - Cache DynamoDB com aioboto3 (gerenciado centralmente)
    - Latência P99 <100ms em produção
    - Performance similar a Node.js
    - Sessão aiohttp global reutilizada em warm starts
    
    Estratégia de Cache:
    1. Busca cache DynamoDB por city_id (async, sem bloqueio GIL)
    2. Se MISS, chama OpenWeather API (async HTTP)
    3. Salva resposta completa no cache (TTL 3h)
    4. Processa dados e retorna Weather entity
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        cache: Optional[AsyncDynamoDBCache] = None
    ):
        """
        Inicializa repositório async
        
        Args:
            api_key: OpenWeather API key (env se None)
            cache: Cache DynamoDB async (usa factory se None)
        """
        self.api_key = api_key or os.environ.get('OPENWEATHER_API_KEY')
        if not self.api_key:
            raise ValueError("❌ OPENWEATHER_API_KEY não configurada")
        
        self.base_url = "https://api.openweathermap.org/data/2.5"
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

    
    @tracer.wrap(resource="async_repository.get_weather")
    async def get_current_weather(
        self,
        city_id: str,
        latitude: float,
        longitude: float,
        city_name: str,
        target_datetime: Optional[datetime] = None,
        skip_cache_check: bool = False
    ) -> Weather:
        """
        Busca dados meteorológicos de forma ASSÍNCRONA
        
        Flow:
        1. Cache GET async (DynamoDB, sem GIL) - opcional
        2. Se MISS: HTTP GET async (OpenWeather API, sem GIL)
        3. Cache SET async (DynamoDB, sem GIL)
        4. Parse e retorna Weather entity
        
        Args:
            city_id: ID da cidade (chave de cache)
            latitude: Latitude
            longitude: Longitude
            city_name: Nome da cidade
            target_datetime: Data/hora alvo (None = próxima disponível)
            skip_cache_check: Se True, pula verificação de cache (já foi feito batch)
        
        Returns:
            Weather entity com dados meteorológicos
        
        Raises:
            ValueError: Se não houver previsões futuras
            aiohttp.ClientError: Se API falhar
        """
        cache_key = city_id
        
        # 🔍 Tentar cache primeiro (async, sem GIL) - apenas se não pulou
        data = None
        if not skip_cache_check and self.cache and self.cache.is_enabled():
            data = await self.cache.get(cache_key)
        
        # 📡 Cache MISS: chamar API (async HTTP, sem GIL)
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
            
            # 💾 Salvar no cache (async, sem GIL)
            # Quando skip_cache_check=True, caller fará batch save
            if self.cache and self.cache.is_enabled() and not skip_cache_check:
                await self.cache.set(cache_key, data)
        
        # 🔄 Processar dados e retornar Weather entity
        return self._process_weather_data(data, city_name, target_datetime)
    
    async def get_current_weather_with_cache_data(
        self,
        city_id: str,
        latitude: float,
        longitude: float,
        city_name: str,
        target_datetime: Optional[datetime] = None
    ) -> Tuple[Weather, str, Dict[str, Any]]:
        """
        Versão que retorna também cache_key e raw_data para batch save posterior
        
        Args:
            city_id: ID da cidade
            latitude: Latitude
            longitude: Longitude
            city_name: Nome da cidade
            target_datetime: Data/hora alvo
        
        Returns:
            Tuple (Weather entity, cache_key, raw_data)
        """
        cache_key = city_id
        
        # 📡 Chamar API (sem cache, será feito batch save depois)
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
        
        # 🔄 Processar dados
        weather = self._process_weather_data(data, city_name, target_datetime)
        
        return (weather, cache_key, data)
    
    def _process_weather_data(
        self,
        data: Dict[str, Any],
        city_name: str,
        target_datetime: Optional[datetime] = None
    ) -> Weather:
        """
        Process API data and return Weather entity
        Delegates to WeatherDataProcessor for all processing logic
        
        Args:
            data: Raw data from API
            city_name: City name
            target_datetime: Target datetime
        
        Returns:
            Weather entity
        """
        return WeatherDataProcessor.process_weather_data(data, city_name, target_datetime)
    
    async def batch_save_weather_to_cache(
        self,
        weather_data_list: List[Tuple[str, Dict[str, Any]]]
    ) -> Dict[str, bool]:
        """
        Salva múltiplos weather data no cache usando batch write
        
        Args:
            weather_data_list: Lista de tuplas (cache_key, data)
        
        Returns:
            Dict com {cache_key: success}
        """
        if not self.cache or not self.cache.is_enabled():
            return {key: False for key, _ in weather_data_list}
        
        try:
            # Preparar items para batch
            items = {cache_key: data for cache_key, data in weather_data_list}
            
            # Executar batch set
            results = await self.cache.batch_set(items)
            
            return results
        
        except Exception as e:
            logger.error(
                "Batch cache save ERROR",
                items_count=len(weather_data_list),
                error=str(e)[:200]
            )
            return {key: False for key, _ in weather_data_list}
    
    @tracer.wrap(resource="async_repository.batch_get_weather")
    async def batch_get_weather_from_cache(self, city_ids: List[str]) -> dict:
        """
        Busca dados de múltiplas cidades do cache em BATCH (1 única chamada DynamoDB)
        
        Performance:
        - Batch: ~50ms para 100 cidades (1 chamada)
        - Individual: ~1000ms para 100 cidades (100 chamadas com contenção)
        
        Args:
            city_ids: Lista de IDs das cidades
        
        Returns:
            Dict[city_id, cache_data] com apenas HITs (MISSes não aparecem)
        """
        if not self.cache or not self.cache.is_enabled():
            return {}
        
        # Usar batch_get do cache (1 única chamada ao DynamoDB)
        results = await self.cache.batch_get(city_ids)
        
        return results


# Factory singleton
_async_repository_instance = None

def get_async_weather_repository(
    api_key: Optional[str] = None,
    cache: Optional[AsyncDynamoDBCache] = None
) -> AsyncOpenWeatherRepository:
    """
    Factory to get async repository singleton
    Reuses between Lambda invocations (warm starts)
    Sessão aiohttp é global e compartilhada
    
    Args:
        api_key: OpenWeather API key
        cache: Cache DynamoDB async
    
    Returns:
        AsyncOpenWeatherRepository instance
    """
    global _async_repository_instance
    
    if _async_repository_instance is None:
        _async_repository_instance = AsyncOpenWeatherRepository(
            api_key=api_key,
            cache=cache
        )
    
    return _async_repository_instance
