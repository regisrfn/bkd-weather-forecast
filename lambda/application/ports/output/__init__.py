"""
Output Ports - Interfaces para comunicação com infraestrutura externa
Define contratos que devem ser implementados pelos adapters de saída
"""
 
from .cache_repository_port import ICacheRepository
from .async_cache_repository_port import IAsyncCacheRepository
