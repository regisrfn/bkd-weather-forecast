"""
Weather Entity - Entidade de domínio que representa dados meteorológicos
"""
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, List
from enum import Enum


class AlertSeverity(Enum):
    """Níveis de severidade de alertas climáticos"""
    INFO = "info"  # Informativo
    WARNING = "warning"  # Atenção
    ALERT = "alert"  # Alerta
    DANGER = "danger"  # Perigo


@dataclass
class WeatherAlert:
    """Alerta climático estruturado"""
    code: str  # Código do alerta (ex: "STORM", "HEAVY_RAIN", "STRONG_WIND")
    severity: AlertSeverity  # Nível de severidade
    description: str  # Descrição em português
    timestamp: datetime  # Data/hora do alerta (quando se aplica)
    
    def to_dict(self) -> dict:
        """Converte para dicionário para resposta da API"""
        return {
            'code': self.code,
            'severity': self.severity.value,
            'description': self.description,
            'timestamp': self.timestamp.isoformat()
        }


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
    description: str = ""  # Descrição do clima (ex: "céu limpo", "nublado")
    feels_like: float = 0.0  # Sensação térmica (°C)
    pressure: float = 0.0  # Pressão atmosférica (hPa)
    visibility: float = 0.0  # Visibilidade (metros)
    weather_alert: List[WeatherAlert] = field(default_factory=list)  # Lista de alertas estruturados
    weather_code: int = 0  # Código da condição climática da API
    
    @property
    def rainfall_intensity(self) -> float:
        """
        Retorna probabilidade de chuva (0-100%)
        Agora baseado no campo 'pop' (Probability of Precipitation) da API
        """
        return self.rain_probability
    
    @staticmethod
    def get_weather_alert(weather_code: int, rain_prob: float, wind_speed: float, 
                         forecast_time: datetime) -> List[WeatherAlert]:
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
        
        # Alertas por código climático - TEMPESTADES
        if 200 <= weather_code < 300:
            if weather_code in [200, 201, 202, 210, 211, 212, 221]:
                alerts.append(WeatherAlert(
                    code="STORM",
                    severity=AlertSeverity.DANGER,
                    description="⚠️ ALERTA: Tempestade com raios",
                    timestamp=alert_time
                ))
            else:
                alerts.append(WeatherAlert(
                    code="STORM_RAIN",
                    severity=AlertSeverity.ALERT,
                    description="⚠️ Tempestade com chuva",
                    timestamp=alert_time
                ))
        
        # CHUVAS
        elif 500 <= weather_code < 600:
            if weather_code in [502, 503, 504, 522, 531]:
                # Chuva forte
                alerts.append(WeatherAlert(
                    code="HEAVY_RAIN",
                    severity=AlertSeverity.ALERT,
                    description="⚠️ ALERTA: Chuva forte",
                    timestamp=alert_time
                ))
            elif rain_prob >= 70:
                # Chuva moderada com alta probabilidade
                alerts.append(WeatherAlert(
                    code="RAIN_EXPECTED",
                    severity=AlertSeverity.WARNING,
                    description="🌧️ Alta probabilidade de chuva",
                    timestamp=alert_time
                ))
        
        # NEVE
        elif 600 <= weather_code < 700:
            alerts.append(WeatherAlert(
                code="SNOW",
                severity=AlertSeverity.INFO,
                description="❄️ Neve (raro no Brasil)",
                timestamp=alert_time
            ))
        
        # Alerta de chuva pela PROBABILIDADE apenas (se não houver outros alertas de chuva)
        # Consolida em um único alerta de chuva
        elif rain_prob >= 70 and not any(a.code in ["STORM", "STORM_RAIN", "HEAVY_RAIN", "RAIN_EXPECTED"] for a in alerts):
            alerts.append(WeatherAlert(
                code="RAIN_EXPECTED",
                severity=AlertSeverity.WARNING,
                description="🌧️ Alta probabilidade de chuva",
                timestamp=alert_time
            ))
        
        # Alertas de VENTO FORTE
        if wind_speed >= 50:
            alerts.append(WeatherAlert(
                code="STRONG_WIND",
                severity=AlertSeverity.ALERT,
                description="💨 ALERTA: Ventos fortes",
                timestamp=alert_time
            ))
        elif wind_speed >= 30:
            alerts.append(WeatherAlert(
                code="MODERATE_WIND",
                severity=AlertSeverity.WARNING,
                description="💨 Ventos moderados",
                timestamp=alert_time
            ))
        
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
            'rainfallIntensity': round(self.rainfall_intensity, 1),
            'temperature': round(self.temperature, 1),
            'humidity': round(self.humidity, 1),
            'windSpeed': round(self.wind_speed, 1),
            'description': self.description,
            'feelsLike': round(self.feels_like, 1),
            'pressure': round(self.pressure, 1),
            'visibility': round(self.visibility),
            'weatherAlert': [alert.to_dict() for alert in self.weather_alert]  # Array de alertas estruturados
        }
