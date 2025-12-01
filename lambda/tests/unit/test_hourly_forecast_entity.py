"""
Testes Unitários - HourlyForecast Entity
Testa a entidade de previsão horária
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import pytest
from domain.entities.hourly_forecast import HourlyForecast


class TestHourlyForecastEntity:
    """Testes para entidade HourlyForecast"""
    
    def test_create_hourly_forecast(self):
        """Deve criar HourlyForecast com todos os campos"""
        forecast = HourlyForecast(
            timestamp="2025-12-01T14:00:00",
            temperature=28.5,
            precipitation=0.5,
            precipitation_probability=30,
            humidity=65,
            wind_speed=12.5,
            wind_direction=180,
            cloud_cover=45,
            weather_code=2
        )
        
        assert forecast.timestamp == "2025-12-01T14:00:00"
        assert forecast.temperature == 28.5
        assert forecast.precipitation == 0.5
        assert forecast.precipitation_probability == 30
        assert forecast.humidity == 65
        assert forecast.wind_speed == 12.5
        assert forecast.wind_direction == 180
        assert forecast.cloud_cover == 45
        assert forecast.weather_code == 2
    
    def test_to_api_response(self):
        """Deve converter para formato de API corretamente"""
        forecast = HourlyForecast(
            timestamp="2025-12-01T14:00:00",
            temperature=28.567,
            precipitation=0.543,
            precipitation_probability=32,
            humidity=65,
            wind_speed=12.567,
            wind_direction=185,
            cloud_cover=48,
            weather_code=2,
            description="Parcialmente nublado"
        )
        
        api_response = forecast.to_api_response()
        
        # Verificar estrutura
        assert 'timestamp' in api_response
        assert 'temperature' in api_response
        assert 'precipitation' in api_response
        assert 'precipitationProbability' in api_response
        assert 'humidity' in api_response
        assert 'windSpeed' in api_response
        assert 'windDirection' in api_response
        assert 'cloudCover' in api_response
        assert 'weatherCode' in api_response
        assert 'description' in api_response
        
        # Verificar valores arredondados
        assert api_response['temperature'] == 28.6
        assert api_response['precipitation'] == 0.5
        assert api_response['windSpeed'] == 12.6
        
        # Verificar inteiros preservados
        assert api_response['precipitationProbability'] == 32
        assert api_response['humidity'] == 65
        assert api_response['windDirection'] == 185
        assert api_response['cloudCover'] == 48
        assert api_response['weatherCode'] == 2
        
        # Verificar descrição
        assert api_response['description'] == "Parcialmente nublado"
    
    def test_wind_direction_range(self):
        """Deve aceitar direção do vento de 0-360 graus"""
        # Norte
        forecast_north = HourlyForecast(
            timestamp="2025-12-01T14:00:00",
            temperature=25.0,
            precipitation=0.0,
            precipitation_probability=0,
            humidity=60,
            wind_speed=10.0,
            wind_direction=0,
            cloud_cover=20,
            weather_code=1
        )
        assert forecast_north.wind_direction == 0
        
        # Sul
        forecast_south = HourlyForecast(
            timestamp="2025-12-01T14:00:00",
            temperature=25.0,
            precipitation=0.0,
            precipitation_probability=0,
            humidity=60,
            wind_speed=10.0,
            wind_direction=180,
            cloud_cover=20,
            weather_code=1
        )
        assert forecast_south.wind_direction == 180
        
        # Oeste (360°)
        forecast_west = HourlyForecast(
            timestamp="2025-12-01T14:00:00",
            temperature=25.0,
            precipitation=0.0,
            precipitation_probability=0,
            humidity=60,
            wind_speed=10.0,
            wind_direction=360,
            cloud_cover=20,
            weather_code=1
        )
        assert forecast_west.wind_direction == 360
