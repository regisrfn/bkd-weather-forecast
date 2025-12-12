"""
Weather Entity - Entidade de domínio que representa dados meteorológicos
"""
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Optional
from enum import Enum

from domain.alerts.primitives import WeatherAlert
from domain.constants import WeatherCondition
from domain.helpers.rainfall_calculator import calculate_rainfall_intensity
from domain.value_objects.daily_aggregated_metrics import DailyAggregatedMetrics


class CloudCoverage(Enum):
    """Descrições de cobertura de nuvens baseadas na porcentagem"""
    CLEAR = "Céu limpo"  # 0-10%
    FEW_CLOUDS = "Poucas nuvens"  # 11-25%
    SCATTERED_CLOUDS = "Parcialmente nublado"  # 26-50%
    BROKEN_CLOUDS = "Nublado"  # 51-84%
    OVERCAST = "Céu encoberto"  # 85-100%


@dataclass
class Weather:
    """Entidade Dados Meteorológicos"""
    city_id: str
    city_name: str
    timestamp: datetime
    temperature: float  # °C
    humidity: float  # %
    wind_speed: float  # km/h
    wind_direction: int = 0  # Direção do vento (graus 0-360)
    rain_probability: float = 0.0  # Probabilidade de chuva (0-100%)
    rain_1h: float = 0.0  # mm na última hora (opcional, para dados históricos)
    rain_accumulated_day: float = 0.0  # Acumulado de chuva esperado no dia (mm)
    description: str = ""  # Descrição do clima (ex: "céu limpo", "nublado")
    feels_like: float = 0.0  # Sensação térmica (°C)
    pressure: float = 0.0  # Pressão atmosférica (hPa)
    visibility: float = 0.0  # Visibilidade (metros)
    clouds: float = 0.0  # Cobertura de nuvens (0-100%)
    weather_alert: List[WeatherAlert] = field(default_factory=list)  # Lista de alertas estruturados
    weather_code: int = 0  # Código da condição climática da API
    temp_min: float = 0.0  # Temperatura mínima (°C)
    temp_max: float = 0.0  # Temperatura máxima (°C)
    is_day: bool = True  # True = dia, False = noite
    daily_aggregates: Optional[DailyAggregatedMetrics] = None  # Métricas agregadas por dia
    
    def __post_init__(self):
        """Auto-classificação usando sistema proprietário de códigos"""
        if self.weather_code == 0 or self.description == "":
            code, desc = WeatherCondition.classify_weather_condition(
                rainfall_intensity=self.rainfall_intensity,
                precipitation=self.rain_1h,
                wind_speed=self.wind_speed,
                clouds=self.clouds,
                visibility=self.visibility,
                temperature=self.temperature,
                rain_probability=self.rain_probability
            )
            object.__setattr__(self, 'weather_code', code)
            object.__setattr__(self, 'description', desc)
    
    @property
    def rainfall_intensity(self) -> int:
        """
        Retorna intensidade de chuva composta (0-100)
        
        Combina volume (mm/h) e probabilidade (%) usando a mesma sigmoide
        utilizada nas previsões horárias/diárias, garantindo consistência entre
        rotas simples e detalhada.
        """
        intensity = calculate_rainfall_intensity(
            rain_probability=self.rain_probability,
            rain_volume=self.rain_1h
        )
        return int(round(intensity))
    
    @property
    def clouds_description(self) -> str:
        """
        Retorna descrição da cobertura de nuvens baseada na porcentagem
        
        Returns:
            Descrição em português da cobertura de nuvens
        """
        if self.clouds <= 10:
            return CloudCoverage.CLEAR.value
        elif self.clouds <= 25:
            return CloudCoverage.FEW_CLOUDS.value
        elif self.clouds <= 50:
            return CloudCoverage.SCATTERED_CLOUDS.value
        elif self.clouds <= 84:
            return CloudCoverage.BROKEN_CLOUDS.value
        else:
            return CloudCoverage.OVERCAST.value
    
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
        
        response = {
            'cityId': self.city_id,
            'cityName': self.city_name,
            'timestamp': timestamp_brasil.isoformat(),  # Agora em horário Brasil
            'rainfallIntensity': self.rainfall_intensity,
            'rainfallProbability': round(self.rain_probability, 1),
            'rainVolumeHour': round(self.rain_1h, 1),
            'dailyRainAccumulation': round(self.rain_accumulated_day, 1),
            'temperature': round(self.temperature, 1),
            'humidity': round(self.humidity, 1),
            'windSpeed': round(self.wind_speed, 1),
            'windDirection': self.wind_direction,
            'description': self.description,
            'feelsLike': round(self.feels_like, 1),
            'pressure': round(self.pressure, 1),
            'visibility': round(self.visibility),
            'clouds': round(self.clouds, 1),
            'cloudsDescription': self.clouds_description,
            'weatherAlert': [alert.to_dict() for alert in self.weather_alert],  # Array de alertas estruturados
            'weatherCode': self.weather_code,
            'tempMin': round(self.temp_min, 1),
            'tempMax': round(self.temp_max, 1),
            'isDay': self.is_day
        }
        
        if self.daily_aggregates:
            response['dailyAggregates'] = self.daily_aggregates.to_api_response()

        return response
