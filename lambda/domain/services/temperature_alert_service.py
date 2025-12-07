"""
Serviço de domínio para alertas de temperatura (frio e neve)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List

from domain.alerts.primitives import AlertSeverity, WeatherAlert
from domain.services.base_alert_service import BaseAlertService

WMO_SNOW_CODES = {71, 73, 75, 77, 85, 86}


@dataclass(frozen=True)
class TemperatureAlertInput:
    temperature_c: float
    weather_code: int
    forecast_time: datetime


class TemperatureAlertService(BaseAlertService):
    """Gera alertas de frio e neve."""

    @staticmethod
    def generate_alerts(data: TemperatureAlertInput) -> List[WeatherAlert]:
        alerts: List[WeatherAlert] = []

        # Neve
        if 600 <= data.weather_code < 700 or data.weather_code in WMO_SNOW_CODES:
            alerts.append(BaseAlertService.create_alert(
                code="SNOW",
                severity=AlertSeverity.INFO,
                description="❄️ Neve (raro no Brasil)",
                timestamp=data.forecast_time,
                details=BaseAlertService.round_details({
                    "weatherCode": data.weather_code,
                    "temperatureC": data.temperature_c
                })
            ))

        # Frio (apenas se temperatura fornecida)
        if data.temperature_c > 0:
            if data.temperature_c < 8:
                alerts.append(BaseAlertService.create_alert(
                    code="VERY_COLD",
                    severity=AlertSeverity.DANGER,
                    description="🥶 ALERTA: Frio intenso",
                    timestamp=data.forecast_time,
                    details=BaseAlertService.round_details({"temperatureC": data.temperature_c})
                ))
            elif data.temperature_c < 12:
                alerts.append(BaseAlertService.create_alert(
                    code="COLD",
                    severity=AlertSeverity.ALERT,
                    description="🧊 Frio",
                    timestamp=data.forecast_time,
                    details=BaseAlertService.round_details({"temperatureC": data.temperature_c})
                ))

        return alerts
