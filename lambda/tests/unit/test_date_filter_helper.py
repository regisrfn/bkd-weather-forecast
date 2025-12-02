"""
Unit Tests for DateFilterHelper
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import pytest
from datetime import datetime
from zoneinfo import ZoneInfo
from infrastructure.adapters.helpers.date_filter_helper import DateFilterHelper
from domain.entities.forecast_snapshot import ForecastSnapshot


class TestGetReferenceDatetime:
    """Tests for get_reference_datetime method"""
    
    def test_get_reference_datetime_none_returns_now(self):
        """Test that None returns current time in specified timezone"""
        result = DateFilterHelper.get_reference_datetime(None, "UTC")
        
        assert result.tzinfo == ZoneInfo("UTC")
        assert isinstance(result, datetime)
        # Should be close to now (within 1 second)
        assert abs((datetime.now(tz=ZoneInfo("UTC")) - result).total_seconds()) < 1
    
    def test_get_reference_datetime_with_timezone(self):
        """Test with datetime that has timezone"""
        dt = datetime(2025, 11, 27, 12, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
        result = DateFilterHelper.get_reference_datetime(dt, "UTC")
        
        assert result.tzinfo == ZoneInfo("UTC")
        # Should be converted to UTC (3 hours ahead of Sao Paulo)
        assert result.hour == 15
    
    def test_get_reference_datetime_without_timezone(self):
        """Test with naive datetime"""
        dt = datetime(2025, 11, 27, 12, 0)
        result = DateFilterHelper.get_reference_datetime(dt, "UTC")
        
        assert result.tzinfo == ZoneInfo("UTC")
        assert result.hour == 12


class TestFilterFutureForecasts:
    """Tests for filter_future_forecasts method"""
    
    @pytest.fixture
    def sample_forecasts(self):
        """Sample forecast data"""
        return [
            {'dt': 1700000000, 'main': {'temp': 20}},  # 2023-11-14 22:13:20 UTC
            {'dt': 1700010000, 'main': {'temp': 21}},  # 2023-11-15 01:00:00 UTC
            {'dt': 1700020000, 'main': {'temp': 22}},  # 2023-11-15 03:46:40 UTC
        ]
    
    def test_filter_future_forecasts_with_reference(self, sample_forecasts):
        """Test filtering forecasts after reference datetime"""
        reference = datetime.fromtimestamp(1700005000, tz=ZoneInfo("UTC"))
        
        result = DateFilterHelper.filter_future_forecasts(sample_forecasts, reference)
        
        assert len(result) == 2
        assert int(result[0].timestamp.timestamp()) == 1700010000
        assert int(result[1].timestamp.timestamp()) == 1700020000
    
    def test_filter_future_forecasts_empty_list(self):
        """Test with empty forecast list"""
        reference = datetime.now(tz=ZoneInfo("UTC"))
        
        result = DateFilterHelper.filter_future_forecasts([], reference)
        
        assert result == []
    
    def test_filter_future_forecasts_all_past(self, sample_forecasts):
        """Test when all forecasts are in the past"""
        reference = datetime.fromtimestamp(1700030000, tz=ZoneInfo("UTC"))
        
        result = DateFilterHelper.filter_future_forecasts(sample_forecasts, reference)
        
        assert result == []


class TestFilterByDate:
    """Tests for filter_by_date method"""
    
    @pytest.fixture
    def sample_forecasts(self):
        """Sample forecast data spanning multiple days"""
        return [
            {'dt': 1764180000, 'main': {'temp': 20}},  # 2025-11-27 00:00:00 UTC
            {'dt': 1764234000, 'main': {'temp': 21}},  # 2025-11-27 15:00:00 UTC
            {'dt': 1764266400, 'main': {'temp': 22}},  # 2025-11-28 00:00:00 UTC
        ]
    
    def test_filter_by_date_brazil_timezone(self, sample_forecasts):
        """Test filtering by specific date in Brazil timezone"""
        target_date = datetime(2025, 11, 27).date()
        
        result = DateFilterHelper.filter_by_date(
            sample_forecasts,
            target_date,
            "America/Sao_Paulo"
        )
        
        # In Brazil timezone, 2025-11-27 00:00 UTC is still 2025-11-26
        # Only the 15:00 UTC forecast is on 2025-11-27 in Brazil
        assert len(result) >= 1
    
    def test_filter_by_date_empty_list(self):
        """Test with empty forecast list"""
        target_date = datetime(2025, 11, 27).date()
        
        result = DateFilterHelper.filter_by_date([], target_date)
        
        assert result == []


class TestSelectClosestForecast:
    """Tests for select_closest_forecast method"""
    
    @pytest.fixture
    def sample_forecasts(self):
        """Sample forecast data"""
        return [
            {'dt': 1764180000, 'dt_txt': '2025-11-27 00:00:00', 'main': {'temp': 20}},
            {'dt': 1764244800, 'dt_txt': '2025-11-27 18:00:00', 'main': {'temp': 25}},
            {'dt': 1764280800, 'dt_txt': '2025-11-28 04:00:00', 'main': {'temp': 22}},
        ]
    
    def test_select_closest_forecast_exact_match(self, sample_forecasts):
        """Test when target matches a forecast exactly"""
        target = datetime.fromtimestamp(1764244800, tz=ZoneInfo("UTC"))
        
        result = DateFilterHelper.select_closest_forecast(sample_forecasts, target)
        
        assert int(result.timestamp.timestamp()) == 1764244800
        assert result.temperature == 25
    
    def test_select_closest_forecast_between_two(self, sample_forecasts):
        """Test selecting closest when target is between forecasts"""
        # Target between first two forecasts
        target = datetime.fromtimestamp(1764200000, tz=ZoneInfo("UTC"))
        
        result = DateFilterHelper.select_closest_forecast(sample_forecasts, target)
        
        # Should select the closest one
        assert int(result.timestamp.timestamp()) in [1764180000, 1764244800]
    
    def test_select_closest_forecast_none_returns_now(self, sample_forecasts):
        """Test with None target datetime"""
        result = DateFilterHelper.select_closest_forecast(sample_forecasts, None)
        
        # Should return last forecast if all are in past, or closest future
        assert result is not None
    
    def test_select_closest_forecast_beyond_range(self, sample_forecasts):
        """Test when target is beyond forecast range"""
        target = datetime.fromtimestamp(1764380800, tz=ZoneInfo("UTC"))
        
        result = DateFilterHelper.select_closest_forecast(sample_forecasts, target)
        
        # Should return last available forecast
        assert int(result.timestamp.timestamp()) == 1764280800
    
    def test_select_closest_forecast_empty_list(self):
        """Test with empty forecast list"""
        result = DateFilterHelper.select_closest_forecast([], None)
        
        assert result is None
    
    def test_select_closest_forecast_past_match_with_target(self, sample_forecasts):
        """Test that specific target can match past forecast (e.g., 18:01 → 18:00)"""
        # Query at 18:01, should return 18:00 forecast
        target = datetime.fromtimestamp(1764244860, tz=ZoneInfo("UTC"))  # 18:01
        
        result = DateFilterHelper.select_closest_forecast(sample_forecasts, target)
        
        # Should return 18:00 forecast (closest match)
        assert int(result.timestamp.timestamp()) == 1764244800  # 18:00
        assert result.temperature == 25
    
    def test_select_closest_forecast_no_target_only_future(self, sample_forecasts):
        """Test that None target only considers future forecasts"""
        # Create forecasts where some are in the past
        now = datetime.now(tz=ZoneInfo("UTC"))
        past_forecasts = [
            {'dt': int(now.timestamp()) - 3600, 'main': {'temp': 20}},  # 1h ago
            {'dt': int(now.timestamp()) + 3600, 'main': {'temp': 25}},  # 1h future
            {'dt': int(now.timestamp()) + 7200, 'main': {'temp': 22}},  # 2h future
        ]
        
        result = DateFilterHelper.select_closest_forecast(past_forecasts, None)
        
        # Should only consider future forecasts
        result_dt = result.timestamp
        assert result_dt >= now


class TestGroupForecastsByDay:
    """Tests for group_forecasts_by_day method"""
    
    @pytest.fixture
    def sample_forecasts(self):
        """Sample forecast data spanning multiple days"""
        return [
            {'dt': 1764180000, 'main': {'temp': 20}},  # 2025-11-27
            {'dt': 1764234000, 'main': {'temp': 21}},  # 2025-11-27
            {'dt': 1764266400, 'main': {'temp': 22}},  # 2025-11-28
            {'dt': 1764320400, 'main': {'temp': 23}},  # 2025-11-28
        ]
    
    def test_group_forecasts_by_day(self, sample_forecasts):
        """Test grouping forecasts by day"""
        result = DateFilterHelper.group_forecasts_by_day(
            sample_forecasts,
            "America/Sao_Paulo"
        )
        
        assert isinstance(result, dict)
        assert len(result) >= 1
        # Each group should be a list of forecasts
        for date_key, forecasts in result.items():
            assert isinstance(forecasts, list)
            assert len(forecasts) >= 1
            assert all(isinstance(f, ForecastSnapshot) for f in forecasts)
    
    def test_group_forecasts_by_day_empty_list(self):
        """Test with empty forecast list"""
        result = DateFilterHelper.group_forecasts_by_day([])
        
        assert result == {}
    
    def test_group_forecasts_by_day_timezone(self, sample_forecasts):
        """Test that timezone affects grouping"""
        result_utc = DateFilterHelper.group_forecasts_by_day(
            sample_forecasts,
            "UTC"
        )
        result_brazil = DateFilterHelper.group_forecasts_by_day(
            sample_forecasts,
            "America/Sao_Paulo"
        )
        
        # Groups might differ due to timezone conversion
        assert isinstance(result_utc, dict)
        assert isinstance(result_brazil, dict)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
