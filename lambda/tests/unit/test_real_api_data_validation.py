"""
Testes com Dados Reais das APIs
Valida que os dados capturados estão corretos e consistentes
"""
import pytest
import json
from pathlib import Path
from datetime import datetime


@pytest.fixture
def real_api_data():
    """Carrega dados reais capturados das APIs"""
    fixtures_path = Path(__file__).parent.parent / "fixtures" / "real_api_data.json"
    with open(fixtures_path) as f:
        return json.load(f)


class TestOpenMeteoRealData:
    """Testes com dados reais do Open-Meteo"""
    
    def test_openmeteo_has_multiple_days(self, real_api_data):
        """REGRA: Open-Meteo deve retornar pelo menos 7 dias de previsão"""
        count = real_api_data["openmeteo_daily"]["count"]
        
        assert count >= 7, f"Poucos dias de previsão: {count} (esperado >= 7)"
    
    def test_openmeteo_daily_has_required_fields(self, real_api_data):
        """REGRA: Cada daily forecast deve ter campos obrigatórios"""
        forecasts = real_api_data["openmeteo_daily"]["forecasts"]
        
        required_fields = [
            "date", "tempMax", "tempMin", "uvIndex",
            "precipitationMm", "rainProbability",
            "windSpeedMax", "windDirection"
        ]
        
        for forecast in forecasts[:3]:  # Verificar primeiros 3
            for field in required_fields:
                assert field in forecast, f"Campo '{field}' ausente no daily forecast"
    
    def test_openmeteo_daily_temp_max_greater_than_min(self, real_api_data):
        """REGRA: Temperatura máxima deve ser maior ou igual à mínima"""
        forecasts = real_api_data["openmeteo_daily"]["forecasts"]
        
        for forecast in forecasts:
            temp_max = forecast["tempMax"]
            temp_min = forecast["tempMin"]
            
            assert temp_max >= temp_min, \
                f"temp_max ({temp_max}) < temp_min ({temp_min}) para {forecast['date']}"
    
    def test_openmeteo_daily_dates_are_sequential(self, real_api_data):
        """REGRA: Datas devem ser sequenciais (sem pulos)"""
        forecasts = real_api_data["openmeteo_daily"]["forecasts"]
        
        for i in range(len(forecasts) - 1):
            current = datetime.fromisoformat(forecasts[i]["date"]).date()
            next_date = datetime.fromisoformat(forecasts[i + 1]["date"]).date()
            
            diff_days = (next_date - current).days
            assert diff_days == 1, f"Datas não sequenciais: {current} -> {next_date}"
    
    def test_openmeteo_hourly_has_many_hours(self, real_api_data):
        """REGRA: Open-Meteo hourly deve ter muitas horas (>100)"""
        count = real_api_data["openmeteo_hourly"]["count"]
        
        assert count >= 100, f"Poucas horas de previsão: {count} (esperado >= 100)"
    
    def test_openmeteo_hourly_has_required_fields(self, real_api_data):
        """REGRA: Cada hourly forecast deve ter campos obrigatórios"""
        forecasts = real_api_data["openmeteo_hourly"]["forecasts"]
        
        required_fields = [
            "timestamp", "temperature", "humidity", "windSpeed",
            "windDirection", "precipitationProbability", "precipitation",
            "weatherCode"
        ]
        
        for forecast in forecasts[:3]:
            for field in required_fields:
                assert field in forecast, f"Campo '{field}' ausente no hourly forecast"
    
    def test_openmeteo_hourly_timestamps_are_sequential(self, real_api_data):
        """REGRA: Timestamps devem ser sequenciais (1 hora de diferença)"""
        forecasts = real_api_data["openmeteo_hourly"]["forecasts"]
        
        for i in range(len(forecasts) - 1):
            current = datetime.fromisoformat(forecasts[i]["timestamp"])
            next_ts = datetime.fromisoformat(forecasts[i + 1]["timestamp"])
            
            diff_hours = (next_ts - current).total_seconds() / 3600
            assert diff_hours == 1, f"Timestamps não sequenciais: {current} -> {next_ts}"


