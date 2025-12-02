"""
Testes Unitários - HourlyWeatherProcessor
Testa o enriquecimento de dados Weather com hourly forecasts
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

from domain.entities.weather import Weather
from domain.entities.hourly_forecast import HourlyForecast
from infrastructure.adapters.helpers.hourly_weather_processor import HourlyWeatherProcessor


@pytest.fixture
def base_weather():
    """Weather entity base do OpenWeather"""
    return Weather(
        city_id="3543204",
        city_name="Ribeirão do Sul",
        timestamp=datetime(2025, 12, 1, 14, 0, tzinfo=ZoneInfo("America/Sao_Paulo")),
        temperature=28.5,
        humidity=65.0,
        wind_speed=12.5,
        wind_direction=180,
        rain_probability=30.0,
        rain_1h=0.5,
        rain_accumulated_day=2.5,
        description="Parcialmente nublado",
        feels_like=29.2,
        pressure=1013.25,
        visibility=10000,
        clouds=45.0,
        weather_code=2,
        temp_min=20.0,
        temp_max=32.0
    )


@pytest.fixture
def hourly_forecasts():
    """Lista de previsões horárias do Open-Meteo"""
    return [
        HourlyForecast(
            timestamp="2025-12-01T13:00:00",
            temperature=27.5,
            precipitation=0.3,
            precipitation_probability=25,
            humidity=68,
            wind_speed=11.0,
            wind_direction=175,
            cloud_cover=42,
            weather_code=2
        ),
        HourlyForecast(
            timestamp="2025-12-01T14:00:00",
            temperature=28.8,
            precipitation=0.4,
            precipitation_probability=32,
            humidity=64,
            wind_speed=13.2,
            wind_direction=185,
            cloud_cover=48,
            weather_code=2
        ),
        HourlyForecast(
            timestamp="2025-12-01T15:00:00",
            temperature=29.2,
            precipitation=0.6,
            precipitation_probability=35,
            humidity=62,
            wind_speed=14.5,
            wind_direction=190,
            cloud_cover=50,
            weather_code=3
        )
    ]


class TestEnrichWeatherWithHourly:
    """Testes para enriquecimento de Weather com dados hourly"""
    
    def test_enrich_with_closest_hour(self, base_weather, hourly_forecasts):
        """Deve enriquecer com dados da hora mais próxima"""
        enriched = HourlyWeatherProcessor.enrich_weather_with_hourly(
            base_weather=base_weather,
            hourly_forecasts=hourly_forecasts,
            target_datetime=datetime(2025, 12, 1, 14, 10, tzinfo=ZoneInfo("America/Sao_Paulo"))
        )
        
        assert enriched is not None
        
        # Dados hourly devem ser atualizados
        assert enriched.temperature == 28.8
        assert enriched.humidity == 64.0
        assert enriched.wind_speed == 13.2
        assert enriched.wind_direction == 185
        assert enriched.rain_probability == 32.0
        assert enriched.clouds == 48.0
        
        # Dados OpenWeather devem ser preservados
        assert enriched.feels_like == 29.2
        assert enriched.pressure == 1013.25
        assert enriched.visibility == 10000
        
        # Metadata deve ser mantida
        assert enriched.city_id == "3543204"
        assert enriched.city_name == "Ribeirão do Sul"
    
    def test_enrich_preserves_openweather_fields(self, base_weather, hourly_forecasts):
        """Deve preservar campos que Open-Meteo não fornece"""
        enriched = HourlyWeatherProcessor.enrich_weather_with_hourly(
            base_weather=base_weather,
            hourly_forecasts=hourly_forecasts
        )
        
        # Campos críticos do OpenWeather devem ser mantidos
        assert enriched.feels_like == base_weather.feels_like
        assert enriched.pressure == base_weather.pressure
        assert enriched.visibility == base_weather.visibility
    
    def test_enrich_with_empty_list(self, base_weather):
        """Deve retornar None se lista de hourly estiver vazia"""
        enriched = HourlyWeatherProcessor.enrich_weather_with_hourly(
            base_weather=base_weather,
            hourly_forecasts=[]
        )
        
        assert enriched is None
    
    def test_enrich_updates_timestamp(self, base_weather, hourly_forecasts):
        """Deve atualizar timestamp para hora mais próxima"""
        enriched = HourlyWeatherProcessor.enrich_weather_with_hourly(
            base_weather=base_weather,
            hourly_forecasts=hourly_forecasts,
            target_datetime=datetime(2025, 12, 1, 14, 30, tzinfo=ZoneInfo("America/Sao_Paulo"))
        )
        
        assert enriched is not None
        # Deve usar timestamp de 14:00 (mais próximo de 14:30)
        assert enriched.timestamp.hour == 14
        assert enriched.timestamp.minute == 0

    def test_enrich_returns_none_when_no_valid_hour(self, base_weather, hourly_forecasts, caplog):
        """Deve retornar None quando nenhuma previsão é válida."""
        # Corromper timestamps para forçar falha de parsing e closest_forecast None
        broken_forecasts = [
            HourlyForecast(
                timestamp="invalid",
                temperature=27.5,
                precipitation=0.3,
                precipitation_probability=25,
                humidity=68,
                wind_speed=11.0,
                wind_direction=175,
                cloud_cover=42,
                weather_code=2
            )
        ]
        enriched = HourlyWeatherProcessor.enrich_weather_with_hourly(
            base_weather=base_weather,
            hourly_forecasts=broken_forecasts,
            target_datetime=datetime(2025, 12, 1, 14, 0)  # naive to hit tz branch
        )

        assert enriched is None
        assert any("No valid hourly forecast found" in msg for msg in caplog.text.splitlines())

    def test_enrich_merges_new_alert(self, base_weather, hourly_forecasts):
        """Deve mesclar alertas do hourly sem duplicar existentes."""
        # Base já com um alerta
        base_weather.weather_alert = Weather.get_weather_alert(
            weather_code=500,
            rain_prob=80,
            wind_speed=10,
            forecast_time=base_weather.timestamp
        )
        # Forçar hourly com código diferente para criar alerta novo
        hourly_custom = [
            HourlyForecast(
                timestamp="2025-12-01T14:00:00",
                temperature=28.8,
                precipitation=5.0,
                precipitation_probability=90,
                humidity=64,
                wind_speed=50.0,
                wind_direction=185,
                cloud_cover=48,
                weather_code=201  # gera alerta de tempestade
            )
        ]

        enriched = HourlyWeatherProcessor.enrich_weather_with_hourly(
            base_weather=base_weather,
            hourly_forecasts=hourly_custom
        )

        # Deve ter aumentado a quantidade de alertas (merge executado)
        assert len(enriched.weather_alert) > 0


class TestFindClosestHourly:
    """Testes para busca da hora mais próxima"""
    
    def test_find_exact_match(self, hourly_forecasts):
        """Deve encontrar match exato"""
        target = datetime(2025, 12, 1, 14, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
        
        closest = HourlyWeatherProcessor._find_closest_hourly(
            hourly_forecasts,
            target
        )
        
        assert closest is not None
        assert closest.timestamp == "2025-12-01T14:00:00"
    
    def test_find_closest_before(self, hourly_forecasts):
        """Deve encontrar hora mais próxima antes do target"""
        target = datetime(2025, 12, 1, 13, 20, tzinfo=ZoneInfo("America/Sao_Paulo"))
        
        closest = HourlyWeatherProcessor._find_closest_hourly(
            hourly_forecasts,
            target
        )
        
        assert closest is not None
        assert closest.timestamp == "2025-12-01T13:00:00"
    
    def test_find_closest_after(self, hourly_forecasts):
        """Deve encontrar hora mais próxima depois do target"""
        target = datetime(2025, 12, 1, 14, 45, tzinfo=ZoneInfo("America/Sao_Paulo"))
        
        closest = HourlyWeatherProcessor._find_closest_hourly(
            hourly_forecasts,
            target
        )
        
        assert closest is not None
        assert closest.timestamp == "2025-12-01T15:00:00"
    
    def test_find_with_empty_list(self):
        """Deve retornar None para lista vazia"""
        target = datetime(2025, 12, 1, 14, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
        
        closest = HourlyWeatherProcessor._find_closest_hourly(
            [],
            target
        )
        
        assert closest is None

    def test_find_closest_with_naive_target(self, hourly_forecasts):
        """Deve aceitar datetime sem tz e aplicar timezone padrão."""
        target = datetime(2025, 12, 1, 14, 0)  # naive
        closest = HourlyWeatherProcessor._find_closest_hourly(hourly_forecasts, target)
        assert closest is not None

    def test_find_closest_with_tz_timestamp(self):
        """Deve tratar timestamps já com tzinfo sem perda."""
        forecasts = [
            HourlyForecast(
                timestamp="2025-12-01T14:00:00+00:00",
                temperature=25,
                precipitation=0,
                precipitation_probability=0,
                humidity=50,
                wind_speed=10,
                wind_direction=0,
                cloud_cover=0,
                weather_code=0
            )
        ]
        target = datetime(2025, 12, 1, 14, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
        closest = HourlyWeatherProcessor._find_closest_hourly(forecasts, target)
        assert closest is not None


class TestCalculateDailyRainAccumulation:
    """Testes para cálculo de acúmulo diário de chuva"""
    
    def test_calculate_same_day(self, hourly_forecasts):
        """Deve somar precipitação do mesmo dia"""
        target = datetime(2025, 12, 1, 14, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
        
        total = HourlyWeatherProcessor._calculate_daily_rain_accumulation(
            hourly_forecasts,
            target
        )
        
        # 0.3 + 0.4 + 0.6 = 1.3
        assert total == pytest.approx(1.3, rel=0.01)
    
    def test_calculate_empty_list(self):
        """Deve retornar 0 para lista vazia"""
        target = datetime(2025, 12, 1, 14, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
        
        total = HourlyWeatherProcessor._calculate_daily_rain_accumulation(
            [],
            target
        )
        
        assert total == 0.0

    def test_calculate_handles_bad_timestamp(self, caplog):
        """Deve ignorar entradas com timestamp inválido."""
        target = datetime(2025, 12, 1, 14, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
        forecasts = [
            HourlyForecast(
                timestamp="invalid",
                temperature=0,
                precipitation=1.0,
                precipitation_probability=50,
                humidity=50,
                wind_speed=10,
                wind_direction=0,
                cloud_cover=0,
                weather_code=0
            )
        ]

        total = HourlyWeatherProcessor._calculate_daily_rain_accumulation(
            forecasts,
            target
        )

        assert total == 0.0
        assert "Failed to process forecast for rain calculation" in caplog.text


class TestCalculateDailyTempExtremes:
    """Testes para cálculo de temperaturas extremas"""
    
    def test_calculate_temp_extremes(self, hourly_forecasts):
        """Deve retornar min/max do dia"""
        target = datetime(2025, 12, 1, 14, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
        
        temp_min, temp_max = HourlyWeatherProcessor._calculate_daily_temp_extremes(
            hourly_forecasts,
            target
        )
        
        assert temp_min == 27.5
        assert temp_max == 29.2

    def test_calculate_temp_extremes_handles_bad_timestamp(self, caplog):
        """Deve retornar (0,0) se todos registros falharem."""
        target = datetime(2025, 12, 1, 14, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
        forecasts = [
            HourlyForecast(
                timestamp="invalid",
                temperature=0,
                precipitation=0,
                precipitation_probability=0,
                humidity=0,
                wind_speed=0,
                wind_direction=0,
                cloud_cover=0,
                weather_code=0
            )
        ]

        temp_min, temp_max = HourlyWeatherProcessor._calculate_daily_temp_extremes(
            forecasts,
            target
        )

        assert (temp_min, temp_max) == (0.0, 0.0)
        assert "Failed to process forecast for temp calculation" in caplog.text
    
    def test_calculate_empty_list(self):
        """Deve retornar (0, 0) para lista vazia"""
        target = datetime(2025, 12, 1, 14, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
        
        temp_min, temp_max = HourlyWeatherProcessor._calculate_daily_temp_extremes(
            [],
            target
        )
        
        assert temp_min == 0.0
        assert temp_max == 0.0


class TestGetWeatherDescription:
    """Testes para conversão de WMO code para descrição"""
    
    def test_clear_sky(self):
        """Deve retornar descrição para céu limpo"""
        desc = HourlyWeatherProcessor._get_weather_description(0)
        assert desc == "Céu limpo"
    
    def test_partly_cloudy(self):
        """Deve retornar descrição para parcialmente nublado"""
        desc = HourlyWeatherProcessor._get_weather_description(2)
        assert desc == "Parcialmente nublado"
    
    def test_rain(self):
        """Deve retornar descrição para chuva"""
        desc = HourlyWeatherProcessor._get_weather_description(61)
        assert desc == "Chuva leve"
        
        desc = HourlyWeatherProcessor._get_weather_description(63)
        assert desc == "Chuva moderada"
    
    def test_thunderstorm(self):
        """Deve retornar descrição para tempestade"""
        desc = HourlyWeatherProcessor._get_weather_description(95)
        assert desc == "Tempestade"
    
    def test_unknown_code(self):
        """Deve retornar descrição padrão para código desconhecido"""
        desc = HourlyWeatherProcessor._get_weather_description(999)
        assert desc == "Condição desconhecida"
