"""
Lambda Function Handler - Clean Architecture
Presentation Layer: gerencia requisições HTTP e delega para use cases
"""
import json
import logging
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext

# Application Layer
from application.use_cases.get_neighbor_cities import GetNeighborCitiesUseCase
from application.use_cases.get_city_weather import GetCityWeatherUseCase
from application.use_cases.get_regional_weather import GetRegionalWeatherUseCase

# Infrastructure Layer
from infrastructure.repositories.municipalities_repository import get_repository
from infrastructure.repositories.weather_repository import get_weather_repository

from config import DEFAULT_RADIUS

# Configurar Powertools
logger = Logger()
tracer = Tracer()

app = APIGatewayRestResolver()

# Dependency Injection: inicializar repositórios (singleton, carrega apenas uma vez)
city_repository = get_repository()
weather_repository = get_weather_repository()

# Inicializar use cases
get_neighbors_use_case = GetNeighborCitiesUseCase(city_repository)
get_city_weather_use_case = GetCityWeatherUseCase(city_repository, weather_repository)
get_regional_weather_use_case = GetRegionalWeatherUseCase(city_repository, weather_repository)


@app.get("/api/cities/neighbors/<city_id>")
@tracer.capture_method
def get_neighbors_route(city_id: str):
    """
    GET /api/cities/neighbors/{cityId}?radius=50
    
    Retorna a cidade centro e suas cidades vizinhas dentro de um raio
    """
    logger.info(f"Buscando vizinhos de {city_id}")
    
    # Extrair raio da query string
    radius = float(app.current_event.get_query_string_value(
        name="radius",
        default_value=str(DEFAULT_RADIUS)
    ))
    
    try:
        # Executar use case
        result = get_neighbors_use_case.execute(city_id, radius)
        
        # Converter entidades para formato API
        response = {
            'centerCity': result['centerCity'].to_api_response(),
            'neighbors': [n.to_api_response() for n in result['neighbors']]
        }
        
        logger.info(f"Encontradas {len(response['neighbors'])} cidades vizinhas de {result['centerCity'].name}")
        
        return response
        
    except ValueError as e:
        return {
            'statusCode': 404 if 'não encontrada' in str(e) else 400,
            'body': {
                'error': 'Not Found' if 'não encontrada' in str(e) else 'Bad Request',
                'message': str(e)
            }
        }


@app.get("/api/weather/city/<city_id>")
@tracer.capture_method
def get_city_weather_route(city_id: str):
    """
    GET /api/weather/city/{cityId}
    
    Retorna dados climáticos de uma cidade específica
    """
    logger.info(f"Buscando dados climáticos de {city_id}")
    
    try:
        # Executar use case
        weather = get_city_weather_use_case.execute(city_id)
        
        # Atualizar city_id na entidade Weather
        weather.city_id = city_id
        
        # Converter entidade para formato API
        response = weather.to_api_response()
        
        logger.info(f"Dados climáticos de {weather.city_name}: {weather.temperature}°C")
        
        return response
        
    except ValueError as e:
        return {
            'statusCode': 404 if 'não encontrada' in str(e) else 400,
            'body': {
                'error': 'Not Found' if 'não encontrada' in str(e) else 'Bad Request',
                'message': str(e)
            }
        }
    except Exception as e:
        logger.error(f"Erro ao buscar clima: {e}")
        return {
            'statusCode': 500,
            'body': {
                'error': 'Internal Server Error',
                'message': 'Erro ao buscar dados meteorológicos'
            }
        }


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
    
    try:
        # Executar use case
        weather_list = get_regional_weather_use_case.execute(city_ids)
        
        # Converter para formato API
        response = [weather.to_api_response() for weather in weather_list]
        
        logger.info(f"Dados climáticos regionais: {len(response)} cidades")
        
        return response
        
    except Exception as e:
        logger.error(f"Erro ao buscar clima regional: {e}")
        return {
            'statusCode': 500,
            'body': {
                'error': 'Internal Server Error',
                'message': 'Erro ao buscar dados meteorológicos'
            }
        }


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
