"""
Input Adapter: Lambda Handler HTTP (100% ASYNC)
Presentation Layer: gerencia requisições HTTP e delega para use cases
"""
import json
import asyncio
from datetime import datetime
from aws_lambda_powertools.event_handler import APIGatewayRestResolver, CORSConfig
from aws_lambda_powertools.utilities.typing import LambdaContext

# Application Layer - Use Cases (ASYNC)
from application.use_cases.get_neighbor_cities_use_case import AsyncGetNeighborCitiesUseCase
from application.use_cases.get_city_weather_use_case import AsyncGetCityWeatherUseCase
from application.use_cases.get_regional_weather_use_case import GetRegionalWeatherUseCase
from application.use_cases.get_city_detailed_forecast_use_case import GetCityDetailedForecastUseCase

# Domain Layer - Exceptions
from domain.exceptions import (
    CityNotFoundException,
    CoordinatesNotFoundException,
    InvalidRadiusException,
    InvalidDateTimeException,
    WeatherDataNotFoundException
)

# Infrastructure Layer - Adapters
from infrastructure.adapters.input.exception_handler_service import ExceptionHandlerService
from infrastructure.adapters.output.municipalities_repository import get_repository
from infrastructure.adapters.output.providers.weather_provider_factory import get_weather_provider_factory

# Shared Layer - Utilities
from shared.config.settings import DEFAULT_RADIUS
from shared.utils.datetime_parser import DateTimeParser
from shared.utils.validators import RadiusValidator, CityIdValidator
from shared.config.logger_config import get_logger

# Configurar Logger com service name do DD_SERVICE
logger = get_logger()

app = APIGatewayRestResolver(cors=CORSConfig(allow_origin="*"))

# =============================
# Global Event Loop (persistente entre invocações Lambda)
# =============================
_global_event_loop = None

# =============================
# Exception Handlers (Delegados para ExceptionHandlerService)
# =============================

exception_service = ExceptionHandlerService()

app.exception_handler(CityNotFoundException)(exception_service.handle_city_not_found)
app.exception_handler(CoordinatesNotFoundException)(exception_service.handle_coordinates_not_found)
app.exception_handler(InvalidRadiusException)(exception_service.handle_invalid_radius)
app.exception_handler(InvalidDateTimeException)(exception_service.handle_invalid_datetime)
app.exception_handler(WeatherDataNotFoundException)(exception_service.handle_weather_data_not_found)
app.exception_handler(ValueError)(exception_service.handle_value_error)
app.exception_handler(Exception)(exception_service.handle_unexpected_error)



# =============================
# Routes (Async execution with sync wrappers for AWS Powertools compatibility)
# =============================

@app.get("/api/cities/neighbors/<city_id>")
def get_neighbors_route(city_id: str):
    """
    GET /api/cities/neighbors/{cityId}?radius=50
    
    Returns center city and neighbor cities within radius
    
    Note: Uses persistent event loop for true client reuse
    """
    # Validate city ID
    CityIdValidator.validate(city_id)
    
    # Extract radius from query string
    radius = float(app.current_event.get_query_string_value(
        name="radius",
        default_value=str(DEFAULT_RADIUS)
    ))
    
    # Validate radius
    RadiusValidator.validate(radius)
    
    # Get city repository (sync singleton)
    city_repository = get_repository()
    
    # Execute async use case (Note: this use case doesn't fetch weather data)
    async def execute_async():
        # Execute use case (ASYNC)
        use_case = AsyncGetNeighborCitiesUseCase(city_repository)
        result = await use_case.execute(city_id, radius)
        
        return result
    
    # Run async code with persistent loop
    result = run_async(execute_async())
    
    # Convert to API format
    response = {
        'centerCity': result['centerCity'].to_api_response(),
        'neighbors': [n.to_api_response() for n in result['neighbors']]
    }
    
    return response


