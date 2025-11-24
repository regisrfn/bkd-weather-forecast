"""
Use Case: Buscar Dados Climáticos de Múltiplas Cidades
"""
from typing import List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from ddtrace import tracer
from domain.entities.weather import Weather
from application.ports.input.get_regional_weather_port import IGetRegionalWeatherUseCase
from application.ports.output.city_repository_port import ICityRepository
from application.ports.output.weather_repository_port import IWeatherRepository


class GetRegionalWeatherUseCase(IGetRegionalWeatherUseCase):
    """Caso de uso: Buscar dados climáticos regionais"""
    
    def __init__(
        self,
        city_repository: ICityRepository,
        weather_repository: IWeatherRepository
    ):
        self.city_repository = city_repository
        self.weather_repository = weather_repository
    
    @tracer.wrap(resource="use_case.get_regional_weather")
    def execute(self, city_ids: list, target_datetime: Optional[datetime] = None) -> list:
        """
        Executa o caso de uso
        
        Args:
            city_ids: Lista de IDs das cidades
            target_datetime: Data/hora específica para previsão (opcional)
        
        Returns:
            List[Weather]: Lista de dados meteorológicos com previsão
        """
        weather_data: List[Weather] = []
        
        # Função auxiliar para buscar dados de uma cidade
        def fetch_city_weather(city_id: str) -> Optional[Weather]:
            try:
                # Buscar cidade
                city = self.city_repository.get_by_id(city_id)
                
                # Ignorar cidades não encontradas ou sem coordenadas
                if not city or not city.has_coordinates():
                    return None
                
                # Buscar dados climáticos
                weather = self.weather_repository.get_current_weather(
                    city.latitude,
                    city.longitude,
                    city.name,
                    target_datetime
                )
                # Definir city_id da entidade
                weather.city_id = city.id
                return weather
                
            except Exception:
                # Ignorar erros individuais
                return None
        
        # Executar requisições em paralelo (máximo 10 threads simultâneas)
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submeter todas as tarefas
            future_to_city = {executor.submit(fetch_city_weather, city_id): city_id 
                             for city_id in city_ids}
            
            # Coletar resultados conforme completam
            for future in as_completed(future_to_city):
                result = future.result()
                if result is not None:
                    weather_data.append(result)
        
        return weather_data
