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
    rain_probability: float = 0.0  # Probabilidade de chuva (0-100%)
    rain_1h: float = 0.0  # mm na última hora (opcional, para dados históricos)
    
    @property
    def rainfall_intensity(self) -> float:
        """
        Retorna probabilidade de chuva (0-100%)
        Agora baseado no campo 'pop' (Probability of Precipitation) da API
        """
        return self.rain_probability
    
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
