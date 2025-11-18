"""
City Entity - Entidade de domínio que representa uma cidade
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class City:
    """Entidade Cidade"""
    id: str  # Código IBGE
    name: str
    state: str
    region: str
    latitude: float
    longitude: float
    
    def has_coordinates(self) -> bool:
        """Verifica se a cidade possui coordenadas válidas"""
        return self.latitude is not None and self.longitude is not None
    
    def to_dict(self) -> dict:
        """Converte para dicionário"""
        return {
            'id': self.id,
            'name': self.name,
            'state': self.state,
            'region': self.region,
            'latitude': self.latitude,
            'longitude': self.longitude
        }
    
    def to_api_response(self, include_state: bool = False) -> dict:
        """Converte para formato de resposta da API"""
        response = {
            'id': self.id,
            'name': self.name,
            'latitude': self.latitude,
            'longitude': self.longitude
        }
        if include_state:
            response['state'] = self.state
        return response


@dataclass
class NeighborCity:
    """Cidade vizinha com distância"""
    city: City
    distance: float
    
    def to_api_response(self) -> dict:
        """Converte para formato de resposta da API"""
        return {
            'id': self.city.id,
            'name': self.city.name,
            'latitude': self.city.latitude,
            'longitude': self.city.longitude,
            'distance': round(self.distance, 1)
        }
