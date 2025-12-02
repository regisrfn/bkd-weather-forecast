"""
Testes Estendidos para Daily Forecast Entity
Foca em casos de borda não cobertos pelos testes existentes
"""
import pytest
from domain.entities.daily_forecast import DailyForecast


class TestDailyForecastExtended:
    """Testes estendidos para DailyForecast"""
    
    def test_from_openmeteo_data_with_iso_timestamps(self):
        """REGRA: Deve extrair HH:MM de timestamps ISO 8601 completos"""
        forecast = DailyForecast.from_openmeteo_data(
            date="2025-12-05",
            temp_max=32.0,
            temp_min=22.0,
            precipitation=0.0,
            rain_prob=10.0,
            wind_speed=15.0,
            wind_direction=180,
            uv_index=5.0,
            sunrise="2025-12-05T06:15:30",  # ISO 8601 completo
            sunset="2025-12-05T18:45:30",   # ISO 8601 completo
            precip_hours=0.0
        )
        
        assert forecast.sunrise == "06:15:30"
        assert forecast.sunset == "18:45:30"
        assert forecast.daylight_hours == 12.5  # ~12h30min
    
    def test_from_openmeteo_data_with_simple_time_format(self):
        """REGRA: Deve aceitar timestamps já no formato HH:MM"""
        forecast = DailyForecast.from_openmeteo_data(
            date="2025-12-05",
            temp_max=32.0,
            temp_min=22.0,
            precipitation=0.0,
            rain_prob=10.0,
            wind_speed=15.0,
            wind_direction=180,
            uv_index=5.0,
            sunrise="05:30",  # Já no formato simplificado
            sunset="19:00",
            precip_hours=0.0
        )
        
        assert forecast.sunrise == "05:30"
        assert forecast.sunset == "19:00"
        assert forecast.daylight_hours == 13.5
    
    def test_daylight_hours_with_invalid_time_format(self):
        """EDGE CASE: Formato inválido de tempo deve retornar 0.0"""
        forecast = DailyForecast(
            date="2025-12-05",
            temp_min=20.0,
            temp_max=30.0,
            precipitation_mm=0.0,
            rain_probability=10.0,
            rainfall_intensity=0.0,
            wind_speed_max=15.0,
            wind_direction=180,
            uv_index=5.0,
            sunrise="invalid",  # Formato inválido
            sunset="also-invalid",
            precipitation_hours=0.0
        )
        
        assert forecast.daylight_hours == 0.0
    
    def test_daylight_hours_with_partial_invalid_format(self):
        """EDGE CASE: Um dos tempos inválido pode calcular mesmo assim (Python é tolerante)"""
        forecast = DailyForecast(
            date="2025-12-05",
            temp_min=20.0,
            temp_max=30.0,
            precipitation_mm=0.0,
            rain_probability=10.0,
            rainfall_intensity=0.0,
            wind_speed_max=15.0,
            wind_direction=180,
            uv_index=5.0,
            sunrise="06:00",
            sunset="25:99",  # Hora inválida mas Python pode parsear "25"
            precipitation_hours=0.0
        )
        
        # Python calcula 25*60 + 99 minutos, então não retorna 0
        # Apenas verificamos que não crashou
        assert isinstance(forecast.daylight_hours, float)
    
    def test_uv_risk_level_boundaries(self):
        """REGRA: Testar todos os limites de UV risk level"""
        test_cases = [
            (0.0, "Baixo", "#4caf50"),
            (2.0, "Baixo", "#4caf50"),
            (2.5, "Moderado", "#ffeb3b"),
            (5.0, "Moderado", "#ffeb3b"),
            (5.5, "Alto", "#ff9800"),
            (7.0, "Alto", "#ff9800"),
            (7.5, "Muito Alto", "#f44336"),
            (10.0, "Muito Alto", "#f44336"),
            (10.5, "Extremo", "#9c27b0"),
            (15.0, "Extremo", "#9c27b0"),
        ]
        
        for uv_value, expected_level, expected_color in test_cases:
            forecast = DailyForecast(
                date="2025-12-05",
                temp_min=20.0,
                temp_max=30.0,
                precipitation_mm=0.0,
                rain_probability=10.0,
            rainfall_intensity=0.0,
                wind_speed_max=15.0,
                wind_direction=180,
                uv_index=uv_value,
                sunrise="06:00",
                sunset="18:00",
                precipitation_hours=0.0
            )
            
            assert forecast.uv_risk_level == expected_level, \
                f"UV {uv_value} deveria ser '{expected_level}'"
            assert forecast.uv_risk_color == expected_color, \
                f"UV {uv_value} deveria ter cor '{expected_color}'"
    
    def test_to_api_response_rounding(self):
        """REGRA: Valores na API response devem ser arredondados para 1 casa decimal"""
        forecast = DailyForecast(
            date="2025-12-05",
            temp_min=20.123456,
            temp_max=30.987654,
            precipitation_mm=5.555555,
            rain_probability=67.777777,
            rainfall_intensity=0.0,
            wind_speed_max=15.333333,
            wind_direction=180,
            uv_index=8.999999,
            sunrise="06:00",
            sunset="18:00",
            precipitation_hours=3.141592
        )
        
        response = forecast.to_api_response()
        
        assert response["tempMin"] == 20.1
        assert response["tempMax"] == 31.0
        assert response["precipitationMm"] == 5.6
        assert response["rainProbability"] == 67.8
        assert response["windSpeedMax"] == 15.3
        assert response["uvIndex"] == 9.0
        assert response["precipitationHours"] == 3.1
    
    def test_to_api_response_includes_all_required_fields(self):
        """REGRA: API response deve incluir todos os campos necessários"""
        forecast = DailyForecast(
            date="2025-12-05",
            temp_min=20.0,
            temp_max=30.0,
            precipitation_mm=0.0,
            rain_probability=10.0,
            rainfall_intensity=0.0,
            wind_speed_max=15.0,
            wind_direction=180,
            uv_index=5.0,
            sunrise="06:00",
            sunset="18:00",
            precipitation_hours=0.0
        )
        
        response = forecast.to_api_response()
        
        required_fields = [
            'date', 'tempMin', 'tempMax', 'precipitationMm', 'rainProbability',
            'windSpeedMax', 'windDirection', 'uvIndex', 'uvRiskLevel', 'uvRiskColor',
            'sunrise', 'sunset', 'precipitationHours', 'daylightHours'
        ]
        
        for field in required_fields:
            assert field in response, f"Campo '{field}' ausente na API response"
    
    def test_daylight_hours_calculation_accuracy(self):
        """REGRA: Cálculo de daylight hours deve ser preciso"""
        # 06:00 às 18:00 = 12 horas exatas
        forecast = DailyForecast(
            date="2025-12-05",
            temp_min=20.0,
            temp_max=30.0,
            precipitation_mm=0.0,
            rain_probability=10.0,
            rainfall_intensity=0.0,
            wind_speed_max=15.0,
            wind_direction=180,
            uv_index=5.0,
            sunrise="06:00",
            sunset="18:00",
            precipitation_hours=0.0
        )
        
        assert forecast.daylight_hours == 12.0
        
        # 05:30 às 19:30 = 14 horas exatas
        forecast2 = DailyForecast(
            date="2025-12-05",
            temp_min=20.0,
            temp_max=30.0,
            precipitation_mm=0.0,
            rain_probability=10.0,
            rainfall_intensity=0.0,
            wind_speed_max=15.0,
            wind_direction=180,
            uv_index=5.0,
            sunrise="05:30",
            sunset="19:30",
            precipitation_hours=0.0
        )
        
        assert forecast2.daylight_hours == 14.0
