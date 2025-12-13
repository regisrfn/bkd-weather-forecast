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
    def enrich_with_hourly_data(
        daily_forecasts: List[DailyForecast],
        hourly_forecasts: List[HourlyForecast]
    ) -> List[DailyForecast]:
        """
        Propaga dados horários para o daily:
        - rainfallIntensity máximo do dia
        - precipitationHours baseado em horas com rainfall_intensity > 1
          (usa o valor calculado das horas quando disponível, evitando inflar com estimativas diárias)
        """
        if not daily_forecasts or not hourly_forecasts:
            return daily_forecasts

        intensity_by_date: dict[str, float] = defaultdict(float)
        precip_hours_by_date: dict[str, float] = defaultdict(float)

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
            if intensity > 1:
                precip_hours_by_date[date_key] += 1.0

        if not intensity_by_date and not precip_hours_by_date:
            return daily_forecasts

        for daily in daily_forecasts:
            date = daily.date
            has_intensity = date in intensity_by_date
            has_precip_hours = date in precip_hours_by_date

            if has_precip_hours:
                computed_hours = precip_hours_by_date[date]
                # Preferir horas derivadas das horas quando > 0 (mais preciso que a estimativa diária)
                if computed_hours > 0:
                    daily.update_precipitation_hours(computed_hours)

            if has_intensity:
                enriched_intensity = max(
                    float(daily.rainfall_intensity),
                    intensity_by_date[date]
                )
                daily.update_rainfall_intensity(enriched_intensity)

        return daily_forecasts
