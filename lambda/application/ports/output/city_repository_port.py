"""
Output Port: Interface do Repositório de Cidades
Define o contrato que deve ser implementado pela camada de infraestrutura
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from domain.entities.city import City


class ICityRepository(ABC):
    """Interface para repositório de cidades"""
    
    @abstractmethod
    def get_by_id(self, city_id: str) -> Optional[City]:
        """Busca cidade por ID (código IBGE)"""
        pass
    
    @abstractmethod
    def get_all(self) -> List[City]:
        """Retorna todas as cidades"""
        pass
    
    @abstractmethod
    def get_with_coordinates(self) -> List[City]:
        """Retorna apenas cidades com coordenadas válidas"""
        pass
    
    @abstractmethod
    def get_by_state(self, state: str) -> List[City]:
        """Retorna todas as cidades de um estado"""
        pass
    
    @abstractmethod
    def search_by_name(self, name: str, state: Optional[str] = None) -> Optional[City]:
        """Busca cidade por nome"""
        pass
