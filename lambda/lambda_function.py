import json
import logging
import os
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext

from cities_data import get_city_by_id, get_all_cities, CITIES_DATABASE
from cities_service import get_neighbors, validate_radius
from weather_service import get_weather_for_city, get_regional_weather
from config import DEFAULT_RADIUS
from municipalities_db import get_db
from openweather_service import WeatherAPIService

# Configurar Powertools
logger = Logger()
tracer = Tracer()

app = APIGatewayRestResolver()

# Inicializar banco de dados (singleton, carrega apenas uma vez)
db = get_db()
weather_service = WeatherAPIService()


@app.get("/api/cities/neighbors/<city_id>")
@tracer.capture_method
def get_neighbors_route(city_id: str):
    """
    GET /api/cities/neighbors/{cityId}?radius=50
    
    Retorna a cidade centro e suas cidades vizinhas dentro de um raio
    """
    logger.info(f"Buscando vizinhos de {city_id}")
    
    # Buscar cidade centro no banco de dados
    center_city = db.get_by_id(city_id)
    if not center_city:
        return {
            'statusCode': 404,
            'body': {
                'error': 'Not Found',
                'message': f'Cidade {city_id} não encontrada'
            }
        }
    
    # Validar se tem coordenadas
    if not center_city.get('latitude') or not center_city.get('longitude'):
        return {
            'statusCode': 400,
            'body': {
                'error': 'Bad Request',
                'message': f'Cidade {city_id} não possui coordenadas'
            }
        }
    
    # Extrair e validar raio
    radius = validate_radius(app.current_event.get_query_string_value(name="radius", default_value=str(DEFAULT_RADIUS)))
    
    # Buscar cidades vizinhas (apenas com coordenadas)
    all_cities = db.get_with_coordinates()
    neighbors = get_neighbors(center_city, all_cities, radius)
    
    response = {
        'centerCity': {
            'id': center_city['id'],
            'name': center_city['name'],
            'latitude': center_city['latitude'],
            'longitude': center_city['longitude']
        },
        'neighbors': neighbors
    }
    
    logger.info(f"Encontradas {len(neighbors)} cidades vizinhas de {center_city['name']}")
    
    return response


@app.get("/api/weather/city/<city_id>")
@tracer.capture_method
def get_city_weather_route(city_id: str):
    """
    GET /api/weather/city/{cityId}
    
    Retorna dados climáticos de uma cidade específica
    """
    logger.info(f"Buscando dados climáticos de {city_id}")
    
    # Buscar dados da cidade no banco
    city = db.get_by_id(city_id)
    if not city:
        return {
            'statusCode': 404,
            'body': {
                'error': 'Not Found',
                'message': f'Cidade {city_id} não encontrada'
            }
        }
    
    # Validar coordenadas
    if not city.get('latitude') or not city.get('longitude'):
        return {
            'statusCode': 400,
            'body': {
                'error': 'Bad Request',
                'message': f'Cidade {city_id} não possui coordenadas'
            }
        }
    
    # Buscar dados climáticos do OpenWeatherMap
    weather = weather_service.get_current_weather(
        city['latitude'],
        city['longitude'],
        city['name']
    )
    
    # Calcular intensidade de chuva (0-100%)
    rain_1h = weather.get('rain_1h', 0)  # mm de chuva na última hora
    rainfall_intensity = min((rain_1h / 10) * 100, 100)  # Normalizar para 0-100%
    
    # Retornar apenas os campos esperados pelo frontend
    response = {
        'cityId': city['id'],
        'cityName': city['name'],
        'timestamp': weather['timestamp'],
        'rainfallIntensity': round(rainfall_intensity, 1),
        'temperature': round(weather['temperature'], 1),
        'humidity': round(weather['humidity'], 1),
        'windSpeed': round(weather['wind_speed'], 1)
    }
    
    logger.info(f"Dados climáticos de {city['name']}: {response['temperature']}°C")
    
    return response


@app.post("/api/weather/regional")
@tracer.capture_method
def post_regional_weather_route():
    """
    POST /api/weather/regional
    Body: { "cityIds": ["3543204", "3550506", ...] }
    
    Retorna dados climáticos de múltiplas cidades
    """
    logger.info("Buscando dados climáticos regionais")
    
    # Extrair cityIds do body
    body = app.current_event.json_body
    city_ids = body.get('cityIds', [])
    
    if not city_ids or not isinstance(city_ids, list):
        return {
            'statusCode': 400,
            'body': {
                'error': 'Bad Request',
                'message': 'cityIds deve ser um array de strings'
            }
        }
    
    # Buscar dados climáticos de todas as cidades
    weather_data = []
    
    for city_id in city_ids:
        city = db.get_by_id(city_id)
        
        if not city or not city.get('latitude') or not city.get('longitude'):
            logger.warning(f"Cidade {city_id} não encontrada ou sem coordenadas")
            continue
        
        try:
            weather = weather_service.get_current_weather(
                city['latitude'],
                city['longitude'],
                city['name']
            )
            
            # Calcular intensidade de chuva (0-100%)
            rain_1h = weather.get('rain_1h', 0)  # mm de chuva na última hora
            rainfall_intensity = min((rain_1h / 10) * 100, 100)  # Normalizar para 0-100%
            
            # Retornar apenas os campos esperados pelo frontend
            city_weather = {
                'cityId': city['id'],
                'cityName': city['name'],
                'timestamp': weather['timestamp'],
                'rainfallIntensity': round(rainfall_intensity, 1),
                'temperature': round(weather['temperature'], 1),
                'humidity': round(weather['humidity'], 1),
                'windSpeed': round(weather['wind_speed'], 1)
            }
            
            weather_data.append(city_weather)
            
        except Exception as e:
            logger.error(f"Erro ao buscar clima de {city['name']}: {e}")
            continue
    
    logger.info(f"Dados climáticos regionais: {len(weather_data)} cidades")
    
    return weather_data


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    """
    Função Lambda principal
    
    AWS Lambda Powertools gerencia automaticamente:
    - Routing de rotas REST
    - CORS
    - Serialização JSON
    - Error handling
    - Logging estruturado
    - Tracing com X-Ray (em produção)
    
    Rotas disponíveis:
    - GET  /api/cities/neighbors/{cityId}?radius=50
    - GET  /api/weather/city/{cityId}
    - POST /api/weather/regional
    """
    return app.resolve(event, context)


