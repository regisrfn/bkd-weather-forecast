"""
Testes Unitários - Domain Entities (Weather)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambda'))

import pytest
from datetime import datetime
from domain.entities.weather import Weather, WeatherAlert, AlertSeverity


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
        rain_1h=2.5,
        description="céu limpo",
        feels_like=29.0,
        pressure=1013.0,
        visibility=10000,
        weather_alert=[],
        weather_code=800
    )
    
    assert weather.city_id == "3543204"
    assert weather.city_name == "Ribeirão Preto"
    assert weather.temperature == 28.5
    assert weather.humidity == 65
    assert weather.wind_speed == 15.2
    assert weather.rain_probability == 45.0
    assert weather.rain_1h == 2.5
    assert weather.description == "céu limpo"
    assert weather.feels_like == 29.0
    assert weather.pressure == 1013.0
    assert weather.visibility == 10000
    assert weather.weather_alert == []
    assert weather.weather_code == 800


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
        rain_1h=2.5,
        description="céu limpo",
        feels_like=29.0,
        pressure=1013.0,
        visibility=10000,
        weather_alert=[],
        weather_code=800
    )
    
    api_response = weather.to_api_response()
    
    assert api_response['cityId'] == "3543204"
    assert api_response['cityName'] == "Ribeirão Preto"
    assert api_response['temperature'] == 28.5
    assert api_response['humidity'] == 65
    assert api_response['windSpeed'] == 15.2
    assert api_response['rainfallIntensity'] == 45.0
    assert api_response['description'] == "céu limpo"
    assert api_response['feelsLike'] == 29.0
    assert api_response['pressure'] == 1013.0
    assert api_response['visibility'] == 10000
    assert api_response['weatherAlert'] == []
    assert isinstance(api_response['weatherAlert'], list)
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


def test_weather_alert_storm():
    """Testa detecção de alerta de tempestade"""
    forecast_time = datetime(2025, 11, 21, 15, 0)
    alerts = Weather.get_weather_alert(
        weather_code=210,  # Tempestade
        rain_prob=80,
        wind_speed=40,
        forecast_time=forecast_time
    )
    assert isinstance(alerts, list)
    assert len(alerts) == 2  # Tempestade + Ventos moderados
    assert any(a.code == "STORM" for a in alerts)
    assert any(a.code == "MODERATE_WIND" for a in alerts)
    
    storm_alert = next(a for a in alerts if a.code == "STORM")
    assert storm_alert.severity == AlertSeverity.DANGER
    assert "Tempestade" in storm_alert.description


def test_weather_alert_heavy_rain():
    """Testa detecção de alerta de chuva forte"""
    forecast_time = datetime(2025, 11, 21, 15, 0)
    alerts = Weather.get_weather_alert(
        weather_code=502,  # Chuva forte
        rain_prob=85,
        wind_speed=20,
        forecast_time=forecast_time
    )
    assert isinstance(alerts, list)
    assert len(alerts) == 1
    assert alerts[0].code == "HEAVY_RAIN"
    assert alerts[0].severity == AlertSeverity.ALERT


def test_weather_alert_strong_wind():
    """Testa detecção de alerta de ventos fortes"""
    forecast_time = datetime(2025, 11, 21, 15, 0)
    alerts = Weather.get_weather_alert(
        weather_code=800,  # Céu limpo
        rain_prob=10,
        wind_speed=55,
        forecast_time=forecast_time
    )
    assert isinstance(alerts, list)
    assert len(alerts) == 1
    assert alerts[0].code == "STRONG_WIND"
    assert alerts[0].severity == AlertSeverity.ALERT


def test_weather_alert_no_alert():
    """Testa condição sem alertas"""
    forecast_time = datetime(2025, 11, 21, 15, 0)
    alerts = Weather.get_weather_alert(
        weather_code=800,  # Céu limpo
        rain_prob=10,
        wind_speed=15,
        forecast_time=forecast_time
    )
    assert isinstance(alerts, list)
    assert len(alerts) == 0


def test_weather_alert_to_dict():
    """Testa serialização de WeatherAlert para dict"""
    alert = WeatherAlert(
        code="STORM",
        severity=AlertSeverity.DANGER,
        description="⚠️ ALERTA: Tempestade",
        timestamp=datetime(2025, 11, 21, 15, 0)
    )
    
    alert_dict = alert.to_dict()
    
    assert alert_dict['code'] == "STORM"
    assert alert_dict['severity'] == "danger"
    assert alert_dict['description'] == "⚠️ ALERTA: Tempestade"
    assert 'timestamp' in alert_dict


def test_weather_alert_deduplication():
    """
    Testa que apenas um alerta por code é retornado
    Valida que múltiplos alertas do mesmo tipo são deduplicated
    """
    forecast_time = datetime(2025, 11, 21, 15, 0)
    
    # Caso com múltiplos alertas possíveis do mesmo tipo
    alerts = Weather.get_weather_alert(
        weather_code=210,  # Tempestade (STORM)
        rain_prob=85,      # Alta prob de chuva
        wind_speed=55,     # Vento forte (STRONG_WIND)
        forecast_time=forecast_time
    )
    
    # Verificar que não há duplicatas de codes
    alert_codes = [alert.code for alert in alerts]
    unique_codes = set(alert_codes)
    
    assert len(alert_codes) == len(unique_codes), "Não deve haver alertas duplicados com o mesmo code"
    
    # Verificar que cada code aparece apenas uma vez
    for code in unique_codes:
        count = alert_codes.count(code)
        assert count == 1, f"O código {code} aparece {count} vezes, deveria aparecer apenas 1 vez"


def test_weather_alert_priority_timestamp():
    """
    Testa que a prioridade por timestamp funciona corretamente
    Mesmo que logicamente a função retorne um alerta por call,
    valida que a estrutura de deduplicação está implementada
    """
    forecast_time = datetime(2025, 11, 21, 15, 0)
    
    alerts = Weather.get_weather_alert(
        weather_code=502,  # Chuva forte
        rain_prob=85,
        wind_speed=20,
        forecast_time=forecast_time
    )
    
    # Verificar que cada alerta tem um timestamp válido
    for alert in alerts:
        assert alert.timestamp is not None
        assert isinstance(alert.timestamp, datetime)
        
    # Verificar que não há duplicatas
    alert_codes = [alert.code for alert in alerts]
    assert len(alert_codes) == len(set(alert_codes))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
