"""
Fixtures compartilhadas para testes de integração
"""
import pytest
import json
from typing import Dict, Any, Optional


class MockContext:
    """Mock do Lambda Context para testes locais"""
    def __init__(self):
        self.function_name = 'weather-forecast-api'
        self.function_version = '$LATEST'
        self.invoked_function_arn = 'arn:aws:lambda:sa-east-1:123456789012:function:weather-forecast-api'
        self.memory_limit_in_mb = '512'
        self.aws_request_id = 'test-request-id-12345'
        self.log_group_name = '/aws/lambda/weather-forecast-api'
        self.log_stream_name = '2025/11/18/[$LATEST]test'
    
    def get_remaining_time_in_millis(self):
        return 30000  # 30 segundos


@pytest.fixture
def mock_context():
    """Fixture que retorna MockContext para todos os testes"""
    return MockContext()


def build_api_gateway_event(
    method: str,
    path: str,
    resource: str,
    path_parameters: Optional[Dict[str, str]] = None,
    query_parameters: Optional[Dict[str, str]] = None,
    body: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Builder genérico para eventos do API Gateway
    
    Args:
        method: HTTP method (GET, POST, etc)
        path: Request path (/api/weather/city/123)
        resource: API Gateway resource (/api/weather/city/{city_id})
        path_parameters: Path params dict (e.g. {'city_id': '123'})
        query_parameters: Query string params dict
        body: Request body dict (will be JSON encoded)
    """
    event = {
        'resource': resource,
        'path': path,
        'httpMethod': method,
        'headers': {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        'pathParameters': path_parameters,
        'queryStringParameters': query_parameters,
        'body': json.dumps(body) if body else None,
        'isBase64Encoded': False
    }
    return event


def build_neighbors_event(city_id: str, radius: str = '50') -> Dict[str, Any]:
    """
    Builder para evento GET /api/cities/neighbors/{city_id}?radius=50
    
    Args:
        city_id: ID da cidade centro
        radius: Raio em km (default 50)
    """
    return build_api_gateway_event(
        method='GET',
        path=f'/api/cities/neighbors/{city_id}',
        resource='/api/cities/neighbors/{city_id}',
        path_parameters={'city_id': city_id},
        query_parameters={'radius': radius}
    )


def build_weather_event(city_id: str, date: Optional[str] = None, time: Optional[str] = None) -> Dict[str, Any]:
    """
    Builder para evento GET /api/weather/city/{city_id}?date=2025-01-15&time=14:00
    
    Args:
        city_id: ID da cidade
        date: Data no formato YYYY-MM-DD (opcional)
        time: Hora no formato HH:MM (opcional)
    """
    query_params = {}
    if date:
        query_params['date'] = date
    if time:
        query_params['time'] = time
    
    return build_api_gateway_event(
        method='GET',
        path=f'/api/weather/city/{city_id}',
        resource='/api/weather/city/{city_id}',
        path_parameters={'city_id': city_id},
        query_parameters=query_params if query_params else None
    )


def build_regional_event(city_ids: list[str], date: Optional[str] = None, time: Optional[str] = None) -> Dict[str, Any]:
    """
    Builder para evento POST /api/weather/regional
    
    Args:
        city_ids: Lista de IDs de cidades
        date: Data no formato YYYY-MM-DD (opcional)
        time: Hora no formato HH:MM (opcional)
    """
    body_data = {'cityIds': city_ids}
    
    query_params = {}
    if date:
        query_params['date'] = date
    if time:
        query_params['time'] = time
    
    return build_api_gateway_event(
        method='POST',
        path='/api/weather/regional',
        resource='/api/weather/regional',
        body=body_data,
        query_parameters=query_params if query_params else None
    )


@pytest.fixture
def ribeirao_preto_id():
    """ID da cidade de Ribeirão Preto (usada em todos os testes)"""
    return '3543204'


@pytest.fixture
def sao_carlos_id():
    """ID da cidade de São Carlos"""
    return '3548708'


@pytest.fixture
def campinas_id():
    """ID da cidade de Campinas"""
    return '3509502'


@pytest.fixture
def test_city_ids(ribeirao_preto_id, sao_carlos_id, campinas_id):
    """Lista de IDs de cidades para testes regionais"""
    return [ribeirao_preto_id, sao_carlos_id, campinas_id]
