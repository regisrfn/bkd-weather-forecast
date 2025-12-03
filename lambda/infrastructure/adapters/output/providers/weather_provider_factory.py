"""
Weather Provider Factory - Cria e gerencia instâncias de providers
Implementa strategy pattern para seleção de providers
"""
from typing import Dict, Optional
from enum import Enum

from application.ports.output.weather_provider_port import IWeatherProvider
from infrastructure.adapters.output.providers.openweather import get_openweather_provider
from infrastructure.adapters.output.providers.openmeteo import get_openmeteo_provider
from infrastructure.adapters.output.cache.async_dynamodb_cache import AsyncDynamoDBCache


class ProviderStrategy(Enum):
    """Estratégias de seleção de provider"""
    OPENWEATHER_PRIMARY = "openweather_primary"  # OpenWeather para tudo
    OPENMETEO_PRIMARY = "openmeteo_primary"  # OpenMeteo para tudo
    HYBRID = "hybrid"  # OpenWeather para current, OpenMeteo para forecasts
    OPENMETEO_ONLY = "openmeteo_only"  # Apenas OpenMeteo (grátis)


class WeatherProviderFactory:
    """
    Factory para criação e gerenciamento de weather providers
    
    Responsabilidades:
    - Criar instâncias de providers (singleton)
    - Implementar estratégias de seleção
    - Gerenciar cache compartilhado
    """
    
    def __init__(
        self,
        strategy: ProviderStrategy = ProviderStrategy.HYBRID,
        cache: Optional[AsyncDynamoDBCache] = None
    ):
        """
        Inicializa factory
        
        Args:
            strategy: Estratégia de seleção de providers
            cache: Cache compartilhado (opcional)
        """
        self.strategy = strategy
        self.cache = cache
        
        # Lazy initialization de providers
        self._openweather: Optional[IWeatherProvider] = None
        self._openmeteo: Optional[IWeatherProvider] = None
    
    def get_current_weather_provider(self) -> IWeatherProvider:
        """
        Retorna provider para dados meteorológicos atuais
        
        Returns:
            Provider apropriado baseado na estratégia
        """
        if self.strategy == ProviderStrategy.OPENWEATHER_PRIMARY:
            return self._get_openweather()
        elif self.strategy == ProviderStrategy.OPENMETEO_PRIMARY:
            return self._get_openmeteo()
        elif self.strategy == ProviderStrategy.HYBRID:
            return self._get_openweather()  # OpenWeather melhor para current
        elif self.strategy == ProviderStrategy.OPENMETEO_ONLY:
            return self._get_openmeteo()
        
        return self._get_openweather()  # Default
    
    def get_daily_forecast_provider(self) -> IWeatherProvider:
        """
        Retorna provider para previsões diárias
        
        Returns:
            Provider apropriado baseado na estratégia
        """
        if self.strategy == ProviderStrategy.OPENWEATHER_PRIMARY:
            # OpenWeather One Call 3.0 tem daily (8 dias)
            return self._get_openweather()
        elif self.strategy == ProviderStrategy.OPENMETEO_PRIMARY:
            return self._get_openmeteo()
        elif self.strategy == ProviderStrategy.HYBRID:
            return self._get_openweather()  # OpenWeather dias 1-8, OpenMeteo complementa 9-16
        elif self.strategy == ProviderStrategy.OPENMETEO_ONLY:
            return self._get_openmeteo()
        
        return self._get_openmeteo()  # Default
    
    def get_hourly_forecast_provider(self) -> IWeatherProvider:
        """
        Retorna provider para previsões horárias
        
        Returns:
            Provider apropriado baseado na estratégia
        """
        if self.strategy == ProviderStrategy.OPENWEATHER_PRIMARY:
            # OpenWeather One Call 3.0 tem hourly (48h) - usar para consistência com alertas
            return self._get_openweather()
        elif self.strategy == ProviderStrategy.OPENMETEO_PRIMARY:
            return self._get_openmeteo()
        elif self.strategy == ProviderStrategy.HYBRID:
            return self._get_openweather()  # OpenWeather para consistência com current/alertas
        elif self.strategy == ProviderStrategy.OPENMETEO_ONLY:
            return self._get_openmeteo()
        
        return self._get_openmeteo()  # Default
    
    def get_all_providers(self) -> list[IWeatherProvider]:
        """
        Retorna todos os providers disponíveis
        Útil para operações que precisam tentar múltiplos providers
        
        Returns:
            Lista de providers
        """
        providers = []
        
        if self.strategy != ProviderStrategy.OPENMETEO_ONLY:
            providers.append(self._get_openweather())
        
        providers.append(self._get_openmeteo())
        
        return providers
    
    def _get_openweather(self) -> IWeatherProvider:
        """Lazy initialization do OpenWeather provider"""
        if self._openweather is None:
            self._openweather = get_openweather_provider(cache=self.cache)
        return self._openweather
    
    def _get_openmeteo(self) -> IWeatherProvider:
        """Lazy initialization do OpenMeteo provider"""
        if self._openmeteo is None:
            self._openmeteo = get_openmeteo_provider(cache=self.cache)
        return self._openmeteo


# Factory singleton global
_factory_instance: Optional[WeatherProviderFactory] = None


def get_weather_provider_factory(
    strategy: ProviderStrategy = ProviderStrategy.HYBRID,
    cache: Optional[AsyncDynamoDBCache] = None
) -> WeatherProviderFactory:
    """
    Retorna singleton da factory
    
    Args:
        strategy: Estratégia de seleção de providers
        cache: Cache compartilhado
    
    Returns:
        WeatherProviderFactory instance
    """
    global _factory_instance
    
    if _factory_instance is None:
        _factory_instance = WeatherProviderFactory(strategy=strategy, cache=cache)
    
    return _factory_instance
