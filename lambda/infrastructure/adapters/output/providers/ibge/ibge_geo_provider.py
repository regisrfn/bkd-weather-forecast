"""
IBGE Geo Provider
Busca malhas (GeoJSON) de municípios com cache DynamoDB
"""
import asyncio
from typing import Optional, Dict, Any

import aiohttp
from ddtrace import tracer

from application.ports.output.geo_provider_port import IGeoProvider
from domain.constants import API, Cache
from domain.exceptions import GeoDataNotFoundException, GeoProviderException
from infrastructure.adapters.output.cache.async_dynamodb_cache import AsyncDynamoDBCache, get_async_cache
from infrastructure.adapters.output.http.aiohttp_session_manager import get_aiohttp_session_manager
from shared.config.logger_config import get_logger

logger = get_logger(child=True)


class IbgeGeoProvider(IGeoProvider):
    """Provider para malhas municipais do IBGE"""

    def __init__(self, cache: Optional[AsyncDynamoDBCache] = None):
        self.base_url = API.IBGE_MESH_BASE_URL.rstrip("/")
        self.cache = cache or get_async_cache()
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
        return "IBGE"

    @tracer.wrap(resource="ibge.get_municipality_mesh")
    async def get_municipality_mesh(self, city_id: str) -> Dict[str, Any]:
        """
        Busca malha GeoJSON do município com cache de 7 dias
        """
        cache_key = f"{Cache.PREFIX_IBGE_MESH}{city_id}"

        # 🔍 Cache first
        if self.cache and self.cache.is_enabled():
            cached = await self.cache.get(cache_key)
            if cached:
                logger.debug("IBGE mesh cache HIT", city_id=city_id)
                return cached

        url = f"{self.base_url}/{city_id}"
        params = {"formato": "application/vnd.geo+json"}

        try:
            session = await self.session_manager.get_session()
            async with session.get(
                url,
                params=params,
                headers={"Accept": "application/vnd.geo+json"}
            ) as response:
                status = response.status

                if status == 404:
                    raise GeoDataNotFoundException(
                        "IBGE mesh not found",
                        details={"city_id": city_id, "status": status}
                    )

                if status >= 500:
                    raise GeoProviderException(
                        "IBGE service unavailable",
                        details={"city_id": city_id, "status": status}
                    )

                if status >= 400:
                    raise GeoProviderException(
                        "Failed to fetch IBGE mesh",
                        details={"city_id": city_id, "status": status}
                    )

                mesh = await response.json(content_type=None)

        except (aiohttp.ClientError, asyncio.TimeoutError) as ex:
            raise GeoProviderException(
                f"IBGE request failed: {str(ex)}",
                details={"city_id": city_id}
            ) from ex

        if not mesh:
            raise GeoDataNotFoundException(
                "Empty GeoJSON returned from IBGE",
                details={"city_id": city_id}
            )

        # 💾 Cache for 7 days
        if self.cache and self.cache.is_enabled():
            await self.cache.set(cache_key, mesh, ttl_seconds=Cache.TTL_IBGE_MESH)
            logger.debug("IBGE mesh cached", city_id=city_id, ttl=Cache.TTL_IBGE_MESH)

        return mesh

    @tracer.wrap(resource="ibge.get_municipality_meshes")
    async def get_municipality_meshes(self, city_ids: list[str]) -> Dict[str, Any]:
        """
        Busca malhas de múltiplos municípios em paralelo reaproveitando cache
        """
        if not city_ids:
            return {}

        unique_ids = list(dict.fromkeys(city_ids))
        semaphore = asyncio.Semaphore(30)

        async def fetch_mesh(city_id: str):
            async with semaphore:
                try:
                    mesh = await self.get_municipality_mesh(city_id)
                    return city_id, mesh
                except GeoDataNotFoundException as ex:
                    logger.warning("IBGE mesh não encontrada", city_id=city_id, error=str(ex))
                except GeoProviderException as ex:
                    logger.warning("Falha ao buscar malha do IBGE", city_id=city_id, error=str(ex))
                except Exception as ex:
                    logger.warning("Erro inesperado ao buscar malha do IBGE", city_id=city_id, error=str(ex))
                return None

        results = await asyncio.gather(
            *(fetch_mesh(city_id) for city_id in unique_ids),
            return_exceptions=True
        )

        meshes: Dict[str, Any] = {}
        for result in results:
            if isinstance(result, tuple):
                city_id, mesh = result
                if mesh:
                    meshes[city_id] = mesh
            elif isinstance(result, Exception):
                logger.warning("Erro de batch IBGE", error=str(result))

        logger.info(
            "Batch de malhas IBGE concluído",
            solicitadas=len(unique_ids),
            retornadas=len(meshes)
        )

        return meshes


# Singleton factory (reutilizado entre invocações Lambda)
_geo_provider_instance: Optional[IbgeGeoProvider] = None


def get_ibge_geo_provider(cache: Optional[AsyncDynamoDBCache] = None) -> IbgeGeoProvider:
    """Retorna instância singleton do provider IBGE"""
    global _geo_provider_instance

    if _geo_provider_instance is None:
        _geo_provider_instance = IbgeGeoProvider(cache=cache)

    return _geo_provider_instance
