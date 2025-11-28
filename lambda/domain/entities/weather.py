"""
Weather Entity - Entidade de domínio que representa dados meteorológicos
"""
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, List
from enum import Enum


# Threshold de probabilidade para alertas de precipitação
RAIN_PROBABILITY_THRESHOLD = 80  # Mínimo de 80% para gerar alertas de chuva

# Threshold de referência para intensidade de chuva (métrica composta)
# Define que 30mm/h com 100% de probabilidade = 100 pontos de intensidade
# Threshold maior permite melhor distribuição visual de chuvas fortes
RAIN_INTENSITY_REFERENCE = 30.0  # mm/h


class AlertSeverity(Enum):
    """Níveis de severidade de alertas climáticos"""
    INFO = "info"  # Informativo
    WARNING = "warning"  # Atenção
    ALERT = "alert"  # Alerta
    DANGER = "danger"  # Perigo


class CloudCoverage(Enum):
    """Descrições de cobertura de nuvens baseadas na porcentagem"""
    CLEAR = "Céu limpo"  # 0-10%
    FEW_CLOUDS = "Poucas nuvens"  # 11-25%
    SCATTERED_CLOUDS = "Parcialmente nublado"  # 26-50%
    BROKEN_CLOUDS = "Nublado"  # 51-84%
    OVERCAST = "Céu encoberto"  # 85-100%


