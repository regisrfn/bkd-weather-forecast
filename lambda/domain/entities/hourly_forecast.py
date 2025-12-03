"""
Hourly Forecast Entity - Entidade de previsão horária do Open-Meteo
"""
from dataclasses import dataclass
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
    weather_code: int  # WMO weather code
    description: str = ""  # Descrição em português do weather_code
    visibility: float = 10000.0  # Visibilidade em metros (default 10km)
    
    def __post_init__(self):
        """Auto-classificação usando sistema proprietário de códigos"""
        if self.weather_code == 0 or self.description == "":
            code, desc = WeatherCondition.classify_weather_condition(
                rainfall_intensity=self.rainfall_intensity,
                precipitation=self.precipitation,
                wind_speed=self.wind_speed,
                clouds=float(self.cloud_cover),
                visibility=self.visibility,
                temperature=self.temperature,
                rain_probability=float(self.precipitation_probability)
            )
            object.__setattr__(self, 'weather_code', code)
            object.__setattr__(self, 'description', desc)
    
    def to_api_response(self) -> dict:
        """
        Converte para formato de resposta da API
        
        Returns:
            Dict com dados da previsão horária formatados
        """
        return {
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
