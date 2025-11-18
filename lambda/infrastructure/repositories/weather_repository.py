"""
Implementação do Repositório de Dados Meteorológicos
Integração com OpenWeatherMap API
"""
import requests
from datetime import datetime
from typing import Optional
from domain.entities.weather import Weather
from domain.repositories.weather_repository import IWeatherRepository
import os


class OpenWeatherRepository(IWeatherRepository):
    """Repositório de dados meteorológicos usando OpenWeatherMap"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa o repositório
        
        Args:
            api_key: Chave da API OpenWeatherMap (opcional, usa env se não fornecida)
        """
        self.api_key = api_key or os.environ.get('OPENWEATHER_API_KEY')
        self.base_url = "https://api.openweathermap.org/data/2.5"
        
        if not self.api_key:
            raise ValueError("OPENWEATHER_API_KEY não configurada")
    
    def get_current_weather(self, latitude: float, longitude: float, city_name: str) -> Weather:
        """
        Busca dados meteorológicos atuais do OpenWeatherMap
        
        Args:
            latitude: Latitude da cidade
            longitude: Longitude da cidade
            city_name: Nome da cidade
        
        Returns:
            Weather: Dados meteorológicos
        
        Raises:
            Exception: Se a chamada à API falhar
        """
        url = f"{self.base_url}/weather"
        
        params = {
            'lat': latitude,
            'lon': longitude,
            'appid': self.api_key,
            'units': 'metric',
            'lang': 'pt_br'
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Converter resposta da API para entidade Weather
        return Weather(
            city_id='',  # Será preenchido pelo use case
            city_name=city_name,
            timestamp=datetime.now(),
            temperature=data['main']['temp'],
            humidity=data['main']['humidity'],
            wind_speed=data['wind']['speed'] * 3.6,  # m/s para km/h
            rain_1h=data.get('rain', {}).get('1h', 0)
        )


def get_weather_repository(api_key: Optional[str] = None) -> IWeatherRepository:
    """
    Factory para criar repositório de weather
    Permite facilmente trocar implementação ou adicionar mock
    """
    return OpenWeatherRepository(api_key)
