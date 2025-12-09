"""
Serviço de domínio para geração de alertas de chuva
Centraliza regras baseadas em rainfall_intensity e probabilidade de chuva.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

from domain.alerts.primitives import (
    AlertSeverity,
    WeatherAlert,
    RAIN_INTENSITY_REFERENCE,
    RAIN_EXPECTED_MIN_PROBABILITY,
)


# Faixas de intensidade (0-100) derivadas de rainfall_intensity
INTENSITY_THRESHOLDS = {
    "DRIZZLE_MIN": 1,      # >0 já considera garoa
    "LIGHT_MIN": 10,       # 10-24 -> chuva fraca
    "MODERATE_MIN": 25,    # 25-59 -> chuva moderada
    "HEAVY_MIN": 60,       # 60+ -> chuva forte
}

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
            details = {"probabilityPercent": round(data.rain_prob, 1)}
            if data.rain_1h > 0:
                details["rainMmH"] = round(data.rain_1h, 1)
            return [
                WeatherAlert(
                    code=code,
                    severity=severity,
                    description=RainAlertService._description_for(code),
                    timestamp=data.forecast_time,
                    details=details,
                )
            ]

        # Fallback: alta probabilidade de chuva com volume mínimo, mas sem classificação de intensidade
        # Só alerta se tiver volume >= 0.3mm E não caiu em nenhuma classificação acima
        if (
            data.rain_prob >= RAIN_EXPECTED_MIN_PROBABILITY
            and data.rain_1h >= 0.3
            and intensity < INTENSITY_THRESHOLDS["DRIZZLE_MIN"]
        ):
            return [
                WeatherAlert(
                    code="RAIN_EXPECTED",
                    severity=AlertSeverity.INFO,
                    description="🌧️ Alta probabilidade de chuva",
                    timestamp=data.forecast_time,
                    details={
                        "probabilityPercent": round(data.rain_prob, 1),
                        "rainMmH": round(data.rain_1h, 1),
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
