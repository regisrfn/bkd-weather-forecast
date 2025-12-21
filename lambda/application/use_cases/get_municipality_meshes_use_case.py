"""
Use Case: Buscar malhas geográficas de múltiplos municípios (IBGE)
"""
from typing import Any, Dict, List
from ddtrace import tracer

from application.ports.output.city_repository_port import ICityRepository
from application.ports.output.geo_provider_port import IGeoProvider
from domain.exceptions import CityNotFoundException


class GetMunicipalityMeshesUseCase:
    """Busca malhas GeoJSON de vários municípios em paralelo"""

    def __init__(
        self,
        city_repository: ICityRepository,
        geo_provider: IGeoProvider
    ):
        self.city_repository = city_repository
        self.geo_provider = geo_provider

    @tracer.wrap(resource="use_case.get_municipality_meshes")
    async def execute(self, city_ids: List[str]) -> Dict[str, Any]:
        """
        Executa busca de malhas para uma lista de municípios

        Args:
            city_ids: Lista de códigos IBGE

        Returns:
            Dict { city_id: GeoJSON Feature }

        Raises:
            CityNotFoundException: se algum município não existir na base local
        """
        if not city_ids:
            return {}

        unique_ids = list(dict.fromkeys(city_ids))

        # Validar existência de todos os municípios antecipadamente
        missing = [city_id for city_id in unique_ids if not self.city_repository.get_by_id(city_id)]
        if missing:
            raise CityNotFoundException(
                "One or more cities not found",
                details={"city_ids": missing}
            )

        meshes = await self.geo_provider.get_municipality_meshes(unique_ids)

        return meshes
