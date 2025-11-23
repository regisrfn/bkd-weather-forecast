"""
Use Case: Buscar Cidades Vizinhas
Regras de negócio para encontrar cidades dentro de um raio
"""
from typing import List
from domain.entities.city import City, NeighborCity
from application.ports.input.get_neighbor_cities_port import IGetNeighborCitiesUseCase
from application.ports.output.city_repository_port import ICityRepository
from shared.utils.haversine import calculate_distance
from config import MIN_RADIUS, MAX_RADIUS, DEFAULT_RADIUS
from shared.tracing import trace_operation


class GetNeighborCitiesUseCase(IGetNeighborCitiesUseCase):
    """Caso de uso: Buscar cidades vizinhas"""
    
    def __init__(self, city_repository: ICityRepository):
        self.city_repository = city_repository
    
    @trace_operation("use_case_get_neighbors")
    def execute(self, center_city_id: str, radius: float = DEFAULT_RADIUS) -> dict:
        """
        Executa o caso de uso
        
        Args:
            center_city_id: ID da cidade centro
            radius: Raio de busca em km
        
        Returns:
            dict com centerCity e neighbors
        
        Raises:
            ValueError: Se cidade não encontrada ou raio inválido
        """
        # Validar raio
        if not MIN_RADIUS <= radius <= MAX_RADIUS:
            raise ValueError(f'Raio deve estar entre {MIN_RADIUS} e {MAX_RADIUS} km')
        
        # Buscar cidade centro
        center_city = self.city_repository.get_by_id(center_city_id)
        if not center_city:
            raise ValueError(f'Cidade {center_city_id} não encontrada')
        
        # Validar coordenadas
        if not center_city.has_coordinates():
            raise ValueError(f'Cidade {center_city_id} não possui coordenadas')
        
        # Buscar cidades com coordenadas
        all_cities = self.city_repository.get_with_coordinates()
        
        # Calcular distâncias e filtrar por raio
        neighbors: List[NeighborCity] = []
        
        for city in all_cities:
            # Ignorar a própria cidade
            if city.id == center_city.id:
                continue
            
            # Calcular distância
            distance = calculate_distance(
                center_city.latitude,
                center_city.longitude,
                city.latitude,
                city.longitude
            )
            
            # Filtrar por raio
            if distance <= radius:
                neighbors.append(NeighborCity(city=city, distance=distance))
        
        # Ordenar por distância
        neighbors.sort(key=lambda n: n.distance)
        
        return {
            'centerCity': center_city,
            'neighbors': neighbors
        }
