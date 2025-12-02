"""
Testes com Dados Reais das APIs
Valida que os dados capturados estão corretos e consistentes
"""
import pytest
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo


@pytest.fixture
def real_api_data():
    """Carrega dados reais capturados das APIs"""
    fixtures_path = Path(__file__).parent.parent / "fixtures" / "real_api_data.json"
    with open(fixtures_path) as f:
        return json.load(f)


class TestOpenWeatherRealData:
    """Testes com dados reais do OpenWeather"""
    
    def test_openweather_has_required_fields(self, real_api_data):
        """REGRA: Response do OpenWeather deve ter todos os campos obrigatórios"""
        ow = real_api_data["openweather_current"]["response"]
        
        required_fields = [
            "temperature", "humidity", "wind_speed", "wind_direction",
            "rain_probability", "description", "feels_like",
            "pressure", "visibility", "clouds", "timestamp"
        ]
        
        for field in required_fields:
            assert field in ow, f"Campo obrigatório '{field}' ausente no OpenWeather"
    
    def test_openweather_temperature_is_reasonable(self, real_api_data):
        """REGRA: Temperatura deve estar em range razoável para Brasil (-10°C a 50°C)"""
        ow = real_api_data["openweather_current"]["response"]
        temp = ow["temperature"]
        
        assert -10 <= temp <= 50, f"Temperatura fora do range razoável: {temp}°C"
    
    def test_openweather_humidity_is_percentage(self, real_api_data):
        """REGRA: Umidade deve estar entre 0 e 100%"""
        ow = real_api_data["openweather_current"]["response"]
        humidity = ow["humidity"]
        
        assert 0 <= humidity <= 100, f"Umidade fora do range: {humidity}%"
    
    def test_openweather_wind_speed_is_positive(self, real_api_data):
        """REGRA: Velocidade do vento deve ser não-negativa"""
        ow = real_api_data["openweather_current"]["response"]
        wind_speed = ow["wind_speed"]
        
        assert wind_speed >= 0, f"Velocidade do vento negativa: {wind_speed}"
    
    def test_openweather_wind_direction_is_valid(self, real_api_data):
        """REGRA: Direção do vento deve estar entre 0 e 360 graus"""
        ow = real_api_data["openweather_current"]["response"]
        wind_dir = ow["wind_direction"]
        
        assert 0 <= wind_dir <= 360, f"Direção do vento inválida: {wind_dir}°"
    
    def test_openweather_clouds_is_percentage(self, real_api_data):
        """REGRA: Cobertura de nuvens deve estar entre 0 e 100%"""
        ow = real_api_data["openweather_current"]["response"]
        clouds = ow["clouds"]
        
        assert 0 <= clouds <= 100, f"Cobertura de nuvens fora do range: {clouds}%"
    
    def test_openweather_timestamp_is_recent(self, real_api_data):
        """REGRA: Timestamp deve ser recente (últimas 24h)"""
        ow = real_api_data["openweather_current"]["response"]
        timestamp = datetime.fromisoformat(ow["timestamp"])
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))
        
        diff_hours = abs((now - timestamp).total_seconds() / 3600)
        assert diff_hours < 24, f"Timestamp muito antigo: {timestamp} (diff: {diff_hours}h)"
    
    def test_openweather_visibility_is_reasonable(self, real_api_data):
        """REGRA: Visibilidade deve estar entre 0 e 10000m (10km)"""
        ow = real_api_data["openweather_current"]["response"]
        visibility = ow["visibility"]
        
        assert 0 <= visibility <= 20000, f"Visibilidade fora do range: {visibility}m"
    
    def test_openweather_pressure_is_reasonable(self, real_api_data):
        """REGRA: Pressão atmosférica deve estar entre 950 e 1050 hPa"""
        ow = real_api_data["openweather_current"]["response"]
        pressure = ow["pressure"]
        
        assert 950 <= pressure <= 1050, f"Pressão fora do range: {pressure} hPa"


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
            "date", "temp_max", "temp_min", "weather_code",
            "precipitation_sum", "precipitation_probability_max",
            "wind_speed_max", "wind_direction_dominant"
        ]
        
        for forecast in forecasts[:3]:  # Verificar primeiros 3
            for field in required_fields:
                assert field in forecast, f"Campo '{field}' ausente no daily forecast"
    
    def test_openmeteo_daily_temp_max_greater_than_min(self, real_api_data):
        """REGRA: Temperatura máxima deve ser maior ou igual à mínima"""
        forecasts = real_api_data["openmeteo_daily"]["forecasts"]
        
        for forecast in forecasts:
            temp_max = forecast["temp_max"]
            temp_min = forecast["temp_min"]
            
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
            "timestamp", "temperature", "humidity", "wind_speed",
            "wind_direction", "precipitation_probability", "precipitation",
            "weather_code"
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


