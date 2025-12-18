"""
Output Port: Interface para repositórios de cache assíncronos
Usado para desacoplar use cases de detalhes do cache (DynamoDB, Redis, etc.)
"""
from typing import Protocol, Optional, Dict, Any, List


class IAsyncCacheRepository(Protocol):
    """Interface assíncrona para repositório de cache"""

    def is_enabled(self) -> bool:
        """
        Verifica se o cache está habilitado
        """
        ...

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Busca item no cache por chave
        """
        ...

    async def set(self, key: str, data: Dict[str, Any], ttl_seconds: int = 10800) -> bool:
        """
        Armazena item no cache com TTL
        """
        ...

    async def batch_get(self, keys: List[str]) -> Dict[str, Any]:
        """
        Busca múltiplos itens em batch
        """
        ...

    async def batch_set(self, items: Dict[str, Any], ttl_seconds: int) -> Dict[str, bool]:
        """
        Persiste múltiplos itens em batch
        """
        ...
