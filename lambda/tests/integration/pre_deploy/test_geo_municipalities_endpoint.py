"""
Integration test: GET /api/geo/municipalities/{cityId}
Executa via lambda_handler (sem mocks) para garantir proxy do IBGE
"""
import json

from infrastructure.adapters.input.lambda_handler import lambda_handler


def test_get_geo_municipality_success(mock_context):
    """Deve retornar GeoJSON do município válido"""
    event = {
        'httpMethod': 'GET',
        'path': '/api/geo/municipalities/3510153',
        'pathParameters': {'city_id': '3510153'},
        'queryStringParameters': None,
        'headers': {},
        'requestContext': {'identity': {'sourceIp': '127.0.0.1'}}
    }

    response = lambda_handler(event, mock_context)

    assert response['statusCode'] == 200

    body = json.loads(response['body'])

    # Validar estrutura mínima do GeoJSON (FeatureCollection)
    assert isinstance(body, dict)
    assert body.get('type') in ('FeatureCollection', 'Feature')

    if body.get('type') == 'FeatureCollection':
        assert 'features' in body
        assert isinstance(body['features'], list)
        assert len(body['features']) > 0
        first = body['features'][0]
        assert 'geometry' in first and 'type' in first['geometry']
    else:
        # Caso IBGE retorne Feature diretamente
        assert 'geometry' in body
        assert 'type' in body['geometry']


def test_get_geo_municipality_not_found(mock_context):
    """Deve retornar 404 para cidade inexistente"""
    event = {
        'httpMethod': 'GET',
        'path': '/api/geo/municipalities/0000000',
        'pathParameters': {'city_id': '0000000'},
        'queryStringParameters': None,
        'headers': {},
        'requestContext': {'identity': {'sourceIp': '127.0.0.1'}}
    }

    response = lambda_handler(event, mock_context)

    assert response['statusCode'] == 404
