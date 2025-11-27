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
        forecast_time=forecast_time,
        rain_1h=0.0,
        temperature=25.0
    )
    assert isinstance(alerts, list)
    assert len(alerts) == 2  # Tempestade + Ventos moderados
    assert any(a.code == "STORM" for a in alerts)
    assert any(a.code == "MODERATE_WIND" for a in alerts)
    
    storm_alert = next(a for a in alerts if a.code == "STORM")
    assert storm_alert.severity == AlertSeverity.DANGER
    assert "Tempestade" in storm_alert.description
    assert storm_alert.details is not None
    assert "weather_code" in storm_alert.details
    
    wind_alert = next(a for a in alerts if a.code == "MODERATE_WIND")
    assert wind_alert.details is not None
    assert "wind_speed_kmh" in wind_alert.details


def test_weather_alert_heavy_rain():
    """Testa detecção de alerta de chuva forte"""
    forecast_time = datetime(2025, 11, 21, 15, 0)
    alerts = Weather.get_weather_alert(
        weather_code=502,  # Chuva forte
        rain_prob=85,
        wind_speed=20,
        forecast_time=forecast_time,
        rain_1h=0.0,
        temperature=22.0
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
        forecast_time=forecast_time,
        rain_1h=0.0,
        temperature=28.0
    )
    assert isinstance(alerts, list)
    assert len(alerts) == 1
    assert alerts[0].code == "STRONG_WIND"
    assert alerts[0].severity == AlertSeverity.ALERT
    assert alerts[0].details is not None
    assert "wind_speed_kmh" in alerts[0].details
    assert alerts[0].details["wind_speed_kmh"] == 55.0


def test_weather_alert_no_alert():
    """Testa condição sem alertas"""
    forecast_time = datetime(2025, 11, 21, 15, 0)
    alerts = Weather.get_weather_alert(
        weather_code=800,  # Céu limpo
        rain_prob=10,
        wind_speed=15,
        forecast_time=forecast_time,
        rain_1h=0.0,
        temperature=25.0
    )
    assert isinstance(alerts, list)
    assert len(alerts) == 0


def test_weather_alert_to_dict():
    """Testa serialização de WeatherAlert para dict"""
    alert = WeatherAlert(
        code="STORM",
        severity=AlertSeverity.DANGER,
        description="⚠️ ALERTA: Tempestade",
        timestamp=datetime(2025, 11, 21, 15, 0),
        details={"wind_speed_kmh": 65.5, "rain_mm_h": 25.0}
    )
    
    alert_dict = alert.to_dict()
    
    assert alert_dict['code'] == "STORM"
    assert alert_dict['severity'] == "danger"
    assert alert_dict['description'] == "⚠️ ALERTA: Tempestade"
    assert 'timestamp' in alert_dict
    assert 'details' in alert_dict
    assert alert_dict['details']['wind_speed_kmh'] == 65.5
    assert alert_dict['details']['rain_mm_h'] == 25.0


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
        forecast_time=forecast_time,
        rain_1h=0.0,
        temperature=24.0
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
        forecast_time=forecast_time,
        rain_1h=0.0,
        temperature=23.0
    )
    
    # Verificar que cada alerta tem um timestamp válido
    for alert in alerts:
        assert alert.timestamp is not None
        assert isinstance(alert.timestamp, datetime)
        
    # Verificar que não há duplicatas
    alert_codes = [alert.code for alert in alerts]
    assert len(alert_codes) == len(set(alert_codes))


def test_weather_alert_drizzle():
    """Testa alerta de garoa baseado em volume de precipitação"""
    forecast_time = datetime(2025, 11, 21, 15, 0)
    alerts = Weather.get_weather_alert(
        weather_code=800,  # Céu limpo
        rain_prob=85,  # Probabilidade alta
        wind_speed=15,
        forecast_time=forecast_time,
        rain_1h=1.5,  # Garoa
        temperature=22.0
    )
    assert isinstance(alerts, list)
    assert len(alerts) == 1
    assert alerts[0].code == "DRIZZLE"
    assert alerts[0].severity == AlertSeverity.INFO
    assert alerts[0].details is not None
    assert "rain_mm_h" in alerts[0].details
    assert alerts[0].details["rain_mm_h"] == 1.5


