"""
Weather Alert Orchestrator - Orquestra geração de alertas de múltiplas fontes
Centraliza lógica de alertas que estava em Weather entity
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List

from domain.alerts.primitives import WeatherAlert
from domain.services.rain_alert_service import RainAlertService, RainAlertInput
from domain.services.wind_alert_service import WindAlertService, WindAlertInput
from domain.services.visibility_alert_service import VisibilityAlertService, VisibilityAlertInput
from domain.services.temperature_alert_service import TemperatureAlertService, TemperatureAlertInput


class WeatherAlertOrchestrator:
    """
    Orquestra a geração de alertas climáticos de múltiplos serviços
    
    Design Pattern: Facade
    - Simplifica acesso aos múltiplos alert services
    - Centraliza lógica de deduplicação
    - Desacopla entities de services
    """
    
    @staticmethod
    def generate_alerts(
        rain_prob: float,
        wind_speed: float,
        forecast_time: datetime,
        rain_1h: float = 0.0,
        rainfall_intensity: float = 0.0,
        temperature: float = 0.0,
        visibility: float = 10000
    ) -> List[WeatherAlert]:
        """
        Gera alertas climáticos baseado em múltiplos parâmetros
        
        Sistema proprietário: não depende de weather_code externo.
        Alertas gerados apenas via thresholds de métricas reais.
        
        Retorna apenas UM alerta por code, priorizando pelo timestamp mais próximo.
        
        Args:
            rain_prob: Probabilidade de chuva (0-100%)
            wind_speed: Velocidade do vento (km/h)
            forecast_time: Data/hora da previsão
            rain_1h: Volume de precipitação em mm/h (opcional)
            rainfall_intensity: Intensidade composta 0-100 (opcional)
            temperature: Temperatura em °C (opcional)
            visibility: Visibilidade em metros (opcional, padrão 10000m)
        
        Returns:
            Lista de alertas estruturados (array vazio se não houver alertas).
            Cada code aparece apenas uma vez, com prioridade para o timestamp mais próximo.
        """
        alerts = []
        
        # Converter para timezone Brasil para consistência
        brasil_tz = ZoneInfo("America/Sao_Paulo")
        if forecast_time.tzinfo is not None:
            alert_time = forecast_time.astimezone(brasil_tz)
        else:
            alert_time = forecast_time.replace(tzinfo=ZoneInfo("UTC")).astimezone(brasil_tz)

        # Alertas via serviços de domínio
        alerts.extend(RainAlertService.generate_alerts(RainAlertInput(
            weather_code=0,  # Não usado mais, apenas para compatibilidade
            rain_prob=rain_prob,
            rain_1h=rain_1h,
            rainfall_intensity=rainfall_intensity,
            forecast_time=alert_time
        )))
        alerts.extend(WindAlertService.generate_alerts(WindAlertInput(
            wind_speed=wind_speed,
            forecast_time=alert_time
        )))
        alerts.extend(VisibilityAlertService.generate_alerts(VisibilityAlertInput(
            visibility_m=visibility,
            forecast_time=alert_time
        )))
        alerts.extend(TemperatureAlertService.generate_alerts(TemperatureAlertInput(
            temperature_c=temperature,
            weather_code=0,  # Não usado mais, apenas para compatibilidade
            forecast_time=alert_time
        )))
        
        # Deduplica alertas: mantém apenas um alerta por code
        # Prioriza pelo timestamp mais próximo (menor timestamp = mais urgente)
        unique_alerts = {}
        for alert in alerts:
            if alert.code not in unique_alerts:
                unique_alerts[alert.code] = alert
            else:
                # Mantém o alerta com timestamp mais próximo (menor)
                if alert.timestamp < unique_alerts[alert.code].timestamp:
                    unique_alerts[alert.code] = alert
        
        return list(unique_alerts.values())
