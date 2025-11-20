"""
Input Port: Interface para buscar dados climáticos regionais
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
from domain.entities.weather import Weather


class IGetRegionalWeatherUseCase(ABC):
    """Interface para caso de uso de buscar dados climáticos de múltiplas cidades"""
    
    @abstractmethod
    def execute(self, city_ids: List[str], target_datetime: Optional[datetime] = None) -> List[Weather]:
        """
        Busca dados climáticos de múltiplas cidades
        
        Args:
            city_ids: Lista de IDs das cidades
            target_datetime: Data/hora específica para previsão (opcional)
        
        Returns:
            List[Weather]: Lista de dados meteorológicos
        """
        pass
