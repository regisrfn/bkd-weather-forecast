"""
Unit tests for ForecastSnapshot normalization.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from datetime import datetime
from zoneinfo import ZoneInfo

from domain.entities.forecast_snapshot import ForecastSnapshot


def test_from_openweather_basic_mapping():
    payload = {
        "dt": 1700000000,
        "main": {
            "temp": 20.5,
            "humidity": 70,
            "feels_like": 21.0,
            "pressure": 1005,
            "temp_min": 19.0,
            "temp_max": 22.0
        },
        "wind": {"speed": 5.0, "deg": 180},
        "pop": 0.6,
        "rain": {"3h": 3.0},
        "visibility": 9000,
        "clouds": {"all": 75},
        "weather": [{"id": 500, "description": "chuva leve"}]
    }

    snapshot = ForecastSnapshot.from_openweather(payload)

    assert snapshot.temperature == 20.5
    assert snapshot.humidity == 70
    assert snapshot.wind_speed_kmh == 18.0  # 5 m/s -> 18 km/h
    assert snapshot.wind_direction == 180
    assert snapshot.rain_probability == 60.0
    assert snapshot.rain_volume_3h == 3.0
    assert snapshot.description == "chuva leve"
    assert snapshot.feels_like == 21.0
    assert snapshot.pressure == 1005
    assert snapshot.visibility == 9000
    assert snapshot.clouds == 75
    assert snapshot.weather_code == 500
    assert snapshot.temp_min == 19.0
    assert snapshot.temp_max == 22.0
    assert snapshot.rain_1h == 1.0
    assert snapshot.timestamp.tzinfo == ZoneInfo("UTC")


def test_from_openmeteo_hourly_mapping():
    class DummyHourly:
        timestamp = "2024-01-01T12:00:00"
        temperature = 22.0
        precipitation = 1.0
        precipitation_probability = 80
        humidity = 50
        wind_speed = 10.0
        wind_direction = 90
        cloud_cover = 20
        weather_code = 81
        description = "chuva"

    snapshot = ForecastSnapshot.from_openmeteo_hourly(DummyHourly(), visibility=8000)

    assert snapshot.rain_volume_3h == 3.0  # 1mm/h * 3h window
    assert snapshot.rain_probability == 80
    assert snapshot.wind_speed_kmh == 10.0
    assert snapshot.visibility == 8000
    assert snapshot.temperature == 22.0
    assert snapshot.timestamp.tzinfo is not None


def test_from_list_handles_mixed_entries():
    payload = {
        "dt": 1700000000,
        "main": {"temp": 20, "temp_min": 19, "temp_max": 21, "humidity": 50},
        "weather": [{"id": 800, "description": "céu limpo"}],
        "wind": {"speed": 2, "deg": 0}
    }
    snapshots = ForecastSnapshot.from_list([payload, ForecastSnapshot.from_openweather(payload)])

    assert len(snapshots) == 2
    assert all(isinstance(s, ForecastSnapshot) for s in snapshots)


def test_forecast_snapshot_handles_invalid_entries():
    """Should skip malformed items and fallback on timestamp parsing."""
    snapshots = ForecastSnapshot.from_list([
        {"dt": "invalid", "main": {}, "weather": [{}]},  # triggers _parse_timestamp fallback
        "not-a-dict"
    ])
    assert snapshots  # list not empty thanks to first entry fallback
    assert snapshots[0].timestamp.tzinfo is not None


def test_forecast_snapshot_skips_unparsable_dict():
    """Dictionary that raises during parsing must be skipped without raising."""
    snapshots = ForecastSnapshot.from_list([
        {"dt": "invalid", "main": "oops", "weather": "bad"}  # will raise AttributeError inside parser
    ])
    assert snapshots == []


def test_parse_iso_timestamp_fallback():
    """Fallback to now() when iso timestamp is invalid."""
    ts = ForecastSnapshot._parse_iso_timestamp("bad-value")
    assert ts.tzinfo is not None
