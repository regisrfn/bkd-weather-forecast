"""
Helpers de assertions para testes de integração
"""
import json
from typing import Dict, Any


def assert_200_ok(response: Dict[str, Any], expected_content_type: str = 'application/json'):
    """
    Valida resposta 200 OK
    
    Args:
        response: Lambda response dict
        expected_content_type: Content-Type esperado
    
    Raises:
        AssertionError: Se a resposta não for 200 ou não tiver estrutura correta
    """
    assert response['statusCode'] == 200, f"Expected 200, got {response['statusCode']}"
    assert 'body' in response, "Response should have body"
    
    # AWS Powertools pode retornar headers ou multiValueHeaders
    if 'multiValueHeaders' in response:
        content_type = response['multiValueHeaders'].get('Content-Type', [None])[0]
    elif 'headers' in response:
        content_type = response['headers'].get('Content-Type')
    else:
        content_type = None
    
    assert content_type == expected_content_type, \
        f"Content-Type should be {expected_content_type}, got {content_type}"


def assert_404_not_found(response: Dict[str, Any]):
    """
    Valida resposta 404 Not Found
    
    Args:
        response: Lambda response dict
    
    Raises:
        AssertionError: Se a resposta não for 404 ou não tiver estrutura de erro
    """
    assert response['statusCode'] == 404, f"Expected 404, got {response['statusCode']}"
    
    body = json.loads(response['body'])
    assert 'error' in body, "404 response should contain 'error' field"
    assert 'type' in body, "404 response should contain 'type' field"
    assert body['type'] == 'CityNotFoundException' or body['type'] == 'CoordinatesNotFoundException' or \
           body['type'] == 'WeatherDataNotFoundException', \
           f"404 error type should be Not Found exception, got {body['type']}"


def assert_400_bad_request(response: Dict[str, Any]):
    """
    Valida resposta 400 Bad Request
    
    Args:
        response: Lambda response dict
    
    Raises:
        AssertionError: Se a resposta não for 400 ou não tiver estrutura de erro
    """
    assert response['statusCode'] == 400, f"Expected 400, got {response['statusCode']}"
    
    body = json.loads(response['body'])
    assert 'error' in body, "400 response should contain 'error' field"
    assert 'type' in body, "400 response should contain 'type' field"
    assert body['type'] in ['InvalidRadiusException', 'InvalidDateTimeException', 'ValidationError'], \
           f"400 error type should be validation exception, got {body['type']}"


def assert_500_error(response: Dict[str, Any]):
    """
    Valida resposta 500 Internal Server Error
    
    Args:
        response: Lambda response dict
    
    Raises:
        AssertionError: Se a resposta não for 500 ou não tiver estrutura de erro
    """
    assert response['statusCode'] == 500, f"Expected 500, got {response['statusCode']}"
    
    body = json.loads(response['body'])
    assert 'error' in body, "500 response should contain 'error' field"
    assert 'type' in body, "500 response should contain 'type' field"


def assert_weather_structure(weather: Dict[str, Any]):
    """
    Valida estrutura de um objeto Weather
    
    Args:
        weather: Dict com dados de clima
    
    Raises:
        AssertionError: Se faltarem campos obrigatórios ou valores estiverem fora do range
    """
    # Campos obrigatórios
    required_fields = ['cityId', 'cityName', 'timestamp', 'temperature', 
                       'humidity', 'windSpeed', 'rainfallIntensity']
    for field in required_fields:
        assert field in weather, f"Weather should contain '{field}'"
    
    # Validar tipos e ranges
    assert isinstance(weather['temperature'], (int, float)), "Temperature should be numeric"
    assert -50 <= weather['temperature'] <= 60, \
           f"Temperature should be in reasonable range (-50 to 60°C), got {weather['temperature']}"
    
    assert isinstance(weather['humidity'], (int, float)), "Humidity should be numeric"
    assert 0 <= weather['humidity'] <= 100, \
           f"Humidity should be 0-100%, got {weather['humidity']}"
    
    assert isinstance(weather['windSpeed'], (int, float)), "Wind speed should be numeric"
    assert weather['windSpeed'] >= 0, \
           f"Wind speed should be non-negative, got {weather['windSpeed']}"
    
    assert isinstance(weather['rainfallIntensity'], (int, float)), "Rainfall intensity should be numeric"
    assert 0 <= weather['rainfallIntensity'] <= 100, \
           f"Rainfall intensity should be 0-100%, got {weather['rainfallIntensity']}"


def assert_neighbor_city_structure(neighbor: Dict[str, Any], max_distance: float):
    """
    Valida estrutura de um NeighborCity
    
    Args:
        neighbor: Dict com dados de vizinho
        max_distance: Distância máxima permitida (raio)
    
    Raises:
        AssertionError: Se faltarem campos obrigatórios ou distância exceder limite
    """
    required_fields = ['id', 'name', 'distance']
    for field in required_fields:
        assert field in neighbor, f"Neighbor should contain '{field}'"
    
    assert isinstance(neighbor['distance'], (int, float)), "Distance should be numeric"
    assert neighbor['distance'] <= max_distance, \
           f"Neighbor distance ({neighbor['distance']}km) should not exceed {max_distance}km"
    assert neighbor['distance'] >= 0, "Distance should be non-negative"


def assert_center_city_structure(center_city: Dict[str, Any], expected_id: str):
    """
    Valida estrutura de centerCity na resposta de neighbors
    
    Args:
        center_city: Dict com dados da cidade centro
        expected_id: ID esperado da cidade
    
    Raises:
        AssertionError: Se faltarem campos obrigatórios ou ID não bater
    """
    required_fields = ['id', 'name', 'latitude', 'longitude']
    for field in required_fields:
        assert field in center_city, f"Center city should contain '{field}'"
    
    assert center_city['id'] == expected_id, \
           f"Center city ID should be {expected_id}, got {center_city['id']}"
    
    # Validar coordenadas
    assert -90 <= center_city['latitude'] <= 90, "Latitude should be -90 to 90"
    assert -180 <= center_city['longitude'] <= 180, "Longitude should be -180 to 180"
