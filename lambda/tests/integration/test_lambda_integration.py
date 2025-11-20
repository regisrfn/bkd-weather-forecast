"""
Script de teste de integração do Lambda
Simula invocações do API Gateway com asserts
Usando cidade 3543204 (Ribeirão Preto)
Executar: pytest tests/integration/test_lambda_integration.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambda'))

import pytest
from infrastructure.adapters.input.lambda_handler import lambda_handler
import json
from datetime import datetime, timedelta


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


def test_get_neighbors():
    """Testa rota GET /api/cities/neighbors/{cityId}"""
    print("\n" + "="*70)
    print("TEST 1: GET /api/cities/neighbors/3543204?radius=50")
    print("(Ribeirão Preto e vizinhos)")
    print("="*70)
    
    event = {
        'resource': '/api/cities/neighbors/{city_id}',
        'path': '/api/cities/neighbors/3543204',
        'httpMethod': 'GET',
        'headers': {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        'queryStringParameters': {
            'radius': '50'
        },
        'pathParameters': {
            'city_id': '3543204'
        },
        'body': None,
        'isBase64Encoded': False
    }
    
    context = MockContext()
    response = lambda_handler(event, context)
    
    # Asserts
    assert response['statusCode'] == 200, f"Expected 200, got {response['statusCode']}"
    assert 'body' in response, "Response should have body"
    assert 'headers' in response, "Response should have headers"
    
    body = json.loads(response['body'])
    
    # Validar estrutura da resposta
    assert 'centerCity' in body, "Response should contain centerCity"
    assert 'neighbors' in body, "Response should contain neighbors"
    
    # Validar cidade centro
    center_city = body['centerCity']
    assert center_city['id'] == '3543204', "Center city ID should be 3543204"
    assert 'name' in center_city, "Center city should have name"
    assert 'latitude' in center_city, "Center city should have latitude"
    assert 'longitude' in center_city, "Center city should have longitude"
    
    # Validar vizinhos
    neighbors = body['neighbors']
    assert isinstance(neighbors, list), "Neighbors should be a list"
    assert len(neighbors) > 0, "Should have at least one neighbor"
    
    # Validar estrutura dos vizinhos
    first_neighbor = neighbors[0]
    assert 'id' in first_neighbor, "Neighbor should have id"
    assert 'name' in first_neighbor, "Neighbor should have name"
    assert 'distance' in first_neighbor, "Neighbor should have distance"
    assert first_neighbor['distance'] <= 50, "All neighbors should be within 50km"
    
    print(f"✅ Status: {response['statusCode']}")
    print(f"✅ Cidade centro: {center_city['name']}")
    print(f"✅ Vizinhos encontrados: {len(neighbors)}")


def test_get_city_weather():
    """Testa rota GET /api/weather/city/{cityId}"""
    print("\n" + "="*70)
    print("TEST 2: GET /api/weather/city/3543204")
    print("(Previsão de Ribeirão Preto - próxima disponível)")
    print("="*70)
    
    event = {
        'resource': '/api/weather/city/{city_id}',
        'path': '/api/weather/city/3543204',
        'httpMethod': 'GET',
        'headers': {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        'queryStringParameters': None,
        'pathParameters': {
            'city_id': '3543204'
        },
        'body': None,
        'isBase64Encoded': False
    }
    
    context = MockContext()
    response = lambda_handler(event, context)
    
    # Asserts
    assert response['statusCode'] == 200, f"Expected 200, got {response['statusCode']}"
    
    body = json.loads(response['body'])
    
    # Validar campos obrigatórios
    assert 'cityId' in body, "Response should contain cityId"
    assert 'cityName' in body, "Response should contain cityName"
    assert 'timestamp' in body, "Response should contain timestamp"
    assert 'temperature' in body, "Response should contain temperature"
    assert 'humidity' in body, "Response should contain humidity"
    assert 'windSpeed' in body, "Response should contain windSpeed"
    assert 'rainfallIntensity' in body, "Response should contain rainfallIntensity"
    
    # Validar tipos e ranges
    assert isinstance(body['temperature'], (int, float)), "Temperature should be numeric"
    assert -50 <= body['temperature'] <= 60, "Temperature should be in reasonable range"
    assert 0 <= body['humidity'] <= 100, "Humidity should be 0-100%"
    assert body['windSpeed'] >= 0, "Wind speed should be non-negative"
    assert 0 <= body['rainfallIntensity'] <= 100, "Rain probability should be 0-100%"
    
    print(f"✅ Status: {response['statusCode']}")
    print(f"✅ Cidade: {body.get('cityName')}")
    print(f"✅ Temperatura: {body.get('temperature')}°C")


def test_post_regional_weather():
    """Testa rota POST /api/weather/regional"""
    print("\n" + "="*70)
    print("TEST 3: POST /api/weather/regional")
    print("(Ribeirão Preto, São Carlos, Campinas)")
    print("="*70)
    
    body_data = {
        'cityIds': ['3543204', '3548708', '3509502']
    }
    
    event = {
        'resource': '/api/weather/regional',
        'path': '/api/weather/regional',
        'httpMethod': 'POST',
        'headers': {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        'queryStringParameters': None,
        'pathParameters': None,
        'body': json.dumps(body_data),
        'isBase64Encoded': False
    }
    
    context = MockContext()
    response = lambda_handler(event, context)
    
    # Asserts
    assert response['statusCode'] == 200, f"Expected 200, got {response['statusCode']}"
    
    body = json.loads(response['body'])
    
    # Validar resposta
    assert isinstance(body, list), "Response should be a list"
    assert len(body) == 3, f"Should have 3 cities, got {len(body)}"
    
    # Validar estrutura de cada cidade
    for weather in body:
        assert 'cityId' in weather, "Weather should contain cityId"
        assert 'cityName' in weather, "Weather should contain cityName"
        assert 'temperature' in weather, "Weather should contain temperature"
        assert 'humidity' in weather, "Weather should contain humidity"
        assert 'rainfallIntensity' in weather, "Weather should contain rainfallIntensity"
        
        # Validar ranges
        assert -50 <= weather['temperature'] <= 60, "Temperature in reasonable range"
        assert 0 <= weather['humidity'] <= 100, "Humidity 0-100%"
        assert 0 <= weather['rainfallIntensity'] <= 100, "Rain probability 0-100%"
    
    print(f"✅ Status: {response['statusCode']}")
    print(f"✅ Cidades processadas: {len(body)}")


if __name__ == '__main__':
    print("="*70)
    print("🧪 TESTES DE INTEGRAÇÃO - WEATHER FORECAST API")
    print("   Cidade de teste: Ribeirão Preto (ID: 3543204)")
    print("="*70)
    
    # Executar testes manualmente (sem pytest)
    try:
        test_get_neighbors()
        test_get_city_weather()
        test_post_regional_weather()
        
        print("\n" + "="*70)
        print("✅ TODOS OS TESTES DE INTEGRAÇÃO PASSARAM!")
        print("="*70)
    except AssertionError as e:
        print("\n" + "="*70)
        print(f"❌ TESTE FALHOU: {e}")
        print("="*70)
        exit(1)
    except Exception as e:
        print("\n" + "="*70)
        print(f"❌ ERRO INESPERADO: {e}")
        print("="*70)
        exit(1)
