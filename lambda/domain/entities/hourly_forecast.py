"""
Hourly Forecast Entity - Entidade de previsão horária do Open-Meteo
"""
from dataclasses import dataclass
from typing import Optional
from domain.constants import WeatherCondition


@dataclass
class HourlyForecast:
    """
    Entidade de Previsão Horária do Open-Meteo
    
    Representa dados meteorológicos previstos para uma hora específica,
    permitindo visualização detalhada e gráficos de tendências horárias.
    """
    timestamp: str  # ISO 8601 format (ex: "2025-12-01T14:00:00")
    temperature: float  # Temperatura em °C
    precipitation: float  # Precipitação em mm
    precipitation_probability: int  # Probabilidade de precipitação % (0-100)
    rainfall_intensity: float  # Intensidade composta 0-100 (volume * probabilidade)
    humidity: int  # Umidade relativa % (0-100)
    wind_speed: float  # Velocidade do vento em km/h
    wind_direction: int  # Direção do vento em graus (0-360)
    cloud_cover: int  # Cobertura de nuvens % (0-100)
    pressure: Optional[float] = None  # Pressão atmosférica (hPa) - nível do mar
    visibility: Optional[float] = None  # Visibilidade (metros)
    uv_index: Optional[float] = None  # Índice UV (0-11+)
    is_day: Optional[int] = None  # 1 = dia, 0 = noite
    apparent_temperature: Optional[float] = None  # Sensação térmica da API (°C)
    weather_code: int = 0  # Código proprietário calculado na entidade
    description: str = ""  # Descrição em português do weather_code
    
    def __post_init__(self):
        """Auto-classificação usando sistema proprietário de códigos"""
        if self.weather_code == 0 or self.description == "":
            # Usar visibility se disponível, senão fallback para 10km
            visibility_value = self.visibility if self.visibility is not None else 10000.0
            
            code, desc = WeatherCondition.classify_weather_condition(
                rainfall_intensity=self.rainfall_intensity,
                precipitation=self.precipitation,
                wind_speed=self.wind_speed,
                clouds=float(self.cloud_cover),
                visibility=visibility_value,
                temperature=self.temperature,
                rain_probability=float(self.precipitation_probability)
            )
            object.__setattr__(self, 'weather_code', code)
            object.__setattr__(self, 'description', desc)
    
    def to_api_response(self) -> dict:
        """
        Converte para formato de resposta da API
        
        Returns:
            Dict com dados formatados para JSON
        """
        response = {
            'timestamp': self.timestamp,
            'temperature': round(self.temperature, 1),
            'precipitation': round(self.precipitation, 1),
            'precipitationProbability': self.precipitation_probability,
            'rainfallIntensity': int(round(self.rainfall_intensity)),
            'humidity': self.humidity,
            'windSpeed': round(self.wind_speed, 1),
            'windDirection': self.wind_direction,
            'cloudCover': self.cloud_cover,
            'weatherCode': self.weather_code,
            'description': self.description
        }
        
        # Adicionar campos opcionais se disponíveis
        if self.pressure is not None:
            response['pressure'] = round(self.pressure, 1)
        if self.visibility is not None:
            response['visibility'] = round(self.visibility, 0)
        if self.uv_index is not None:
            response['uvIndex'] = round(self.uv_index, 1)
        if self.is_day is not None:
            response['isDay'] = bool(self.is_day)
        if self.apparent_temperature is not None:
            response['apparentTemperature'] = round(self.apparent_temperature, 1)
        
        return response
