"""
Configurações e fixtures compartilhadas para testes unitários
"""
import pytest
from domain.entities.hourly_forecast import HourlyForecast
from domain.helpers.rainfall_calculator import calculate_rainfall_intensity


@pytest.fixture
def make_hourly_forecast():
    """
    Factory fixture para criar HourlyForecast com valores padrão
    
    Usage:
        def test_something(make_hourly_forecast):
            forecast = make_hourly_forecast(timestamp='2024-01-01T12:00:00')
    """
    def _make(
        timestamp: str = '2024-01-01T12:00:00',
        temperature: float = 25.0,
        precipitation: float = 0.0,
        precipitation_probability: int = 0,
        humidity: int = 60,
        wind_speed: float = 10.0,
        wind_direction: int = 180,
        cloud_cover: int = 50,
        weather_code: int = 0,
        description: str = 'céu limpo'
    ) -> HourlyForecast:
        rainfall_intensity = calculate_rainfall_intensity(precipitation_probability, precipitation)
        
        return HourlyForecast(
            timestamp=timestamp,
            temperature=temperature,
            precipitation=precipitation,
            precipitation_probability=precipitation_probability,
            rainfall_intensity=rainfall_intensity,
            humidity=humidity,
            wind_speed=wind_speed,
            wind_direction=wind_direction,
            cloud_cover=cloud_cover,
            weather_code=weather_code,
            description=description
        )
    
    return _make