@app.get("/api/weather/city/<city_id>")
def get_city_weather_route(city_id: str):
    """
    GET /api/weather/city/{cityId}?date=2025-11-20&time=15:00
    
    Returns weather forecast for a specific city
    
    Query params (optional):
    - date: Date in format YYYY-MM-DD (ex: 2025-11-20)
    - time: Time in format HH:MM (ex: 15:00)
    
    Note: Uses persistent event loop for true client reuse
    """
    # Validate city ID
    CityIdValidator.validate(city_id)
    
    # Extract date and time from query string
    date_str = app.current_event.get_query_string_value(name="date", default_value=None)
    time_str = app.current_event.get_query_string_value(name="time", default_value=None)
    
    # Parse datetime (throws InvalidDateTimeException)
    target_datetime = DateTimeParser.from_query_params(date_str, time_str)
    
    # Get city repository e weather provider via factory
    city_repository = get_repository()
    factory = get_weather_provider_factory()
    weather_provider = factory.get_weather_provider()
    
    # Execute async use case
    async def execute_async():
        # Execute use case (ASYNC)
        use_case = AsyncGetCityWeatherUseCase(city_repository, weather_provider)
        weather = await use_case.execute(city_id, target_datetime)
        
        # Update city_id in Weather entity
        weather.city_id = city_id
        
        return weather
    
    # Run async code with persistent loop
    weather = run_async(execute_async())
    
    # Convert to API format
    response = weather.to_api_response()
    
    return response


@app.get("/api/weather/city/<city_id>/detailed")
def get_city_detailed_forecast_route(city_id: str):
    """
    GET /api/weather/city/{cityId}/detailed?date=2025-11-20&time=15:00
    
    Returns detailed forecast with extended data:
    - Current weather (extraído do hourly Open-Meteo)
    - Daily forecasts for 16 days (Open-Meteo API)
    - UV index, sunrise/sunset, precipitation hours
    
    Query params (optional):
    - date: Date in format YYYY-MM-DD (ex: 2025-11-20)
    - time: Time in format HH:MM (ex: 15:00)
    
    Note: Uses persistent event loop for true client reuse
    """
    # Validate city ID
    CityIdValidator.validate(city_id)
    
    # Extract date and time from query string
    date_str = app.current_event.get_query_string_value(name="date", default_value=None)
    time_str = app.current_event.get_query_string_value(name="time", default_value=None)
    
    # Parse datetime (throws InvalidDateTimeException)
    target_datetime = DateTimeParser.from_query_params(date_str, time_str)
    
    # Get city repository e providers via factory
    city_repository = get_repository()
    factory = get_weather_provider_factory()
    weather_provider = factory.get_weather_provider()
    
    # Execute async use case
    async def execute_async():
        # Execute use case (ASYNC with asyncio.gather for parallel calls)
        use_case = GetCityDetailedForecastUseCase(
            city_repository=city_repository,
            weather_provider=weather_provider
        )
        extended_forecast = await use_case.execute(city_id, target_datetime)
        
        return extended_forecast
    
    # Run async code with persistent loop
    extended_forecast = run_async(execute_async())
    
    # Convert to API format
    response = extended_forecast.to_api_response()
    
    return response


@app.post("/api/weather/regional")
def post_regional_weather_route():
    """
    POST /api/weather/regional?date=2025-11-20&time=15:00
    Body: { "cityIds": ["3543204", "3550506", ...] }
    
    100% ASYNC with aioboto3 + aiohttp - NO GIL
    Performance: 50-100+ cities in parallel with P99 latency <200ms
    
    Query params (optional):
    - date: Date in format YYYY-MM-DD (ex: 2025-11-20)
    - time: Time in format HH:MM (ex: 15:00)
    
    Note: Uses persistent event loop for true client reuse
    """
    # Extract cityIds from body
    body = app.current_event.json_body
    city_ids = body.get('cityIds', [])
    
    # Validate cityIds format
    if not isinstance(city_ids, list):
        raise InvalidDateTimeException(
            "cityIds must be an array of strings",
            details={"body": body}
        )
    
    # Validate all city IDs
    for city_id in city_ids:
        CityIdValidator.validate(city_id)
    
    # Extract date and time from query string
    date_str = app.current_event.get_query_string_value(name="date", default_value=None)
    time_str = app.current_event.get_query_string_value(name="time", default_value=None)
    
    # Parse datetime (throws InvalidDateTimeException)
    target_datetime = DateTimeParser.from_query_params(date_str, time_str)
    
    # Get city repository e weather provider via factory
    city_repository = get_repository()
    factory = get_weather_provider_factory()
    weather_provider = factory.get_weather_provider()
    
    # Execute async use case
    async def execute_async():
        # Execute use case (ASYNC with asyncio.gather)
        use_case = GetRegionalWeatherUseCase(
            city_repository=city_repository,
            weather_provider=weather_provider
        )
        weather_list = await use_case.execute(city_ids, target_datetime)
        
        return weather_list
    
    # Run async code with persistent loop
    weather_list = run_async(execute_async())
    
    # Convert to API format
    response = [weather.to_api_response() for weather in weather_list]
    
    return response




