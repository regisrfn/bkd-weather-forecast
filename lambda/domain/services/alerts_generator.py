"""
Alerts Generator - Geração otimizada de alertas climáticos
Substituindo loops aninhados por algoritmos single-pass
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, List, Dict, Protocol
from collections import defaultdict

from domain.alerts.primitives import WeatherAlert, AlertSeverity
from domain.constants import Weather as WeatherConstants, App
from domain.services.weather_alert_orchestrator import WeatherAlertOrchestrator
from shared.config.logger_config import get_logger

logger = get_logger(child=True)


class ForecastLike(Protocol):
    """
    Protocol (interface) para forecasts compatíveis com geração de alertas
    Qualquer classe com esses campos pode ser usada (HourlyForecast, DailyForecast, etc)
    """
    timestamp: datetime | str
    temperature: float
    wind_speed: float
    wind_direction: int
    rain_probability: float | int
    precipitation: float
    rainfall_intensity: float  # Intensidade composta 0-100
    weather_code: int


class AlertsGenerator:
    """
    Gerador de alertas climáticos otimizado
    
    OTIMIZAÇÕES:
    - Single-pass através de forecasts (O(n) ao invés de O(n²))
    - Deduplicação com set ao invés de lista
    - Sliding window para trends de temperatura
    - Cálculo incremental de extremos diários
    """
    
    @staticmethod
    async def generate_alerts_for_weather(
        weather_provider,
        latitude: float,
        longitude: float,
        city_id: str,
        target_datetime: Optional[datetime] = None,
        days_limit: int = 7
    ) -> List[WeatherAlert]:
        """
        Gera alertas combinando hourly (48h) + daily (5 dias) forecasts
        Método auxiliar para evitar duplicação nos use cases
        
        Args:
            weather_provider: Provider para buscar dados meteorológicos
            latitude: Latitude da cidade
            longitude: Longitude da cidade
            city_id: ID da cidade
            target_datetime: Data/hora de referência (padrão: agora)
            days_limit: Número de dias para análise (padrão: 7)
        
        Returns:
            Lista de alertas dos próximos N dias
        """
        try:
            # Buscar hourly forecasts (48h = 2 dias, granularidade horária)
            hourly_forecasts = await weather_provider.get_hourly_forecast(
                latitude=latitude,
                longitude=longitude,
                city_id=city_id,
                hours=48
            )
            
            # Buscar daily forecasts (7 dias, para cobrir dias 3-7)
            daily_forecasts = await weather_provider.get_daily_forecast(
                latitude=latitude,
                longitude=longitude,
                city_id=city_id,
                days=7
            )
            
            # Combinar: hourly (dias 1-2) + daily (dias 3-7)
            combined_forecasts = list(hourly_forecasts) if hourly_forecasts else []
            
            if daily_forecasts and len(daily_forecasts) > 2:
                # Adicionar daily dos dias 3-7 (índices 2-6)
                combined_forecasts.extend(daily_forecasts[2:days_limit])
            
            # Gerar alertas com os forecasts combinados
            alerts = AlertsGenerator.generate_alerts_next_days(
                forecasts=combined_forecasts,
                target_datetime=target_datetime,
                days_limit=days_limit
            )
            
            return alerts
            
        except Exception as e:
            logger.warning(f"Failed to generate alerts: {e}")
            return []
    
    @staticmethod
    def generate_alerts_next_days(
        forecasts: List[ForecastLike],
        target_datetime: Optional[datetime] = None,
        days_limit: int = 7
    ) -> List[WeatherAlert]:
        """
        Gera alertas analisando os próximos N dias a partir de uma data de referência
        Usado para alertas em tempo real (não históricos)
        
        Args:
            forecasts: Lista de forecasts (qualquer horário)
            target_datetime: Data de referência (padrão: datetime.now())
            days_limit: Número de dias para analisar (padrão: 7)
        
        Returns:
            Lista de alertas únicos dos próximos N dias
        """
        if not forecasts:
            return []
        
        brasil_tz = ZoneInfo(App.TIMEZONE)
        
        # Normalizar target_datetime
        if target_datetime is None:
            now = datetime.now(tz=brasil_tz)
        elif target_datetime.tzinfo is None:
            now = target_datetime.replace(tzinfo=brasil_tz)
        else:
            now = target_datetime.astimezone(brasil_tz)
        
        future_limit = now + timedelta(days=days_limit)
        
        # Filtrar apenas próximos N dias
        next_days_forecasts = []
        for f in forecasts:
            ts = AlertsGenerator._parse_timestamp(f)
            if now <= ts <= future_limit:
                next_days_forecasts.append((f, ts))
        
        if not next_days_forecasts:
            return []
        
        # Ordenar por timestamp
        next_days_forecasts.sort(key=lambda x: x[1])
        
        # Deduplicação por código
        alerts_by_code: Dict[str, WeatherAlert] = {}
        
        # Acumular extremos diários para análise de temperatura
        daily_extremes: Dict[datetime, Dict] = defaultdict(lambda: {
            'temps': [],
            'first_forecast': None
        })
        
        for forecast, timestamp in next_days_forecasts:
            # Normalizar campos (DailyForecast vs HourlyForecast)
            rain_prob = float(getattr(forecast, 'rain_probability', 0) or getattr(forecast, 'precipitation_probability', 0))
            wind_speed = float(getattr(forecast, 'wind_speed', 0) or getattr(forecast, 'wind_speed_max', 0) or getattr(forecast, 'wind_speed_kmh', 0))
            precipitation = float(getattr(forecast, 'precipitation', 0) or getattr(forecast, 'precipitation_mm', 0))
            rain_1h = precipitation
            
            # Temperature: HourlyForecast tem 'temperature', DailyForecast tem 'temp_min' e 'temp_max'
            if hasattr(forecast, 'temperature'):
                temperature = float(forecast.temperature)
            else:
                # Para DailyForecast, usar média
                temp_min = float(getattr(forecast, 'temp_min', 20.0))
                temp_max = float(getattr(forecast, 'temp_max', 30.0))
                temperature = (temp_min + temp_max) / 2.0
            
            visibility = float(getattr(forecast, 'visibility', 10000))
            uv_index = float(getattr(forecast, 'uv_index', 0))
            
            # Gerar alertas básicos
            basic_alerts = WeatherAlertOrchestrator.generate_alerts(
                rain_prob=rain_prob,
                wind_speed=wind_speed,
                forecast_time=timestamp,
                rain_1h=rain_1h,
                rainfall_intensity=getattr(forecast, 'rainfall_intensity', 0.0),
                temperature=temperature,
                visibility=visibility
            )
            
            # Alertas específicos para previsões diárias (quando disponível)
            # 1. HEAVY_RAIN_DAY - Chuva acumulada alta no dia
            if precipitation > 0 and rain_prob > 60:
                # Usar rainfall_intensity já calculado pela entidade
                rainfall_intensity = getattr(forecast, 'rainfall_intensity', 0.0)
                
                if rainfall_intensity >= 25 and precipitation > 20:
                    severity = AlertSeverity.WARNING if precipitation < 50 else AlertSeverity.ALERT
                    basic_alerts.append(WeatherAlert(
                        code="HEAVY_RAIN_DAY",
                        severity=severity,
                        description=f"🌧️ Chuva forte prevista ({precipitation:.0f}mm acumulados)",
                        timestamp=timestamp,
                        details={
                            "date": timestamp.date().isoformat(),
                            "precipitation_mm": round(precipitation, 1),
                            "rain_probability": round(rain_prob, 0),
                            "intensity": round(rainfall_intensity, 1)
                        }
                    ))
            
            # 2. STRONG_WIND_DAY - Vento forte sustentado
            if wind_speed > WeatherConstants.WIND_SPEED_WARNING:
                if wind_speed >= WeatherConstants.WIND_SPEED_DANGER:
                    severity = AlertSeverity.ALERT
                    description = f"💨 Ventos muito fortes previstos ({wind_speed:.0f} km/h)"
                else:
                    severity = AlertSeverity.WARNING
                    description = f"💨 Ventos fortes previstos ({wind_speed:.0f} km/h)"
                
                basic_alerts.append(WeatherAlert(
                    code="STRONG_WIND_DAY",
                    severity=severity,
                    description=description,
                    timestamp=timestamp,
                    details={
                        "date": timestamp.date().isoformat(),
                        "wind_speed_kmh": round(wind_speed, 1)
                    }
                ))
            
            # 3. EXTREME_UV - Índice UV extremo
            if uv_index >= 11:
                basic_alerts.append(WeatherAlert(
                    code="EXTREME_UV",
                    severity=AlertSeverity.WARNING,
                    description=f"☀️ Índice UV extremo ({uv_index:.0f})",
                    timestamp=timestamp,
                    details={
                        "date": timestamp.date().isoformat(),
                        "uv_index": round(uv_index, 1)
                    }
                ))
            
            # Deduplicar mantendo timestamp mais próximo
            for alert in basic_alerts:
                if alert.code not in alerts_by_code:
                    alerts_by_code[alert.code] = alert
                elif alert.timestamp < alerts_by_code[alert.code].timestamp:
                    alerts_by_code[alert.code] = alert
            
            # Acumular extremos diários para trends de temperatura
            date_key = timestamp.astimezone(brasil_tz).date()
            daily = daily_extremes[date_key]
            daily['temps'].append(temperature)
            # Usar temp_max/temp_min se disponível (para daily forecasts)
            temp_max = getattr(forecast, 'temp_max', temperature)
            temp_min = getattr(forecast, 'temp_min', temperature)
            if temp_max != temperature or temp_min != temperature:
                daily['temps'].extend([temp_max, temp_min])
            if daily['first_forecast'] is None:
                daily['first_forecast'] = (forecast, timestamp)
        
        # Adicionar rain_ends_at
        AlertsGenerator._add_rain_end_times(
            list(alerts_by_code.values()),
            [f for f, _ in next_days_forecasts]
        )
        
        # Analisar trends de temperatura (TEMP_DROP e TEMP_RISE)
        temp_alerts = AlertsGenerator._analyze_temperature_trends_optimized(
            daily_extremes,
            brasil_tz
        )
        
        # Adicionar alertas de temperatura (sem duplicatas)
        for alert in temp_alerts:
            if alert.code not in alerts_by_code:
                alerts_by_code[alert.code] = alert
        
        return list(alerts_by_code.values())
    
    @staticmethod
    def generate_all_alerts(
        forecasts: List[ForecastLike],
        target_datetime: Optional[datetime] = None
    ) -> List[WeatherAlert]:
        """
        Gera todos os alertas de uma só vez
        OTIMIZADO: Single-pass através dos forecasts
        
        Args:
            forecasts: Lista de ForecastSnapshot
            target_datetime: Datetime de referência
        
        Returns:
            Lista de alertas únicos (deduplicated)
        """
        if not forecasts:
            return []
        
        # Datetime de referência
        brasil_tz = ZoneInfo(App.TIMEZONE)
        if target_datetime is None:
            ref_dt = datetime.now(tz=brasil_tz)
        elif target_datetime.tzinfo is not None:
            ref_dt = target_datetime.astimezone(brasil_tz)
        else:
            ref_dt = target_datetime.replace(tzinfo=brasil_tz)
        
        # Filtrar apenas forecasts futuros
        future_forecasts = []
        for f in forecasts:
            # Parse timestamp (suporta datetime ou string ISO)
            ts = AlertsGenerator._parse_timestamp(f)
            if ts >= ref_dt:
                future_forecasts.append((f, ts))
        
        if not future_forecasts:
            return []
        
        # Sets para deduplicação eficiente
        alerts_by_code: Dict[str, WeatherAlert] = {}
        
        # SINGLE-PASS: coletar alertas básicos + extremos diários
        daily_extremes: Dict[datetime, Dict] = defaultdict(lambda: {
            'temps': [],
            'first_forecast': None
        })
        
        for forecast, timestamp in future_forecasts:
            # Normalizar campos (suporta diferentes formatos)
            rain_prob = float(getattr(forecast, 'rain_probability', 0) or getattr(forecast, 'precipitation_probability', 0))
            wind_speed = float(getattr(forecast, 'wind_speed', 0) or getattr(forecast, 'wind_speed_kmh', 0))
            precipitation = float(getattr(forecast, 'precipitation', 0))
            rain_1h = precipitation  # HourlyForecast já é por hora
            temperature = float(forecast.temperature)
            visibility = float(getattr(forecast, 'visibility', 10000))
            
            # Alertas básicos de cada forecast
            basic_alerts = WeatherAlertOrchestrator.generate_alerts(
                weather_code=forecast.weather_code,
                rain_prob=rain_prob,
                wind_speed=wind_speed,
                forecast_time=timestamp,
                rain_1h=rain_1h,
                temperature=temperature,
                visibility=visibility
            )
            
            # Adicionar com deduplicação (manter timestamp mais próximo)
            for alert in basic_alerts:
                if alert.code not in alerts_by_code:
                    alerts_by_code[alert.code] = alert
                elif alert.timestamp < alerts_by_code[alert.code].timestamp:
                    alerts_by_code[alert.code] = alert
            
            # Acumular extremos diários para trends
            date_key = timestamp.astimezone(brasil_tz).date()
            daily = daily_extremes[date_key]
            daily['temps'].extend([
                temperature,
                temperature,  # temp_min não disponível em hourly
                temperature   # temp_max não disponível em hourly
            ])
            if daily['first_forecast'] is None:
                daily['first_forecast'] = (forecast, timestamp)
        
        # Adicionar rain_ends_at aos alertas de chuva
        # Extrair apenas forecasts (sem timestamps) para compatibilidade
        AlertsGenerator._add_rain_end_times(
            list(alerts_by_code.values()),
            [f for f, _ in future_forecasts]
        )
        
        # Analisar trends de temperatura (algoritmo otimizado)
        temp_alerts = AlertsGenerator._analyze_temperature_trends_optimized(
            daily_extremes,
            brasil_tz
        )
        
        # Merge de alertas de temperatura
        for alert in temp_alerts:
            if alert.code not in alerts_by_code:
                alerts_by_code[alert.code] = alert
        
        return list(alerts_by_code.values())
    
    @staticmethod
    def _analyze_temperature_trends_optimized(
        daily_extremes: Dict,
        brasil_tz: ZoneInfo
    ) -> List[WeatherAlert]:
        """
        Analisa trends de temperatura com algoritmo otimizado
        ANTES: O(n²) com loops aninhados
        DEPOIS: O(n) com sliding window
        
        Args:
            daily_extremes: Dict com extremos por dia
            brasil_tz: Timezone Brasil
        
        Returns:
            Lista com até 2 alertas (maior drop, maior rise)
        """
        if len(daily_extremes) < 2:
            return []
        
        # Calcular max/min por dia
        daily_data = []
        for date_key in sorted(daily_extremes.keys()):
            data = daily_extremes[date_key]
            temps = data['temps']
            if temps and data['first_forecast']:
                forecast, timestamp = data['first_forecast']
                daily_data.append({
                    'date': date_key,
                    'max': max(temps),
                    'min': min(temps),
                    'first_timestamp': timestamp
                })
        
        if len(daily_data) < 2:
            return []
        
        # Encontrar maior variação (drop e rise) em uma única passagem
        max_drop = None
        max_rise = None
        
        # OTIMIZAÇÃO: Apenas comparar dias adjacentes ou próximos
        # ao invés de todas as combinações
        for i in range(len(daily_data) - 1):
            day1 = daily_data[i]
            
            # Olhar próximos 3 dias apenas (janela razoável)
            for j in range(i + 1, min(i + 4, len(daily_data))):
                day2 = daily_data[j]
                
                variation = day2['max'] - day1['max']
                days_between = (day2['date'] - day1['date']).days
                
                # Threshold de 8°C
                if abs(variation) >= WeatherConstants.TEMP_VARIATION_THRESHOLD:
                    alert_time = day1['first_timestamp'].astimezone(brasil_tz)
                    
                    # Ajustar se necessário
                    if alert_time.date() != day1['date']:
                        alert_time = datetime.combine(
                            day1['date'],
                            datetime.min.time()
                        ).replace(tzinfo=brasil_tz)
                    
                    if variation < 0:  # Drop
                        if max_drop is None or abs(variation) > abs(max_drop['variation']):
                            max_drop = {
                                'variation': variation,
                                'alert': WeatherAlert(
                                    code="TEMP_DROP",
                                    severity=AlertSeverity.INFO,
                                    description=f"🌡️ Queda de temperatura ({abs(variation):.0f}°C em {days_between} {'dia' if days_between == 1 else 'dias'})",
                                    timestamp=alert_time,
                                    details={
                                        "day_1_date": day1['date'].isoformat(),
                                        "day_1_max_c": round(day1['max'], 1),
                                        "day_2_date": day2['date'].isoformat(),
                                        "day_2_max_c": round(day2['max'], 1),
                                        "variation_c": round(variation, 1),
                                        "days_between": days_between
                                    }
                                )
                            }
                    else:  # Rise
                        if max_rise is None or variation > max_rise['variation']:
                            max_rise = {
                                'variation': variation,
                                'alert': WeatherAlert(
                                    code="TEMP_RISE",
                                    severity=AlertSeverity.WARNING,
                                    description=f"🌡️ Aumento de temperatura (+{variation:.0f}°C em {days_between} {'dia' if days_between == 1 else 'dias'})",
                                    timestamp=alert_time,
                                    details={
                                        "day_1_date": day1['date'].isoformat(),
                                        "day_1_max_c": round(day1['max'], 1),
                                        "day_2_date": day2['date'].isoformat(),
                                        "day_2_max_c": round(day2['max'], 1),
                                        "variation_c": round(variation, 1),
                                        "days_between": days_between
                                    }
                                )
                            }
        
        # Retornar apenas os alertas de maior magnitude
        alerts = []
        if max_drop:
            alerts.append(max_drop['alert'])
        if max_rise:
            alerts.append(max_rise['alert'])
        
        return alerts
    
    @staticmethod
    def _add_rain_end_times(
        alerts: List[WeatherAlert],
        forecasts: List[ForecastLike]
    ) -> None:
        """
        Adiciona rain_ends_at aos alertas de chuva (in-place)
        
        Args:
            alerts: Lista de alertas (modificada in-place)
            forecasts: Lista de forecasts ordenados
        """
        rain_codes = {
            "DRIZZLE", "LIGHT_RAIN", "MODERATE_RAIN",
            "HEAVY_RAIN", "STORM", "STORM_RAIN"
        }
        
        brasil_tz = ZoneInfo(App.TIMEZONE)
        
        for alert in alerts:
            if alert.code in rain_codes and alert.details:
                # Encontrar quando chuva termina
                alert_dt = alert.timestamp
                if alert_dt.tzinfo is None:
                    alert_dt = alert_dt.replace(tzinfo=brasil_tz)
                
                rain_end = AlertsGenerator._find_rain_end(
                    forecasts,
                    alert_dt,
                    brasil_tz
                )
                
                if rain_end:
                    alert.details["rain_ends_at"] = rain_end.isoformat()
    
    @staticmethod
    def _find_rain_end(
        forecasts: List[ForecastLike],
        start_time: datetime,
        brasil_tz: ZoneInfo
    ) -> Optional[datetime]:
        """
        Encontra quando a chuva termina usando rainfall_intensity >= 1
        
        Args:
            forecasts: Lista de forecasts
            start_time: Início da chuva
            brasil_tz: Timezone
        
        Returns:
            Datetime quando chuva termina ou None se não conseguir identificar
        """
        # Filtrar apenas HourlyForecasts >= start_time
        hourly_forecasts = []
        for f in forecasts:
            # Apenas HourlyForecast (tem timestamp e não tem temp_min)
            if not hasattr(f, 'timestamp') or hasattr(f, 'temp_min'):
                continue
            
            ts = AlertsGenerator._parse_timestamp(f)
            if ts >= start_time:
                hourly_forecasts.append((f, ts))
        
        if not hourly_forecasts:
            return None
        
        hourly_forecasts.sort(key=lambda x: x[1])
        
        last_rain_time = None
        consecutive_no_rain = 0
        
        for forecast, timestamp in hourly_forecasts:
            # Calcular rainfall_intensity
            intensity = getattr(forecast, 'rainfall_intensity', 0)
            
            if intensity >= 1:
                # Está chovendo
                last_rain_time = timestamp.astimezone(brasil_tz)
                consecutive_no_rain = 0
            else:
                # Não está chovendo
                consecutive_no_rain += 1
                
                # Se tiver 2 horas consecutivas sem chuva, termina
                if last_rain_time and consecutive_no_rain >= 2:
                    # Retorna última hora com chuva + 1h
                    return last_rain_time + timedelta(hours=1)
        
        # Se não encontrou 2h consecutivas sem chuva, retornar None
        return None
    
    @staticmethod
    def _parse_timestamp(forecast: ForecastLike) -> datetime:
        """
        Parse timestamp de forecast (suporta datetime, string ISO, ou date string)
        
        Args:
            forecast: Forecast com timestamp ou date
        
        Returns:
            datetime timezone-aware
        """
        # Tentar pegar timestamp (HourlyForecast)
        timestamp = getattr(forecast, 'timestamp', None)
        
        # Se não tem timestamp, tentar date (DailyForecast)
        if timestamp is None:
            date_str = getattr(forecast, 'date', None)
            if date_str:
                # Converter "YYYY-MM-DD" para datetime no início do dia
                try:
                    dt = datetime.fromisoformat(f"{date_str}T00:00:00")
                    return dt.replace(tzinfo=ZoneInfo(App.TIMEZONE))
                except Exception:
                    return datetime.now(tz=ZoneInfo('UTC'))
        
        # Já é datetime
        if isinstance(timestamp, datetime):
            if timestamp.tzinfo is None:
                return timestamp.replace(tzinfo=ZoneInfo('UTC'))
            return timestamp
        
        # É string ISO (de HourlyForecast/DailyForecast)
        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=ZoneInfo(App.TIMEZONE))
                return dt
            except Exception:
                return datetime.now(tz=ZoneInfo('UTC'))
        
        # Fallback
        return datetime.now(tz=ZoneInfo('UTC'))
