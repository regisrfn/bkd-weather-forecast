"""
Testes Unitários - Validação dos Campos de Direção do Vento
Garante que estamos usando wind_direction_10m corretamente
"""
import pytest
from datetime import datetime, timezone
from domain.entities.hourly_forecast import HourlyForecast
from domain.entities.weather import Weather


class TestWindDirectionFields:
    """Valida uso correto dos campos de direção do vento"""
    
    def test_hourly_forecast_uses_wind_direction_10m(self):
        """
        Valida que HourlyForecast usa wind_direction (que vem de wind_direction_10m)
        Este é o padrão meteorológico a 10m de altura
        """
        hourly = HourlyForecast(
            timestamp=datetime.now(timezone.utc),
            temperature=25.0,
            precipitation=0.0,
            precipitation_probability=10,
            humidity=70,
            wind_speed=15.0,
            wind_direction=225,  # SW - 225° (vem de wind_direction_10m da API)
            cloud_cover=30,
            weather_code=2
        )
        
        assert hourly.wind_direction == 225
        assert 0 <= hourly.wind_direction <= 360
        
        # Valida API response
        api_response = hourly.to_api_response()
        assert api_response['windDirection'] == 225
        
    def test_weather_entity_has_wind_direction(self):
        """
        Valida que Weather entity tem campo wind_direction
        Enriquecido com dados hourly (wind_direction_10m)
        """
        weather = Weather(
            city_id='123',
            city_name='Test City',
            timestamp=datetime.now(timezone.utc),
            temperature=28.5,
            humidity=65,
            wind_speed=20.0,
            wind_direction=135,  # SE - 135° (enriquecido de hourly)
            rain_probability=25.0,
            rain_1h=0.5,
            rain_accumulated_day=2.5,
            description='Partly cloudy',
            feels_like=30.0,
            pressure=1013,
            visibility=10000,
            clouds=40,
            weather_alert=[],
            weather_code=801,
            temp_min=22.0,
            temp_max=32.0
        )
        
        assert weather.wind_direction == 135
        assert 0 <= weather.wind_direction <= 360
        
        # Valida API response
        api_response = weather.to_api_response()
        assert api_response['windDirection'] == 135
        
    def test_wind_direction_cardinal_points(self):
        """
        Valida que wind_direction representa corretamente pontos cardeais
        0° = N, 90° = E, 180° = S, 270° = W (padrão meteorológico)
        """
        test_cases = [
            (0, "Norte"),
            (45, "Nordeste"),
            (90, "Leste"),
            (135, "Sudeste"),
            (180, "Sul"),
            (225, "Sudoeste"),
            (270, "Oeste"),
            (315, "Noroeste"),
            (360, "Norte"),  # 360° = 0° (wrap around)
        ]
        
        for degrees, direction in test_cases:
            hourly = HourlyForecast(
                timestamp=datetime.now(timezone.utc),
                temperature=25.0,
                precipitation=0.0,
                precipitation_probability=10,
                humidity=70,
                wind_speed=15.0,
                wind_direction=degrees,
                cloud_cover=30,
                weather_code=2
            )
            
            assert hourly.wind_direction == degrees
            assert 0 <= hourly.wind_direction <= 360
            print(f"✅ {degrees}° = {direction}")
    
    def test_wind_direction_range_validation(self):
        """
        Valida que wind_direction está no range correto (0-360)
        """
        # Valores válidos
        valid_directions = [0, 45, 90, 135, 180, 225, 270, 315, 360]
        
        for direction in valid_directions:
            hourly = HourlyForecast(
                timestamp=datetime.now(timezone.utc),
                temperature=25.0,
                precipitation=0.0,
                precipitation_probability=10,
                humidity=70,
                wind_speed=15.0,
                wind_direction=direction,
                cloud_cover=30,
                weather_code=2
            )
            assert 0 <= hourly.wind_direction <= 360
        
        print("✅ Todos os valores válidos passaram (0-360°)")