class TestDataQuality:
    """Testes de qualidade dos dados"""
    
    def test_no_null_values_in_critical_fields(self, real_api_data):
        """REGRA: Campos críticos nunca devem ser null"""
        om_hourly = real_api_data["openmeteo_hourly"]["forecasts"]
        first_forecast = om_hourly[0]
        
        critical_fields = ["temperature", "humidity", "windSpeed", "timestamp"]
        
        for field in critical_fields:
            value = first_forecast.get(field)
            assert value is not None, f"Campo crítico '{field}' é null"
    
    def test_no_negative_humidity(self, real_api_data):
        """REGRA: Umidade nunca deve ser negativa"""
        om_hourly = real_api_data["openmeteo_hourly"]["forecasts"]
        for forecast in om_hourly[:5]:
            assert forecast["humidity"] >= 0, f"Open-Meteo humidity negativa em {forecast['timestamp']}"
    
    def test_no_negative_precipitation(self, real_api_data):
        """REGRA: Precipitação nunca deve ser negativa"""
        om_hourly = real_api_data["openmeteo_hourly"]["forecasts"]
        
        for forecast in om_hourly[:5]:
            assert forecast["precipitation"] >= 0, \
                f"Precipitação negativa em {forecast['timestamp']}: {forecast['precipitation']}"
    
    def test_precipitation_probability_is_percentage(self, real_api_data):
        """REGRA: Probabilidade de precipitação deve estar entre 0 e 100%"""
        om_hourly = real_api_data["openmeteo_hourly"]["forecasts"]
        
        for forecast in om_hourly[:5]:
            prob = forecast["precipitationProbability"]
            assert 0 <= prob <= 100, \
                f"Probabilidade fora do range em {forecast['timestamp']}: {prob}%"
    
    def test_weather_codes_are_valid(self, real_api_data):
        """REGRA: Códigos meteorológicos devem estar em ranges válidos"""
        om_hourly = real_api_data["openmeteo_hourly"]["forecasts"]
        for forecast in om_hourly[:5]:
            code = forecast["weatherCode"]
            assert code >= 0, f"Weather code inválido: {code}"


class TestBoundaryValues:
    """Testes de valores extremos e limites"""
    
    def test_max_temperature_is_not_absurd(self, real_api_data):
        """REGRA: Temperatura máxima não deve ser absurdamente alta (>60°C)"""
        om_daily = real_api_data["openmeteo_daily"]["forecasts"]
        
        for forecast in om_daily:
            temp_max = forecast["tempMax"]
            assert temp_max < 60, f"Temperatura máxima absurda: {temp_max}°C para {forecast['date']}"
    
    def test_min_temperature_is_not_absurd(self, real_api_data):
        """REGRA: Temperatura mínima não deve ser absurdamente baixa (<-20°C no Brasil)"""
        om_daily = real_api_data["openmeteo_daily"]["forecasts"]
        
        for forecast in om_daily:
            temp_min = forecast["tempMin"]
            assert temp_min > -20, f"Temperatura mínima absurda: {temp_min}°C para {forecast['date']}"
    
    def test_wind_speed_is_not_hurricane(self, real_api_data):
        """REGRA: Velocidade do vento não deve ser de furacão (>200 km/h) em condições normais"""
        om_daily = real_api_data["openmeteo_daily"]["forecasts"]
        
        for forecast in om_daily:
            wind_max = forecast["windSpeedMax"]
            assert wind_max < 200, f"Vento de furacão: {wind_max} km/h para {forecast['date']}"
    
    def test_precipitation_sum_is_reasonable(self, real_api_data):
        """REGRA: Precipitação diária não deve ser absurda (>500mm)"""
        om_daily = real_api_data["openmeteo_daily"]["forecasts"]
        
        for forecast in om_daily:
            precip = forecast["precipitationMm"]
            assert precip < 500, f"Precipitação absurda: {precip}mm para {forecast['date']}"
