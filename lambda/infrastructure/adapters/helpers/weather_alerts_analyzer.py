"""
Weather Alerts Analyzer - Centralized alert generation and analysis logic
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, List, Sequence
from aws_lambda_powertools import Logger

from domain.entities.forecast_snapshot import ForecastSnapshot
from domain.entities.weather import Weather, WeatherAlert, AlertSeverity
from infrastructure.adapters.helpers.date_filter_helper import DateFilterHelper
from domain.alerts.primitives import RAIN_INTENSITY_REFERENCE

logger = Logger(child=True)


class WeatherAlertsAnalyzer:
    """
    Analyzes weather forecast data and generates alerts
    Handles all alert-related logic in one place
    """
    
    @staticmethod
    def collect_all_alerts(
        forecasts: Sequence,
        target_datetime: Optional[datetime] = None
    ) -> List[WeatherAlert]:
        """
        Collect alerts from all future forecasts
        Removes duplicates by alert code
        
        Args:
            forecasts: List of forecast dictionaries
            target_datetime: Reference datetime (None = now UTC)
        
        Returns:
            List of unique weather alerts
        """
        normalized = ForecastSnapshot.from_list(forecasts)
        all_alerts = []
        seen_codes = set()
        
        # Get reference datetime
        reference_datetime = DateFilterHelper.get_reference_datetime(target_datetime, "UTC")
        
        # Filter future forecasts
        future_forecasts = DateFilterHelper.filter_future_forecasts(normalized, reference_datetime)
        
        # Generate basic alerts from each forecast
        for forecast_item in future_forecasts:
            alerts = Weather.get_weather_alert(
                weather_code=forecast_item.weather_code,
                rain_prob=forecast_item.rain_probability,
                wind_speed=forecast_item.wind_speed_kmh,
                forecast_time=forecast_item.timestamp,
                rain_1h=forecast_item.rain_1h,
                temperature=forecast_item.temperature,
                visibility=forecast_item.visibility
            )
            
            # Add only new alerts (by code)
            for alert in alerts:
                if alert.code not in seen_codes:
                    all_alerts.append(alert)
                    seen_codes.add(alert.code)
        
        # Add rain_ends_at to rain alerts
        WeatherAlertsAnalyzer._add_rain_end_times(all_alerts, future_forecasts)
        
        # Analyze temperature trends
        temp_trend_alerts = WeatherAlertsAnalyzer.analyze_temperature_trend(
            future_forecasts,
            reference_datetime
        )
        
        for alert in temp_trend_alerts:
            if alert.code not in seen_codes:
                all_alerts.append(alert)
                seen_codes.add(alert.code)
        
        return all_alerts
    
    @staticmethod
    def _add_rain_end_times(alerts: List[WeatherAlert], forecasts: List[dict]) -> None:
        """
        Add rain_ends_at field to rain alerts
        Mutates alerts in place
        
        Args:
            alerts: List of weather alerts
            forecasts: List of future forecasts
        """
        rain_alert_codes = {"DRIZZLE", "LIGHT_RAIN", "MODERATE_RAIN", "HEAVY_RAIN", "STORM", "STORM_RAIN"}
        
        for alert in alerts:
            if alert.code in rain_alert_codes and alert.details:
                rain_end_time = WeatherAlertsAnalyzer.find_rain_end_time(
                    forecasts,
                    alert.timestamp
                )
                if rain_end_time:
                    alert.details["rain_ends_at"] = rain_end_time.isoformat()
    
    @staticmethod
    def find_rain_end_time(
        forecasts: Sequence,
        alert_timestamp: datetime
    ) -> Optional[datetime]:
        """
        Find when rain is expected to stop
        
        Args:
            forecasts: List of future forecasts
            alert_timestamp: Timestamp of rain alert (UTC)
        
        Returns:
            End time of rain in Brazil timezone (or None if continuous rain)
        """
        brasil_tz = ZoneInfo("America/Sao_Paulo")
        normalized = ForecastSnapshot.from_list(forecasts)
        
        # Ensure alert_timestamp is in UTC
        if alert_timestamp.tzinfo is None:
            alert_timestamp = alert_timestamp.replace(tzinfo=ZoneInfo("UTC"))
        elif alert_timestamp.tzinfo != ZoneInfo("UTC"):
            alert_timestamp = alert_timestamp.astimezone(ZoneInfo("UTC"))
        
        # Filter forecasts >= alert timestamp
        future = sorted(
            [f for f in normalized if f.timestamp >= alert_timestamp],
            key=lambda f: f.timestamp
        )
        
        last_rain_time = None
        window_hours = WeatherAlertsAnalyzer._forecast_window_hours(future)
        
        for forecast in future:
            if WeatherAlertsAnalyzer._is_precipitating(forecast):
                last_rain_time = forecast.timestamp.astimezone(brasil_tz)
            elif last_rain_time:
                # First forecast after rain ends
                break
        
        # Add forecast window to last rain timestamp (end of forecast interval)
        if last_rain_time:
            last_rain_time = last_rain_time + timedelta(hours=window_hours)
        
        return last_rain_time
    
    @staticmethod
    def analyze_temperature_trend(
        forecasts: Sequence,
        reference_datetime: datetime
    ) -> List[WeatherAlert]:
        """
        Analyze temperature trends between all pairs of days
        Detects significant variations (>8°C) between max temps
        
        Args:
            forecasts: List of future forecasts
            reference_datetime: Reference datetime (UTC)
        
        Returns:
            List of temperature trend alerts (TEMP_DROP, TEMP_RISE)
        """
        normalized = ForecastSnapshot.from_list(forecasts)
        if not normalized:
            return []
        
        alerts = []
        brasil_tz = ZoneInfo("America/Sao_Paulo")
        
        # Group forecasts by day and calculate extremes
        daily_temps = WeatherAlertsAnalyzer._calculate_daily_extremes(normalized)
        
        if not daily_temps:
            return []
        
        # Analyze variations between all pairs of days
        sorted_dates = sorted(daily_temps.keys())
        
        # Track max drop and max rise to avoid duplicates
        max_drop = None
        max_rise = None
        
        for i in range(len(sorted_dates)):
            for j in range(i + 1, len(sorted_dates)):
                day1 = sorted_dates[i]
                day2 = sorted_dates[j]
                
                temp1_max = daily_temps[day1]['max']
                temp2_max = daily_temps[day2]['max']
                
                variation = temp2_max - temp1_max
                days_between = (day2 - day1).days
                
                # Detect significant variations (>8°C)
                if abs(variation) >= 8:
                    # Use first timestamp of day1 converted to Brazil timezone
                    alert_time_utc = daily_temps[day1]['first_timestamp']
                    alert_time = alert_time_utc.astimezone(brasil_tz)
                    
                    # If after conversion day changed, adjust to midnight of day1
                    if alert_time.date() != day1:
                        alert_time = datetime.combine(day1, datetime.min.time()).replace(tzinfo=brasil_tz)
                    
                    if variation < 0:
                        # Temperature drop - keep only the largest drop
                        if max_drop is None or abs(variation) > abs(max_drop['variation']):
                            max_drop = {
                                'variation': variation,
                                'alert': WeatherAlert(
                                    code="TEMP_DROP",
                                    severity=AlertSeverity.INFO,
                                    description=f"🌡️ Queda de temperatura ({abs(variation):.0f}°C em {days_between} {'dia' if days_between == 1 else 'dias'})",
                                    timestamp=alert_time,
                                    details={
                                        "day_1_date": day1.isoformat(),
                                        "day_1_max_c": round(temp1_max, 1),
                                        "day_2_date": day2.isoformat(),
                                        "day_2_max_c": round(temp2_max, 1),
                                        "variation_c": round(variation, 1),
                                        "days_between": days_between
                                    }
                                )
                            }
                    else:
                        # Temperature rise - keep only the largest rise
                        if max_rise is None or variation > max_rise['variation']:
                            max_rise = {
                                'variation': variation,
                                'alert': WeatherAlert(
                                    code="TEMP_RISE",
                                    severity=AlertSeverity.WARNING,
                                    description=f"🌡️ Aumento de temperatura (+{variation:.0f}°C em {days_between} {'dia' if days_between == 1 else 'dias'})",
                                    timestamp=alert_time,
                                    details={
                                        "day_1_date": day1.isoformat(),
                                        "day_1_max_c": round(temp1_max, 1),
                                        "day_2_date": day2.isoformat(),
                                        "day_2_max_c": round(temp2_max, 1),
                                        "variation_c": round(variation, 1),
                                        "days_between": days_between
                                    }
                                )
                            }
        
        # Add only the alerts with maximum variation
        if max_drop:
            alerts.append(max_drop['alert'])
        if max_rise:
            alerts.append(max_rise['alert'])
        
        return alerts
    
    @staticmethod
    def _calculate_daily_extremes(forecasts: Sequence) -> dict:
        """
        Calculate daily temperature extremes
        
        Args:
            forecasts: List of forecasts (raw dict or ForecastSnapshot)
        
        Returns:
            Dict with date as key and temp info as value
        """
        normalized = ForecastSnapshot.from_list(forecasts)
        daily_temps = {}
        
        for forecast in normalized:
            forecast_dt = forecast.timestamp
            date_key = forecast_dt.date()
            
            if date_key not in daily_temps:
                daily_temps[date_key] = {
                    'temps': [],
                    'max': float('-inf'),
                    'min': float('inf'),
                    'first_timestamp': forecast_dt
                }
            
            temp = forecast.temperature
            temp_max = forecast.temp_max
            temp_min = forecast.temp_min
            
            daily_temps[date_key]['temps'].extend([temp, temp_max, temp_min])
            daily_temps[date_key]['max'] = max(daily_temps[date_key]['max'], temp, temp_max, temp_min)
            daily_temps[date_key]['min'] = min(daily_temps[date_key]['min'], temp, temp_max, temp_min)
        
        return daily_temps

    @staticmethod
    def _rain_intensity_score(forecast: ForecastSnapshot) -> float:
        """
        Calculate composite rain intensity (0-100) using volume + probability.
        Mirrors Weather.rainfall_intensity but without requiring the entity.
        """
        if forecast.rain_volume_3h <= 0:
            return 0.0
        rain_1h = forecast.rain_volume_3h / 3.0
        composite = (rain_1h * forecast.rain_probability / 100.0) / RAIN_INTENSITY_REFERENCE * 100.0
        return max(0.0, min(100.0, composite))

    @staticmethod
    def _code_indicates_precipitation(weather_code: int) -> bool:
        """
        Identify precipitation codes for both OpenWeather and WMO (Open-Meteo).
        """
        # OpenWeather ranges: 2xx thunderstorm, 3xx drizzle, 5xx rain, 6xx snow
        if 200 <= weather_code < 700:
            return True
        # WMO ranges (Open-Meteo): drizzle 51-57, rain 61-67, showers 80-82, thunderstorm 95-99
        if 51 <= weather_code <= 57:
            return True
        if 61 <= weather_code <= 67:
            return True
        if 80 <= weather_code <= 82:
            return True
        if 95 <= weather_code <= 99:
            return True
        return False

    @staticmethod
    def _is_precipitating(forecast: ForecastSnapshot) -> bool:
        """
        Decide if a forecast represents ongoing precipitation using intensity and codes.
        """
        intensity = WeatherAlertsAnalyzer._rain_intensity_score(forecast)
        if intensity >= 1.0:
            return True
        if forecast.rain_volume_3h > 0 and forecast.rain_probability >= 40:
            return True
        return WeatherAlertsAnalyzer._code_indicates_precipitation(forecast.weather_code)

    @staticmethod
    def _forecast_window_hours(forecasts: List[ForecastSnapshot]) -> float:
        """
        Estimate forecast window (hours) based on the first two points.
        Defaults to 3h when not enough data.
        """
        if len(forecasts) < 2:
            return 3.0
        first, second = forecasts[0], forecasts[1]
        diff_hours = abs((second.timestamp - first.timestamp).total_seconds()) / 3600.0
        # Clamp to reasonable bounds (OpenWeather =3h, Open-Meteo hourly =1h)
        return max(1.0, min(3.0, diff_hours))
