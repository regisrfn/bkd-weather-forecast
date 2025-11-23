"""
Use Case: Buscar Dados Climáticos de Uma Cidade
"""
from typing import Optional
from datetime import datetime
from domain.entities.weather import Weather
from application.ports.input.get_city_weather_port import IGetCityWeatherUseCase
from application.ports.output.city_repository_port import ICityRepository
from application.ports.output.weather_repository_port import IWeatherRepository
from shared.tracing import trace_operation


class GetCityWeatherUseCase(IGetCityWeatherUseCase):
    """Caso de uso: Buscar dados climáticos de uma cidade"""
    
    def __init__(
        self,
        city_repository: ICityRepository,
        weather_repository: IWeatherRepository
    ):
        self.city_repository = city_repository
        self.weather_repository = weather_repository
    
    @trace_operation("use_case_get_city_weather")
    def execute(self, city_id: str, target_datetime: Optional[datetime] = None) -> Weather:
        """
        Executa o caso de uso
        
        Args:
            city_id: ID da cidade
            target_datetime: Data/hora específica para previsão (opcional)
        
        Returns:
            Weather: Dados meteorológicos com previsão
        
        Raises:
            ValueError: Se cidade não encontrada ou sem coordenadas
        """
        # Buscar cidade
        city = self.city_repository.get_by_id(city_id)
        if not city:
            raise ValueError(f'Cidade {city_id} não encontrada')
        
        # Validar coordenadas
        if not city.has_coordinates():
            raise ValueError(f'Cidade {city_id} não possui coordenadas')
        
        # Buscar dados climáticos
        weather = self.weather_repository.get_current_weather(
            city.latitude,
            city.longitude,
            city.name,
            target_datetime
        )
        
        return weather
