"""
Testes para OpenWeatherDataMapper._parse_forecast_item
Cobre parsing de items individuais do forecast
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from infrastructure.adapters.output.providers.openweather.mappers.openweather_data_mapper import OpenWeatherDataMapper


class TestOpenWeatherParseItem:
    """Testa parsing de item individual do forecast"""

    def test_parse_forecast_item_basic(self):
        """Deve parsear item básico corretamente"""
        forecast_raw = {
            'dt': 1701529200,  # 2023-12-02 15:00:00 UTC
            'main': {
                'temp': 25.5,
                'temp_min': 24.0,
                'temp_max': 27.0,
                'humidity': 65,
                'feels_like': 26.0
            },
            'weather': [{
                'main': 'Clear',
                'description': 'céu limpo',
                'id': 800
            }],
            'wind': {
                'speed': 3.5,
                'deg': 180
            },
            'clouds': {
                'all': 10
            },
            'visibility': 10000,
            'pop': 0.0
        }
        
        result = OpenWeatherDataMapper._parse_forecast_item(
            forecast_raw=forecast_raw,
            city_id="123",
            city_name="Test City",
            temp_min_day=22.0,
            temp_max_day=30.0,
            rain_accumulated_day=0.0
        )
        
        assert result.temperature == 25.5
        assert result.city_id == "123"
        assert result.city_name == "Test City"
        assert result.wind_speed == 12.6  # 3.5 m/s * 3.6 = 12.6 km/h
        assert result.humidity == 65
        assert result.clouds == 10

    def test_parse_forecast_item_with_rain(self):
        """Deve parsear item com chuva"""
        forecast_raw = {
            'dt': 1701529200,
            'main': {
                'temp': 22.0,
                'temp_min': 21.0,
                'temp_max': 23.0,
                'humidity': 85,
                'feels_like': 23.0
            },
            'weather': [{
                'main': 'Rain',
                'description': 'chuva moderada',
                'id': 501
            }],
            'wind': {
                'speed': 5.0,
                'deg': 90
            },
            'clouds': {
                'all': 90
            },
            'visibility': 5000,
            'pop': 0.8,
            'rain': {
                '3h': 6.0
            }
        }
        
        result = OpenWeatherDataMapper._parse_forecast_item(
            forecast_raw=forecast_raw,
            city_id="456",
            city_name="Rainy City",
            temp_min_day=20.0,
            temp_max_day=24.0,
            rain_accumulated_day=10.0
        )
        
        assert result.description == "chuva moderada"
        assert result.visibility == 5000  # metros (não converte)
        assert result.rain_probability == 80.0  # 0.8 * 100

    def test_parse_forecast_item_with_snow(self):
        """Deve parsear item com neve"""
        forecast_raw = {
            'dt': 1701529200,
            'main': {
                'temp': -2.0,
                'temp_min': -5.0,
                'temp_max': 0.0,
                'humidity': 90,
                'feels_like': -5.0
            },
            'weather': [{
                'main': 'Snow',
                'description': 'neve',
                'id': 600
            }],
            'wind': {
                'speed': 8.0,
                'deg': 0
            },
            'clouds': {
                'all': 100
            },
            'visibility': 2000,
            'pop': 1.0,
            'snow': {
                '3h': 5.0
            }
        }
        
        result = OpenWeatherDataMapper._parse_forecast_item(
            forecast_raw=forecast_raw,
            city_id="789",
            city_name="Snowy City"
        )
        
        assert result.temperature == -2.0
        assert result.description == "neve"
        assert result.wind_speed == 28.8  # 8.0 * 3.6

    def test_parse_forecast_item_missing_optional_fields(self):
        """Deve lidar com campos opcionais ausentes"""
        forecast_raw = {
            'dt': 1701529200,
            'main': {
                'temp': 25.0,
                'humidity': 60,
                'feels_like': 25.0
            },
            'weather': [{
                'main': 'Clear',
                'description': 'limpo'
            }],
            'wind': {
                'speed': 2.0
            }
            # Sem clouds, visibility, pop, rain
        }
        
        result = OpenWeatherDataMapper._parse_forecast_item(
            forecast_raw=forecast_raw,
            city_id="999",
            city_name="Minimal City"
        )
        
        assert result.temperature == 25.0
        assert result.city_id == "999"
        # Deve ter valores padrão para campos ausentes
        assert result.rain_probability >= 0

    def test_parse_forecast_item_wind_conversion(self):
        """Deve converter vento de m/s para km/h corretamente"""
        forecast_raw = {
            'dt': 1701529200,
            'main': {
                'temp': 20.0,
                'humidity': 50,
                'feels_like': 20.0
            },
            'weather': [{'main': 'Clear', 'description': 'limpo'}],
            'wind': {
                'speed': 10.0,  # m/s
                'deg': 270
            }
        }
        
        result = OpenWeatherDataMapper._parse_forecast_item(
            forecast_raw=forecast_raw,
            city_id="111",
            city_name="Windy"
        )
        
        assert result.wind_speed == 36.0  # 10 * 3.6 = 36 km/h

    def test_parse_forecast_item_visibility_conversion(self):
        """Deve converter visibilidade de metros para km"""
        forecast_raw = {
            'dt': 1701529200,
            'main': {
                'temp': 20.0,
                'humidity': 80,
                'feels_like': 20.0
            },
            'weather': [{'main': 'Mist', 'description': 'neblina'}],
            'wind': {'speed': 2.0},
            'visibility': 3500  # metros
        }
        
        result = OpenWeatherDataMapper._parse_forecast_item(
            forecast_raw=forecast_raw,
            city_id="222",
            city_name="Foggy"
        )
        
        assert result.visibility == 3500  # metros (não converte para km)

    def test_parse_forecast_item_high_pop(self):
        """Deve parsear probabilidade de precipitação alta"""
        forecast_raw = {
            'dt': 1701529200,
            'main': {
                'temp': 18.0,
                'humidity': 95,
                'feels_like': 18.0
            },
            'weather': [{'main': 'Rain', 'description': 'chuva'}],
            'wind': {'speed': 4.0},
            'pop': 0.98  # 98%
        }
        
        result = OpenWeatherDataMapper._parse_forecast_item(
            forecast_raw=forecast_raw,
            city_id="333",
            city_name="Rainy"
        )
        
        assert result.rain_probability == 98.0

    def test_parse_forecast_item_preserves_timestamp(self):
        """Deve manter o timestamp original"""
        dt_unix = 1701529200
        forecast_raw = {
            'dt': dt_unix,
            'main': {'temp': 25.0, 'humidity': 60, 'feels_like': 25.0},
            'weather': [{'main': 'Clear', 'description': 'limpo'}],
            'wind': {'speed': 2.0}
        }
        
        result = OpenWeatherDataMapper._parse_forecast_item(
            forecast_raw=forecast_raw,
            city_id="444",
            city_name="Test"
        )
        
        # Verificar que o timestamp foi convertido corretamente
        assert result.timestamp is not None
        assert isinstance(result.timestamp, datetime)

    def test_parse_forecast_item_uses_temp_min_max_from_params(self):
        """Deve usar temp_min/max passados como parâmetro"""
        forecast_raw = {
            'dt': 1701529200,
            'main': {
                'temp': 25.0,
                'temp_min': 24.0,  # Será ignorado
                'temp_max': 26.0,  # Será ignorado
                'humidity': 60,
                'feels_like': 25.0
            },
            'weather': [{'main': 'Clear', 'description': 'limpo'}],
            'wind': {'speed': 2.0}
        }
        
        result = OpenWeatherDataMapper._parse_forecast_item(
            forecast_raw=forecast_raw,
            city_id="555",
            city_name="Test",
            temp_min_day=20.0,  # Valores externos
            temp_max_day=30.0
        )
        
        # Deve usar os valores passados como parâmetro, não os do forecast
        assert result.temperature == 25.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
