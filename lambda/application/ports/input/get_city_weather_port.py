"""
Input Port: Interface para buscar dados climáticos de uma cidade
"""
from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime
from domain.entities.weather import Weather


class IGetCityWeatherUseCase(ABC):
    """Interface para caso de uso de buscar dados climáticos de uma cidade"""
    
    @abstractmethod
    def execute(self, city_id: str, target_datetime: Optional[datetime] = None) -> Weather:
        """
        Busca dados climáticos de uma cidade
        
        Args:
            city_id: ID da cidade
            target_datetime: Data/hora específica para previsão (opcional)
        
        Returns:
            Weather: Dados meteorológicos com previsão
        
        Raises:
            ValueError: Se cidade não encontrada ou sem coordenadas
        """
        pass
