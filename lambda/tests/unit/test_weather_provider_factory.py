"""Testes Unitários - WeatherProviderFactory"""
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from infrastructure.adapters.output.providers import weather_provider_factory as factory_module
from infrastructure.adapters.output.providers.weather_provider_factory import (
    WeatherProviderFactory,
    get_weather_provider_factory,
)


@pytest.fixture
def provider(monkeypatch):
    calls = {"om": 0}
    openmeteo = MagicMock(provider_name="OpenMeteo")

    def fake_get_openmeteo_provider(cache=None):
        calls["om"] += 1
        return openmeteo

    monkeypatch.setattr(factory_module, "get_openmeteo_provider", fake_get_openmeteo_provider)
    monkeypatch.setattr(factory_module, "_factory_instance", None)

    return openmeteo, calls


def test_factory_returns_openmeteo_for_all_methods(provider):
    openmeteo, calls = provider

    factory = WeatherProviderFactory()

    assert factory.get_weather_provider() is openmeteo
    assert factory.get_current_weather_provider() is openmeteo
    assert factory.get_daily_forecast_provider() is openmeteo
    assert factory.get_hourly_forecast_provider() is openmeteo
    assert factory.get_all_providers() == [openmeteo]

    # lazy init: segunda chamada não instancia novamente
    factory.get_weather_provider()
    assert calls["om"] == 1


def test_get_weather_provider_factory_singleton(provider, monkeypatch):
    openmeteo, calls = provider
    monkeypatch.setattr(factory_module, "_factory_instance", None)

    factory = get_weather_provider_factory()
    again = get_weather_provider_factory()

    assert factory is again
    assert factory.get_weather_provider() is openmeteo
    assert calls["om"] == 1
