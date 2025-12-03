"""
Serviço de domínio para geração de alertas de chuva
Centraliza regras baseadas em rainfall_intensity, probabilidade e códigos WMO/OWM.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

from domain.alerts.primitives import (
    AlertSeverity,
    WeatherAlert,
    RAIN_INTENSITY_REFERENCE,
    RAIN_PROBABILITY_THRESHOLD,
)


# Faixas de intensidade (0-100) derivadas de rainfall_intensity
INTENSITY_THRESHOLDS = {
    "DRIZZLE_MIN": 1,      # >0 já considera garoa
    "LIGHT_MIN": 10,       # 10-24 -> chuva fraca
    "MODERATE_MIN": 25,    # 25-59 -> chuva moderada
    "HEAVY_MIN": 60,       # 60+ -> chuva forte
}

# Severidade mínima sugerida por códigos (WMO e OpenWeather)
# Usado como piso quando não há volume ou intensidade relevante.
CODE_SEVERITY_FLOOR = {
    # WMO rain showers
    80: ("LIGHT_RAIN", AlertSeverity.INFO),
    81: ("MODERATE_RAIN", AlertSeverity.WARNING),
    82: ("HEAVY_RAIN", AlertSeverity.ALERT),
    # WMO thunderstorms
    95: ("STORM", AlertSeverity.DANGER),
    96: ("STORM", AlertSeverity.DANGER),
    99: ("STORM", AlertSeverity.DANGER),
}


def _owm_floor(code: int) -> Optional[Tuple[str, AlertSeverity]]:
    """Mapeia códigos OpenWeather para severidade mínima."""
    if 200 <= code < 300:
        return ("STORM", AlertSeverity.DANGER)
    if code in [502, 503, 504, 522, 531]:
        return ("HEAVY_RAIN", AlertSeverity.ALERT)
    if code in [500, 501, 511, 520, 521]:
        return ("LIGHT_RAIN", AlertSeverity.INFO)
    return None


@dataclass(frozen=True)
class RainAlertInput:
    weather_code: int  # Mantido para compatibilidade, mas não usado mais
    rain_prob: float
    rain_1h: float
    rainfall_intensity: float  # Intensidade já calculada pela entidade
    forecast_time: datetime


class RainAlertService:
    """Gera alertas de chuva com base em intensidade composta e códigos."""

    @staticmethod
    def compute_rainfall_intensity(rain_prob: float, rain_1h: float) -> float:
        """Replica o cálculo do Weather.rainfall_intensity (0-100)."""
        if rain_1h == 0:
            return 0.0
        composite = (rain_1h * (rain_prob / 100.0)) / RAIN_INTENSITY_REFERENCE * 100.0
        return min(100.0, composite)

    @staticmethod
    def _code_floor(code: int) -> Optional[Tuple[str, AlertSeverity]]:
        if code in CODE_SEVERITY_FLOOR:
            return CODE_SEVERITY_FLOOR[code]
        return _owm_floor(code)

    @staticmethod
    def _classify_by_intensity(intensity: float) -> Optional[Tuple[str, AlertSeverity]]:
        if intensity >= INTENSITY_THRESHOLDS["HEAVY_MIN"]:
            return ("HEAVY_RAIN", AlertSeverity.ALERT)
        if intensity >= INTENSITY_THRESHOLDS["MODERATE_MIN"]:
            return ("MODERATE_RAIN", AlertSeverity.WARNING)
        if intensity >= INTENSITY_THRESHOLDS["LIGHT_MIN"]:
            return ("LIGHT_RAIN", AlertSeverity.INFO)
        if intensity >= INTENSITY_THRESHOLDS["DRIZZLE_MIN"]:
            return ("DRIZZLE", AlertSeverity.INFO)
        return None

    @staticmethod
    def _is_rain_code(code: int) -> bool:
        return (
            code in CODE_SEVERITY_FLOOR
            or 200 <= code < 300
            or 300 <= code < 400
            or 500 <= code < 600
        )

    @staticmethod
    def generate_alerts(data: RainAlertInput) -> List[WeatherAlert]:
        """Retorna zero ou um alerta de precipitação."""
        # Usar rainfall_intensity já calculado ao invés de recalcular
        intensity = data.rainfall_intensity

        intensity_class = RainAlertService._classify_by_intensity(intensity)
        
        # Sistema proprietário: não depende mais de weather_code
        # Tempestade detectada por alta intensidade + alta probabilidade
        is_storm = intensity >= 40 and data.rain_prob >= 70
        
        chosen = intensity_class
        
        # Se for tempestade (alta intensidade + prob), elevar severidade
        if is_storm and intensity >= INTENSITY_THRESHOLDS["MODERATE_MIN"]:
            chosen = ("STORM", AlertSeverity.ALERT)

        if chosen:
            code, severity = chosen
            details = {"probability_percent": round(data.rain_prob, 1)}
            if data.rain_1h > 0:
                details["rain_mm_h"] = round(data.rain_1h, 1)
            return [
                WeatherAlert(
                    code=code,
                    severity=severity,
                    description=RainAlertService._description_for(code),
                    timestamp=data.forecast_time,
                    details=details,
                )
            ]

        # Fallback: alta probabilidade de chuva, MAS sem volume/intensidade
        if (
            data.rain_prob >= RAIN_PROBABILITY_THRESHOLD
            and data.rain_1h == 0
            and intensity == 0
        ):
            return [
                WeatherAlert(
                    code="RAIN_EXPECTED",
                    severity=AlertSeverity.INFO,
                    description="🌧️ Alta probabilidade de chuva",
                    timestamp=data.forecast_time,
                    details={
                        "probability_percent": round(data.rain_prob, 1),
                    },
                )
            ]

        return []

    @staticmethod
    def _description_for(code: str) -> str:
        return {
            "DRIZZLE": "🌦️ Garoa",
            "LIGHT_RAIN": "🌧️ Chuva fraca",
            "MODERATE_RAIN": "🌧️ Chuva moderada",
            "HEAVY_RAIN": "⚠️ ALERTA: Chuva forte",
            "STORM": "⚠️ ALERTA: Tempestade com raios",
        }.get(code, "🌧️ Chuva")
