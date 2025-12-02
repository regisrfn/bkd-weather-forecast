"""
Weather Provider Port - Interface genérica para provedores climáticos
Desacopla domínio de implementações concretas (OpenWeather, OpenMeteo, etc)
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime

from domain.entities.weather import Weather
from domain.entities.daily_forecast import DailyForecast
from domain.entities.hourly_forecast import HourlyForecast


class IWeatherProvider(ABC):
    """
    Interface genérica para provedores de dados meteorológicos
    
    Qualquer provider (OpenWeather, OpenMeteo, WeatherAPI, etc) deve implementar
    esta interface para ser usado pela aplicação.
    """
    
    @abstractmethod
    async def get_current_weather(
        self,
        latitude: float,
        longitude: float,
        city_id: str,
        city_name: str,
        target_datetime: Optional[datetime] = None
    ) -> Weather:
        """
        Busca dados meteorológicos atuais ou para datetime específico
        
        Args:
            latitude: Latitude da localização
            longitude: Longitude da localização
            city_id: ID único da cidade (para cache)
            city_name: Nome da cidade (para exibição)
            target_datetime: Datetime específico (None = mais próximo disponível)
        
        Returns:
            Weather entity com dados meteorológicos
        
        Raises:
            ProviderException: Se o provider falhar
        """
        pass
    
    @abstractmethod
    async def get_daily_forecast(
        self,
        latitude: float,
        longitude: float,
        city_id: str,
        days: int = 16
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
        hours: int = 168
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
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nome do provider (ex: 'OpenWeather', 'OpenMeteo')"""
        pass
    
    @property
    @abstractmethod
    def supports_current_weather(self) -> bool:
        """Se o provider suporta dados atuais"""
        pass
    
    @property
    @abstractmethod
    def supports_daily_forecast(self) -> bool:
        """Se o provider suporta previsões diárias"""
        pass
    
    @property
    @abstractmethod
    def supports_hourly_forecast(self) -> bool:
        """Se o provider suporta previsões horárias"""
        pass
