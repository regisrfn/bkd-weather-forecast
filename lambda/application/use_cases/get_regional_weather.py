"""
Use Case: Buscar Dados Climáticos de Múltiplas Cidades
"""
from typing import List, Optional
from datetime import datetime
from domain.entities.weather import Weather
from domain.repositories.city_repository import ICityRepository
from domain.repositories.weather_repository import IWeatherRepository


class GetRegionalWeatherUseCase:
    """Caso de uso: Buscar dados climáticos regionais"""
    
    def __init__(
        self,
        city_repository: ICityRepository,
        weather_repository: IWeatherRepository
    ):
        self.city_repository = city_repository
        self.weather_repository = weather_repository
    
    def execute(self, city_ids: List[str], target_datetime: Optional[datetime] = None) -> List[Weather]:
        """
        Executa o caso de uso
        
        Args:
            city_ids: Lista de IDs das cidades
            target_datetime: Data/hora específica para previsão (opcional)
        
        Returns:
            List[Weather]: Lista de dados meteorológicos com previsão
        """
        weather_data: List[Weather] = []
        
        for city_id in city_ids:
            # Buscar cidade
            city = self.city_repository.get_by_id(city_id)
            
            # Ignorar cidades não encontradas ou sem coordenadas
            if not city or not city.has_coordinates():
                continue
            
            try:
                # Buscar dados climáticos
                weather = self.weather_repository.get_current_weather(
                    city.latitude,
                    city.longitude,
                    city.name,
                    target_datetime
                )
                # Definir city_id da entidade
                weather.city_id = city.id
                weather_data.append(weather)
                
            except Exception:
                # Ignorar erros individuais e continuar
                continue
        
        return weather_data
