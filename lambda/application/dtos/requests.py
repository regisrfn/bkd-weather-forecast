"""Request DTOs - Contratos de entrada para use cases"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass(frozen=True)
class GetWeatherRequest:
    """Request para buscar clima de uma cidade"""
    city_id: str
    target_datetime: Optional[datetime] = None


@dataclass(frozen=True)
class GetDetailedForecastRequest:
    """Request para buscar previsão detalhada (current + daily + hourly)"""
    city_id: str
    target_datetime: Optional[datetime] = None


@dataclass(frozen=True)
class GetRegionalWeatherRequest:
    """Request para buscar clima regional"""
    center_city_id: str
    radius_km: float
    target_datetime: Optional[datetime] = None


@dataclass(frozen=True)
class GetNeighborCitiesRequest:
    """Request para buscar cidades vizinhas"""
    center_city_id: str
    radius_km: float
