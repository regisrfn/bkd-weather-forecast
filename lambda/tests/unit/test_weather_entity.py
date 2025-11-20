"""
Testes Unitários - Domain Entities (Weather)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambda'))

import pytest
from datetime import datetime
from domain.entities.weather import Weather


def test_weather_creation():
    """Testa criação de entidade Weather"""
    weather = Weather(
        city_id="3543204",
        city_name="Ribeirão Preto",
        timestamp=datetime(2025, 11, 20, 15, 0),
        temperature=28.5,
        humidity=65,
        wind_speed=15.2,
        rain_probability=45.0,
        rain_1h=2.5
    )
    
    assert weather.city_id == "3543204"
    assert weather.city_name == "Ribeirão Preto"
    assert weather.temperature == 28.5
    assert weather.humidity == 65
    assert weather.wind_speed == 15.2
    assert weather.rain_probability == 45.0
    assert weather.rain_1h == 2.5


def test_weather_to_api_response():
    """Testa conversão de Weather para formato API"""
    weather = Weather(
        city_id="3543204",
        city_name="Ribeirão Preto",
        timestamp=datetime(2025, 11, 20, 15, 0),
        temperature=28.5,
        humidity=65,
        wind_speed=15.2,
        rain_probability=45.0,
        rain_1h=2.5
    )
    
    api_response = weather.to_api_response()
    
    assert api_response['cityId'] == "3543204"
    assert api_response['cityName'] == "Ribeirão Preto"
    assert api_response['temperature'] == 28.5
    assert api_response['humidity'] == 65
    assert api_response['windSpeed'] == 15.2
    assert api_response['rainfallIntensity'] == 45.0
    assert 'timestamp' in api_response


def test_weather_optional_rain():
    """Testa Weather com valores opcionais de chuva"""
    weather = Weather(
        city_id="3543204",
        city_name="Ribeirão Preto",
        timestamp=datetime(2025, 11, 20, 15, 0),
        temperature=28.5,
        humidity=65,
        wind_speed=15.2,
        rain_probability=0.0,
        rain_1h=0.0
    )
    
    assert weather.rain_probability == 0.0
    assert weather.rain_1h == 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
