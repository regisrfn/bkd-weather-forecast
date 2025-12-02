"""
OpenWeather Data Mapper - Transforma dados da API OpenWeather para entities
LOCALIZAÇÃO: infrastructure (transforma dados externos → domínio)
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, Dict, Any, List, Tuple

from domain.entities.weather import Weather
from domain.constants import App


class OpenWeatherDataMapper:
    """
    Mapper para transformar respostas da API OpenWeather em entities de domínio
    
    Responsabilidade: Traduzir formato OpenWeather → Domain entities
    Localização: Infrastructure (conhece detalhes da API externa)
    """
    
    @staticmethod
    def map_forecast_response_to_weather(
        data: Dict[str, Any],
        city_id: str,
        city_name: str,
        target_datetime: Optional[datetime] = None
    ) -> Weather:
        """
        Mapeia resposta /forecast da API OpenWeather para Weather entity
        
        OTIMIZADO: Single-pass através dos forecasts
        - Seleciona forecast mais próximo do target
        - Calcula extremos diários
        - Acumula precipitação diária
        - Tudo em um único loop
        
        Args:
            data: Resposta raw da API OpenWeather (/forecast endpoint)
            city_id: ID da cidade
            city_name: Nome da cidade
            target_datetime: Datetime alvo (None = mais próximo futuro)
        
        Returns:
            Weather entity completo
        
        Raises:
            ValueError: Se não há previsões disponíveis
        """
        raw_forecasts = data.get('list', [])
        if not raw_forecasts:
            raise ValueError("Nenhuma previsão disponível na resposta")
        
        # Obter datetime de referência
        brasil_tz = ZoneInfo(App.TIMEZONE)
        if target_datetime is None:
            ref_dt = datetime.now(tz=brasil_tz)
        elif target_datetime.tzinfo is not None:
            ref_dt = target_datetime.astimezone(brasil_tz)
        else:
            ref_dt = target_datetime.replace(tzinfo=brasil_tz)
        
        # SINGLE-PASS: processar tudo em um loop
        selected_forecast = None
        min_diff = float('inf')
        temps_day = []
        rain_day = 0.0
        target_date = ref_dt.date()
        
        for forecast_raw in raw_forecasts:
            # Parse timestamp
            dt_unix = forecast_raw.get('dt', 0)
            forecast_dt = datetime.fromtimestamp(dt_unix, tz=ZoneInfo('UTC')).astimezone(brasil_tz)
            
            # Selecionar forecast mais próximo do target (futuro apenas)
            if forecast_dt >= ref_dt:
                diff = abs((forecast_dt - ref_dt).total_seconds())
                if diff < min_diff:
                    min_diff = diff
                    selected_forecast = forecast_raw
            
            # Acumular dados do dia alvo para cálculos
            if forecast_dt.date() == target_date:
                main = forecast_raw.get('main', {})
                temps_day.extend([
                    main.get('temp', 0),
                    main.get('temp_min', 0),
                    main.get('temp_max', 0)
                ])
                
                # Rain volume (3h window)
                rain = forecast_raw.get('rain', {})
                rain_day += rain.get('3h', 0.0)
        
        if not selected_forecast:
            raise ValueError("Nenhuma previsão futura disponível")
        
        # Extrair dados do forecast selecionado
        return OpenWeatherDataMapper._parse_forecast_item(
            forecast_raw=selected_forecast,
            city_id=city_id,
            city_name=city_name,
            temp_min_day=min(temps_day) if temps_day else None,
            temp_max_day=max(temps_day) if temps_day else None,
            rain_accumulated_day=rain_day
        )
    
    @staticmethod
    def _parse_forecast_item(
        forecast_raw: Dict[str, Any],
        city_id: str,
        city_name: str,
        temp_min_day: Optional[float] = None,
        temp_max_day: Optional[float] = None,
        rain_accumulated_day: float = 0.0
    ) -> Weather:
        """
        Parse um item individual da lista de forecasts OpenWeather
        
        Args:
            forecast_raw: Item raw da API
            city_id: ID da cidade
            city_name: Nome da cidade
            temp_min_day: Temperatura mínima do dia (pré-calculada)
            temp_max_day: Temperatura máxima do dia (pré-calculada)
            rain_accumulated_day: Chuva acumulada do dia (pré-calculada)
        
        Returns:
            Weather entity
        """
        # Extrair seções
        main = forecast_raw.get('main', {})
        weather_list = forecast_raw.get('weather', [{}])
        weather_info = weather_list[0] if weather_list else {}
        wind = forecast_raw.get('wind', {})
        clouds = forecast_raw.get('clouds', {})
        rain = forecast_raw.get('rain', {})
        
        # Parse timestamp
        dt_unix = forecast_raw.get('dt', 0)
        timestamp = datetime.fromtimestamp(dt_unix, tz=ZoneInfo('UTC'))
        
        # Extrair dados
        temperature = main.get('temp', 0.0)
        humidity = main.get('humidity', 0.0)
        pressure = main.get('pressure', 0.0)
        feels_like = main.get('feels_like', 0.0)
        
        # Temperaturas do item (fallback se não temos dados do dia)
        temp_min = temp_min_day if temp_min_day is not None else main.get('temp_min', temperature)
        temp_max = temp_max_day if temp_max_day is not None else main.get('temp_max', temperature)
        
        # Vento
        wind_speed_ms = wind.get('speed', 0.0)
        wind_speed_kmh = wind_speed_ms * 3.6  # m/s → km/h
        wind_direction = wind.get('deg', 0)
        
        # Precipitação
        rain_3h = rain.get('3h', 0.0)
        rain_1h = rain_3h / 3.0  # Aproximação
        rain_probability = forecast_raw.get('pop', 0.0) * 100  # 0-1 → 0-100
        
        # Outros
        visibility = forecast_raw.get('visibility', 10000)
        cloud_cover = clouds.get('all', 0.0)
        description = weather_info.get('description', '')
        weather_code = weather_info.get('id', 0)
        
        return Weather(
            city_id=city_id,
            city_name=city_name,
            timestamp=timestamp,
            temperature=temperature,
            humidity=humidity,
            wind_speed=wind_speed_kmh,
            wind_direction=wind_direction,
            rain_probability=rain_probability,
            rain_1h=rain_1h,
            rain_accumulated_day=rain_accumulated_day,
            description=description,
            feels_like=feels_like,
            pressure=pressure,
            visibility=visibility,
            clouds=cloud_cover,
            weather_alert=[],  # Alertas gerados externamente
            weather_code=weather_code,
            temp_min=temp_min,
            temp_max=temp_max
        )
