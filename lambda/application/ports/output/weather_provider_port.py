"""Weather Provider Port - Interface genérica para provedores climáticos"""
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from domain.entities.weather import Weather
from domain.entities.daily_forecast import DailyForecast
from domain.entities.hourly_forecast import HourlyForecast


class IWeatherProvider(ABC):
    """
    Interface genérica para provedores de dados meteorológicos.
    A aplicação passou a usar apenas Open-Meteo, mas mantemos a interface
    para facilitar troca futura de fonte.
    """

    @abstractmethod
    async def get_daily_forecast(
        self,
        latitude: float,
        longitude: float,
        city_id: str,
        days: int = 16,
        prefetched_data: Optional[dict] = None,
        cache_writes: Optional[dict] = None
    ) -> List[DailyForecast]:
        """
        Busca previsões diárias
        
        Args:
            latitude: Latitude da localização
            longitude: Longitude da localização
            city_id: ID único da cidade (para cache)
            days: Número de dias de previsão
        
        Returns:
            Lista de DailyForecast entities
        
        Raises:
            ProviderException: Se o provider falhar
        """
        pass
    
    @abstractmethod
    async def get_hourly_forecast(
        self,
        latitude: float,
        longitude: float,
        city_id: str,
        hours: int = 168,
        prefetched_data: Optional[dict] = None,
        cache_writes: Optional[dict] = None
    ) -> List[HourlyForecast]:
        """
        Busca previsões horárias
        
        Args:
            latitude: Latitude da localização
            longitude: Longitude da localização
            city_id: ID único da cidade (para cache)
            hours: Número de horas de previsão
        
        Returns:
            Lista de HourlyForecast entities
        
        Raises:
            ProviderException: Se o provider falhar
        """
        pass

    @staticmethod
    @abstractmethod
    def extract_current_weather_from_hourly(
        hourly_forecasts: List[HourlyForecast],
        daily_forecasts: Optional[List[DailyForecast]],
        city_id: str,
        city_name: str,
        target_datetime: Optional[datetime] = None
    ) -> Weather:
        """
        Converte dados horários já obtidos em um Weather atual.
        Implementação default fica no adapter que sabe transformar os dados.
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nome do provider (ex: 'OpenMeteo')"""
        pass
