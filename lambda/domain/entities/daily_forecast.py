"""
Daily Forecast Entity - Entidade de domínio para previsões diárias estendidas
Fonte: Open-Meteo API (até 16 dias de previsão)
"""
from dataclasses import dataclass
from typing import Optional

from domain.helpers.rainfall_calculator import calculate_rainfall_intensity
from domain.constants import WeatherCondition


@dataclass
class DailyForecast:
    """
    Entidade de Previsão Diária Estendida
    
    Representa dados meteorológicos agregados por dia complementares
    às previsões horárias do Open-Meteo.
    """
    date: str  # Formato YYYY-MM-DD
    temp_min: float  # Temperatura mínima (°C)
    temp_max: float  # Temperatura máxima (°C)
    precipitation_mm: float  # Precipitação total do dia (mm)
    rain_probability: float  # Probabilidade média de chuva (0-100%)
    rainfall_intensity: float  # Intensidade composta 0-100 (volume * probabilidade)
    wind_speed_max: float  # Velocidade máxima do vento (km/h)
    wind_direction: int  # Direção dominante do vento (graus 0-360)
    uv_index: float  # Índice UV máximo (0-11+)
    sunrise: str  # Horário do nascer do sol (HH:MM)
    sunset: str  # Horário do pôr do sol (HH:MM)
    precipitation_hours: float  # Horas de precipitação esperadas (0-24h)
    clouds: Optional[float] = None  # Cobertura de nuvens estimada (0-100%)
    visibility: Optional[float] = None  # Visibilidade estimada (metros)
    apparent_temp_min: Optional[float] = None  # Sensação térmica mínima (°C)
    apparent_temp_max: Optional[float] = None  # Sensação térmica máxima (°C)
    weather_code: int = 0  # Código proprietário da condição climática
    description: str = ""  # Descrição em português
    
    def __post_init__(self):
        """Auto-classificação usando sistema proprietário de códigos"""
        self._update_weather_summary()

    def _update_weather_summary(self, force: bool = False) -> None:
        """
        Atualiza weather_code/description usando regras proprietárias
        
        Args:
            force: Se True recalcula mesmo que já exista valor
        """
        if not force and self.weather_code != 0 and self.description:
            return

        temp_avg = (self.temp_min + self.temp_max) / 2
        precip_per_hour = self.precipitation_mm / self.precipitation_hours if self.precipitation_hours > 0 else 0
        clouds_value = self.clouds if self.clouds is not None else 50.0
        visibility_value = self.visibility if self.visibility is not None else 10000.0

        code, desc = WeatherCondition.classify_weather_condition(
            rainfall_intensity=self.rainfall_intensity,
            precipitation=precip_per_hour,
            wind_speed=self.wind_speed_max,
            clouds=clouds_value,
            visibility=visibility_value,
            temperature=temp_avg,
            rain_probability=self.rain_probability
        )
        object.__setattr__(self, 'weather_code', code)
        object.__setattr__(self, 'description', desc)

    def update_rainfall_intensity(self, rainfall_intensity: float) -> None:
        """
        Ajusta rainfall_intensity e reclassifica o resumo do clima
        """
        object.__setattr__(self, 'rainfall_intensity', rainfall_intensity)
        self._update_weather_summary(force=True)

    def update_precipitation_hours(self, precipitation_hours: float) -> None:
        """
        Atualiza horas de precipitação e reclassifica o resumo do clima
        """
        safe_hours = max(0.0, precipitation_hours)
        object.__setattr__(self, 'precipitation_hours', safe_hours)
        self._update_weather_summary(force=True)
    
    def update_clouds_visibility(self, clouds: Optional[float], visibility: Optional[float]) -> None:
        """
        Atualiza nuvens/visibilidade estimadas e reclassifica o resumo do clima
        """
        if clouds is not None:
            object.__setattr__(self, 'clouds', max(0.0, min(100.0, clouds)))
        if visibility is not None:
            object.__setattr__(self, 'visibility', max(0.0, visibility))
        self._update_weather_summary(force=True)
    
    @property
    def daylight_hours(self) -> float:
        """
        Calcula duração do dia em horas baseado em sunrise/sunset
        
        Returns:
            Horas de luz do dia (ex: 13.5 para 13h30min)
        """
        try:
            sunrise_parts = self.sunrise.split(':')
            sunset_parts = self.sunset.split(':')
            
            sunrise_minutes = int(sunrise_parts[0]) * 60 + int(sunrise_parts[1])
            sunset_minutes = int(sunset_parts[0]) * 60 + int(sunset_parts[1])
            
            daylight_minutes = sunset_minutes - sunrise_minutes
            return round(daylight_minutes / 60, 1)
        except (ValueError, IndexError):
            return 0.0
    
    @property
    def uv_risk_level(self) -> str:
        """
        Retorna nível de risco baseado no índice UV
        
        Escala OMS:
        - 0-2: Baixo (verde)
        - 3-5: Moderado (amarelo)
        - 6-7: Alto (laranja)
        - 8-10: Muito alto (vermelho)
        - 11+: Extremo (roxo)
        
        Returns:
            String descrevendo o nível de risco
        """
        if self.uv_index <= 2:
            return "Baixo"
        elif self.uv_index <= 5:
            return "Moderado"
        elif self.uv_index <= 7:
            return "Alto"
        elif self.uv_index <= 10:
            return "Muito Alto"
        else:
            return "Extremo"
    
    @property
    def uv_risk_color(self) -> str:
        """
        Retorna cor CSS para o nível de risco UV
        
        Returns:
            Cor em hexadecimal
        """
        if self.uv_index <= 2:
            return "#4caf50"  # verde
        elif self.uv_index <= 5:
            return "#ffeb3b"  # amarelo
        elif self.uv_index <= 7:
            return "#ff9800"  # laranja
        elif self.uv_index <= 10:
            return "#f44336"  # vermelho
        else:
            return "#9c27b0"  # roxo

    @property
    def wind_direction_arrow(self) -> str:
        """
        Retorna uma seta simples apontando para onde o vento sopra
        (wind_direction representa de onde o vento vem, por isso +180°)
        """
        arrows = ['↑', '↗', '→', '↘', '↓', '↙', '←', '↖']
        blowing_to = (self.wind_direction + 180) % 360
        index = int((blowing_to + 22.5) // 45) % 8
        return arrows[index]
    
    def to_api_response(self) -> dict:
        """
        Converte para formato de resposta da API
        
        Returns:
            Dict com dados formatados para JSON
        """
        response = {
            'date': self.date,
            'tempMin': round(self.temp_min, 1),
            'tempMax': round(self.temp_max, 1),
            'precipitationMm': round(self.precipitation_mm, 1),
            'rainProbability': round(self.rain_probability, 1),
            'rainfallIntensity': int(round(self.rainfall_intensity)),
            'windSpeedMax': round(self.wind_speed_max, 1),
            'windSpeed': round(self.wind_speed_max, 1),
            'windDirection': self.wind_direction,
            'windDirectionArrow': self.wind_direction_arrow,
            'uvIndex': round(self.uv_index, 1),
            'uvRiskLevel': self.uv_risk_level,
            'uvRiskColor': self.uv_risk_color,
            'sunrise': self.sunrise,
            'sunset': self.sunset,
            'precipitationHours': round(self.precipitation_hours, 1),
            'daylightHours': self.daylight_hours,
            'weatherCode': self.weather_code,
            'description': self.description
        }

        # Cobertura de nuvens média (se disponível)
        if self.clouds is not None:
            response['cloudCover'] = round(self.clouds, 1)
        
        # Adicionar apparent temperatures se disponíveis
        if self.apparent_temp_min is not None:
            response['apparentTempMin'] = round(self.apparent_temp_min, 1)
        if self.apparent_temp_max is not None:
            response['apparentTempMax'] = round(self.apparent_temp_max, 1)
        
        return response
    
    @staticmethod
    def from_openmeteo_data(
        date: str,
        temp_max: float,
        temp_min: float,
        precipitation: float,
        rain_prob: float,
        wind_speed: float,
        wind_direction: int,
        uv_index: float,
        sunrise: str,
        sunset: str,
        precip_hours: float,
        cloud_cover_mean: Optional[float] = None,
        apparent_temp_min: Optional[float] = None,
        apparent_temp_max: Optional[float] = None
    ) -> 'DailyForecast':
        """
        Cria instância a partir de dados da API Open-Meteo
        
        Args:
            date: Data no formato YYYY-MM-DD
            temp_max: Temperatura máxima
            temp_min: Temperatura mínima
            precipitation: Precipitação total (mm)
            rain_prob: Probabilidade de chuva (0-100)
            wind_speed: Velocidade máxima do vento (km/h)
            uv_index: Índice UV máximo
            sunrise: Nascer do sol (ISO 8601)
            sunset: Pôr do sol (ISO 8601)
            precip_hours: Horas de precipitação
            cloud_cover_mean: Cobertura média de nuvens diária (0-100) se disponível
        
        Returns:
            Nova instância de DailyForecast
        """
        # Extrair apenas HH:MM do timestamp ISO 8601
        # Ex: "2025-11-30T05:11" -> "05:11"
        sunrise_time = sunrise.split('T')[1] if 'T' in sunrise else sunrise
        sunset_time = sunset.split('T')[1] if 'T' in sunset else sunset
        
        # Calcular rainfall_intensity: (volume * probabilidade) / referência
        # Para dados diários, usamos precipitação distribuída nas horas de chuva
        if precip_hours > 0 and precipitation > 0:
            precip_per_hour = precipitation / precip_hours
        else:
            precip_per_hour = 0.0
        rainfall_intensity = calculate_rainfall_intensity(rain_prob, precip_per_hour)
        
        return DailyForecast(
            date=date,
            temp_min=temp_min,
            temp_max=temp_max,
            precipitation_mm=precipitation,
            rain_probability=rain_prob,
            rainfall_intensity=rainfall_intensity,
            wind_speed_max=wind_speed,
            wind_direction=wind_direction,
            uv_index=uv_index,
            sunrise=sunrise_time,
            sunset=sunset_time,
            precipitation_hours=precip_hours,
            clouds=cloud_cover_mean,
            apparent_temp_min=apparent_temp_min,
            apparent_temp_max=apparent_temp_max
        )
