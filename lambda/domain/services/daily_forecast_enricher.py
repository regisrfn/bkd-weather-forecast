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
        clouds_sum_count: dict[str, tuple[float, int]] = defaultdict(lambda: (0.0, 0))
        visibility_min: dict[str, float] = {}

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

            # Cobertura de nuvens média
            if forecast.cloud_cover is not None:
                current_sum, current_count = clouds_sum_count[date_key]
                clouds_sum_count[date_key] = (current_sum + float(forecast.cloud_cover), current_count + 1)

            # Menor visibilidade do dia (pior caso)
            if forecast.visibility is not None:
                current_min = visibility_min.get(date_key)
                visibility_value = float(forecast.visibility)
                if current_min is None or visibility_value < current_min:
                    visibility_min[date_key] = visibility_value

        has_weather_signals = bool(intensity_by_date) or bool(precip_hours_by_date) or bool(clouds_sum_count) or bool(visibility_min)
        if not has_weather_signals:
            return daily_forecasts

        for daily in daily_forecasts:
            date = daily.date
            has_intensity = date in intensity_by_date
            has_precip_hours = date in precip_hours_by_date
            has_clouds = date in clouds_sum_count and clouds_sum_count[date][1] > 0
            has_visibility = date in visibility_min

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

            if has_clouds or has_visibility:
                avg_clouds = None
                if has_clouds:
                    clouds_total, clouds_count = clouds_sum_count[date]
                    avg_clouds = clouds_total / clouds_count if clouds_count > 0 else None
                vis_value = visibility_min.get(date)
                daily.update_clouds_visibility(avg_clouds, vis_value)

        return daily_forecasts
