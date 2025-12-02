"""
Testes Unitários - WeatherProviderFactory
"""
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from infrastructure.adapters.output.providers import weather_provider_factory as factory_module
from infrastructure.adapters.output.providers.weather_provider_factory import (
    WeatherProviderFactory,
    ProviderStrategy,
    get_weather_provider_factory,
)


@pytest.fixture
def providers(monkeypatch):
    calls = {"ow": 0, "om": 0}
    openweather = MagicMock(provider_name="OpenWeather")
    openmeteo = MagicMock(provider_name="OpenMeteo")

    def fake_get_openweather_provider(cache=None):
        calls["ow"] += 1
        return openweather

    def fake_get_openmeteo_provider(cache=None):
        calls["om"] += 1
        return openmeteo

    monkeypatch.setattr(factory_module, "get_openweather_provider", fake_get_openweather_provider)
    monkeypatch.setattr(factory_module, "get_openmeteo_provider", fake_get_openmeteo_provider)
    monkeypatch.setattr(factory_module, "_factory_instance", None)

    return openweather, openmeteo, calls


def test_hybrid_strategy_uses_correct_providers(providers):
    openweather, openmeteo, calls = providers

    factory = WeatherProviderFactory(strategy=ProviderStrategy.HYBRID)

    assert factory.get_current_weather_provider() is openweather
    assert factory.get_daily_forecast_provider() is openmeteo
    assert factory.get_hourly_forecast_provider() is openmeteo

    # Lazy init - cada provider apenas uma vez
    factory.get_current_weather_provider()
    assert calls["ow"] == 1
    assert calls["om"] == 1


def test_openmeteo_only_strategy_and_singleton(providers, monkeypatch):
    openweather, openmeteo, calls = providers
    monkeypatch.setattr(factory_module, "_factory_instance", None)

    factory = get_weather_provider_factory(strategy=ProviderStrategy.OPENMETEO_ONLY)
    assert factory.get_current_weather_provider() is openmeteo
    assert factory.get_daily_forecast_provider() is openmeteo
    assert factory.get_hourly_forecast_provider() is openmeteo
    assert factory.get_all_providers() == [openmeteo]

    # Segunda chamada deve reutilizar singleton
    again = get_weather_provider_factory()
    assert again is factory
    assert calls["ow"] == 0
    assert calls["om"] == 1

