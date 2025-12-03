"""
Domain Constants - Todas as constantes da aplicação centralizadas
Consolidando settings.py, primitives.py e valores hardcoded
"""
import os


class API:
    """Constantes de APIs externas"""
    
    # OpenWeather One Call API 3.0
    OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/3.0"
    OPENWEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY', '')
    
    # Open-Meteo
    OPENMETEO_BASE_URL = "https://api.open-meteo.com/v1"
    
    # Timeouts e limites HTTP
    HTTP_TIMEOUT_TOTAL = 15  # segundos
    HTTP_TIMEOUT_CONNECT = 5  # segundos
    HTTP_TIMEOUT_READ = 10  # segundos
    HTTP_CONNECTION_LIMIT = 100
    HTTP_CONNECTION_LIMIT_PER_HOST = 30
    DNS_CACHE_TTL = 300  # segundos


class Cache:
    """Constantes de cache"""
    
    # DynamoDB
    TABLE_NAME = os.environ.get('CACHE_TABLE_NAME', 'weather-forecast-cache-prod')
    ENABLED = os.environ.get('CACHE_ENABLED', 'true').lower() in ('true', '1', 'yes')
    
    # TTLs por tipo de dado (segundos)
    TTL_OPENWEATHER = 10800  # 3 horas
    TTL_OPENMETEO_DAILY = 10800  # 3 horas (dados diários menos voláteis)
    TTL_OPENMETEO_HOURLY = 3600  # 1 hora (current e hourly)
    
    # Prefixos de chave
    PREFIX_OPENWEATHER = ""  # sem prefixo (compatibilidade)
    PREFIX_OPENMETEO_DAILY = "openmeteo_"
    PREFIX_OPENMETEO_HOURLY = "openmeteo_hourly_"
    
    # Batch operations
    BATCH_SIZE = 25  # limite DynamoDB


class Weather:
    """Constantes relacionadas a dados meteorológicos"""
    
    # Thresholds de alertas
    RAIN_PROBABILITY_THRESHOLD = 80  # mínimo % para alertas
    RAIN_INTENSITY_REFERENCE = 30.0  # mm/h para cálculo de intensidade
    WIND_SPEED_WARNING = 40.0  # km/h
    WIND_SPEED_DANGER = 60.0  # km/h
    VISIBILITY_WARNING = 1000  # metros
    VISIBILITY_DANGER = 500  # metros
    TEMP_EXTREME_COLD = 5.0  # °C
    TEMP_EXTREME_HOT = 35.0  # °C
    TEMP_VARIATION_THRESHOLD = 8.0  # °C entre dias
    
    # Códigos WMO (Open-Meteo)
    WMO_CLEAR = {0}
    WMO_PARTLY_CLOUDY = {1, 2, 3}
    WMO_FOG = {45, 48}
    WMO_DRIZZLE = {51, 53, 55, 56, 57}
    WMO_RAIN = {61, 63, 65, 66, 67}
    WMO_SNOW = {71, 73, 75, 77, 85, 86}
    WMO_RAIN_SHOWERS = {80, 81, 82}
    WMO_THUNDERSTORM = {95, 96, 99}
    
    # Códigos OpenWeather
    OW_THUNDERSTORM = range(200, 300)  # 2xx
    OW_DRIZZLE = range(300, 400)  # 3xx
    OW_RAIN = range(500, 600)  # 5xx
    OW_SNOW = range(600, 700)  # 6xx
    OW_ATMOSPHERE = range(700, 800)  # 7xx (neblina, fumaça)
    OW_CLEAR = {800}
    OW_CLOUDS = range(801, 900)  # 80x
    
    # Mapeamento WMO -> Descrição PT-BR
    WMO_DESCRIPTIONS = {
        0: "Céu limpo",
        1: "Principalmente limpo",
        2: "Parcialmente nublado",
        3: "Nublado",
        45: "Neblina",
        48: "Nevoeiro com geada",
        51: "Garoa leve",
        53: "Garoa moderada",
        55: "Garoa intensa",
        56: "Garoa congelante leve",
        57: "Garoa congelante intensa",
        61: "Chuva leve",
        63: "Chuva moderada",
        65: "Chuva forte",
        66: "Chuva congelante leve",
        67: "Chuva congelante forte",
        71: "Neve leve",
        73: "Neve moderada",
        75: "Neve forte",
        77: "Grãos de neve",
        80: "Pancadas de chuva leves",
        81: "Pancadas de chuva moderadas",
        82: "Pancadas de chuva fortes",
        85: "Pancadas de neve leves",
        86: "Pancadas de neve fortes",
        95: "Tempestade",
        96: "Tempestade com granizo leve",
        99: "Tempestade com granizo forte"
    }
    
    # Thresholds de intensidade de chuva (mm/h)
    RAIN_INTENSITY_LIGHT = 2.5
    RAIN_INTENSITY_MODERATE = 7.6
    RAIN_INTENSITY_HEAVY = 50.0
    
    # Unidades
    UNITS_METRIC = "metric"
    LANGUAGE_PT_BR = "pt_br"


