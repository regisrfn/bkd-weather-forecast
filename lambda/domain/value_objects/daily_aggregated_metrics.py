"""
Value Object: Métricas agregadas por dia
"""
from dataclasses import dataclass


@dataclass
class DailyAggregatedMetrics:
    """
    Métricas diárias derivadas de previsões horárias e diárias
    """
    date: str  # YYYY-MM-DD
    rain_volume: float
    rain_intensity_max: float
    rain_probability_max: float
    wind_speed_max: float
    temp_min: float
    temp_max: float

    def to_api_response(self) -> dict:
        """Converte para formato camelCase usado na API"""
        return {
            'date': self.date,
            'rainVolume': round(self.rain_volume, 1),
            'rainIntensityMax': int(round(self.rain_intensity_max, 1)),
            'rainProbabilityMax': round(self.rain_probability_max, 1),
            'windSpeedMax': round(self.wind_speed_max, 1),
            'tempMin': round(self.temp_min, 1),
            'tempMax': round(self.temp_max, 1),
        }
