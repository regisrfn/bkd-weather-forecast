"""
Infrastructure Layer - Clean Architecture
Contém implementações concretas de repositórios e serviços externos
"""

from infrastructure.adapters.output.cache.async_dynamodb_cache import AsyncDynamoDBCache, get_async_cache
from infrastructure.adapters.output.http.aiohttp_session_manager import get_aiohttp_session_manager
from infrastructure.adapters.output.providers import (
    OpenWeatherProvider,
    OpenMeteoProvider,
    WeatherProviderFactory
)

__all__ = [
    'AsyncDynamoDBCache',
    'get_async_cache',
    'get_aiohttp_session_manager',
    'OpenWeatherProvider',
    'OpenMeteoProvider',
    'WeatherProviderFactory'
]
