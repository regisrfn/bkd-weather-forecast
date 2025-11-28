"""
Date Filter Helper - Centralized date filtering and selection logic
Eliminates code duplication in weather repository
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, List
from aws_lambda_powertools import Logger

logger = Logger(child=True)


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
        forecasts: List[dict],
        reference_datetime: datetime
    ) -> List[dict]:
        """
        Filter forecasts to only include future ones
        
        Args:
            forecasts: List of forecast dictionaries
            reference_datetime: Reference datetime (must have timezone)
        
        Returns:
            List of future forecasts
        """
        if not forecasts:
            return []
        
        return [
            f for f in forecasts
            if datetime.fromtimestamp(f['dt'], tz=ZoneInfo("UTC")) >= reference_datetime
        ]
    
    @staticmethod
    def filter_by_date(
        forecasts: List[dict],
        target_date,
        timezone: str = "America/Sao_Paulo"
    ) -> List[dict]:
        """
        Filter forecasts by a specific date
        
        Args:
            forecasts: List of forecast dictionaries
            target_date: Target date (date object)
            timezone: Timezone to use for date comparison
        
        Returns:
            List of forecasts for the target date
        """
        if not forecasts:
            return []
        
        tz = ZoneInfo(timezone)
        
        return [
            f for f in forecasts
            if datetime.fromtimestamp(f['dt'], tz=ZoneInfo("UTC")).astimezone(tz).date() == target_date
        ]
    
    @staticmethod
    def select_closest_forecast(
        forecasts: List[dict],
        target_datetime: Optional[datetime] = None
    ) -> Optional[dict]:
        """
        Select the forecast closest to the target datetime
        Returns last available forecast if target is beyond forecast range
        
        Args:
            forecasts: List of forecast dictionaries
            target_datetime: Target datetime (None = now)
        
        Returns:
            Selected forecast or None if list is empty
        """
        if not forecasts:
            return None
        
        reference_datetime = DateFilterHelper.get_reference_datetime(target_datetime, "UTC")
        
        # Filter future forecasts
        future_forecasts = DateFilterHelper.filter_future_forecasts(forecasts, reference_datetime)
        
        if not future_forecasts:
            # No future forecasts - return last available (day 5)
            last_forecast = forecasts[-1]
            last_forecast_dt = datetime.fromtimestamp(last_forecast['dt'], tz=ZoneInfo("UTC"))
            logger.info(
                "Returning last available forecast",
                last_forecast_dt=last_forecast_dt.isoformat(),
                requested_dt=reference_datetime.isoformat(),
                reason="Requested date beyond forecast limit (5 days)"
            )
            return last_forecast
        
        # Find closest forecast
        closest_forecast = min(
            future_forecasts,
            key=lambda f: abs(
                datetime.fromtimestamp(f['dt'], tz=ZoneInfo("UTC")) - reference_datetime
            ).total_seconds()
        )
        
        return closest_forecast
    
    @staticmethod
    def group_forecasts_by_day(
        forecasts: List[dict],
        timezone: str = "America/Sao_Paulo"
    ) -> dict:
        """
        Group forecasts by date
        
        Args:
            forecasts: List of forecast dictionaries
            timezone: Timezone for date grouping
        
        Returns:
            Dict with date as key and forecast list as value
        """
        if not forecasts:
            return {}
        
        tz = ZoneInfo(timezone)
        grouped = {}
        
        for forecast in forecasts:
            forecast_dt = datetime.fromtimestamp(forecast['dt'], tz=ZoneInfo("UTC"))
            date_key = forecast_dt.astimezone(tz).date()
            
            if date_key not in grouped:
                grouped[date_key] = []
            
            grouped[date_key].append(forecast)
        
        return grouped
