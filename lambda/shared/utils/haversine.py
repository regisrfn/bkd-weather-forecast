"""
Cálculo de distância usando fórmula de Haversine
Movido de cities_service.py para shared/utils
"""
import math


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula distância entre dois pontos usando fórmula de Haversine
    
    Args:
        lat1: Latitude do ponto 1
        lon1: Longitude do ponto 1
        lat2: Latitude do ponto 2
        lon2: Longitude do ponto 2
    
    Returns:
        float: Distância em quilômetros
    """
    # Raio da Terra em km
    R = 6371.0
    
    # Converter graus para radianos
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Diferenças
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Fórmula de Haversine
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    
    return distance
