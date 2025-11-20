"""
Output Adapter: Implementação do Repositório de Dados Meteorológicos
Integração com OpenWeatherMap API (Forecast)
"""
import requests
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, List
from domain.entities.weather import Weather
from application.ports.output.weather_repository_port import IWeatherRepository


class OpenWeatherRepository(IWeatherRepository):
    """Repositório de dados meteorológicos usando OpenWeatherMap Forecast API"""
    
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
    
    def get_current_weather(self, latitude: float, longitude: float, city_name: str, 
                           target_datetime: Optional[datetime] = None) -> Weather:
        """
        Busca dados meteorológicos (previsão) do OpenWeatherMap
        
        Args:
            latitude: Latitude da cidade
            longitude: Longitude da cidade
            city_name: Nome da cidade
            target_datetime: Data/hora específica para previsão (opcional, usa próxima disponível se None)
        
        Returns:
            Weather: Dados meteorológicos com probabilidade de chuva
        
        Raises:
            Exception: Se a chamada à API falhar ou não houver dados para a data solicitada
        """
        url = f"{self.base_url}/forecast"
        
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
        
        # Selecionar previsão mais próxima da data/hora solicitada
        forecast_item = self._select_forecast(data['list'], target_datetime)
        
        if not forecast_item:
            raise ValueError("Nenhuma previsão disponível para a data/hora solicitada")
        
        # Converter resposta da API para entidade Weather
        return Weather(
            city_id='',  # Será preenchido pelo use case
            city_name=city_name,
            timestamp=datetime.fromtimestamp(forecast_item['dt']),
            temperature=forecast_item['main']['temp'],
            humidity=forecast_item['main']['humidity'],
            wind_speed=forecast_item['wind']['speed'] * 3.6,  # m/s para km/h
            rain_probability=forecast_item.get('pop', 0) * 100,  # 0-1 para 0-100%
            rain_1h=forecast_item.get('rain', {}).get('3h', 0) / 3  # Aproximação de 3h para 1h
        )
    
    def _select_forecast(self, forecasts: List[dict], target_datetime: Optional[datetime]) -> Optional[dict]:
        """
        Seleciona a previsão mais próxima da data/hora solicitada
        
        Args:
            forecasts: Lista de previsões da API
            target_datetime: Data/hora alvo (None = primeira disponível)
        
        Returns:
            Previsão selecionada ou None se não houver
        
        Nota: Busca a previsão MAIS PRÓXIMA (antes ou depois) do horário solicitado,
        considerando que OpenWeather fornece previsões a cada 3 horas.
        """
        if not forecasts:
            return None
        
        # Se não há data alvo, retorna a primeira previsão
        if target_datetime is None:
            return forecasts[0]
        
        # Converter target_datetime para UTC se tiver timezone
        if target_datetime.tzinfo is not None:
            target_datetime_utc = target_datetime.astimezone(ZoneInfo("UTC"))
        else:
            # Se não tem timezone, assume UTC
            target_datetime_utc = target_datetime.replace(tzinfo=ZoneInfo("UTC"))
        
        # Encontra previsão MAIS PRÓXIMA usando min() com key function
        closest_forecast = min(
            forecasts,
            key=lambda f: abs(
                datetime.fromtimestamp(f['dt'], tz=ZoneInfo("UTC")) - target_datetime_utc
            ).total_seconds()
        )
        
        return closest_forecast


def get_weather_repository(api_key: Optional[str] = None) -> IWeatherRepository:
    """
    Factory para criar repositório de weather
    Permite facilmente trocar implementação ou adicionar mock
    """
    return OpenWeatherRepository(api_key)
