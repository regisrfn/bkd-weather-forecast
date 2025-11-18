"""
Interface do Repositório de Dados Meteorológicos
Define o contrato que deve ser implementado pela camada de infraestrutura
"""
from abc import ABC, abstractmethod
from typing import List
from domain.entities.weather import Weather


class IWeatherRepository(ABC):
    """Interface para repositório de dados meteorológicos"""
    
    @abstractmethod
    def get_current_weather(self, latitude: float, longitude: float, city_name: str) -> Weather:
        """
        Busca dados meteorológicos atuais para uma localização
        
        Args:
            latitude: Latitude da cidade
            longitude: Longitude da cidade
            city_name: Nome da cidade (para identificação)
        
        Returns:
            Weather: Dados meteorológicos atuais
        
        Raises:
            Exception: Se não conseguir buscar os dados
        """
        pass
