"""
Forecast Snapshot - normalized view of provider payloads
Centralizes field mapping so the rest of the codebase does not rely on raw JSON
structure from the weather providers (OpenWeather/Open-Meteo).
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Sequence, Union
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class ForecastSnapshot:
    """
    Normalized forecast representation used across the domain.
    All values are stored using consistent units and timezone-aware timestamps.
    """
    timestamp: datetime  # Always timezone-aware (UTC)
    temperature: float
    humidity: float
    wind_speed_kmh: float
    wind_direction: int
    rain_probability: float
    rain_volume_3h: float
    description: str
    feels_like: float
    pressure: float
    visibility: float
    clouds: float
    weather_code: int
    temp_min: float
    temp_max: float

    @property
    def rain_1h(self) -> float:
        """Approximate hourly rain derived from the 3h window provided by OpenWeather."""
        return self.rain_volume_3h / 3.0

    @classmethod
    def from_openweather(cls, payload: Dict[str, Any]) -> "ForecastSnapshot":
        """
        Build a snapshot from an OpenWeather forecast item.

        Args:
            payload: Single forecast object from the OpenWeather API response.

        Returns:
            ForecastSnapshot with normalized fields.
        """
        main = payload.get('main') or {}
        wind = payload.get('wind') or {}
        weather_list = payload.get('weather') or [{}]
        weather_block = weather_list[0] if weather_list else {}
        rain_block = payload.get('rain') or {}
        clouds_block = payload.get('clouds') or {}

        timestamp = ForecastSnapshot._parse_timestamp(payload.get('dt'))

        return cls(
            timestamp=timestamp,
            temperature=float(main.get('temp', 0.0)),
            humidity=float(main.get('humidity', 0.0)),
            wind_speed_kmh=float(wind.get('speed', 0.0)) * 3.6,  # m/s -> km/h
            wind_direction=int(wind.get('deg', 0) or 0),
            rain_probability=float(payload.get('pop', 0.0)) * 100.0,
            rain_volume_3h=float(rain_block.get('3h', 0.0) or 0.0),
            description=str(weather_block.get('description', "")),
            feels_like=float(main.get('feels_like', main.get('temp', 0.0) or 0.0)),
            pressure=float(main.get('pressure', 0.0)),
            visibility=float(payload.get('visibility', 0.0)),
            clouds=float(clouds_block.get('all', 0.0)),
            weather_code=int(weather_block.get('id', 0) or 0),
            temp_min=float(main.get('temp_min', main.get('temp', 0.0) or 0.0)),
            temp_max=float(main.get('temp_max', main.get('temp', 0.0) or 0.0))
        )

    @classmethod
    def from_openmeteo_hourly(
        cls,
        hourly_forecast: Any,
        visibility: float = 10000.0
    ) -> "ForecastSnapshot":
        """
        Build a snapshot from an Open-Meteo HourlyForecast entity.

        Args:
            hourly_forecast: HourlyForecast entity returned by the Open-Meteo adapter.
            visibility: Visibility value to carry over from OpenWeather (m).

        Returns:
            ForecastSnapshot with normalized fields.
        """
        timestamp = ForecastSnapshot._parse_iso_timestamp(hourly_forecast.timestamp)

        return cls(
            timestamp=timestamp,
            temperature=float(hourly_forecast.temperature),
            humidity=float(hourly_forecast.humidity),
            wind_speed_kmh=float(hourly_forecast.wind_speed),
            wind_direction=int(hourly_forecast.wind_direction),
            rain_probability=float(hourly_forecast.precipitation_probability),
            rain_volume_3h=float(hourly_forecast.precipitation) * 3.0,
            description=str(hourly_forecast.description),
            feels_like=float(hourly_forecast.temperature),
            pressure=0.0,
            visibility=float(visibility),
            clouds=float(hourly_forecast.cloud_cover),
            weather_code=int(hourly_forecast.weather_code),
            temp_min=float(hourly_forecast.temperature),
            temp_max=float(hourly_forecast.temperature)
        )

    @staticmethod
    def from_list(
        forecasts: Sequence[Union["ForecastSnapshot", Dict[str, Any]]]
    ) -> List["ForecastSnapshot"]:
        """
        Normalize a list of mixed forecast representations into ForecastSnapshots.
        """
        normalized: List[ForecastSnapshot] = []
        for forecast in forecasts or []:
            if isinstance(forecast, ForecastSnapshot):
                normalized.append(forecast)
            elif isinstance(forecast, dict):
                try:
                    normalized.append(ForecastSnapshot.from_openweather(forecast))
                except Exception:
                    # Skip malformed entries rather than failing the whole request
                    continue
        return normalized

    @staticmethod
    def _parse_timestamp(timestamp: Any) -> datetime:
        """Convert a unix timestamp to timezone-aware datetime in UTC."""
        try:
            return datetime.fromtimestamp(float(timestamp), tz=ZoneInfo("UTC"))
        except Exception:
            return datetime.now(tz=ZoneInfo("UTC"))

    @staticmethod
    def _parse_iso_timestamp(timestamp: str) -> datetime:
        """Parse ISO timestamp strings and normalize to UTC."""
        try:
            dt = datetime.fromisoformat(timestamp)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo("America/Sao_Paulo"))
            return dt.astimezone(ZoneInfo("UTC"))
        except Exception:
            return datetime.now(tz=ZoneInfo("UTC"))

