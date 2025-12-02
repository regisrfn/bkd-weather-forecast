"""
Serviço de domínio para alertas de vento
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List

from domain.alerts.primitives import AlertSeverity, WeatherAlert


@dataclass(frozen=True)
class WindAlertInput:
    wind_speed: float  # km/h
    forecast_time: datetime


class WindAlertService:
    """Gera alertas de vento a partir da velocidade (km/h)."""

    @staticmethod
    def generate_alerts(data: WindAlertInput) -> List[WeatherAlert]:
        alerts: List[WeatherAlert] = []

        if data.wind_speed >= 50:
            alerts.append(WeatherAlert(
                code="STRONG_WIND",
                severity=AlertSeverity.ALERT,
                description="💨 ALERTA: Ventos fortes",
                timestamp=data.forecast_time,
                details={"wind_speed_kmh": round(data.wind_speed, 1)}
            ))
        elif data.wind_speed >= 30:
            alerts.append(WeatherAlert(
                code="MODERATE_WIND",
                severity=AlertSeverity.INFO,
                description="💨 Ventos moderados",
                timestamp=data.forecast_time,
                details={"wind_speed_kmh": round(data.wind_speed, 1)}
            ))

        return alerts
