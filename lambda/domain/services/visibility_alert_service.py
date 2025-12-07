"""
Serviço de domínio para alertas de visibilidade
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List

from domain.alerts.primitives import AlertSeverity, WeatherAlert
from domain.services.base_alert_service import BaseAlertService


@dataclass(frozen=True)
class VisibilityAlertInput:
    visibility_m: float  # metros
    forecast_time: datetime


class VisibilityAlertService(BaseAlertService):
    """Gera alertas de visibilidade reduzida."""

    @staticmethod
    def generate_alerts(data: VisibilityAlertInput) -> List[WeatherAlert]:
        alerts: List[WeatherAlert] = []

        if data.visibility_m < 1000:
            alerts.append(BaseAlertService.create_alert(
                code="LOW_VISIBILITY",
                severity=AlertSeverity.ALERT,
                description="🌫️ ALERTA: Visibilidade reduzida",
                timestamp=data.forecast_time,
                details={"visibilityMeters": int(data.visibility_m)}
            ))
        elif data.visibility_m < 3000:
            alerts.append(BaseAlertService.create_alert(
                code="LOW_VISIBILITY",
                severity=AlertSeverity.WARNING,
                description="🌫️ Visibilidade reduzida",
                timestamp=data.forecast_time,
                details={"visibilityMeters": int(data.visibility_m)}
            ))

        return alerts
