"""
Weather Data Processor - Centralized weather data processing logic
Handles parsing and calculation of weather metrics
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, List, Dict, Any, Tuple

from domain.entities.weather import Weather
from domain.entities.forecast_snapshot import ForecastSnapshot
from infrastructure.adapters.helpers.date_filter_helper import DateFilterHelper
from infrastructure.adapters.helpers.weather_alerts_analyzer import WeatherAlertsAnalyzer


class WeatherDataProcessor:
    """
    Processes raw weather API data into Weather entities
    Handles all data transformation and calculation logic
    """
    
    @staticmethod
    def process_weather_data(
        data: Dict[str, Any],
        city_name: str,
        target_datetime: Optional[datetime] = None
    ) -> Weather:
        """
        Process raw weather API data into Weather entity
        
        Args:
            data: Raw data from OpenWeatherMap API
            city_name: City name
            target_datetime: Target datetime for forecast selection
        
        Returns:
            Weather entity
        
        Raises:
            ValueError: If no future forecasts available
        """
        forecasts = ForecastSnapshot.from_list(data.get('list', []))
        if not forecasts:
            raise ValueError("Nenhuma previsão futura disponível")
        
        # Select forecast
        forecast_item = DateFilterHelper.select_closest_forecast(
            forecasts,
            target_datetime
        )
        
        if not forecast_item:
            raise ValueError("Nenhuma previsão futura disponível")
        
        # Generate alerts from all future forecasts
        weather_alerts = WeatherAlertsAnalyzer.collect_all_alerts(
            forecasts,
            target_datetime
        )
        
        # Calculate daily temperature extremes
        temp_min_day, temp_max_day = WeatherDataProcessor.get_daily_temp_extremes(
            forecasts,
            target_datetime
        )
        
        # Calculate daily rain accumulation
        daily_rain_accumulation = WeatherDataProcessor.calculate_daily_rain_accumulation(
            forecasts,
            target_datetime
        )
        
        # Create Weather entity
        return Weather(
            city_id='',  # Filled by use case
            city_name=city_name,
            timestamp=forecast_item.timestamp,
            temperature=forecast_item.temperature,
            humidity=forecast_item.humidity,
            wind_speed=forecast_item.wind_speed_kmh,
            wind_direction=forecast_item.wind_direction,
            rain_probability=forecast_item.rain_probability,
            rain_1h=forecast_item.rain_1h,
            rain_accumulated_day=daily_rain_accumulation,
            description=forecast_item.description,
            feels_like=forecast_item.feels_like,
            pressure=forecast_item.pressure,
            visibility=forecast_item.visibility,
            clouds=forecast_item.clouds,
            weather_alert=weather_alerts,
            weather_code=forecast_item.weather_code,
            temp_min=temp_min_day,
            temp_max=temp_max_day
        )
    
    @staticmethod
    def get_daily_temp_extremes(
        forecasts: List[Any],
        target_datetime: Optional[datetime]
    ) -> Tuple[float, float]:
        """
        Calculate min/max temperatures for the ENTIRE target day
        
        Important: Returns min/max for the whole day, regardless of query time.
        Example: If querying at 18:00, still includes forecasts from 00:00-18:00
        to get accurate daily extremes.
        
        Args:
            forecasts: List of forecasts (raw dict or ForecastSnapshot)
            target_datetime: Target date (None = today)
        
        Returns:
            Tuple (temp_min, temp_max) for the entire day
        """
        normalized = ForecastSnapshot.from_list(forecasts)
        if not normalized:
            return (0.0, 0.0)
        
        # Get target date
        reference_datetime = DateFilterHelper.get_reference_datetime(target_datetime, "UTC")
        target_date = reference_datetime.date()
        
        # Filter forecasts for target day (ALL forecasts for the day, not just future)
        # This ensures we get the true daily min/max regardless of query time
        day_forecasts = [
            f for f in normalized
            if f.timestamp.date() == target_date
        ]
        
        if not day_forecasts:
            # Fallback: first forecast available
            first_forecast = normalized[0]
            return (first_forecast.temp_min, first_forecast.temp_max)
        
        # Extract all temperatures from the day
        temps = []
        for f in day_forecasts:
            temps.append(f.temperature)
            temps.append(f.temp_min)
            temps.append(f.temp_max)
        
        return (min(temps), max(temps))
    
    @staticmethod
    def calculate_daily_rain_accumulation(
        forecasts: List[Any],
        target_datetime: Optional[datetime]
    ) -> float:
        """
        Calculate total expected rain accumulation for the target day
        
        Args:
            forecasts: List of forecasts from API (raw dict or ForecastSnapshot)
            target_datetime: Reference datetime (None = today in Brazil timezone)
        
        Returns:
            Total expected rain accumulation for the day (mm)
        """
        normalized = ForecastSnapshot.from_list(forecasts)
        if not normalized:
            return 0.0
        
        # Get reference datetime in Brazil timezone for date comparison
        if target_datetime is None:
            reference_datetime = datetime.now(tz=ZoneInfo("America/Sao_Paulo"))
        elif target_datetime.tzinfo is not None:
            reference_datetime = target_datetime.astimezone(ZoneInfo("America/Sao_Paulo"))
        else:
            reference_datetime = target_datetime.replace(tzinfo=ZoneInfo("America/Sao_Paulo"))
        
        target_date = reference_datetime.date()
        
        # Filter forecasts for target day in Brazil timezone
        day_forecasts = [
            f for f in normalized
            if f.timestamp.astimezone(ZoneInfo("America/Sao_Paulo")).date() == target_date
        ]
        
        if not day_forecasts:
            return 0.0
        
        # Sum all rain values for the day
        total_rain = 0.0
        for forecast in day_forecasts:
            total_rain += forecast.rain_volume_3h
        
        return total_rain
