"""
Extended Forecast Entity - Entidade agregada para previsões detalhadas
Combina dados atuais (OpenWeather) com previsões estendidas (Open-Meteo)
"""
from dataclasses import dataclass, field
from typing import List, Optional
from domain.entities.weather import Weather
from domain.entities.daily_forecast import DailyForecast
from domain.entities.hourly_forecast import HourlyForecast


@dataclass
class ExtendedForecast:
    """
    Entidade Agregada de Previsão Estendida
    
    Consolida informações atuais detalhadas (OpenWeather) com
    previsões diárias de até 16 dias (Open-Meteo) e previsões
    horárias de até 7 dias (168 horas) para fornecer uma visão
    completa das condições meteorológicas.
    """
    city_id: str
    city_name: str
    city_state: str
    current_weather: Weather  # Dados atuais detalhados (prioritariamente Open-Meteo hourly)
    daily_forecasts: List[DailyForecast] = field(default_factory=list)  # Até 16 dias
    hourly_forecasts: List[HourlyForecast] = field(default_factory=list)  # Até 168 horas (7 dias)
    extended_available: bool = True  # Flag se dados Open-Meteo estão disponíveis
    
    def to_api_response(self) -> dict:
        """
        Converte para formato de resposta da API
        
        Returns:
            Dict consolidado com todos os dados
        """
        return {
            'cityInfo': {
                'cityId': self.city_id,
                'cityName': self.city_name,
                'state': self.city_state
            },
            'currentWeather': self.current_weather.to_api_response(),
            'dailyForecasts': [forecast.to_api_response() for forecast in self.daily_forecasts],
            'hourlyForecasts': [forecast.to_api_response() for forecast in self.hourly_forecasts],
            'extendedAvailable': self.extended_available,
            'forecastDays': len(self.daily_forecasts)
        }
