"""
Value Object para coordenadas geográficas
Garante imutabilidade e validação no domínio
"""
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Coordinates:
    """
    Value Object para coordenadas geográficas
    
    Características:
    - Imutável (frozen=True)
    - Auto-validação no __post_init__
    - Comportamentos do domínio (distance_to)
    - Type-safe (não são floats soltos)
    """
    latitude: float
    longitude: float
    
    def __post_init__(self):
        """Valida coordenadas no momento da criação"""
        if not (-90 <= self.latitude <= 90):
            raise ValueError(
                f"Latitude inválida: {self.latitude}. "
                f"Deve estar entre -90 e 90 graus."
            )
        if not (-180 <= self.longitude <= 180):
            raise ValueError(
                f"Longitude inválida: {self.longitude}. "
                f"Deve estar entre -180 e 180 graus."
            )
    
    def distance_to(self, other: 'Coordinates') -> float:
        """
        Calcula distância em km até outra coordenada usando Haversine
        
        Args:
            other: Coordenadas de destino
        
        Returns:
            Distância em quilômetros
        
        Example:
            >>> sp = Coordinates(-23.5505, -46.6333)
            >>> rj = Coordinates(-22.9068, -43.1729)
            >>> sp.distance_to(rj)
            357.48  # km aproximadamente
        """
        from shared.utils.haversine import calculate_distance
        return calculate_distance(
            self.latitude,
            self.longitude,
            other.latitude,
            other.longitude
        )
    
    def to_tuple(self) -> Tuple[float, float]:
        """
        Retorna coordenadas como tupla (lat, lon)
        
        Returns:
            Tupla (latitude, longitude)
        """
        return (self.latitude, self.longitude)
    
    def __str__(self) -> str:
        """String representation amigável"""
        lat_dir = "N" if self.latitude >= 0 else "S"
        lon_dir = "E" if self.longitude >= 0 else "W"
        return f"{abs(self.latitude):.4f}°{lat_dir}, {abs(self.longitude):.4f}°{lon_dir}"
    
    @classmethod
    def from_tuple(cls, coords: Tuple[float, float]) -> 'Coordinates':
        """
        Factory method para criar a partir de tupla
        
        Args:
            coords: Tupla (latitude, longitude)
        
        Returns:
            Instância de Coordinates
        """
        return cls(latitude=coords[0], longitude=coords[1])
