"""
Use Case: Buscar malha geográfica de município (IBGE)
"""
from ddtrace import tracer

from application.ports.output.city_repository_port import ICityRepository
from application.ports.output.geo_provider_port import IGeoProvider
from domain.exceptions import CityNotFoundException, GeoDataNotFoundException
from shared.config.logger_config import get_logger

logger = get_logger(child=True)


class GetMunicipalityMeshUseCase:
    """Busca malha GeoJSON de um município com validação de existência"""

    def __init__(
        self,
        city_repository: ICityRepository,
        geo_provider: IGeoProvider
    ):
        self.city_repository = city_repository
        self.geo_provider = geo_provider

    @tracer.wrap(resource="use_case.get_municipality_mesh")
    async def execute(self, city_id: str):
        """
        Executa busca da malha geográfica

        Args:
            city_id: Código IBGE do município

        Returns:
            GeoJSON Feature retornado pelo provider

        Raises:
            CityNotFoundException: município não existe no repositório local
            GeoDataNotFoundException: provider não retornou malha
        """
        city = self.city_repository.get_by_id(city_id)
        if not city:
            raise CityNotFoundException(
                "City not found",
                details={"city_id": city_id}
            )

        mesh = await self.geo_provider.get_municipality_mesh(city_id)

        if not mesh:
            raise GeoDataNotFoundException(
                "Geo data not found",
                details={"city_id": city_id}
            )

        logger.info(
            "GeoJSON carregado com sucesso",
            city_id=city_id,
            provider=self.geo_provider.provider_name
        )

        return mesh
