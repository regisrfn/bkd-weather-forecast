"""
Serviço de domínio para alertas de temperatura (frio e neve)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List

from domain.alerts.primitives import AlertSeverity, WeatherAlert
from domain.services.base_alert_service import BaseAlertService
from domain.constants import WeatherCondition

# Compatibilidade: aceitar tanto códigos proprietários (900+) quanto antigos (600-699)
SNOW_CODES = {
    WeatherCondition.LIGHT_SNOW,
    WeatherCondition.MODERATE_SNOW,
    WeatherCondition.HEAVY_SNOW,
}


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
        if (
            data.weather_code in SNOW_CODES
            or 600 <= data.weather_code < 700  # compatibilidade com códigos legados
        ):
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
