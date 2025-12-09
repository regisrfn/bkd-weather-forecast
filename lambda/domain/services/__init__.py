"""
Domain Services - Serviços de lógica de negócio pura (sem conhecimento de APIs externas)

IMPORTANTE: Mappers de APIs externas → domain entities pertencem à infrastructure!
- infrastructure/providers/openmeteo/mappers/openmeteo_data_mapper.py
"""

from domain.services.alerts_generator import AlertsGenerator
from domain.services.weather_enricher import WeatherEnricher

# Manter imports de services de alertas existentes
from domain.services.rain_alert_service import RainAlertService
from domain.services.wind_alert_service import WindAlertService
from domain.services.visibility_alert_service import VisibilityAlertService
from domain.services.temperature_alert_service import TemperatureAlertService

__all__ = [
    'AlertsGenerator',
    'WeatherEnricher',
    'RainAlertService',
    'WindAlertService',
    'VisibilityAlertService',
    'TemperatureAlertService'
]
