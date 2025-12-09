"""
Configurações centralizadas da aplicação
"""
import os

# API de Clima (Open-Meteo não requer chave)
OPENMETEO_BASE_URL = 'https://api.open-meteo.com/v1'

# Cidade central (Ribeirão do Sul)
CENTER_CITY_ID = '3543204'
CENTER_CITY_NAME = 'Ribeirão do Sul'
CENTER_CITY_LAT = -22.7572
CENTER_CITY_LON = -49.9439

# Limites de raio (km)
MIN_RADIUS = 10
MAX_RADIUS = 150
DEFAULT_RADIUS = 50

# Cache (segundos)
CACHE_TTL = 300  # Legacy - não usado
CACHE_TTL_SECONDS = int(os.environ.get('CACHE_TTL_SECONDS', '10800'))  # 3 horas
CACHE_ENABLED = os.environ.get('CACHE_ENABLED', 'true').lower() in ('true', '1', 'yes')
CACHE_TABLE_NAME = os.environ.get('CACHE_TABLE_NAME', 'weather-forecast-cache-prod')

# AWS
AWS_REGION = os.environ.get('AWS_REGION', 'sa-east-1')

# CORS
CORS_ORIGIN = os.environ.get('CORS_ORIGIN', '*')