# =============================
# Lambda Handler (100% ASYNC)
# =============================

@logger.inject_lambda_context()
def lambda_handler(event, context: LambdaContext):
    """
    AWS Lambda main function - 100% ASYNC
    
    100% ASYNC with aioboto3 + aiohttp (NO GIL)
    Performance: 50-100+ cities in parallel with P99 latency <200ms
    
    AWS Lambda Powertools manages:
    - REST routing with exception handlers
    - CORS
    - JSON serialization
    - Structured logging
    
    Datadog APM manages:
    - Distributed tracing
    - Performance monitoring
    - Custom metrics
    
    Available routes:
    - GET  /api/cities/neighbors/{cityId}?radius=50
    - GET  /api/weather/city/{cityId}?date=2025-11-20&time=15:00
    - POST /api/weather/regional?date=2025-11-20&time=15:00
    
    Datetime parameters (optional):
    - date: YYYY-MM-DD (ex: 2025-11-20)
    - time: HH:MM (ex: 15:00)
    - If omitted, returns next available forecast
    """
    # Extrair IP de origem e session_id
    headers = event.get('headers', {}) or {}
    request_context = event.get('requestContext', {}) or {}
    identity = request_context.get('identity', {}) or {}
    
    logger.info(
        "Requisição Lambda recebida",
        rota=event.get('path', 'N/A'),
        metodo=event.get('httpMethod', 'N/A'),
        request_id=getattr(context, 'aws_request_id', 'N/A'),
        source_ip=identity.get('sourceIp', 'N/A'),
        session_id=headers.get('x-session-id', 'N/A')
    )
    
    response = app.resolve(event, context)
    
    # Add CORS headers manually
    if 'headers' not in response:
        response['headers'] = {}
    
    response['headers']['Access-Control-Allow-Origin'] = '*'
    response['headers']['Access-Control-Allow-Headers'] = 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Requested-With,X-Session-Id'
    response['headers']['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    response['headers']['Access-Control-Max-Age'] = '86400'
    
    status_code = response.get('statusCode', 'N/A')
    logger.info(
        "Requisição Lambda concluída",
        status_code=status_code,
        sucesso=status_code == 200
    )
    
    return response


def get_or_create_event_loop():
    """
    Retorna event loop global persistente
    
    Benefícios:
    - Reutiliza event loop entre invocações Lambda (warm starts)
    - Clientes aioboto3/aiohttp permanecem válidos
    - TRUE REUSE: Mesmos clientes em múltiplas invocações
    """
    global _global_event_loop
    
    # Se loop existe e não está fechado, reutilizar
    if _global_event_loop is not None and not _global_event_loop.is_closed():
        return _global_event_loop
    
    # Criar novo loop se necessário
    _global_event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_global_event_loop)
    
    return _global_event_loop


def run_async(coro):
    """
    Executa coroutine no event loop global (NÃO fecha o loop)
    
    Args:
        coro: Coroutine a ser executada
    
    Returns:
        Resultado da coroutine
    """
    loop = get_or_create_event_loop()
    return loop.run_until_complete(coro)
