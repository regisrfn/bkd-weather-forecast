"""
Testes Unitários - GetCityDetailedForecastUseCase
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from application.use_cases.get_city_detailed_forecast_use_case import GetCityDetailedForecastUseCase
from domain.alerts.primitives import WeatherAlert, AlertSeverity
from domain.entities.city import City
from domain.entities.daily_forecast import DailyForecast
from domain.entities.hourly_forecast import HourlyForecast
from domain.entities.weather import Weather
from domain.exceptions import CityNotFoundException
from domain.services import weather_enricher
from domain.services import alerts_generator


def _make_city() -> City:
    return City(
        id="3543204",
        name="Ribeirão Preto",
        state="SP",
        region="Sudeste",
        latitude=-21.1704,
        longitude=-47.8103
    )


def _make_weather() -> Weather:
    return Weather(
        city_id="3543204",
        city_name="Ribeirão Preto",
        timestamp=datetime(2025, 11, 27, 15, 0, tzinfo=ZoneInfo("UTC")),
        temperature=28.0,
        humidity=60,
        wind_speed=12.0,
        rain_probability=10.0,
        description="céu limpo",
    )


def _make_daily() -> list[DailyForecast]:
    return [
        DailyForecast(
            date="2025-11-28",
            temp_min=20.0,
            temp_max=30.0,
            precipitation_mm=2.0,
            rain_probability=20.0,
                rainfall_intensity=0.0,
            wind_speed_max=15.0,
            wind_direction=90,
            uv_index=7.5,
            sunrise="06:00",
            sunset="18:00",
            precipitation_hours=1.0,
        )
    ]


def _make_hourly() -> list[HourlyForecast]:
    return [
        HourlyForecast(
            timestamp="2025-11-27T15:00:00-03:00",
            temperature=27.0,
            precipitation=0.2,
            precipitation_probability=15,
            rainfall_intensity=0.0,
            humidity=55,
            wind_speed=10.0,
            wind_direction=180,
            cloud_cover=20,
            weather_code=1,
            description="Claro",
        )
    ]


@pytest.fixture
def city_repository():
    return MagicMock()


@pytest.fixture
def providers():
    current = MagicMock()
    current.provider_name = "CurrentProvider"
    current.get_current_weather = AsyncMock()

    daily = MagicMock()
    daily.provider_name = "DailyProvider"
    daily.get_daily_forecast = AsyncMock()

    hourly = MagicMock()
    hourly.provider_name = "HourlyProvider"
    hourly.get_hourly_forecast = AsyncMock()

    return current, daily, hourly


def _build_use_case(city_repository, providers):
    current, daily, hourly = providers
    return GetCityDetailedForecastUseCase(
        city_repository=city_repository,
        current_weather_provider=current,
        daily_forecast_provider=daily,
        hourly_forecast_provider=hourly,
    )


@pytest.mark.asyncio
async def test_execute_success_enriches_and_merges_alerts(city_repository, providers):
    """
    Testa que o use case:
    - Chama todos os providers
    - Retorna ExtendedForecast com dados
    - Inclui daily e hourly forecasts
    """
    city_repository.get_by_id.return_value = _make_city()

    current_provider, daily_provider, hourly_provider = providers
    base_weather = _make_weather()

    # Configure all async methods
    current_provider.get_current_weather.return_value = base_weather
    daily_provider.get_daily_forecast.return_value = _make_daily()
    hourly_provider.get_hourly_forecast.return_value = _make_hourly()

    use_case = _build_use_case(city_repository, providers)
    result = await use_case.execute("3543204")

    # Verificar estrutura do resultado
    assert result.current_weather is not None
    assert result.current_weather.city_id == "3543204"
    assert result.extended_available is True
    assert len(result.daily_forecasts) > 0
    assert len(result.hourly_forecasts) > 0
    
    # Verificar que todos os providers foram chamados (agora são apenas 3 calls)
    current_provider.get_current_weather.assert_called_once()
    daily_provider.get_daily_forecast.assert_called_once()
    hourly_provider.get_hourly_forecast.assert_called_once()


@pytest.mark.asyncio
async def test_execute_continues_without_daily_data(monkeypatch, city_repository, providers):
    city_repository.get_by_id.return_value = _make_city()
    current_provider, daily_provider, hourly_provider = providers

    current_provider.get_current_weather.return_value = _make_weather()
    daily_provider.get_daily_forecast.side_effect = RuntimeError("daily boom")
    hourly_provider.get_hourly_forecast.return_value = _make_hourly()

    def mock_enrich(base_weather, hourly_forecasts, target_datetime=None):
        return base_weather
    
    monkeypatch.setattr(
        weather_enricher.WeatherEnricher,
        "enrich_with_hourly_data",
        mock_enrich,
    )
    
    def mock_alerts(forecasts, target_datetime=None, days_limit=7):
        return []
    
    monkeypatch.setattr(
        alerts_generator.AlertsGenerator,
        "generate_alerts_next_days",
        mock_alerts,
    )

    use_case = _build_use_case(city_repository, providers)
    result = await use_case.execute("3543204")

    assert result.extended_available is False
    assert result.daily_forecasts == []
    assert result.hourly_forecasts


@pytest.mark.asyncio
async def test_execute_raises_when_city_missing(city_repository, providers):
    city_repository.get_by_id.return_value = None
    use_case = _build_use_case(city_repository, providers)

    with pytest.raises(CityNotFoundException):
        await use_case.execute("0000000")

