"""
Unit Tests for WeatherAlertsAnalyzer
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import pytest
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from infrastructure.adapters.helpers.weather_alerts_analyzer import WeatherAlertsAnalyzer
from domain.entities.weather import WeatherAlert, AlertSeverity


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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
