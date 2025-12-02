"""
Serviço de domínio para alertas de temperatura (frio e neve)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List

from domain.alerts.primitives import AlertSeverity, WeatherAlert

WMO_SNOW_CODES = {71, 73, 75, 77, 85, 86}


@dataclass(frozen=True)
class TemperatureAlertInput:
    temperature_c: float
    weather_code: int
    forecast_time: datetime


class TemperatureAlertService:
    """Gera alertas de frio e neve."""

    @staticmethod
    def generate_alerts(data: TemperatureAlertInput) -> List[WeatherAlert]:
        alerts: List[WeatherAlert] = []

        # Neve
        if 600 <= data.weather_code < 700 or data.weather_code in WMO_SNOW_CODES:
            alerts.append(WeatherAlert(
                code="SNOW",
                severity=AlertSeverity.INFO,
                description="❄️ Neve (raro no Brasil)",
                timestamp=data.forecast_time,
                details={"weather_code": data.weather_code, "temperature_c": round(data.temperature_c, 1)}
            ))

        # Frio (apenas se temperatura fornecida)
        if data.temperature_c > 0:
            if data.temperature_c < 8:
                alerts.append(WeatherAlert(
                    code="VERY_COLD",
                    severity=AlertSeverity.DANGER,
                    description="🥶 ALERTA: Frio intenso",
                    timestamp=data.forecast_time,
                    details={"temperature_c": round(data.temperature_c, 1)}
                ))
            elif data.temperature_c < 12:
                alerts.append(WeatherAlert(
                    code="COLD",
                    severity=AlertSeverity.ALERT,
                    description="🧊 Frio",
                    timestamp=data.forecast_time,
                    details={"temperature_c": round(data.temperature_c, 1)}
                ))

        return alerts