@dataclass
class WeatherAlert:
    """Alerta climático estruturado"""
    code: str  # Código do alerta (ex: "STORM", "HEAVY_RAIN", "STRONG_WIND")
    severity: AlertSeverity  # Nível de severidade
    description: str  # Descrição em português
    timestamp: datetime  # Data/hora do alerta (quando se aplica)
    details: Optional[dict] = None  # Detalhes adicionais opcionais (ex: velocidade vento, mm chuva)
    
    def to_dict(self) -> dict:
        """Converte para dicionário para resposta da API"""
        result = {
            'code': self.code,
            'severity': self.severity.value,
            'description': self.description,
            'timestamp': self.timestamp.isoformat()
        }
        if self.details is not None:
            result['details'] = self.details
        return result


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
    def rainfall_intensity(self) -> float:
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
            return 0.0
        
        # Calcula intensidade composta: volume × probabilidade normalizado
        composite_intensity = (self.rain_1h * self.rain_probability / 100.0) / RAIN_INTENSITY_REFERENCE * 100.0
        
        # Limita em 100 para manter compatibilidade com frontend
        return min(100.0, composite_intensity)
    
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
        
        # Alertas de PRECIPITAÇÃO baseados em VOLUME (mm/h)
        # Requer probabilidade >= 80% para reduzir falsos positivos
        if rain_1h > 0 and rain_prob >= RAIN_PROBABILITY_THRESHOLD:
            if rain_1h >= 50:
                alerts.append(WeatherAlert(
                    code="HEAVY_RAIN",
                    severity=AlertSeverity.ALERT,
                    description="⚠️ ALERTA: Chuva forte",
                    timestamp=alert_time,
                    details={"rain_mm_h": round(rain_1h, 1), "probability_percent": round(rain_prob, 1)}
                ))
            elif rain_1h >= 10:
                alerts.append(WeatherAlert(
                    code="MODERATE_RAIN",
                    severity=AlertSeverity.WARNING,
                    description="🌧️ Chuva moderada",
                    timestamp=alert_time,
                    details={"rain_mm_h": round(rain_1h, 1), "probability_percent": round(rain_prob, 1)}
                ))
            elif rain_1h >= 2.5:
                alerts.append(WeatherAlert(
                    code="LIGHT_RAIN",
                    severity=AlertSeverity.INFO,
                    description="🌧️ Chuva fraca",
                    timestamp=alert_time,
                    details={"rain_mm_h": round(rain_1h, 1), "probability_percent": round(rain_prob, 1)}
                ))
            else:  # rain_1h > 0 mas < 2.5
                alerts.append(WeatherAlert(
                    code="DRIZZLE",
                    severity=AlertSeverity.INFO,
                    description="🌦️ Garoa",
                    timestamp=alert_time,
                    details={"rain_mm_h": round(rain_1h, 1), "probability_percent": round(rain_prob, 1)}
                ))
        
        # Alertas por código climático - TEMPESTADES
        if 200 <= weather_code < 300:
            if weather_code in [200, 201, 202, 210, 211, 212, 221]:
                alert_details = {"weather_code": weather_code, "probability_percent": round(rain_prob, 1)}
                if rain_1h > 0:
                    alert_details["rain_mm_h"] = round(rain_1h, 1)
                alerts.append(WeatherAlert(
                    code="STORM",
                    severity=AlertSeverity.DANGER,
                    description="⚠️ ALERTA: Tempestade com raios",
                    timestamp=alert_time,
                    details=alert_details
                ))
            else:
                alert_details = {"weather_code": weather_code, "probability_percent": round(rain_prob, 1)}
                if rain_1h > 0:
                    alert_details["rain_mm_h"] = round(rain_1h, 1)
                alerts.append(WeatherAlert(
                    code="STORM_RAIN",
                    severity=AlertSeverity.ALERT,
                    description="⚠️ Tempestade com chuva",
                    timestamp=alert_time,
                    details=alert_details
                ))
        
        # Alertas de CHUVA por código climático (quando não há volume medido)
        # Códigos 500-599 indicam chuva, mas API nem sempre retorna volume
        elif 500 <= weather_code < 600 and rain_1h == 0:
            if weather_code in [502, 503, 504, 522, 531]:
                # Chuva forte prevista por código (independente de probabilidade)
                alerts.append(WeatherAlert(
                    code="HEAVY_RAIN",
                    severity=AlertSeverity.ALERT,
                    description="⚠️ ALERTA: Chuva forte prevista",
                    timestamp=alert_time,
                    details={"weather_code": weather_code, "probability_percent": round(rain_prob, 1)}
                ))
            elif rain_prob >= RAIN_PROBABILITY_THRESHOLD:
                # Chuva leve/moderada com alta probabilidade (código 500-501, 520-521, etc)
                alerts.append(WeatherAlert(
                    code="RAIN_EXPECTED",
                    severity=AlertSeverity.INFO,
                    description="🌧️ Alta probabilidade de chuva",
                    timestamp=alert_time,
                    details={"weather_code": weather_code, "probability_percent": round(rain_prob, 1)}
                ))
        
        # NEVE
        elif 600 <= weather_code < 700:
            alerts.append(WeatherAlert(
                code="SNOW",
                severity=AlertSeverity.INFO,
                description="❄️ Neve (raro no Brasil)",
                timestamp=alert_time,
                details={"weather_code": weather_code, "temperature_c": round(temperature, 1)}
            ))
        
        # Fallback: RAIN_EXPECTED para alta probabilidade SEM volume E SEM código de chuva
        # Captura casos onde API indica alta probabilidade mas não retorna código nem volume
        # Evita redundância: só gera se NÃO houver alertas de precipitação
        elif rain_prob >= RAIN_PROBABILITY_THRESHOLD and not any(
            a.code in ["STORM", "STORM_RAIN", "HEAVY_RAIN", "MODERATE_RAIN", "LIGHT_RAIN", "DRIZZLE", "RAIN_EXPECTED"]
            for a in alerts
        ):
            alerts.append(WeatherAlert(
                code="RAIN_EXPECTED",
                severity=AlertSeverity.INFO,
                description="🌧️ Alta probabilidade de chuva",
                timestamp=alert_time,
                details={"probability_percent": round(rain_prob, 1)}
            ))
        
        # Alertas de VENTO FORTE
        if wind_speed >= 50:
            alerts.append(WeatherAlert(
                code="STRONG_WIND",
                severity=AlertSeverity.ALERT,
                description="💨 ALERTA: Ventos fortes",
                timestamp=alert_time,
                details={"wind_speed_kmh": round(wind_speed, 1)}
            ))
        elif wind_speed >= 30:
            alerts.append(WeatherAlert(
                code="MODERATE_WIND",
                severity=AlertSeverity.INFO,
                description="💨 Ventos moderados",
                timestamp=alert_time,
                details={"wind_speed_kmh": round(wind_speed, 1)}
            ))
        
        # Alertas de TEMPERATURA (frio considerando contexto brasileiro)
        if temperature > 0:  # Apenas se temperatura foi fornecida
            if temperature < 8:
                alerts.append(WeatherAlert(
                    code="VERY_COLD",
                    severity=AlertSeverity.DANGER,
                    description="🥶 ALERTA: Frio intenso",
                    timestamp=alert_time,
                    details={"temperature_c": round(temperature, 1)}
                ))
            elif temperature < 12:
                alerts.append(WeatherAlert(
                    code="COLD",
                    severity=AlertSeverity.ALERT,
                    description="🧊 Frio",
                    timestamp=alert_time,
                    details={"temperature_c": round(temperature, 1)}
                ))
        
        # Alertas de VISIBILIDADE
        if visibility < 1000:  # Menos de 1km
            alerts.append(WeatherAlert(
                code="LOW_VISIBILITY",
                severity=AlertSeverity.ALERT,
                description="🌫️ ALERTA: Visibilidade reduzida",
                timestamp=alert_time,
                details={"visibility_m": int(visibility)}
            ))
        elif visibility < 3000:  # Menos de 3km
            alerts.append(WeatherAlert(
                code="LOW_VISIBILITY",
                severity=AlertSeverity.WARNING,
                description="🌫️ Visibilidade reduzida",
                timestamp=alert_time,
                details={"visibility_m": int(visibility)}
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
            'rainfallProbability': round(self.rain_probability, 1),
            'rainVolumeHour': round(self.rain_1h, 1),
            'dailyRainAccumulation': round(self.rain_accumulated_day, 1),
            'temperature': round(self.temperature, 1),
            'humidity': round(self.humidity, 1),
            'windSpeed': round(self.wind_speed, 1),
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
