"""
Service: Enriquecimento de previsões diárias com métricas horárias
"""
from collections import defaultdict
from typing import List

from domain.entities.daily_forecast import DailyForecast
from domain.entities.hourly_forecast import HourlyForecast


class DailyForecastEnricher:
    """
    Enriquecimento de DailyForecasts usando dados horários disponíveis
    """

    @staticmethod
    def apply_hourly_rainfall_intensity(
        daily_forecasts: List[DailyForecast],
        hourly_forecasts: List[HourlyForecast]
    ) -> List[DailyForecast]:
        """
        Propaga o maior rainfall_intensity horário para cada dia correspondente
        mantendo o valor diário original quando não houver dado horário.
        """
        if not daily_forecasts or not hourly_forecasts:
            return daily_forecasts

        intensity_by_date: dict[str, float] = defaultdict(float)

        for forecast in hourly_forecasts:
            # timestamp formato ISO: YYYY-MM-DDTHH:MM
            date_key = forecast.timestamp.split('T')[0] if forecast.timestamp else None
            if not date_key:
                continue

            try:
                intensity = float(forecast.rainfall_intensity)
            except (TypeError, ValueError):
                continue

            if intensity > intensity_by_date[date_key]:
                intensity_by_date[date_key] = intensity

        if not intensity_by_date:
            return daily_forecasts

        for daily in daily_forecasts:
            if daily.date not in intensity_by_date:
                continue

            enriched_intensity = max(
                float(daily.rainfall_intensity),
                intensity_by_date[daily.date]
            )
            daily.update_rainfall_intensity(enriched_intensity)

        return daily_forecasts