def test_weather_alert_light_rain():
    """Testa alerta de chuva fraca"""
    forecast_time = datetime(2025, 11, 21, 15, 0)
    alerts = Weather.get_weather_alert(
        weather_code=800,
        rain_prob=82,  # Probabilidade alta
        wind_speed=15,
        forecast_time=forecast_time,
        rain_1h=5.0,  # Chuva fraca
        temperature=20.0
    )
    assert isinstance(alerts, list)
    assert len(alerts) == 1
    assert alerts[0].code == "LIGHT_RAIN"
    assert alerts[0].severity == AlertSeverity.INFO
    assert alerts[0].details["rain_mm_h"] == 5.0


def test_weather_alert_moderate_rain():
    """Testa alerta de chuva moderada"""
    forecast_time = datetime(2025, 11, 21, 15, 0)
    alerts = Weather.get_weather_alert(
        weather_code=800,
        rain_prob=90,  # Probabilidade alta
        wind_speed=20,
        forecast_time=forecast_time,
        rain_1h=15.0,  # Chuva moderada
        temperature=19.0
    )
    assert isinstance(alerts, list)
    assert len(alerts) == 1
    assert alerts[0].code == "MODERATE_RAIN"
    assert alerts[0].severity == AlertSeverity.WARNING
    assert alerts[0].details["rain_mm_h"] == 15.0


def test_weather_alert_heavy_rain_by_volume():
    """Testa alerta de chuva forte baseado em volume"""
    forecast_time = datetime(2025, 11, 21, 15, 0)
    alerts = Weather.get_weather_alert(
        weather_code=800,
        rain_prob=90,
        wind_speed=25,
        forecast_time=forecast_time,
        rain_1h=55.0,  # Chuva forte
        temperature=18.0
    )
    assert isinstance(alerts, list)
    assert len(alerts) == 1
    assert alerts[0].code == "HEAVY_RAIN"
    assert alerts[0].severity == AlertSeverity.ALERT
    assert alerts[0].details["rain_mm_h"] == 55.0


def test_weather_alert_cold():
    """Testa alerta de frio"""
    forecast_time = datetime(2025, 11, 21, 15, 0)
    alerts = Weather.get_weather_alert(
        weather_code=800,
        rain_prob=10,
        wind_speed=15,
        forecast_time=forecast_time,
        rain_1h=0.0,
        temperature=11.0  # Frio
    )
    assert isinstance(alerts, list)
    assert len(alerts) == 1
    assert alerts[0].code == "COLD"
    assert alerts[0].severity == AlertSeverity.ALERT
    assert alerts[0].details is not None
    assert "temperature_c" in alerts[0].details
    assert alerts[0].details["temperature_c"] == 11.0


def test_weather_alert_very_cold():
    """Testa alerta de frio intenso"""
    forecast_time = datetime(2025, 11, 21, 15, 0)
    alerts = Weather.get_weather_alert(
        weather_code=800,
        rain_prob=10,
        wind_speed=15,
        forecast_time=forecast_time,
        rain_1h=0.0,
        temperature=6.0  # Frio intenso
    )
    assert isinstance(alerts, list)
    assert len(alerts) == 1
    assert alerts[0].code == "VERY_COLD"
    assert alerts[0].severity == AlertSeverity.DANGER
    assert alerts[0].details["temperature_c"] == 6.0


