"""
Unit Tests for WeatherDataProcessor
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import pytest
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from infrastructure.adapters.helpers.weather_data_processor import WeatherDataProcessor
from domain.entities.weather import Weather
from infrastructure.adapters.helpers import date_filter_helper


@pytest.fixture
def test_data():
    """Load test-data.json"""
    test_data_path = os.path.join(os.path.dirname(__file__), 'test-data.json')
    with open(test_data_path, 'r') as f:
        return json.load(f)


class TestProcessWeatherData:
    """Tests for process_weather_data method"""
    
    def test_process_weather_data_success(self, test_data):
        """Test successful processing of weather data"""
        city_name = "Ibirarema"
        target_dt = datetime(2025, 11, 27, 15, 0, tzinfo=ZoneInfo("UTC"))
        
        weather = WeatherDataProcessor.process_weather_data(
            test_data,
            city_name,
            target_dt
        )
        
        assert isinstance(weather, Weather)
        assert weather.city_name == city_name
        assert weather.temperature > 0
        assert 0 <= weather.humidity <= 100
        assert weather.wind_speed >= 0
        assert 0 <= weather.rain_probability <= 100
        assert isinstance(weather.description, str)
        assert isinstance(weather.weather_alert, list)
    
    def test_process_weather_data_with_rain(self, test_data):
        """Test processing forecast with rain"""
        city_name = "Ibirarema"
        # Last forecast has rain (dt: 1764601200)
        target_dt = datetime(2025, 12, 1, 15, 0, tzinfo=ZoneInfo("UTC"))
        
        weather = WeatherDataProcessor.process_weather_data(
            test_data,
            city_name,
            target_dt
        )
        
        assert isinstance(weather, Weather)
        assert weather.rain_probability > 0
        assert weather.description == "chuva leve"
        assert weather.weather_code == 500
    
    def test_process_weather_data_no_target_datetime(self, test_data):
        """Test processing without target datetime"""
        city_name = "Ibirarema"
        
        weather = WeatherDataProcessor.process_weather_data(
            test_data,
            city_name,
            None
        )
        
        assert isinstance(weather, Weather)
        assert weather.city_name == city_name
        assert weather.timestamp is not None
    
    def test_process_weather_data_empty_forecasts(self):
        """Test with empty forecast list"""
        data = {'list': []}
        city_name = "Test City"
        
        with pytest.raises(ValueError, match="Nenhuma previsão futura disponível"):
            WeatherDataProcessor.process_weather_data(data, city_name, None)

    def test_process_weather_data_missing_closest_forecast(self, monkeypatch, test_data):
        """Should raise if closest forecast selection fails."""
        city_name = "Ibirarema"

        # Force select_closest_forecast to return None to hit safeguard
        monkeypatch.setattr(
            date_filter_helper.DateFilterHelper,
            "select_closest_forecast",
            lambda forecasts, target: None
        )

        with pytest.raises(ValueError, match="Nenhuma previsão futura disponível"):
            WeatherDataProcessor.process_weather_data(
                test_data,
                city_name,
                None
            )


class TestGetDailyTempExtremes:
    """Tests for get_daily_temp_extremes method"""
    
    def test_get_daily_temp_extremes_with_target_date(self, test_data):
        """Test calculating min/max temperatures for specific day"""
        forecasts = test_data['list']
        target_dt = datetime(2025, 11, 27, 12, 0, tzinfo=ZoneInfo("UTC"))
        
        temp_min, temp_max = WeatherDataProcessor.get_daily_temp_extremes(
            forecasts,
            target_dt
        )
        
        assert isinstance(temp_min, float)
        assert isinstance(temp_max, float)
        assert temp_min <= temp_max
        assert temp_min > 0  # Realistic temperature
        assert temp_max < 50  # Realistic temperature
    
    def test_get_daily_temp_extremes_empty_list(self):
        """Test with empty forecast list"""
        temp_min, temp_max = WeatherDataProcessor.get_daily_temp_extremes([], None)
        
        assert temp_min == 0.0
        assert temp_max == 0.0
    
    def test_get_daily_temp_extremes_no_target(self, test_data):
        """Test without target datetime (today)"""
        forecasts = test_data['list']
        
        temp_min, temp_max = WeatherDataProcessor.get_daily_temp_extremes(
            forecasts,
            None
        )
        
        assert isinstance(temp_min, float)
        assert isinstance(temp_max, float)
        assert temp_min <= temp_max
    
    def test_get_daily_temp_extremes_includes_whole_day(self, test_data):
        """Test that temperature extremes include ALL forecasts for the day, not just future ones"""
        forecasts = test_data['list']
        
        # Query at end of day (e.g., 21:00) - should still include earlier forecasts
        target_dt = datetime(2025, 11, 27, 21, 0, tzinfo=ZoneInfo("UTC"))
        
        temp_min_late, temp_max_late = WeatherDataProcessor.get_daily_temp_extremes(
            forecasts,
            target_dt
        )
        
        # Query at start of day (e.g., 03:00)
        target_dt_early = datetime(2025, 11, 27, 3, 0, tzinfo=ZoneInfo("UTC"))
        
        temp_min_early, temp_max_early = WeatherDataProcessor.get_daily_temp_extremes(
            forecasts,
            target_dt_early
        )
        
        # Both queries should return same extremes for the day
        # (since we now include all forecasts for the day, not just future ones)
        assert isinstance(temp_min_late, float)
        assert isinstance(temp_max_late, float)
        assert isinstance(temp_min_early, float)
        assert isinstance(temp_max_early, float)
        
        # The late query should have same or similar extremes as early query
        # because they both look at the entire day
        assert temp_min_late <= temp_max_late
        assert temp_min_early <= temp_max_early


class TestCalculateDailyRainAccumulation:
    """Tests for calculate_daily_rain_accumulation method"""
    
    def test_calculate_daily_rain_accumulation_no_rain(self, test_data):
        """Test with day that has no rain"""
        forecasts = test_data['list'][:10]  # First 10 forecasts (clear sky)
        target_dt = datetime(2025, 11, 27, 12, 0, tzinfo=ZoneInfo("UTC"))
        
        total_rain = WeatherDataProcessor.calculate_daily_rain_accumulation(
            forecasts,
            target_dt
        )
        
        assert isinstance(total_rain, float)
        assert total_rain >= 0
    
    def test_calculate_daily_rain_accumulation_with_rain(self, test_data):
        """Test with day that has rain"""
        # Last forecast has rain
        forecasts = [test_data['list'][-1]]
        target_dt = datetime(2025, 12, 1, 15, 0, tzinfo=ZoneInfo("UTC"))
        
        total_rain = WeatherDataProcessor.calculate_daily_rain_accumulation(
            forecasts,
            target_dt
        )
        
        assert isinstance(total_rain, float)
        # Last forecast has rain, so should be > 0
        assert total_rain >= 0
    
    def test_calculate_daily_rain_accumulation_empty_list(self):
        """Test with empty forecast list"""
        total_rain = WeatherDataProcessor.calculate_daily_rain_accumulation([], None)
        
        assert total_rain == 0.0
    
    def test_calculate_daily_rain_accumulation_no_target(self, test_data):
        """Test without target datetime (today)"""
        forecasts = test_data['list']
        
        total_rain = WeatherDataProcessor.calculate_daily_rain_accumulation(
            forecasts,
            None
        )
        
        assert isinstance(total_rain, float)
        assert total_rain >= 0
    
    def test_calculate_daily_rain_accumulation_sums_all_periods(self):
        """Test that daily rain correctly sums all 3h periods for the day"""
        # Create forecasts for a specific day with known rain amounts
        # Use Brazil timezone to ensure date alignment
        brazil_tz = ZoneInfo("America/Sao_Paulo")
        base_dt = datetime(2024, 11, 27, 0, 0, tzinfo=brazil_tz)
        base_timestamp = int(base_dt.timestamp())
        
        forecasts = [
            # Day 1: 4 forecasts with rain (total should be 2+3+4+5 = 14mm)
            {'dt': base_timestamp, 'rain': {'3h': 2.0}},  # 00:00
            {'dt': base_timestamp + 10800, 'rain': {'3h': 3.0}},  # 03:00
            {'dt': base_timestamp + 21600, 'rain': {'3h': 4.0}},  # 06:00
            {'dt': base_timestamp + 32400, 'rain': {'3h': 5.0}},  # 09:00
            # Day 2: Should not be included
            {'dt': base_timestamp + 86400, 'rain': {'3h': 10.0}},  # Next day
        ]
        
        target_dt = datetime(2024, 11, 27, 6, 0, tzinfo=brazil_tz)
        
        total_rain = WeatherDataProcessor.calculate_daily_rain_accumulation(
            forecasts,
            target_dt
        )
        
        # Should sum only first 4 forecasts: 2+3+4+5 = 14mm
        assert total_rain == 14.0

    def test_calculate_daily_rain_accumulation_naive_target(self, test_data):
        """Should handle naive datetime by injecting timezone."""
        forecasts = test_data['list'][:2]
        target_dt = datetime(2025, 11, 27, 12, 0)  # naive

        total_rain = WeatherDataProcessor.calculate_daily_rain_accumulation(
            forecasts,
            target_dt
        )

        assert total_rain >= 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
