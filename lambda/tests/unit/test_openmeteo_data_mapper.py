"""Testes unitários para OpenMeteoDataMapper"""
import pytest
from unittest.mock import patch
from infrastructure.adapters.output.providers.openmeteo.mappers.openmeteo_data_mapper import (
    OpenMeteoDataMapper
)
from domain.entities.hourly_forecast import HourlyForecast


class TestOpenMeteoDataMapper:
    """Testes para OpenMeteoDataMapper"""
    
    def test_map_daily_response_with_missing_temperatures(self):
        """Testa que dias com temperaturas ausentes são pulados"""
        data = {
            'daily': {
                'time': ['2024-01-01', '2024-01-02', '2024-01-03'],
                'temperature_2m_max': [25.0, None, 28.0],  # Segundo dia sem temp
                'temperature_2m_min': [15.0, 10.0, 16.0]
            }
        }
        
        with patch('infrastructure.adapters.output.providers.openmeteo.mappers.openmeteo_data_mapper.logger'):
            result = OpenMeteoDataMapper.map_daily_response_to_forecasts(data)
        
        # Deve retornar apenas 2 dias (pula o que não tem temp_max)
        assert len(result) == 2
        assert result[0].date == '2024-01-01'
        assert result[1].date == '2024-01-03'
    
    def test_map_daily_response_with_exception(self):
        """Testa que exceções em dias específicos não param o processamento"""
        data = {
            'daily': {
                'time': ['2024-01-01', '2024-01-02', '2024-01-03'],
                'temperature_2m_max': [25.0, 30.0, 28.0],
                'temperature_2m_min': [15.0, 20.0, 16.0],
                'wind_direction_10m_dominant': [180, 'invalid', 90]  # Valor inválido no meio
            }
        }
        
        with patch('infrastructure.adapters.output.providers.openmeteo.mappers.openmeteo_data_mapper.logger'):
            # Deve processar os dias válidos
            result = OpenMeteoDataMapper.map_daily_response_to_forecasts(data)
        
        # Pode retornar 2 ou 3 dependendo de como lida com conversão
        assert len(result) >= 2
    
    def test_map_daily_response_with_all_fields(self):
        """Testa mapeamento com todos os campos opcionais presentes"""
        data = {
            'daily': {
                'time': ['2024-01-01'],
                'temperature_2m_max': [25.0],
                'temperature_2m_min': [15.0],
                'precipitation_sum': [10.5],
                'precipitation_probability_mean': [80.0],
                'wind_speed_10m_max': [25.0],
                'wind_direction_10m_dominant': [180],
                'uv_index_max': [7.5],
                'sunrise': ['06:30'],
                'sunset': ['18:45'],
                'precipitation_hours': [4.5]
            }
        }
        
        result = OpenMeteoDataMapper.map_daily_response_to_forecasts(data)
        
        assert len(result) == 1
        forecast = result[0]
        assert forecast.temp_max == 25.0
        assert forecast.temp_min == 15.0
        assert forecast.precipitation_mm == 10.5
        assert forecast.rain_probability == 80.0
        assert forecast.wind_speed_max == 25.0
        assert forecast.wind_direction == 180
        assert forecast.uv_index == 7.5
    
    def test_map_daily_response_with_missing_optional_fields(self):
        """Testa mapeamento com campos opcionais ausentes (usa defaults)"""
        data = {
            'daily': {
                'time': ['2024-01-01'],
                'temperature_2m_max': [25.0],
                'temperature_2m_min': [15.0]
                # Todos os outros campos ausentes
            }
        }
        
        result = OpenMeteoDataMapper.map_daily_response_to_forecasts(data)
        
        assert len(result) == 1
        forecast = result[0]
        assert forecast.temp_max == 25.0
        assert forecast.temp_min == 15.0
        # Campos opcionais devem ter defaults
        assert forecast.precipitation_mm == 0.0
        assert forecast.rain_probability == 0.0
        assert forecast.wind_speed_max == 0.0
    
    def test_map_hourly_response_respects_max_hours(self):
        """Testa que max_hours limita corretamente o número de resultados"""
        data = {
            'hourly': {
                'time': [f'2024-01-01T{h:02d}:00' for h in range(24)],
                'temperature_2m': [20 + h for h in range(24)],
                'precipitation': [0.0] * 24,
                'precipitation_probability': [50] * 24,
                'relative_humidity_2m': [70] * 24,
                'wind_speed_10m': [10.0] * 24,
                'wind_direction_10m': [180] * 24,
                'cloud_cover': [50] * 24,
                'weather_code': [1] * 24
            }
        }
        
        result = OpenMeteoDataMapper.map_hourly_response_to_forecasts(data, max_hours=5)
        
        assert len(result) == 5  # Deve retornar apenas 5 horas
        assert result[0].timestamp == '2024-01-01T00:00'
        assert result[4].timestamp == '2024-01-01T04:00'
    
    def test_map_hourly_response_with_missing_fields(self):
        """Testa mapeamento horário com campos ausentes (usa defaults)"""
        data = {
            'hourly': {
                'time': ['2024-01-01T12:00'],
                'temperature_2m': [25.0]
                # Outros campos ausentes
            }
        }
        
        result = OpenMeteoDataMapper.map_hourly_response_to_forecasts(data, max_hours=24)
        
        assert len(result) == 1
        forecast = result[0]
        assert forecast.temperature == 25.0
        assert forecast.precipitation == 0.0
        assert forecast.precipitation_probability == 0
        assert forecast.humidity == 0
    
    def test_map_hourly_response_with_exception(self):
        """Testa que exceções em horas específicas não param o processamento"""
        data = {
            'hourly': {
                'time': ['2024-01-01T00:00', '2024-01-01T01:00', '2024-01-01T02:00'],
                'temperature_2m': [20.0, 21.0, 22.0],
                'weather_code': [1, 'invalid', 2]  # Valor inválido no meio
            }
        }
        
        with patch('infrastructure.adapters.output.providers.openmeteo.mappers.openmeteo_data_mapper.logger'):
            result = OpenMeteoDataMapper.map_hourly_response_to_forecasts(data, max_hours=10)
        
        # Pode retornar 2 ou 3 dependendo de como lida com conversão
        assert len(result) >= 2
    
    def test_map_hourly_to_weather(self):
        """Testa conversão de HourlyForecast para Weather"""
        hourly = HourlyForecast(
            timestamp='2024-01-01T12:00:00',
            temperature=25.0,
            precipitation=2.5,
            precipitation_probability=80,
            rainfall_intensity=6.67,  # (2.5 * 80/100) / 30 * 100
            humidity=70,
            wind_speed=15.0,
            wind_direction=180,
            cloud_cover=60,
            weather_code=61,
            description='chuva fraca'
        )
        
        result = OpenMeteoDataMapper.map_hourly_to_weather(
            hourly_forecast=hourly,
            city_id='123',
            city_name='São Paulo'
        )
        
        assert result.city_id == '123'
        assert result.city_name == 'São Paulo'
        assert result.temperature == 25.0
        assert result.humidity == 70.0
        assert result.wind_speed == 15.0
        assert result.wind_direction == 180
        assert result.rain_probability == 80.0
        assert result.rain_1h == 2.5
        assert result.description == 'chuva fraca'
        assert result.clouds == 60.0
        assert result.weather_code == 61
        # Campos não fornecidos pelo OpenMeteo
        assert result.feels_like == 0.0
        assert result.pressure == 0.0
        assert result.visibility == 10000.0
    
    def test_get_wmo_description_known_code(self):
        """Testa descrição para código WMO conhecido"""
        # Código 0 = Céu limpo (com C maiúsculo)
        result = OpenMeteoDataMapper.get_wmo_description(0)
        assert result == 'Céu limpo'
    
    def test_get_wmo_description_unknown_code(self):
        """Testa descrição para código WMO desconhecido"""
        result = OpenMeteoDataMapper.get_wmo_description(9999)
        assert result == 'Condição desconhecida'
    
    def test_map_daily_with_none_wind_direction(self):
        """Testa que wind_direction=None é tratado corretamente"""
        data = {
            'daily': {
                'time': ['2024-01-01'],
                'temperature_2m_max': [25.0],
                'temperature_2m_min': [15.0],
                'wind_direction_10m_dominant': [None]  # Explicitamente None
            }
        }
        
        result = OpenMeteoDataMapper.map_daily_response_to_forecasts(data)
        
        assert len(result) == 1
        assert result[0].wind_direction == 0  # Fallback para 0
    
    def test_map_hourly_empty_data(self):
        """Testa mapeamento com dados vazios"""
        data = {'hourly': {}}
        
        result = OpenMeteoDataMapper.map_hourly_response_to_forecasts(data, max_hours=10)
        
        assert result == []
    
    def test_map_daily_empty_data(self):
        """Testa mapeamento com dados vazios"""
        data = {'daily': {}}
        
        result = OpenMeteoDataMapper.map_daily_response_to_forecasts(data)
        
        assert result == []
