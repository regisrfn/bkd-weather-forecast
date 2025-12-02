"""
OpenWeather Data Mapper - Transforma dados da One Call API 3.0 para entities
LOCALIZAÇÃO: infrastructure (transforma dados externos → domínio)
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Dict, Any, List

from domain.entities.weather import Weather
from domain.entities.daily_forecast import DailyForecast
from domain.entities.hourly_forecast import HourlyForecast
from domain.helpers.rainfall_calculator import calculate_rainfall_intensity
from domain.constants import App, Weather as WeatherConstants
from domain.services.weather_alert_orchestrator import WeatherAlertOrchestrator
from domain.alerts.primitives import WeatherAlert, AlertSeverity


class OpenWeatherDataMapper:
    """
    Mapper para transformar respostas da One Call API 3.0 em entities de domínio
    
    Responsabilidade: Traduzir formato OpenWeather One Call → Domain entities
    Localização: Infrastructure (conhece detalhes da API externa)
    """
    
    @staticmethod
    def map_onecall_current_to_weather(
        data: Dict[str, Any],
        city_id: str,
        city_name: str,
        target_datetime: Optional[datetime] = None,
        include_daily_alerts: bool = False
    ) -> Weather:
        """
        Mapeia campo 'current' da One Call API 3.0 para Weather entity
        
        Args:
            data: Resposta raw da One Call API (/onecall endpoint)
            city_id: ID da cidade
            city_name: Nome da cidade
            target_datetime: Datetime alvo (usado para calcular alertas)
            include_daily_alerts: Se True, inclui alertas de médio prazo (8 dias) para rota detalhada
        
        Returns:
            Weather entity completo com dados atuais
        """
        current = data.get('current', {})
        if not current:
            raise ValueError("Campo 'current' não encontrado na resposta One Call")
        
        brasil_tz = ZoneInfo(App.TIMEZONE)
        
        # Parse timestamp
        dt_unix = current.get('dt', 0)
        timestamp = datetime.fromtimestamp(dt_unix, tz=ZoneInfo('UTC')).astimezone(brasil_tz)
        
        # Extrair dados meteorológicos
        weather_list = current.get('weather', [{}])
        weather_info = weather_list[0] if weather_list else {}
        
        temperature = current.get('temp', 0.0)
        feels_like = current.get('feels_like', temperature)
        pressure = current.get('pressure', 0.0)
        humidity = current.get('humidity', 0.0)
        dew_point = current.get('dew_point', 0.0)
        uvi = current.get('uvi', 0.0)
        clouds = current.get('clouds', 0.0)
        visibility = current.get('visibility', 10000)
        wind_speed_ms = current.get('wind_speed', 0.0)
        wind_speed_kmh = wind_speed_ms * 3.6
        wind_direction = current.get('wind_deg', 0)
        
        # Precipitação (One Call pode ter rain.1h e snow.1h)
        rain = current.get('rain', {})
        snow = current.get('snow', {})
        rain_1h = rain.get('1h', 0.0) + snow.get('1h', 0.0)
        
        description = weather_info.get('description', '')
        weather_code = weather_info.get('id', 0)
        
        # Gerar alertas analisando hourly forecasts se disponível (48h - curto prazo)
        alerts = []
        if 'hourly' in data:
            alerts = OpenWeatherDataMapper._generate_alerts_from_hourly(
                hourly_data=data['hourly'],  # Todas as 48 horas disponíveis
                ref_dt=target_datetime or timestamp
            )
        
        # Adicionar alertas de médio prazo (8 dias) para rota detalhada
        if include_daily_alerts and 'daily' in data:
            # Converter dados raw do OpenWeather para ForecastLike
            from domain.services.alerts_generator import AlertsGenerator
            
            daily_forecasts = []
            for day_raw in data['daily']:
                dt_unix = day_raw.get('dt', 0)
                day_dt = datetime.fromtimestamp(dt_unix, tz=ZoneInfo('UTC')).astimezone(ZoneInfo(App.TIMEZONE))
                
                # Apenas dias futuros
                if day_dt.date() <= (target_datetime or timestamp).date():
                    continue
                
                temp_data = day_raw.get('temp', {})
                wind_speed_ms = day_raw.get('wind_speed', 0.0)
                
                # Criar objeto simples compatível com ForecastLike
                class DailyForecastAdapter:
                    def __init__(self, raw_data, dt):
                        self.timestamp = dt
                        self.temperature = raw_data.get('temp', {}).get('day', 0.0)
                        self.wind_speed = raw_data.get('wind_speed', 0.0) * 3.6  # m/s -> km/h
                        self.wind_direction = raw_data.get('wind_deg', 0)
                        self.rain_probability = raw_data.get('pop', 0.0) * 100
                        self.precipitation = raw_data.get('rain', 0.0) + raw_data.get('snow', 0.0)
                        self.weather_code = raw_data.get('weather', [{}])[0].get('id', 0) if raw_data.get('weather') else 0
                        self.temp_max = raw_data.get('temp', {}).get('max', 0.0)
                        self.temp_min = raw_data.get('temp', {}).get('min', 0.0)
                        self.uv_index = raw_data.get('uvi', 0.0)
                        
                        # Calcular rainfall_intensity (OpenWeather não fornece precip_hours para daily)
                        # Usamos 24h como período padrão para dados diários
                        if self.precipitation > 0 and self.rain_probability > 0:
                            precip_per_hour = self.precipitation / 24.0
                            self.rainfall_intensity = calculate_rainfall_intensity(self.rain_probability, precip_per_hour)
                        else:
                            self.rainfall_intensity = 0.0
                
                daily_forecasts.append(DailyForecastAdapter(day_raw, day_dt))
            
            if daily_forecasts:
                # Usar AlertsGenerator centralizado com limite de 10 dias
                daily_alerts = AlertsGenerator.generate_alerts_next_days(
                    forecasts=daily_forecasts,
                    target_datetime=target_datetime or timestamp,
                    days_limit=10  # 8 dias de previsão + margem
                )
                
                # Filtrar apenas alertas de médio prazo (não duplicar os de curto prazo)
                medium_term_codes = {'TEMP_DROP', 'TEMP_RISE', 'HEAVY_RAIN_DAY', 'STRONG_WIND_DAY', 'EXTREME_UV'}
                daily_alerts = [a for a in daily_alerts if a.code in medium_term_codes]
                
                alerts.extend(daily_alerts)
                
                # Deduplicar após combinação (manter o mais próximo)
                unique_alerts = {}
                for alert in alerts:
                    if alert.code not in unique_alerts:
                        unique_alerts[alert.code] = alert
                    else:
                        if alert.timestamp < unique_alerts[alert.code].timestamp:
                            unique_alerts[alert.code] = alert
                alerts = list(unique_alerts.values())
        
        # Extrair temp min/max do dia de 'daily' se disponível
        temp_min = temperature
        temp_max = temperature
        rain_accumulated_day = rain_1h
        
        if 'daily' in data and len(data['daily']) > 0:
            today = data['daily'][0]
            temp_data = today.get('temp', {})
            temp_min = temp_data.get('min', temperature)
            temp_max = temp_data.get('max', temperature)
            rain_accumulated_day = today.get('rain', 0.0) + today.get('snow', 0.0)
        
        return Weather(
            city_id=city_id,
            city_name=city_name,
            timestamp=timestamp,
            temperature=temperature,
            humidity=humidity,
            wind_speed=wind_speed_kmh,
            wind_direction=wind_direction,
            rain_probability=0.0,  # Current não tem probability
            rain_1h=rain_1h,
            rain_accumulated_day=rain_accumulated_day,
            description=description,
            feels_like=feels_like,
            pressure=pressure,
            visibility=visibility,
            clouds=clouds,
            weather_alert=alerts,
            weather_code=weather_code,
            temp_min=temp_min,
            temp_max=temp_max
        )
    
    @staticmethod
    def map_onecall_daily_to_forecasts(
        data: Dict[str, Any],
        max_days: int = 8
    ) -> List[DailyForecast]:
        """
        Mapeia campo 'daily' da One Call API 3.0 para lista de DailyForecast
        
        Args:
            data: Resposta raw da One Call API
            max_days: Número máximo de dias a retornar (padrão 8)
        
        Returns:
            Lista de DailyForecast entities (até max_days elementos)
        """
        daily_list = data.get('daily', [])
        if not daily_list:
            raise ValueError("Campo 'daily' não encontrado na resposta One Call")
        
        brasil_tz = ZoneInfo(App.TIMEZONE)
        forecasts = []
        
        for day_data in daily_list[:max_days]:
            # Parse date
            dt_unix = day_data.get('dt', 0)
            forecast_date = datetime.fromtimestamp(dt_unix, tz=ZoneInfo('UTC')).astimezone(brasil_tz)
            date_str = forecast_date.strftime('%Y-%m-%d')
            
            # Temperaturas
            temp_data = day_data.get('temp', {})
            temp_min = temp_data.get('min', 0.0)
            temp_max = temp_data.get('max', 0.0)
            
            # Precipitação
            precipitation_mm = day_data.get('rain', 0.0) + day_data.get('snow', 0.0)
            rain_probability = day_data.get('pop', 0.0) * 100  # 0-1 → 0-100
            
            # Vento
            wind_speed_ms = day_data.get('wind_speed', 0.0)
            wind_speed_kmh = wind_speed_ms * 3.6
            wind_direction = day_data.get('wind_deg', 0)
            
            # UV e astronômicos
            uv_index = day_data.get('uvi', 0.0)
            sunrise_unix = day_data.get('sunrise', 0)
            sunset_unix = day_data.get('sunset', 0)
            
            sunrise_dt = datetime.fromtimestamp(sunrise_unix, tz=brasil_tz)
            sunset_dt = datetime.fromtimestamp(sunset_unix, tz=brasil_tz)
            sunrise_str = sunrise_dt.strftime('%H:%M')
            sunset_str = sunset_dt.strftime('%H:%M')
            
            # Precipitation hours (estimativa baseada em probabilidade)
            # One Call não fornece diretamente, aproximamos
            precipitation_hours = (rain_probability / 100) * 12.0  # Estimativa
            
            # Calcular rainfall_intensity: (volume * probabilidade) / referência
            # Para dados diários do OpenWeather, usamos 24h como período padrão
            precip_per_hour = precipitation_mm / 24.0 if precipitation_mm > 0 else 0.0
            rainfall_intensity = calculate_rainfall_intensity(rain_probability, precip_per_hour)
            
            forecast = DailyForecast(
                date=date_str,
                temp_min=temp_min,
                temp_max=temp_max,
                precipitation_mm=precipitation_mm,
                rain_probability=rain_probability,
                rainfall_intensity=rainfall_intensity,
                wind_speed_max=wind_speed_kmh,
                wind_direction=wind_direction,
                uv_index=uv_index,
                sunrise=sunrise_str,
                sunset=sunset_str,
                precipitation_hours=precipitation_hours
            )
            
            forecasts.append(forecast)
        
        return forecasts
    
    @staticmethod
    def map_onecall_hourly_to_forecasts(
        data: Dict[str, Any],
        max_hours: int = 48
    ) -> List[HourlyForecast]:
        """
        Mapeia campo 'hourly' da One Call API 3.0 para lista de HourlyForecast
        
        Args:
            data: Resposta raw da One Call API
            max_hours: Número máximo de horas a retornar (padrão 48)
        
        Returns:
            Lista de HourlyForecast entities (até max_hours elementos)
        """
        hourly_list = data.get('hourly', [])
        if not hourly_list:
            raise ValueError("Campo 'hourly' não encontrado na resposta One Call")
        
        brasil_tz = ZoneInfo(App.TIMEZONE)
        forecasts = []
        
        for hour_data in hourly_list[:max_hours]:
            # Parse timestamp
            dt_unix = hour_data.get('dt', 0)
            forecast_dt = datetime.fromtimestamp(dt_unix, tz=ZoneInfo('UTC')).astimezone(brasil_tz)
            timestamp_str = forecast_dt.strftime('%Y-%m-%dT%H:%M')
            
            # Dados meteorológicos
            temperature = hour_data.get('temp', 0.0)
            humidity = hour_data.get('humidity', 0)
            clouds = hour_data.get('clouds', 0)
            
            # Vento
            wind_speed_ms = hour_data.get('wind_speed', 0.0)
            wind_speed_kmh = wind_speed_ms * 3.6
            wind_direction = hour_data.get('wind_deg', 0)
            
            # Precipitação
            rain = hour_data.get('rain', {})
            snow = hour_data.get('snow', {})
            precipitation = rain.get('1h', 0.0) + snow.get('1h', 0.0)
            precipitation_probability = int(hour_data.get('pop', 0.0) * 100)
            
            # Weather code e descrição
            weather_list = hour_data.get('weather', [{}])
            weather_info = weather_list[0] if weather_list else {}
            weather_code = weather_info.get('id', 0)
            description = weather_info.get('description', '')
            
            # Calcular rainfall_intensity
            rainfall_intensity = calculate_rainfall_intensity(precipitation_probability, precipitation)
            
            forecast = HourlyForecast(
                timestamp=timestamp_str,
                temperature=temperature,
                precipitation=precipitation,
                precipitation_probability=precipitation_probability,
                rainfall_intensity=rainfall_intensity,
                humidity=humidity,
                wind_speed=wind_speed_kmh,
                wind_direction=wind_direction,
                cloud_cover=clouds,
                weather_code=weather_code,
                description=description
            )
            
            forecasts.append(forecast)
        
        return forecasts
    
    @staticmethod
    def _generate_alerts_from_hourly(
        hourly_data: List[Dict[str, Any]],
        ref_dt: datetime
    ) -> List:
        """
        Gera alertas analisando previsões horárias (até 48h)
        
        Args:
            hourly_data: Lista de forecasts hourly (todas as horas disponíveis, até 48)
            ref_dt: Datetime de referência
        
        Returns:
            Lista de WeatherAlert
        """
        all_alerts = []
        brasil_tz = ZoneInfo(App.TIMEZONE)
        
        for hour_data in hourly_data:
            dt_unix = hour_data.get('dt', 0)
            forecast_dt = datetime.fromtimestamp(dt_unix, tz=ZoneInfo('UTC')).astimezone(brasil_tz)
            
            # Extrair dados
            weather_list = hour_data.get('weather', [{}])
            weather_info = weather_list[0] if weather_list else {}
            
            rain = hour_data.get('rain', {})
            snow = hour_data.get('snow', {})
            rain_1h = rain.get('1h', 0.0) + snow.get('1h', 0.0)
            rain_prob = hour_data.get('pop', 0.0) * 100
            
            wind_speed_ms = hour_data.get('wind_speed', 0.0)
            wind_speed_kmh = wind_speed_ms * 3.6
            
            temperature = hour_data.get('temp', 0.0)
            visibility = hour_data.get('visibility', 10000)
            
            # Gerar alertas
            hour_alerts = WeatherAlertOrchestrator.generate_alerts(
                weather_code=weather_info.get('id', 0),
                rain_prob=rain_prob,
                wind_speed=wind_speed_kmh,
                forecast_time=forecast_dt,
                rain_1h=rain_1h,
                temperature=temperature,
                visibility=visibility
            )
            
            all_alerts.extend(hour_alerts)
        
        # Deduplicar por code
        unique_alerts = {}
        for alert in all_alerts:
            if alert.code not in unique_alerts:
                unique_alerts[alert.code] = alert
            else:
                # Manter o mais próximo
                if alert.timestamp < unique_alerts[alert.code].timestamp:
                    unique_alerts[alert.code] = alert
        
        return list(unique_alerts.values())
