"""Application DTOs - Data Transfer Objects para contratos de API"""

from application.dtos.requests import (
    GetWeatherRequest,
    GetRegionalWeatherRequest,
    GetNeighborCitiesRequest,
    GetDetailedForecastRequest
)
from application.dtos.responses import (
    WeatherResponse,
    ExtendedForecastResponse,
    RegionalWeatherResponse,
    NeighborCitiesResponse
)

__all__ = [
    'GetWeatherRequest',
    'GetRegionalWeatherRequest',
    'GetNeighborCitiesRequest',
    'GetDetailedForecastRequest',
    'WeatherResponse',
    'ExtendedForecastResponse',
    'RegionalWeatherResponse',
    'NeighborCitiesResponse'
]
