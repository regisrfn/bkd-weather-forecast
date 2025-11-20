"""
Weather Entity - Entidade de domínio que representa dados meteorológicos
"""
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo
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
        """
        Converte para formato de resposta da API
        
        IMPORTANTE: Converte timestamp para timezone do Brasil (America/Sao_Paulo)
        para evitar confusão com horários UTC na interface do usuário.
        """
        # Converter timestamp para timezone do Brasil
        brasil_tz = ZoneInfo("America/Sao_Paulo")
        
        # Se o timestamp já tem timezone, converte; senão, assume UTC e converte
        if self.timestamp.tzinfo is not None:
            timestamp_brasil = self.timestamp.astimezone(brasil_tz)
        else:
            timestamp_brasil = self.timestamp.replace(tzinfo=ZoneInfo("UTC")).astimezone(brasil_tz)
        
        return {
            'cityId': self.city_id,
            'cityName': self.city_name,
            'timestamp': timestamp_brasil.isoformat(),  # Agora em horário Brasil
            'rainfallIntensity': round(self.rainfall_intensity, 1),
            'temperature': round(self.temperature, 1),
            'humidity': round(self.humidity, 1),
            'windSpeed': round(self.wind_speed, 1)
        }
