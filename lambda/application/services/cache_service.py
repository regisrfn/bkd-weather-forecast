"""
Serviço de cache genérico para a camada de aplicação.
Centraliza leitura/gravação em batch sem expor detalhes de adapters.
"""
import asyncio
from typing import Dict, Any, List, Optional, Tuple

from application.ports.output.async_cache_repository_port import IAsyncCacheRepository


class CacheService:
    """Coordena operações de cache assíncronas via porta de saída."""

    def __init__(self, cache_repository: Optional[IAsyncCacheRepository]):
        self.cache_repository = cache_repository

    def _cache_available(self) -> bool:
        return bool(self.cache_repository and self.cache_repository.is_enabled())

    async def prefetch(self, keys: List[str]) -> Dict[str, Any]:
        """
        Busca múltiplas chaves em batch.
        """
        if not keys or not self._cache_available():
            return {}

        return await self.cache_repository.batch_get(keys) or {}

    async def persist(self, items: Dict[str, Any], ttl_seconds: int) -> Dict[str, bool]:
        """
        Persiste itens em batch com TTL informado.
        """
        if not items or not self._cache_available():
            return {key: False for key in items.keys()}

        return await self.cache_repository.batch_set(items, ttl_seconds=ttl_seconds)

    async def persist_many(self, batches: List[Tuple[Dict[str, Any], int]]) -> None:
        """
        Persiste múltiplos lotes com TTLs diferentes em paralelo.
        """
        if not self._cache_available():
            return

        tasks = [
            self.cache_repository.batch_set(items, ttl_seconds=ttl)
            for items, ttl in batches
            if items
        ]

        if tasks:
            await asyncio.gather(*tasks)
            total_items = sum(len(items) for items, _ in batches)
