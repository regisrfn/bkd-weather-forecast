"""
Weather Data Processor - Centralized weather data processing logic
Handles parsing and calculation of weather metrics
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, List, Dict, Any, Tuple

from domain.entities.weather import Weather
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
        # Select forecast
        forecast_item = DateFilterHelper.select_closest_forecast(
            data['list'],
            target_datetime
        )
        
        if not forecast_item:
            raise ValueError("Nenhuma previsão futura disponível")
        
        # Extract forecast data
        weather_code = forecast_item['weather'][0]['id']
        rain_prob = forecast_item.get('pop', 0) * 100
        wind_speed = forecast_item['wind']['speed'] * 3.6
        forecast_time = datetime.fromtimestamp(forecast_item['dt'], tz=ZoneInfo("UTC"))
        
        # Generate alerts from all future forecasts
        weather_alerts = WeatherAlertsAnalyzer.collect_all_alerts(
            data['list'],
            target_datetime
        )
        
        # Calculate daily temperature extremes
        temp_min_day, temp_max_day = WeatherDataProcessor.get_daily_temp_extremes(
            data['list'],
            target_datetime
        )
        
        # Calculate daily rain accumulation
        daily_rain_accumulation = WeatherDataProcessor.calculate_daily_rain_accumulation(
            data['list'],
            target_datetime
        )
        
        # Create Weather entity
        return Weather(
            city_id='',  # Filled by use case
            city_name=city_name,
            timestamp=forecast_time,
            temperature=forecast_item['main']['temp'],
            humidity=forecast_item['main']['humidity'],
            wind_speed=wind_speed,
            rain_probability=rain_prob,
            rain_1h=forecast_item.get('rain', {}).get('3h', 0) / 3,
            rain_accumulated_day=daily_rain_accumulation,
            description=forecast_item['weather'][0].get('description', ''),
            feels_like=forecast_item['main'].get('feels_like', 0),
            pressure=forecast_item['main'].get('pressure', 0),
            visibility=forecast_item.get('visibility', 0),
            clouds=forecast_item.get('clouds', {}).get('all', 0),
            weather_alert=weather_alerts,
            weather_code=weather_code,
            temp_min=temp_min_day,
            temp_max=temp_max_day
        )
    
    @staticmethod
    def get_daily_temp_extremes(
        forecasts: List[dict],
        target_datetime: Optional[datetime]
    ) -> Tuple[float, float]:
        """
        Calculate min/max temperatures for the ENTIRE target day
        
        Important: Returns min/max for the whole day, regardless of query time.
        Example: If querying at 18:00, still includes forecasts from 00:00-18:00
        to get accurate daily extremes.
        
        Args:
            forecasts: List of forecasts
            target_datetime: Target date (None = today)
        
        Returns:
            Tuple (temp_min, temp_max) for the entire day
        """
        if not forecasts:
            return (0.0, 0.0)
        
        # Get target date
        reference_datetime = DateFilterHelper.get_reference_datetime(target_datetime, "UTC")
        target_date = reference_datetime.date()
        
        # Filter forecasts for target day (ALL forecasts for the day, not just future)
        # This ensures we get the true daily min/max regardless of query time
        day_forecasts = [
            f for f in forecasts
            if datetime.fromtimestamp(f['dt'], tz=ZoneInfo("UTC")).date() == target_date
        ]
        
        if not day_forecasts:
            # Fallback: first forecast available
            return (forecasts[0]['main']['temp_min'], forecasts[0]['main']['temp_max'])
        
        # Extract all temperatures from the day
        temps = []
        for f in day_forecasts:
            temps.append(f['main']['temp'])
            temps.append(f['main']['temp_min'])
            temps.append(f['main']['temp_max'])
        
        return (min(temps), max(temps))
    
    @staticmethod
    def calculate_daily_rain_accumulation(
        forecasts: List[dict],
        target_datetime: Optional[datetime]
    ) -> float:
        """
        Calculate total expected rain accumulation for the target day
        
        Args:
            forecasts: List of forecasts from API
            target_datetime: Reference datetime (None = today in Brazil timezone)
        
        Returns:
            Total expected rain accumulation for the day (mm)
        """
        if not forecasts:
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
        day_forecasts = DateFilterHelper.filter_by_date(
            forecasts,
            target_date,
            "America/Sao_Paulo"
        )
        
        if not day_forecasts:
            return 0.0
        
        # Sum all rain.3h values for the day
        total_rain = 0.0
        for forecast in day_forecasts:
            rain_3h = forecast.get('rain', {}).get('3h', 0)
            total_rain += rain_3h
        
        return total_rain
