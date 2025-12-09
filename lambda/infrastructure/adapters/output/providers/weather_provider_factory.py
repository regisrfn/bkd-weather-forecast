"""
Weather Provider Factory - criação centralizada do provider único (Open-Meteo)
"""
from typing import Optional

from application.ports.output.weather_provider_port import IWeatherProvider
from infrastructure.adapters.output.providers.openmeteo import get_openmeteo_provider
from infrastructure.adapters.output.cache.async_dynamodb_cache import AsyncDynamoDBCache


class WeatherProviderFactory:
    """
    Factory simples para gerenciar o provider de clima.
    Mantém lazy-loading e singleton para reuso em execução quente da Lambda.
    """

    def __init__(self, cache: Optional[AsyncDynamoDBCache] = None):
        self.cache = cache
        self._openmeteo: Optional[IWeatherProvider] = None

    def get_weather_provider(self) -> IWeatherProvider:
        """Retorna provider padrão (Open-Meteo)."""
        return self._get_openmeteo()

    # Métodos de compatibilidade usados pela camada de entrada
    def get_current_weather_provider(self) -> IWeatherProvider:
        return self._get_openmeteo()

    def get_daily_forecast_provider(self) -> IWeatherProvider:
        return self._get_openmeteo()

    def get_hourly_forecast_provider(self) -> IWeatherProvider:
        return self._get_openmeteo()

    def get_all_providers(self) -> list[IWeatherProvider]:
        """Mantido para compatibilidade com chamadas que iteravam sobre providers."""
        return [self._get_openmeteo()]

    def _get_openmeteo(self) -> IWeatherProvider:
        if self._openmeteo is None:
            self._openmeteo = get_openmeteo_provider(cache=self.cache)
        return self._openmeteo


# Factory singleton global
_factory_instance: Optional[WeatherProviderFactory] = None


def get_weather_provider_factory(
    cache: Optional[AsyncDynamoDBCache] = None
) -> WeatherProviderFactory:
    """
    Retorna singleton da factory (somente Open-Meteo).
    """
    global _factory_instance

    if _factory_instance is None:
        _factory_instance = WeatherProviderFactory(cache=cache)

    return _factory_instance