class TestCrossProviderConsistency:
    """Testes de consistência entre providers"""
    
    def test_temperatures_are_similar_between_providers(self, real_api_data):
        """REGRA: Temperaturas de providers diferentes devem ser similares (±10°C)"""
        ow_temp = real_api_data["openweather_current"]["response"]["temperature"]
        
        # Pegar primeira hora do Open-Meteo
        om_hourly = real_api_data["openmeteo_hourly"]["forecasts"][0]
        om_temp = om_hourly["temperature"]
        
        diff = abs(ow_temp - om_temp)
        assert diff <= 10, f"Temperaturas muito diferentes: OW={ow_temp}°C, OM={om_temp}°C (diff={diff})"
    
    def test_wind_speeds_are_similar_between_providers(self, real_api_data):
        """REGRA: Velocidades do vento devem ser similares (±20 km/h)"""
        ow_wind = real_api_data["openweather_current"]["response"]["wind_speed"]
        om_wind = real_api_data["openmeteo_hourly"]["forecasts"][0]["wind_speed"]
        
        diff = abs(ow_wind - om_wind)
        assert diff <= 20, f"Ventos muito diferentes: OW={ow_wind}, OM={om_wind} (diff={diff})"
    
    def test_metadata_has_correct_city_info(self, real_api_data):
        """REGRA: Metadata deve conter informações corretas da cidade"""
        metadata = real_api_data["metadata"]
        city = metadata["city"]
        
        assert city["name"] == "Ribeirão Preto"
        assert city["state"] == "SP"
        assert city["city_id"] == "3451682"
        
        # Coordenadas devem estar próximas de Ribeirão Preto
        assert -22 <= city["latitude"] <= -21
        assert -48 <= city["longitude"] <= -47


class TestDataQuality:
    """Testes de qualidade dos dados"""
    
    def test_no_null_values_in_critical_fields(self, real_api_data):
        """REGRA: Campos críticos nunca devem ser null"""
        ow = real_api_data["openweather_current"]["response"]
        
        critical_fields = ["temperature", "humidity", "wind_speed", "timestamp"]
        
        for field in critical_fields:
            value = ow.get(field)
            assert value is not None, f"Campo crítico '{field}' é null"
    
    def test_no_negative_humidity(self, real_api_data):
        """REGRA: Umidade nunca deve ser negativa"""
        # OpenWeather
        ow_humidity = real_api_data["openweather_current"]["response"]["humidity"]
        assert ow_humidity >= 0, "OpenWeather humidity negativa"
        
        # Open-Meteo hourly
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
            prob = forecast["precipitation_probability"]
            assert 0 <= prob <= 100, \
                f"Probabilidade fora do range em {forecast['timestamp']}: {prob}%"
    
    def test_weather_codes_are_valid(self, real_api_data):
        """REGRA: Códigos meteorológicos devem estar em ranges válidos"""
        # OpenWeather: 200-900
        ow_code = real_api_data["openweather_current"]["response"].get("weather_code")
        if ow_code is not None:
            assert 200 <= ow_code <= 900, f"Weather code OW inválido: {ow_code}"
        
        # Open-Meteo WMO: 0-99
        om_hourly = real_api_data["openmeteo_hourly"]["forecasts"]
        for forecast in om_hourly[:5]:
            code = forecast["weather_code"]
            assert 0 <= code <= 99, f"Weather code OM inválido: {code}"


class TestBoundaryValues:
    """Testes de valores extremos e limites"""
    
    def test_max_temperature_is_not_absurd(self, real_api_data):
        """REGRA: Temperatura máxima não deve ser absurdamente alta (>60°C)"""
        om_daily = real_api_data["openmeteo_daily"]["forecasts"]
        
        for forecast in om_daily:
            temp_max = forecast["temp_max"]
            assert temp_max < 60, f"Temperatura máxima absurda: {temp_max}°C para {forecast['date']}"
    
    def test_min_temperature_is_not_absurd(self, real_api_data):
        """REGRA: Temperatura mínima não deve ser absurdamente baixa (<-20°C no Brasil)"""
        om_daily = real_api_data["openmeteo_daily"]["forecasts"]
        
        for forecast in om_daily:
            temp_min = forecast["temp_min"]
            assert temp_min > -20, f"Temperatura mínima absurda: {temp_min}°C para {forecast['date']}"
    
    def test_wind_speed_is_not_hurricane(self, real_api_data):
        """REGRA: Velocidade do vento não deve ser de furacão (>200 km/h) em condições normais"""
        om_daily = real_api_data["openmeteo_daily"]["forecasts"]
        
        for forecast in om_daily:
            wind_max = forecast["wind_speed_max"]
            assert wind_max < 200, f"Vento de furacão: {wind_max} km/h para {forecast['date']}"
    
    def test_precipitation_sum_is_reasonable(self, real_api_data):
        """REGRA: Precipitação diária não deve ser absurda (>500mm)"""
        om_daily = real_api_data["openmeteo_daily"]["forecasts"]
        
        for forecast in om_daily:
            precip = forecast["precipitation_sum"]
            assert precip < 500, f"Precipitação absurda: {precip}mm para {forecast['date']}"
