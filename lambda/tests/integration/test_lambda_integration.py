"""
Testes de integração do Lambda - Weather Forecast API
Organizados em classes pytest para melhor estruturação
Executar: pytest tests/integration/test_lambda_integration.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambda'))

import pytest
from infrastructure.adapters.input.lambda_handler import lambda_handler
import json

# Import fixtures e assertions
from tests.integration.conftest import (
    mock_context, 
    build_neighbors_event, 
    build_weather_event, 
    build_regional_event,
    ribeirao_preto_id,
    test_city_ids
)
from tests.integration.assertions import (
    assert_200_ok,
    assert_404_not_found,
    assert_400_bad_request,
    assert_weather_structure,
    assert_neighbor_city_structure,
    assert_center_city_structure
)


class TestNeighborsEndpoint:
    """Testes do endpoint GET /api/cities/neighbors/{city_id}"""
    
    def test_get_neighbors_success(self, mock_context, ribeirao_preto_id):
        """Testa busca de vizinhos com sucesso (Ribeirão Preto, raio 50km)"""
        event = build_neighbors_event(city_id=ribeirao_preto_id, radius='50')
        response = lambda_handler(event, mock_context)
        
        # Validar resposta 200
        assert_200_ok(response)
        
        body = json.loads(response['body'])
        
        # Validar estrutura da resposta
        assert 'centerCity' in body, "Response should contain centerCity"
        assert 'neighbors' in body, "Response should contain neighbors"
        
        # Validar cidade centro
        assert_center_city_structure(body['centerCity'], ribeirao_preto_id)
        
        # Validar vizinhos
        neighbors = body['neighbors']
        assert isinstance(neighbors, list), "Neighbors should be a list"
        assert len(neighbors) > 0, "Should have at least one neighbor"
        
        # Validar estrutura de cada vizinho
        for neighbor in neighbors:
            assert_neighbor_city_structure(neighbor, max_distance=50.0)
    
    def test_invalid_radius_returns_400(self, mock_context, ribeirao_preto_id):
        """Testa erro 400 com raio inválido (maior que 500km)"""
        event = build_neighbors_event(city_id=ribeirao_preto_id, radius='999')
        response = lambda_handler(event, mock_context)
        
        assert_400_bad_request(response)
        
        body = json.loads(response['body'])
        assert 'details' in body, "400 error should contain details"
        # Details should have radius, min, max fields
        assert 'max' in body['details'], "Should specify max in details"
        assert body['details']['max'] == 500.0, "Max should be 500.0"
    
    def test_city_not_found_returns_404(self, mock_context):
        """Testa erro 404 quando cidade não existe"""
        event = build_neighbors_event(city_id='9999999', radius='50')
        response = lambda_handler(event, mock_context)
        
        assert_404_not_found(response)


class TestWeatherEndpoint:
    """Testes do endpoint GET /api/weather/city/{city_id}"""
    
    def test_get_city_weather_success(self, mock_context, ribeirao_preto_id):
        """Testa busca de previsão de tempo com sucesso"""
        event = build_weather_event(city_id=ribeirao_preto_id)
        response = lambda_handler(event, mock_context)
        
        # Validar resposta 200
        assert_200_ok(response)
        
        body = json.loads(response['body'])
        
        # Validar estrutura completa do Weather
        assert_weather_structure(body)
        
        # Validar cidade específica
        assert body['cityId'] == ribeirao_preto_id
    
    def test_city_not_found_returns_404(self, mock_context):
        """Testa erro 404 quando cidade não existe"""
        event = build_weather_event(city_id='9999999')
        response = lambda_handler(event, mock_context)
        
        assert_404_not_found(response)


class TestRegionalEndpoint:
    """Testes do endpoint POST /api/weather/regional"""
    
    def test_post_regional_weather_success(self, mock_context, test_city_ids):
        """Testa busca regional de clima para 3 cidades"""
        event = build_regional_event(city_ids=test_city_ids)
        response = lambda_handler(event, mock_context)
        
        # Validar resposta 200
        assert_200_ok(response)
        
        body = json.loads(response['body'])
        
        # Validar lista de resultados
        assert isinstance(body, list), "Response should be a list"
        assert len(body) == len(test_city_ids), \
               f"Should have {len(test_city_ids)} cities, got {len(body)}"
        
        # Validar estrutura de cada cidade
        for weather in body:
            assert_weather_structure(weather)
        
        # Validar que todas as cidades foram retornadas
        returned_ids = {w['cityId'] for w in body}
        expected_ids = set(test_city_ids)
        assert returned_ids == expected_ids, \
               f"Expected cities {expected_ids}, got {returned_ids}"
    
    def test_empty_city_list_returns_empty(self, mock_context):
        """Testa que lista vazia de cidades retorna lista vazia"""
        event = build_regional_event(city_ids=[])
        response = lambda_handler(event, mock_context)
        
        assert_200_ok(response)
        
        body = json.loads(response['body'])
        assert body == [], "Empty input should return empty list"
