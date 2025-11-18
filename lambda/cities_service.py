"""
Serviço para buscar cidades vizinhas
"""
from typing import List, Dict, Any
from utils import haversine_distance
from config import MIN_RADIUS, MAX_RADIUS, DEFAULT_RADIUS


def get_neighbors(center_city: Dict[str, Any], all_cities: List[Dict[str, Any]], radius: float) -> List[Dict[str, Any]]:
    """
    Busca cidades vizinhas dentro de um raio
    
    Args:
        center_city: Dados da cidade central
        all_cities: Lista de todas as cidades disponíveis
        radius: Raio de busca em km
    
    Returns:
        list: Lista de cidades vizinhas com distância
    """
    neighbors = []
    
    center_lat = center_city['latitude']
    center_lon = center_city['longitude']
    center_id = center_city['id']
    
    for city in all_cities:
        # Pular a própria cidade centro
        if city['id'] == center_id:
            continue
        
        # Calcular distância
        distance = haversine_distance(
            center_lat,
            center_lon,
            city['latitude'],
            city['longitude']
        )
        
        # Adicionar se estiver dentro do raio
        if distance <= radius:
            neighbor = {
                'id': city['id'],
                'name': city['name'],
                'latitude': city['latitude'],
                'longitude': city['longitude'],
                'distance': distance
            }
            neighbors.append(neighbor)
    
    # Ordenar por distância
    neighbors.sort(key=lambda x: x['distance'])
    
    return neighbors


def validate_radius(radius_str: str) -> float:
    """
    Valida e normaliza o parâmetro de raio
    
    Args:
        radius_str: Raio como string
    
    Returns:
        float: Raio validado
    """
    try:
        radius = float(radius_str)
        
        # Aplicar limites
        if radius < MIN_RADIUS:
            radius = MIN_RADIUS
        elif radius > MAX_RADIUS:
            radius = MAX_RADIUS
        
        return radius
    except (ValueError, TypeError):
        return DEFAULT_RADIUS
