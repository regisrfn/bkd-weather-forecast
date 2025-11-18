import json
import logging
import os
from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext

from cities_data import get_city_by_id, get_all_cities, CITIES_DATABASE
from cities_service import get_neighbors, validate_radius
from weather_service import get_weather_for_city, get_regional_weather
from config import DEFAULT_RADIUS

# Configurar Powertools
logger = Logger()

# Tracer só em produção (requer aws-xray-sdk)
if os.environ.get('AWS_EXECUTION_ENV'):
    from aws_lambda_powertools import Tracer
    tracer = Tracer()
    def trace_method(func):
        return tracer.capture_method(func)
else:
    def trace_method(func):
        return func

app = APIGatewayRestResolver()


@app.get("/api/cities/neighbors/<city_id>")
@trace_method
def get_neighbors_route(city_id: str):
    """
    GET /api/cities/neighbors/{cityId}?radius=50
    
    Retorna a cidade centro e suas cidades vizinhas dentro de um raio
    """
    logger.info(f"Buscando vizinhos de {city_id}")
    
    # Buscar cidade centro
    center_city = get_city_by_id(city_id)
    if not center_city:
        return {
            'statusCode': 404,
            'body': {
                'error': 'Not Found',
                'message': f'Cidade {city_id} não encontrada'
            }
        }
    
    # Extrair e validar raio
    radius = validate_radius(app.current_event.get_query_string_value(name="radius", default_value=str(DEFAULT_RADIUS)))
    
    # Buscar cidades vizinhas
    all_cities = get_all_cities()
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
@trace_method
def get_city_weather_route(city_id: str):
    """
    GET /api/weather/city/{cityId}
    
    Retorna dados climáticos de uma cidade específica
    """
    logger.info(f"Buscando dados climáticos de {city_id}")
    
    # Buscar dados da cidade
    city = get_city_by_id(city_id)
    if not city:
        return {
            'statusCode': 404,
            'body': {
                'error': 'Not Found',
                'message': f'Cidade {city_id} não encontrada'
            }
        }
    
    # Buscar dados climáticos
    weather = get_weather_for_city(
        city_id=city['id'],
        city_name=city['name'],
        lat=city['latitude'],
        lon=city['longitude']
    )
    
    logger.info(f"Dados climáticos de {city['name']}: {weather}")
    
    return weather


@app.post("/api/weather/regional")
@trace_method
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
    weather_data = get_regional_weather(city_ids, CITIES_DATABASE)
    
    logger.info(f"Dados climáticos regionais: {len(weather_data)} cidades")
    
    return weather_data


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
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


