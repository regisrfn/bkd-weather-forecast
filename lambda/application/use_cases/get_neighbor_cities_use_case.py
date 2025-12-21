"""
Async Use Case: Get Neighbor Cities
100% async implementation with aioboto3
"""
import asyncio
from typing import List
from ddtrace import tracer

from domain.entities.city import City, NeighborCity
from domain.exceptions import CityNotFoundException, CoordinatesNotFoundException, InvalidRadiusException
from application.ports.input.get_neighbor_cities_port import IGetNeighborCitiesUseCase
from application.ports.output.city_repository_port import ICityRepository
from shared.utils.haversine import calculate_distance
from shared.utils.validators import RadiusValidator


class AsyncGetNeighborCitiesUseCase(IGetNeighborCitiesUseCase):
    """Async use case: Find neighbor cities within radius"""
    
    def __init__(self, city_repository: ICityRepository):
        self.city_repository = city_repository
    
    @tracer.wrap(resource="use_case.async_get_neighbor_cities")
    async def execute(self, center_city_id: str, radius: float) -> dict:
        """
        Execute use case asynchronously
        
        Args:
            center_city_id: Center city ID
            radius: Search radius in km
        
        Returns:
            dict with centerCity and neighbors
        
        Raises:
            InvalidRadiusException: If radius is invalid
            CityNotFoundException: If city not found
            CoordinatesNotFoundException: If city has no coordinates
        """
        # Validate radius (throws InvalidRadiusException)
        RadiusValidator.validate(radius)
        
        # Get center city (sync operation - in-memory lookup)
        center_city = self.city_repository.get_by_id(center_city_id)
        if not center_city:
            raise CityNotFoundException(
                f"City not found",
                details={"city_id": center_city_id}
            )
        
        # Validate coordinates
        if not center_city.has_coordinates():
            raise CoordinatesNotFoundException(
                f"City has no coordinates",
                details={"city_id": center_city_id, "city_name": center_city.name}
            )
        
        # Get all cities with coordinates (sync - in-memory)
        all_cities = self.city_repository.get_with_coordinates()
        
        # Calculate distances and filter (CPU-bound, but fast)
        neighbors: List[NeighborCity] = []
        
        for city in all_cities:
            if city.id == center_city.id:
                continue
            
            distance = calculate_distance(
                center_city.latitude,
                center_city.longitude,
                city.latitude,
                city.longitude
            )
            
            if distance <= radius:
                neighbors.append(NeighborCity(city=city, distance=distance))
        
        # Sort by distance
        neighbors.sort(key=lambda n: n.distance)
        
        return {
            'centerCity': center_city,
            'neighbors': neighbors
        }
