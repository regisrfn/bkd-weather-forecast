"""
Input Adapter: Lambda Handler HTTP
Presentation Layer: gerencia requisições HTTP e delega para use cases
"""
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayRestResolver, CORSConfig
from aws_lambda_powertools.utilities.typing import LambdaContext

# Application Layer - Use Cases
from application.use_cases.get_neighbor_cities import GetNeighborCitiesUseCase
from application.use_cases.get_city_weather import GetCityWeatherUseCase
from application.use_cases.get_regional_weather import GetRegionalWeatherUseCase

# Infrastructure Layer - Adapters
from infrastructure.adapters.output.municipalities_repository import get_repository
from infrastructure.adapters.output.weather_repository import get_weather_repository

from config import DEFAULT_RADIUS

# Configurar Powertools
logger = Logger()

app = APIGatewayRestResolver(cors=CORSConfig(allow_origin="*"))

# Dependency Injection: inicializar repositórios (singleton, carrega apenas uma vez)
city_repository = get_repository()
weather_repository = get_weather_repository()

# Inicializar use cases
get_neighbors_use_case = GetNeighborCitiesUseCase(city_repository)
get_city_weather_use_case = GetCityWeatherUseCase(city_repository, weather_repository)
get_regional_weather_use_case = GetRegionalWeatherUseCase(city_repository, weather_repository)


@app.get("/api/cities/neighbors/<city_id>")
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
def get_city_weather_route(city_id: str):
    """
    GET /api/weather/city/{cityId}?date=2025-11-20&time=15:00
    
    Retorna dados climáticos (previsão) de uma cidade específica
    
    Query params opcionais:
    - date: Data no formato YYYY-MM-DD (ex: 2025-11-20)
    - time: Hora no formato HH:MM (ex: 15:00)
    """
    logger.info(f"Buscando dados climáticos de {city_id}")
    
    # Extrair data e hora da query string (opcional)
    date_str = app.current_event.get_query_string_value(name="date", default_value=None)
    time_str = app.current_event.get_query_string_value(name="time", default_value=None)
    
    target_datetime = None
    
    # Timezone do Brasil (São Paulo)
    brazil_tz = ZoneInfo("America/Sao_Paulo")
    
    # Parsear data/hora se fornecidas
    if date_str or time_str:
        try:
            # Se apenas data, usa meio-dia
            if date_str and not time_str:
                target_datetime = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=12, tzinfo=brazil_tz)
            # Se apenas hora, usa hoje
            elif time_str and not date_str:
                from datetime import date
                today = date.today()
                time_obj = datetime.strptime(time_str, "%H:%M").time()
                target_datetime = datetime.combine(today, time_obj, tzinfo=brazil_tz)
            # Se ambos fornecidos
            else:
                datetime_str = f"{date_str} {time_str}"
                target_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M").replace(tzinfo=brazil_tz)
        except ValueError as e:
            return {
                'statusCode': 400,
                'body': {
                    'error': 'Bad Request',
                    'message': f'Formato de data/hora inválido. Use date=YYYY-MM-DD e time=HH:MM. Erro: {str(e)}'
                }
            }
    
    try:
        # Executar use case
        weather = get_city_weather_use_case.execute(city_id, target_datetime)
        
        # Atualizar city_id na entidade Weather
        weather.city_id = city_id
        
        # Converter entidade para formato API
        response = weather.to_api_response()
        
        logger.info(f"Dados climáticos de {weather.city_name}: {weather.temperature}°C, probabilidade de chuva: {weather.rain_probability}%")
        
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
def post_regional_weather_route():
    """
    POST /api/weather/regional?date=2025-11-20&time=15:00
    Body: { "cityIds": ["3543204", "3550506", ...] }
    
    Retorna dados climáticos (previsão) de múltiplas cidades
    
    Query params opcionais:
    - date: Data no formato YYYY-MM-DD (ex: 2025-11-20)
    - time: Hora no formato HH:MM (ex: 15:00)
    """
    logger.info("Buscando dados climáticos regionais")
    
    # Extrair cityIds do body
    body = app.current_event.json_body
    logger.info(f"Body recebido: {body}")
    city_ids = body.get('cityIds', [])
    logger.info(f"city_ids extraído: {city_ids}")
    
    if not city_ids or not isinstance(city_ids, list):
        return {
            'statusCode': 400,
            'body': {
                'error': 'Bad Request',
                'message': 'cityIds deve ser um array de strings'
            }
        }
    
    # Extrair data e hora da query string (opcional)
    date_str = app.current_event.get_query_string_value(name="date", default_value=None)
    time_str = app.current_event.get_query_string_value(name="time", default_value=None)
    
    target_datetime = None
    
    # Timezone do Brasil (São Paulo)
    brazil_tz = ZoneInfo("America/Sao_Paulo")
    
    # Parsear data/hora se fornecidas
    if date_str or time_str:
        try:
            from datetime import date
            # Se apenas data, usa meio-dia
            if date_str and not time_str:
                target_datetime = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=12, tzinfo=brazil_tz)
            # Se apenas hora, usa hoje
            elif time_str and not date_str:
                today = date.today()
                time_obj = datetime.strptime(time_str, "%H:%M").time()
                target_datetime = datetime.combine(today, time_obj, tzinfo=brazil_tz)
            # Se ambos fornecidos
            else:
                datetime_str = f"{date_str} {time_str}"
                target_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M").replace(tzinfo=brazil_tz)
        except ValueError as e:
            return {
                'statusCode': 400,
                'body': {
                    'error': 'Bad Request',
                    'message': f'Formato de data/hora inválido. Use date=YYYY-MM-DD e time=HH:MM. Erro: {str(e)}'
                }
            }
    
    try:
        # Executar use case
        weather_list = get_regional_weather_use_case.execute(city_ids, target_datetime)
        
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


@logger.inject_lambda_context()
def lambda_handler(event, context: LambdaContext):
    """
    Função Lambda principal
    
    AWS Lambda Powertools gerencia automaticamente:
    - Routing de rotas REST
    - CORS
    - Serialização JSON
    - Error handling
    - Logging estruturado
    
    Datadog APM gerencia:
    - Distributed tracing
    - Performance monitoring
    - Custom metrics
    
    Rotas disponíveis:
    - GET  /api/cities/neighbors/{cityId}?radius=50
    - GET  /api/weather/city/{cityId}?date=2025-11-20&time=15:00
    - POST /api/weather/regional?date=2025-11-20&time=15:00
    
    Parâmetros de data/hora (opcionais):
    - date: YYYY-MM-DD (ex: 2025-11-20)
    - time: HH:MM (ex: 15:00)
    - Se omitidos, retorna próxima previsão disponível
    """
    response = app.resolve(event, context)
    
    # Adicionar headers CORS manualmente
    if 'headers' not in response:
        response['headers'] = {}
    
    response['headers']['Access-Control-Allow-Origin'] = '*'
    response['headers']['Access-Control-Allow-Headers'] = 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Requested-With'
    response['headers']['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    response['headers']['Access-Control-Max-Age'] = '86400'
    
    return response