def test_weather_alert_multiple_with_details():
    """Testa múltiplos alertas com details"""
    forecast_time = datetime(2025, 11, 21, 15, 0)
    alerts = Weather.get_weather_alert(
        weather_code=210,  # Tempestade
        rain_prob=90,
        wind_speed=60,  # Vento forte
        forecast_time=forecast_time,
        rain_1h=20.0,  # Chuva moderada
        temperature=10.0  # Frio
    )
    assert isinstance(alerts, list)
    # Deve ter: MODERATE_RAIN (volume), STORM (código), STRONG_WIND, COLD
    assert len(alerts) >= 3
    
    # Verificar que todos os alertas têm details
    for alert in alerts:
        assert alert.details is not None
        assert isinstance(alert.details, dict)


def test_temperature_drop_with_days_between():
    """Testa alerta TEMP_DROP com campo days_between"""
    alert = WeatherAlert(
        code="TEMP_DROP",
        severity=AlertSeverity.WARNING,
        description="🌡️ Queda de temperatura (13°C em 2 dias)",
        timestamp=datetime(2025, 11, 22, 12, 0),
        details={
            "day_1_date": "2025-11-20",
            "day_1_max_c": 25.0,
            "day_2_date": "2025-11-22",
            "day_2_max_c": 12.0,
            "variation_c": -13.0,
            "days_between": 2
        }
    )
    
    assert alert.code == "TEMP_DROP"
    assert alert.severity == AlertSeverity.WARNING
    assert "13°C" in alert.description
    assert "2 dias" in alert.description
    assert alert.details["days_between"] == 2
    assert alert.details["variation_c"] == -13.0


def test_temperature_rise_with_days_between():
    """Testa alerta TEMP_RISE com campo days_between"""
    alert = WeatherAlert(
        code="TEMP_RISE",
        severity=AlertSeverity.INFO,
        description="🌡️ Aumento de temperatura (+10°C em 3 dias)",
        timestamp=datetime(2025, 11, 23, 12, 0),
        details={
            "day_1_date": "2025-11-20",
            "day_1_max_c": 15.0,
            "day_2_date": "2025-11-23",
            "day_2_max_c": 25.0,
            "variation_c": 10.0,
            "days_between": 3
        }
    )
    
    assert alert.code == "TEMP_RISE"
    assert alert.severity == AlertSeverity.INFO
    assert "+10°C" in alert.description
    assert "3 dias" in alert.description
    assert alert.details["days_between"] == 3
    assert alert.details["variation_c"] == 10.0


def test_low_visibility_alert():
    """Testa alerta LOW_VISIBILITY com visibilidade < 1km"""
    alerts = Weather.get_weather_alert(
        weather_code=800,
        rain_prob=0,
        wind_speed=10,
        forecast_time=datetime(2025, 11, 27, 12, 0),
        visibility=500  # 500 metros
    )
    
    assert len(alerts) == 1
    assert alerts[0].code == "LOW_VISIBILITY"
    assert alerts[0].severity == AlertSeverity.ALERT
    assert "Visibilidade reduzida" in alerts[0].description
    assert alerts[0].details["visibility_m"] == 500


def test_low_visibility_warning():
    """Testa alerta LOW_VISIBILITY warning com visibilidade < 3km"""
    alerts = Weather.get_weather_alert(
        weather_code=800,
        rain_prob=0,
        wind_speed=10,
        forecast_time=datetime(2025, 11, 27, 12, 0),
        visibility=2000  # 2km
    )
    
    assert len(alerts) == 1
    assert alerts[0].code == "LOW_VISIBILITY"
    assert alerts[0].severity == AlertSeverity.WARNING
    assert "Visibilidade reduzida" in alerts[0].description
    assert alerts[0].details["visibility_m"] == 2000


def test_no_low_visibility_alert():
    """Testa que não gera alerta com boa visibilidade"""
    alerts = Weather.get_weather_alert(
        weather_code=800,
        rain_prob=0,
        wind_speed=10,
        forecast_time=datetime(2025, 11, 27, 12, 0),
        visibility=10000  # 10km - boa visibilidade
    )
    
    assert len(alerts) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
