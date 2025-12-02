"""
Domain Constants - Todas as constantes da aplicação centralizadas
Consolidando settings.py, primitives.py e valores hardcoded
"""
import os


class API:
    """Constantes de APIs externas"""
    
    # OpenWeather
    OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"
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
    TTL_OPENMETEO_DAILY = 3600  # 1 hora
    TTL_OPENMETEO_HOURLY = 3600  # 1 hora
    
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
