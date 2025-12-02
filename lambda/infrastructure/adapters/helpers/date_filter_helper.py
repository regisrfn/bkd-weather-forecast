"""
Date Filter Helper - Centralized date filtering and selection logic
Eliminates code duplication in weather repository
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, List, Sequence

from domain.entities.forecast_snapshot import ForecastSnapshot


class DateFilterHelper:
    """
    Helper class to handle all date filtering operations
    Eliminates repetitive date filtering logic across repository methods
    """
    
    @staticmethod
    def get_reference_datetime(
        target_datetime: Optional[datetime] = None,
        timezone: str = "UTC"
    ) -> datetime:
        """
        Get reference datetime for filtering (either target or current time)
        Ensures datetime has proper timezone
        
        Args:
            target_datetime: Optional target datetime
            timezone: Timezone to use (default: UTC)
        
        Returns:
            Reference datetime with timezone
        """
        tz = ZoneInfo(timezone)
        
        if target_datetime is None:
            return datetime.now(tz=tz)
        elif target_datetime.tzinfo is not None:
            return target_datetime.astimezone(tz)
        else:
            return target_datetime.replace(tzinfo=tz)
    
    @staticmethod
    def filter_future_forecasts(
        forecasts: Sequence,
        reference_datetime: datetime
    ) -> List[ForecastSnapshot]:
        """
        Filter forecasts to only include future ones
        
        Args:
            forecasts: List of forecasts (raw dict or ForecastSnapshot)
            reference_datetime: Reference datetime (must have timezone)
        
        Returns:
            List of future forecasts
        """
        normalized = ForecastSnapshot.from_list(forecasts)
        if not normalized:
            return []
        
        return [
            f for f in normalized
            if f.timestamp >= reference_datetime
        ]
    
    @staticmethod
    def filter_by_date(
        forecasts: Sequence,
        target_date,
        timezone: str = "America/Sao_Paulo"
    ) -> List[ForecastSnapshot]:
        """
        Filter forecasts by a specific date
        
        Args:
            forecasts: List of forecasts (raw dict or ForecastSnapshot)
            target_date: Target date (date object)
            timezone: Timezone to use for date comparison
        
        Returns:
            List of forecasts for the target date
        """
        normalized = ForecastSnapshot.from_list(forecasts)
        if not normalized:
            return []
        
        tz = ZoneInfo(timezone)
        
        return [
            f for f in normalized
            if f.timestamp.astimezone(tz).date() == target_date
        ]
    
    @staticmethod
    def select_closest_forecast(
        forecasts: Sequence,
        target_datetime: Optional[datetime] = None
    ) -> Optional[ForecastSnapshot]:
        """
        Select the forecast closest to the target datetime
        Returns last available forecast if target is beyond forecast range
        
        Behavior:
        - If target_datetime is None (current time): Only future forecasts
        - If target_datetime is specified: Find closest forecast (can be slightly past)
          Example: Query 18:01 returns 18:00 forecast if available
        
        Args:
            forecasts: List of forecasts (raw dict or ForecastSnapshot)
            target_datetime: Target datetime (None = now, future only)
        
        Returns:
            Selected forecast or None if list is empty
        """
        normalized = ForecastSnapshot.from_list(forecasts)
        if not normalized:
            return None
        
        reference_datetime = DateFilterHelper.get_reference_datetime(target_datetime, "UTC")
        
        # If no specific target was provided (using current time), only consider future
        if target_datetime is None:
            future_forecasts = DateFilterHelper.filter_future_forecasts(normalized, reference_datetime)
            
            if not future_forecasts:
                # No future forecasts - return last available (day 5)
                return normalized[-1]
            
            # Find closest future forecast
            closest_forecast = min(
                future_forecasts,
                key=lambda f: abs(
                    f.timestamp - reference_datetime
                ).total_seconds()
            )
        else:
            # Specific target provided - find closest forecast (can be past)
            closest_forecast = min(
                normalized,
                key=lambda f: abs(
                    f.timestamp - reference_datetime
                ).total_seconds()
            )
        
        return closest_forecast
    
    @staticmethod
    def group_forecasts_by_day(
        forecasts: Sequence,
        timezone: str = "America/Sao_Paulo"
    ) -> dict:
        """
        Group forecasts by date
        
        Args:
            forecasts: List of forecasts (raw dict or ForecastSnapshot)
            timezone: Timezone for date grouping
        
        Returns:
            Dict with date as key and forecast list as value
        """
        normalized = ForecastSnapshot.from_list(forecasts)
        if not normalized:
            return {}
        
        tz = ZoneInfo(timezone)
        grouped = {}
        
        for forecast in normalized:
            date_key = forecast.timestamp.astimezone(tz).date()
            
            if date_key not in grouped:
                grouped[date_key] = []
            
            grouped[date_key].append(forecast)
        
        return grouped
