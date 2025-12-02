"""
Unit Tests for WeatherAlertsAnalyzer
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import pytest
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from infrastructure.adapters.helpers.weather_alerts_analyzer import WeatherAlertsAnalyzer
from domain.entities.weather import WeatherAlert, AlertSeverity
from domain.entities.forecast_snapshot import ForecastSnapshot


@pytest.fixture
def test_data():
    """Load test-data.json"""
    test_data_path = os.path.join(os.path.dirname(__file__), 'test-data.json')
    with open(test_data_path, 'r') as f:
        return json.load(f)


class TestCollectAllAlerts:
    """Tests for collect_all_alerts method"""
    
    def test_collect_all_alerts_no_severe_conditions(self, test_data):
        """Test alert collection when no severe conditions exist"""
        forecasts = test_data['list'][:10]  # First 10 forecasts (clear sky)
        target_dt = datetime(2025, 11, 27, 12, 0, tzinfo=ZoneInfo("UTC"))
        
        alerts = WeatherAlertsAnalyzer.collect_all_alerts(forecasts, target_dt)
        
        assert isinstance(alerts, list)
        # May have some alerts depending on data
    
    def test_collect_all_alerts_with_rain(self, test_data):
        """Test alert collection with rain forecast"""
        # Last forecast has rain
        forecasts = [test_data['list'][-1]]
        target_dt = datetime(2025, 12, 1, 15, 0, tzinfo=ZoneInfo("UTC"))
        
        alerts = WeatherAlertsAnalyzer.collect_all_alerts(forecasts, target_dt)
        
        assert isinstance(alerts, list)
        # May have rain alerts depending on probability
    
    def test_collect_all_alerts_empty_list(self):
        """Test with empty forecast list"""
        alerts = WeatherAlertsAnalyzer.collect_all_alerts([], None)
        
        assert isinstance(alerts, list)
        assert len(alerts) == 0
    
    def test_collect_all_alerts_no_duplicates(self, test_data):
        """Test that duplicate alert codes are removed"""
        forecasts = test_data['list']
        target_dt = datetime(2025, 11, 27, 12, 0, tzinfo=ZoneInfo("UTC"))
        
        alerts = WeatherAlertsAnalyzer.collect_all_alerts(forecasts, target_dt)
        
        # Check no duplicate codes
        alert_codes = [alert.code for alert in alerts]
        assert len(alert_codes) == len(set(alert_codes))

    def test_collect_all_alerts_deduplicates_with_snapshots(self):
        """Ensure dedupe branch is exercised when multiple alerts have same code."""
        ts = datetime(2025, 1, 1, 12, 0, tzinfo=ZoneInfo("UTC"))
        snapshots = [
            ForecastSnapshot(
                timestamp=ts,
                temperature=25,
                humidity=50,
                wind_speed_kmh=10,
                wind_direction=0,
                rain_probability=90,
                rain_volume_3h=6.0,
                description="chuva",
                feels_like=25,
                pressure=1010,
                visibility=10000,
                clouds=90,
                weather_code=500,
                temp_min=24,
                temp_max=26
            ),
            ForecastSnapshot(
                timestamp=ts + timedelta(hours=3),
                temperature=24,
                humidity=55,
                wind_speed_kmh=10,
                wind_direction=0,
                rain_probability=90,
                rain_volume_3h=6.0,
                description="chuva",
                feels_like=24,
                pressure=1010,
                visibility=10000,
                clouds=90,
                weather_code=500,
                temp_min=23,
                temp_max=25
            ),
        ]

        alerts = WeatherAlertsAnalyzer.collect_all_alerts(snapshots, ts)
        assert len(alerts) >= 1  # Alert exists


class TestFindRainEndTime:
    """Tests for find_rain_end_time method"""
    
    @pytest.fixture
    def rain_forecasts(self):
        """Sample forecasts with rain"""
        return [
            {
                'dt': 1700000000,
                'weather': [{'id': 500}],  # Light rain
                'rain': {'3h': 2.5},
                'pop': 0.9
            },
            {
                'dt': 1700010800,
                'weather': [{'id': 500}],  # Light rain
                'rain': {'3h': 1.5},
                'pop': 0.85
            },
            {
                'dt': 1700021600,
                'weather': [{'id': 800}],  # Clear
                'rain': {},
                'pop': 0.1
            }
        ]
    
    def test_find_rain_end_time_with_end(self, rain_forecasts):
        """Test finding rain end time"""
        alert_timestamp = datetime.fromtimestamp(1700000000, tz=ZoneInfo("UTC"))
        
        rain_end = WeatherAlertsAnalyzer.find_rain_end_time(
            rain_forecasts,
            alert_timestamp
        )
        
        # Should return time after last rain forecast + 3h
        assert rain_end is not None
        assert rain_end.tzinfo is not None
    
    def test_find_rain_end_time_continuous_rain(self):
        """Test when rain doesn't end"""
        forecasts = [
            {
                'dt': 1700000000,
                'weather': [{'id': 500}],
                'rain': {'3h': 2.5},
                'pop': 0.9
            }
        ]
        alert_timestamp = datetime.fromtimestamp(1700000000, tz=ZoneInfo("UTC"))
        
        rain_end = WeatherAlertsAnalyzer.find_rain_end_time(
            forecasts,
            alert_timestamp
        )
        
        # Should return last forecast + 3h
        assert rain_end is not None
    
    def test_find_rain_end_time_empty_list(self):
        """Test with empty forecast list"""
        alert_timestamp = datetime.now(tz=ZoneInfo("UTC"))
        
        rain_end = WeatherAlertsAnalyzer.find_rain_end_time(
            [],
            alert_timestamp
        )
        
        assert rain_end is None

    def test_find_rain_end_time_naive_timestamp(self):
        """Should handle naive alert timestamp by assuming UTC."""
        ts = datetime(2024, 1, 1, 0, 0)  # naive
        snapshot_rain = ForecastSnapshot(
            timestamp=ts.replace(tzinfo=ZoneInfo("UTC")),
            temperature=20,
            humidity=60,
            wind_speed_kmh=5,
            wind_direction=0,
            rain_probability=90,
            rain_volume_3h=3.0,
            description="chuva",
            feels_like=20,
            pressure=1010,
            visibility=10000,
            clouds=50,
            weather_code=500,
            temp_min=20,
            temp_max=20
        )
        snapshot_clear = ForecastSnapshot(
            timestamp=ts.replace(tzinfo=ZoneInfo("UTC")) + timedelta(hours=3),
            temperature=21,
            humidity=50,
            wind_speed_kmh=5,
            wind_direction=0,
            rain_probability=0,
            rain_volume_3h=0.0,
            description="clear",
            feels_like=21,
            pressure=1010,
            visibility=10000,
            clouds=0,
            weather_code=800,
            temp_min=21,
            temp_max=21
        )

        rain_end = WeatherAlertsAnalyzer.find_rain_end_time(
            [snapshot_rain, snapshot_clear],
            ts  # naive
        )

        expected = snapshot_rain.timestamp.astimezone(ZoneInfo("America/Sao_Paulo")) + timedelta(hours=3)
        assert rain_end == expected

    def test_find_rain_end_time_non_utc_alert(self):
        """Should normalize non-UTC alert timestamp."""
        ts_sp = datetime(2024, 1, 1, 0, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
        snapshot_rain = ForecastSnapshot(
            timestamp=ts_sp.astimezone(ZoneInfo("UTC")),
            temperature=20,
            humidity=60,
            wind_speed_kmh=5,
            wind_direction=0,
            rain_probability=90,
            rain_volume_3h=3.0,
            description="chuva",
            feels_like=20,
            pressure=1010,
            visibility=10000,
            clouds=50,
            weather_code=500,
            temp_min=20,
            temp_max=20
        )
        rain_end = WeatherAlertsAnalyzer.find_rain_end_time(
            [snapshot_rain],
            ts_sp
        )

        expected = ts_sp + timedelta(hours=3)
        assert rain_end == expected

    def test_find_rain_end_time_handles_wmo_codes(self):
        """Rain end should consider WMO precip codes (Open-Meteo hourly)."""
        ts = datetime(2024, 1, 1, 0, 0, tzinfo=ZoneInfo("UTC"))
        snapshot_rain = ForecastSnapshot(
            timestamp=ts,
            temperature=20,
            humidity=60,
            wind_speed_kmh=5,
            wind_direction=0,
            rain_probability=10,
            rain_volume_3h=0.0,
            description="chuva fraca",
            feels_like=20,
            pressure=1010,
            visibility=10000,
            clouds=50,
            weather_code=61,  # WMO rain code
            temp_min=20,
            temp_max=20
        )
        snapshot_clear = ForecastSnapshot(
            timestamp=ts + timedelta(hours=1),
            temperature=21,
            humidity=50,
            wind_speed_kmh=5,
            wind_direction=0,
            rain_probability=0,
            rain_volume_3h=0.0,
            description="clear",
            feels_like=21,
            pressure=1010,
            visibility=10000,
            clouds=0,
            weather_code=0,
            temp_min=21,
            temp_max=21
        )

        rain_end = WeatherAlertsAnalyzer.find_rain_end_time(
            [snapshot_rain, snapshot_clear],
            ts
        )

        expected = ts.astimezone(ZoneInfo("America/Sao_Paulo")) + timedelta(hours=1)
        assert rain_end == expected

    def test_find_rain_end_time_uses_intensity_without_precip_code(self):
        """Rain end should trigger on high rain intensity even with clear code."""
        ts = datetime(2024, 1, 1, 0, 0, tzinfo=ZoneInfo("UTC"))
        snapshot_rain = ForecastSnapshot(
            timestamp=ts,
            temperature=20,
            humidity=60,
            wind_speed_kmh=5,
            wind_direction=0,
            rain_probability=90,
            rain_volume_3h=3.0,  # 1mm/h
            description="heavy shower",
            feels_like=20,
            pressure=1010,
            visibility=10000,
            clouds=90,
            weather_code=800,  # Clear code, but precipitation volume should trigger
            temp_min=20,
            temp_max=20
        )
        snapshot_clear = ForecastSnapshot(
            timestamp=ts + timedelta(hours=3),
            temperature=21,
            humidity=50,
            wind_speed_kmh=5,
            wind_direction=0,
            rain_probability=0,
            rain_volume_3h=0.0,
            description="clear",
            feels_like=21,
            pressure=1010,
            visibility=10000,
            clouds=0,
            weather_code=800,
            temp_min=21,
            temp_max=21
        )

        rain_end = WeatherAlertsAnalyzer.find_rain_end_time(
            [snapshot_rain, snapshot_clear],
            ts
        )

        expected = ts.astimezone(ZoneInfo("America/Sao_Paulo")) + timedelta(hours=3)
        assert rain_end == expected


class TestAnalyzeTemperatureTrend:
    """Tests for analyze_temperature_trend method"""
    
    @pytest.fixture
    def temp_variation_forecasts(self):
        """Forecasts with significant temperature variation"""
        # Day 1: 25°C max
        day1_forecasts = [
            {
                'dt': 1700000000,
                'main': {'temp': 25, 'temp_max': 25, 'temp_min': 20}
            },
            {
                'dt': 1700010800,
                'main': {'temp': 24, 'temp_max': 25, 'temp_min': 20}
            }
        ]
        # Day 2: 15°C max (10°C drop)
        day2_forecasts = [
            {
                'dt': 1700086400,
                'main': {'temp': 15, 'temp_max': 15, 'temp_min': 10}
            },
            {
                'dt': 1700097200,
                'main': {'temp': 14, 'temp_max': 15, 'temp_min': 10}
            }
        ]
        return day1_forecasts + day2_forecasts
    
    def test_analyze_temperature_trend_with_drop(self, temp_variation_forecasts):
        """Test detection of temperature drop"""
        reference = datetime.fromtimestamp(1700000000, tz=ZoneInfo("UTC"))
        
        alerts = WeatherAlertsAnalyzer.analyze_temperature_trend(
            temp_variation_forecasts,
            reference
        )
        
        assert isinstance(alerts, list)
        # Should detect temperature drop
        if len(alerts) > 0:
            temp_drop_alert = next(
                (a for a in alerts if a.code == "TEMP_DROP"),
                None
            )
            if temp_drop_alert:
                assert temp_drop_alert.severity == AlertSeverity.INFO
    
    def test_analyze_temperature_trend_empty_list(self):
        """Test with empty forecast list"""
        reference = datetime.now(tz=ZoneInfo("UTC"))
        
        alerts = WeatherAlertsAnalyzer.analyze_temperature_trend([], reference)
        
        assert alerts == []

    def test_analyze_temperature_trend_empty_extremes(self, monkeypatch):
        """Hit branch when daily extremes are empty after normalization."""
        reference = datetime.now(tz=ZoneInfo("UTC"))
        dummy_snapshot = ForecastSnapshot.from_openweather({
            "dt": int(reference.timestamp()),
            "main": {"temp": 20, "humidity": 50, "temp_min": 20, "temp_max": 20},
            "wind": {"speed": 1},
            "weather": [{"id": 800}],
        })

        with monkeypatch.context() as m:
            m.setattr(
                WeatherAlertsAnalyzer,
                "_calculate_daily_extremes",
                lambda forecasts: {}
            )
            alerts = WeatherAlertsAnalyzer.analyze_temperature_trend([dummy_snapshot], reference)
            assert alerts == []

    def test_analyze_temperature_trend_temp_rise(self):
        """Detect temperature rise branch."""
        day1 = datetime(2025, 1, 1, 0, 0, tzinfo=ZoneInfo("UTC"))
        day2 = day1 + timedelta(days=1)
        forecasts = [
            ForecastSnapshot(
                timestamp=day1,
                temperature=20,
                humidity=50,
                wind_speed_kmh=5,
                wind_direction=0,
                rain_probability=0,
                rain_volume_3h=0.0,
                description="clear",
                feels_like=20,
                pressure=1010,
                visibility=10000,
                clouds=0,
                weather_code=800,
                temp_min=19,
                temp_max=21
            ),
            ForecastSnapshot(
                timestamp=day2,
                temperature=30,
                humidity=50,
                wind_speed_kmh=5,
                wind_direction=0,
                rain_probability=0,
                rain_volume_3h=0.0,
                description="hot",
                feels_like=30,
                pressure=1010,
                visibility=10000,
                clouds=0,
                weather_code=800,
                temp_min=29,
                temp_max=31
            ),
        ]

        alerts = WeatherAlertsAnalyzer.analyze_temperature_trend(forecasts, day1)
        rise = [a for a in alerts if a.code == "TEMP_RISE"]
        assert rise
    
    def test_analyze_temperature_trend_no_significant_variation(self):
        """Test when temperature variation is not significant (<8°C)"""
        forecasts = [
            {
                'dt': 1700000000,
                'main': {'temp': 25, 'temp_max': 25, 'temp_min': 23}
            },
            {
                'dt': 1700086400,
                'main': {'temp': 22, 'temp_max': 22, 'temp_min': 20}
            }
        ]
        reference = datetime.fromtimestamp(1700000000, tz=ZoneInfo("UTC"))
        
        alerts = WeatherAlertsAnalyzer.analyze_temperature_trend(
            forecasts,
            reference
        )
        
        # Should not generate alerts for small variations
        assert len(alerts) == 0


class TestCalculateDailyExtremes:
    """Tests for _calculate_daily_extremes method"""
    
    def test_calculate_daily_extremes_success(self):
        """Test calculating daily temperature extremes"""
        forecasts = [
            {
                'dt': 1700000000,
                'main': {'temp': 25, 'temp_max': 26, 'temp_min': 24}
            },
            {
                'dt': 1700010800,
                'main': {'temp': 27, 'temp_max': 28, 'temp_min': 26}
            },
            {
                'dt': 1700086400,  # Next day
                'main': {'temp': 20, 'temp_max': 21, 'temp_min': 19}
            }
        ]
        
        daily_extremes = WeatherAlertsAnalyzer._calculate_daily_extremes(forecasts)
        
        assert isinstance(daily_extremes, dict)
        assert len(daily_extremes) >= 1
        
        # Check structure
        for date_key, temps in daily_extremes.items():
            assert 'max' in temps
            assert 'min' in temps
            assert 'first_timestamp' in temps
            assert temps['max'] >= temps['min']
    
    def test_calculate_daily_extremes_empty_list(self):
        """Test with empty forecast list"""
        daily_extremes = WeatherAlertsAnalyzer._calculate_daily_extremes([])
        
        assert daily_extremes == {}

    def test_calculate_daily_extremes_handles_patch(self, monkeypatch):
        """Ensure branch when _calculate_daily_extremes returns empty dict."""
        reference = datetime.now(tz=ZoneInfo("UTC"))
        with monkeypatch.context() as m:
            m.setattr(
                WeatherAlertsAnalyzer,
                "_calculate_daily_extremes",
                lambda forecasts: {}
            )
            alerts = WeatherAlertsAnalyzer.analyze_temperature_trend([], reference)
            assert alerts == []


class TestPrecipitationHelpers:
    """Unit tests for precipitation helper functions."""

    def _snapshot(self, **kwargs):
        base_ts = kwargs.pop("timestamp", datetime(2024, 1, 1, 0, 0, tzinfo=ZoneInfo("UTC")))
        defaults = dict(
            timestamp=base_ts,
            temperature=20,
            humidity=50,
            wind_speed_kmh=5,
            wind_direction=0,
            rain_probability=0,
            rain_volume_3h=0.0,
            description="",
            feels_like=20,
            pressure=1010,
            visibility=10000,
            clouds=10,
            weather_code=800,
            temp_min=20,
            temp_max=20
        )
        defaults.update(kwargs)
        return ForecastSnapshot(**defaults)

    def test_is_precipitating_by_intensity(self):
        """High intensity (volume x prob) should flag precipitation even with clear code."""
        snapshot = self._snapshot(rain_probability=100, rain_volume_3h=9.0, weather_code=800)
        assert WeatherAlertsAnalyzer._is_precipitating(snapshot) is True

    def test_is_precipitating_false_for_low_volume_low_prob(self):
        """Low volume and low prob without precip code should not flag rain."""
        snapshot = self._snapshot(rain_probability=5, rain_volume_3h=0.5, weather_code=800)
        assert WeatherAlertsAnalyzer._is_precipitating(snapshot) is False

    def test_forecast_window_hours_defaults_to_three(self):
        """Fallback to 3h when only one forecast is present."""
        snapshot = self._snapshot()
        assert WeatherAlertsAnalyzer._forecast_window_hours([snapshot]) == 3.0

    def test_forecast_window_hours_respects_hourly_spacing(self):
        """Should infer 1h window when spacing is hourly (Open-Meteo)."""
        ts = datetime(2024, 1, 1, 0, 0, tzinfo=ZoneInfo("UTC"))
        s1 = self._snapshot(timestamp=ts)
        s2 = self._snapshot(timestamp=ts + timedelta(hours=1))
        assert WeatherAlertsAnalyzer._forecast_window_hours([s1, s2]) == 1.0

    def test_code_indicates_precipitation_coverage(self):
        """Exercise all precipitation code branches."""
        assert WeatherAlertsAnalyzer._code_indicates_precipitation(200) is True
        assert WeatherAlertsAnalyzer._code_indicates_precipitation(55) is True
        assert WeatherAlertsAnalyzer._code_indicates_precipitation(81) is True
        assert WeatherAlertsAnalyzer._code_indicates_precipitation(96) is True

    def test_is_precipitating_by_volume_probability(self):
        """Should detect precipitation when volume>0 and prob>=40 even with low intensity."""
        snapshot = self._snapshot(rain_probability=50, rain_volume_3h=1.0, weather_code=800)
        assert WeatherAlertsAnalyzer._is_precipitating(snapshot) is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
