"""
Weather Entity - Entidade de domínio que representa dados meteorológicos
"""
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, List
from enum import Enum

from domain.alerts.primitives import (
    AlertSeverity,
    WeatherAlert,
    RAIN_PROBABILITY_THRESHOLD,
    RAIN_INTENSITY_REFERENCE
)
from domain.services.rain_alert_service import RainAlertService, RainAlertInput
from domain.services.wind_alert_service import WindAlertService, WindAlertInput
from domain.services.visibility_alert_service import VisibilityAlertService, VisibilityAlertInput
from domain.services.temperature_alert_service import TemperatureAlertService, TemperatureAlertInput


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
    
    @property
    def rainfall_intensity(self) -> int:
        """
        Retorna intensidade de chuva composta (0-100)
        
        Combina volume de precipitação (mm/h) e probabilidade (%) em uma métrica única:
        - 0 pontos: Sem chuva ou volume insignificante
        - 100 pontos: Chuva forte garantida (30mm/h a 100% probabilidade)
        - Escala proporcional: volume × probabilidade / threshold
        
        Resolve o problema de "100% probabilidade mas 0mm" retornando 0 pontos,
        pois intensidade real = volume × probabilidade.
        
        Threshold: 30mm/h permite melhor distribuição visual de chuvas fortes.
        """
        if self.rain_1h == 0:
            return 0
        
        # Calcula intensidade composta: volume × probabilidade normalizado
        composite_intensity = (self.rain_1h * self.rain_probability / 100.0) / RAIN_INTENSITY_REFERENCE * 100.0
        
        # Limita em 100 e arredonda para inteiro
        return round(min(100.0, composite_intensity))
    
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
    
    @staticmethod
    def get_weather_alert(weather_code: int, rain_prob: float, wind_speed: float, 
                         forecast_time: datetime, rain_1h: float = 0.0, 
                         temperature: float = 0.0, visibility: float = 10000) -> List[WeatherAlert]:
        """
        Identifica alertas climáticos baseado no código da condição e outros parâmetros
        
        Retorna apenas UM alerta por code, priorizando pelo timestamp mais próximo.
        
        Códigos OpenWeatherMap:
        - 2xx: Tempestade
        - 3xx: Garoa
        - 5xx: Chuva
        - 6xx: Neve
        - 7xx: Atmosfera (neblina, fumaça, etc)
        - 800: Céu limpo
        - 80x: Nuvens
        
        Args:
            weather_code: Código da condição climática da API
            rain_prob: Probabilidade de chuva (0-100%)
            wind_speed: Velocidade do vento (km/h)
            forecast_time: Data/hora da previsão
            rain_1h: Volume de precipitação em mm/h (opcional)
            temperature: Temperatura em °C (opcional)
            visibility: Visibilidade em metros (opcional, padrão 10000m)
        
        Returns:
            Lista de alertas estruturados (array vazio se não houver alertas).
            Cada code aparece apenas uma vez, com prioridade para o timestamp mais próximo.
        """
        alerts = []
        
        # Converter para timezone Brasil para consistência
        brasil_tz = ZoneInfo("America/Sao_Paulo")
        if forecast_time.tzinfo is not None:
            alert_time = forecast_time.astimezone(brasil_tz)
        else:
            alert_time = forecast_time.replace(tzinfo=ZoneInfo("UTC")).astimezone(brasil_tz)

        # Alertas via serviços de domínio
        alerts.extend(RainAlertService.generate_alerts(RainAlertInput(
            weather_code=weather_code,
            rain_prob=rain_prob,
            rain_1h=rain_1h,
            forecast_time=alert_time
        )))
        alerts.extend(WindAlertService.generate_alerts(WindAlertInput(
            wind_speed=wind_speed,
            forecast_time=alert_time
        )))
        alerts.extend(VisibilityAlertService.generate_alerts(VisibilityAlertInput(
            visibility_m=visibility,
            forecast_time=alert_time
        )))
        alerts.extend(TemperatureAlertService.generate_alerts(TemperatureAlertInput(
            temperature_c=temperature,
            weather_code=weather_code,
            forecast_time=alert_time
        )))
        
        # Deduplica alertas: mantém apenas um alerta por code
        # Prioriza pelo timestamp mais próximo (menor timestamp = mais urgente)
        unique_alerts = {}
        for alert in alerts:
            if alert.code not in unique_alerts:
                unique_alerts[alert.code] = alert
            else:
                # Mantém o alerta com timestamp mais próximo (menor)
                if alert.timestamp < unique_alerts[alert.code].timestamp:
                    unique_alerts[alert.code] = alert
        
        return list(unique_alerts.values())
    
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
            'tempMin': round(self.temp_min, 1),
            'tempMax': round(self.temp_max, 1)
        }