class WeatherCondition:
    """
    Sistema proprietário de códigos meteorológicos
    Baseado em métricas reais (rainfall_intensity, precipitação, vento, temperatura, nuvens)
    ao invés de depender de códigos WMO ou OpenWeather
    """
    
    # Céu limpo e nuvens (100-399)
    CLEAR = 100
    CLEAR_DESC = "Céu limpo"
    
    PARTLY_CLOUDY = 200
    PARTLY_CLOUDY_DESC = "Parcialmente nublado"
    
    CLOUDY = 300
    CLOUDY_DESC = "Nublado"
    
    OVERCAST = 350
    OVERCAST_DESC = "Céu encoberto"
    
    # Garoa/Drizzle (400-499)
    LIGHT_DRIZZLE = 400
    LIGHT_DRIZZLE_DESC = "Garoa leve"
    
    MODERATE_DRIZZLE = 410
    MODERATE_DRIZZLE_DESC = "Garoa moderada"
    
    HEAVY_DRIZZLE = 420
    HEAVY_DRIZZLE_DESC = "Garoa intensa"
    
    # Chuva (500-599)
    LIGHT_RAIN = 500
    LIGHT_RAIN_DESC = "Chuva leve"
    
    MODERATE_RAIN = 510
    MODERATE_RAIN_DESC = "Chuva moderada"
    
    HEAVY_RAIN = 520
    HEAVY_RAIN_DESC = "Chuva forte"
    
    VERY_HEAVY_RAIN = 530
    VERY_HEAVY_RAIN_DESC = "Chuva muito forte"
    
    # Tempestade (600-699)
    STORM_LIGHT = 600
    STORM_LIGHT_DESC = "Tempestade leve"
    
    STORM_MODERATE = 610
    STORM_MODERATE_DESC = "Tempestade moderada"
    
    STORM_HEAVY = 620
    STORM_HEAVY_DESC = "Tempestade forte"
    
    STORM_SEVERE = 630
    STORM_SEVERE_DESC = "Tempestade severa"
    
    # Neblina/Fog (700-799)
    FOG_LIGHT = 700
    FOG_LIGHT_DESC = "Neblina leve"
    
    FOG = 710
    FOG_DESC = "Neblina"
    
    FOG_HEAVY = 720
    FOG_HEAVY_DESC = "Nevoeiro denso"
    
    # Condições especiais (800-899)
    HAZE = 800
    HAZE_DESC = "Névoa seca"
    
    # Neve (900-999) - raro no Brasil mas incluído para completude
    LIGHT_SNOW = 900
    LIGHT_SNOW_DESC = "Neve leve"
    
    MODERATE_SNOW = 910
    MODERATE_SNOW_DESC = "Neve moderada"
    
    HEAVY_SNOW = 920
    HEAVY_SNOW_DESC = "Neve forte"
    
    @staticmethod
    def classify_weather_condition(
        rainfall_intensity: float,
        precipitation: float,
        wind_speed: float,
        clouds: float,
        visibility: float,
        temperature: float,
        rain_probability: float = 0.0
    ) -> tuple[int, str]:
        """
        Classifica condição meteorológica baseada em métricas reais
        
        Args:
            rainfall_intensity: Intensidade composta 0-100 (volume × probabilidade)
            precipitation: Volume de precipitação (mm)
            wind_speed: Velocidade do vento (km/h)
            clouds: Cobertura de nuvens (0-100%)
            visibility: Visibilidade (metros)
            temperature: Temperatura (°C)
            rain_probability: Probabilidade de chuva (0-100%)
        
        Returns:
            Tupla (código, descrição)
        """
        
        # PRIORIDADE 1: Tempestade (alta intensidade + vento forte)
        if rainfall_intensity >= 40 and wind_speed >= 30:
            if rainfall_intensity >= 70 or wind_speed >= 60:
                return (WeatherCondition.STORM_SEVERE, WeatherCondition.STORM_SEVERE_DESC)
            elif rainfall_intensity >= 55 or wind_speed >= 45:
                return (WeatherCondition.STORM_HEAVY, WeatherCondition.STORM_HEAVY_DESC)
            elif rainfall_intensity >= 45:
                return (WeatherCondition.STORM_MODERATE, WeatherCondition.STORM_MODERATE_DESC)
            else:
                return (WeatherCondition.STORM_LIGHT, WeatherCondition.STORM_LIGHT_DESC)
        
        # PRIORIDADE 2: Chuva (baseada em rainfall_intensity)
        if rainfall_intensity >= 25:
            if precipitation >= 50 or rainfall_intensity >= 60:
                return (WeatherCondition.VERY_HEAVY_RAIN, WeatherCondition.VERY_HEAVY_RAIN_DESC)
            elif precipitation >= 10 or rainfall_intensity >= 40:
                return (WeatherCondition.HEAVY_RAIN, WeatherCondition.HEAVY_RAIN_DESC)
            elif precipitation >= 2.5 or rainfall_intensity >= 30:
                return (WeatherCondition.MODERATE_RAIN, WeatherCondition.MODERATE_RAIN_DESC)
            else:
                return (WeatherCondition.LIGHT_RAIN, WeatherCondition.LIGHT_RAIN_DESC)
        
        # PRIORIDADE 3: Garoa (precipitação baixa mas presente)
        if precipitation > 0 or (rain_probability >= 60 and rainfall_intensity > 0):
            if precipitation >= 2.5:
                return (WeatherCondition.HEAVY_DRIZZLE, WeatherCondition.HEAVY_DRIZZLE_DESC)
            elif precipitation >= 0.5:
                return (WeatherCondition.MODERATE_DRIZZLE, WeatherCondition.MODERATE_DRIZZLE_DESC)
            else:
                return (WeatherCondition.LIGHT_DRIZZLE, WeatherCondition.LIGHT_DRIZZLE_DESC)
        
        # PRIORIDADE 4: Neblina/Fog (baixa visibilidade)
        if visibility < 3000:
            if visibility < 500:
                return (WeatherCondition.FOG_HEAVY, WeatherCondition.FOG_HEAVY_DESC)
            elif visibility < 1000:
                return (WeatherCondition.FOG, WeatherCondition.FOG_DESC)
            else:
                return (WeatherCondition.FOG_LIGHT, WeatherCondition.FOG_LIGHT_DESC)
        
        # PRIORIDADE 5: Neve (temperatura baixa + precipitação)
        if temperature < 2 and precipitation > 0:
            if precipitation >= 10:
                return (WeatherCondition.HEAVY_SNOW, WeatherCondition.HEAVY_SNOW_DESC)
            elif precipitation >= 2.5:
                return (WeatherCondition.MODERATE_SNOW, WeatherCondition.MODERATE_SNOW_DESC)
            else:
                return (WeatherCondition.LIGHT_SNOW, WeatherCondition.LIGHT_SNOW_DESC)
        
        # PRIORIDADE 6: Névoa seca (visibilidade reduzida sem chuva)
        if visibility < 5000 and precipitation == 0:
            return (WeatherCondition.HAZE, WeatherCondition.HAZE_DESC)
        
        # PRIORIDADE 7: Cobertura de nuvens (sem precipitação)
        if clouds >= 85:
            return (WeatherCondition.OVERCAST, WeatherCondition.OVERCAST_DESC)
        elif clouds >= 50:
            return (WeatherCondition.CLOUDY, WeatherCondition.CLOUDY_DESC)
        elif clouds >= 20:
            return (WeatherCondition.PARTLY_CLOUDY, WeatherCondition.PARTLY_CLOUDY_DESC)
        else:
            return (WeatherCondition.CLEAR, WeatherCondition.CLEAR_DESC)


class Geo:
    """Constantes geográficas"""
    
    # Cidade central (Ribeirão do Sul)
    CENTER_CITY_ID = "3543204"
    CENTER_CITY_NAME = "Ribeirão do Sul"
    CENTER_CITY_LAT = -22.7572
    CENTER_CITY_LON = -49.9439
    
    # Limites de raio (km)
    MIN_RADIUS = 10
    MAX_RADIUS = 150
    DEFAULT_RADIUS = 50
    
    # Limites de coordenadas
    MIN_LATITUDE = -90
    MAX_LATITUDE = 90
    MIN_LONGITUDE = -180
    MAX_LONGITUDE = 180


class AWS:
    """Constantes AWS"""
    
    REGION = os.environ.get('AWS_REGION', 'sa-east-1')


class App:
    """Constantes da aplicação"""
    
    # CORS
    CORS_ORIGIN = os.environ.get('CORS_ORIGIN', '*')
    
    # Timezone padrão
    TIMEZONE = "America/Sao_Paulo"
    
    # Previsões
    FORECAST_DAYS_DEFAULT = 16
    FORECAST_HOURS_DEFAULT = 168  # 7 dias
