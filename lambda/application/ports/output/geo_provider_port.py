"""
Output Port: Geo Provider
Contrato para provedores de malha geográfica (IBGE)
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class IGeoProvider(ABC):
    """Interface para provedores de dados geográficos"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nome do provider (ex.: IBGE)"""
        raise NotImplementedError

    @abstractmethod
    async def get_municipality_mesh(self, city_id: str) -> Dict[str, Any]:
        """
        Busca malha geográfica (GeoJSON) de um município
        
        Args:
            city_id: Código IBGE do município
        
        Returns:
            GeoJSON Feature como dict
        
        Raises:
            DomainException subclasses para erros de negócio/provider
        """
        raise NotImplementedError

    @abstractmethod
    async def get_municipality_meshes(self, city_ids: list[str]) -> Dict[str, Any]:
        """
        Busca malhas GeoJSON para múltiplos municípios em paralelo

        Args:
            city_ids: Lista de códigos IBGE

        Returns:
            Dict com {city_id: GeoJSON Feature}
        """
        raise NotImplementedError
