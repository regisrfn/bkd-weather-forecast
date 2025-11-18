"""
Weather Entity - Entidade de domínio que representa dados meteorológicos
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Weather:
    """Entidade Dados Meteorológicos"""
    city_id: str
    city_name: str
    timestamp: datetime
    temperature: float  # °C
    humidity: float  # %
    wind_speed: float  # km/h
    rain_1h: float = 0.0  # mm na última hora
    
    @property
    def rainfall_intensity(self) -> float:
        """
        Calcula intensidade de chuva (0-100%)
        Baseado em: https://www.weather.gov/bgm/forecast_terms
        """
        return min((self.rain_1h / 10) * 100, 100)
    
    def to_api_response(self) -> dict:
        """Converte para formato de resposta da API"""
        return {
            'cityId': self.city_id,
            'cityName': self.city_name,
            'timestamp': self.timestamp.isoformat(),
            'rainfallIntensity': round(self.rainfall_intensity, 1),
            'temperature': round(self.temperature, 1),
            'humidity': round(self.humidity, 1),
            'windSpeed': round(self.wind_speed, 1)
        }
