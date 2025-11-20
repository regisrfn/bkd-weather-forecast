"""
Input Port: Interface para buscar vizinhos de uma cidade
"""
from abc import ABC, abstractmethod
from typing import Dict, List
from domain.entities.city import City


class IGetNeighborCitiesUseCase(ABC):
    """Interface para caso de uso de buscar cidades vizinhas"""
    
    @abstractmethod
    def execute(self, city_id: str, radius: float) -> Dict[str, any]:
        """
        Busca cidade centro e suas cidades vizinhas dentro de um raio
        
        Args:
            city_id: ID da cidade centro
            radius: Raio em quilômetros
        
        Returns:
            Dict com 'centerCity' e 'neighbors' (lista de cidades)
        
        Raises:
            ValueError: Se cidade não encontrada ou sem coordenadas
        """
        pass
