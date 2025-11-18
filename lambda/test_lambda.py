"""
Script de teste local do Lambda
Simula invocações do API Gateway
"""
from lambda_function import lambda_handler
import json


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
    print("TEST 1: GET /api/cities/neighbors/3550308?radius=50")
    print("(São Paulo e vizinhos)")
    print("="*70)
    
    event = {
        'resource': '/api/cities/neighbors/{city_id}',
        'path': '/api/cities/neighbors/3550308',
        'httpMethod': 'GET',
        'headers': {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        'queryStringParameters': {
            'radius': '50'
        },
        'pathParameters': {
            'city_id': '3550308'
        },
        'body': None,
        'isBase64Encoded': False
    }
    
    context = MockContext()
    response = lambda_handler(event, context)
    
    print(f"\nStatus: {response['statusCode']}")
    
    body = json.loads(response['body'])
    
    if response['statusCode'] == 200:
        print(f"Cidade centro: {body['centerCity']['name']}")
        print(f"Vizinhos encontrados: {len(body['neighbors'])}")
        
        if body['neighbors']:
            print("\nPrimeiros 5 vizinhos:")
            for neighbor in body['neighbors'][:5]:
                print(f"  - {neighbor['name']} ({neighbor['distance']:.1f} km)")
    else:
        print(f"Erro: {body}")
    
    return response


def test_get_city_weather():
    """Testa rota GET /api/weather/city/{cityId}"""
    print("\n" + "="*70)
    print("TEST 2: GET /api/weather/city/3550308")
    print("(Clima de São Paulo)")
    print("="*70)
    
    event = {
        'resource': '/api/weather/city/{city_id}',
        'path': '/api/weather/city/3550308',
        'httpMethod': 'GET',
        'headers': {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        'queryStringParameters': None,
        'pathParameters': {
            'city_id': '3550308'
        },
        'body': None,
        'isBase64Encoded': False
    }
    
    context = MockContext()
    response = lambda_handler(event, context)
    
    print(f"\nStatus: {response['statusCode']}")
    
    body = json.loads(response['body'])
    
    if response['statusCode'] == 200:
        print(f"Cidade: {body.get('cityName')}/{body.get('state')}")
        print(f"Fonte: {body.get('source')}")
        print(f"Temperatura: {body.get('temperature')}°C")
        print(f"Umidade: {body.get('humidity')}%")
        print(f"Vento: {body.get('wind_speed')} km/h")
        print(f"Condição: {body.get('weather_description')}")
    else:
        print(f"Erro: {body}")
    
    return response


def test_post_regional_weather():
    """Testa rota POST /api/weather/regional"""
    print("\n" + "="*70)
    print("TEST 3: POST /api/weather/regional")
    print("(Clima de São Paulo, Rio de Janeiro, Brasília)")
    print("="*70)
    
    body_data = {
        'cityIds': ['3550308', '3304557', '5300108']
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
    
    print(f"\nStatus: {response['statusCode']}")
    
    body = json.loads(response['body'])
    
    if response['statusCode'] == 200:
        print(f"Cidades processadas: {len(body)}")
        
        for weather in body:
            print(f"\n  {weather.get('cityName')}/{weather.get('state')}:")
            print(f"    Temperatura: {weather.get('temperature')}°C")
            print(f"    Umidade: {weather.get('humidity')}%")
            print(f"    Fonte: {weather.get('source')}")
    else:
        print(f"Erro: {body}")
    
    return response


if __name__ == '__main__':
    print("="*70)
    print("🧪 TESTES DO LAMBDA WEATHER FORECAST API")
    print("="*70)
    
    # Executar testes
    test_get_neighbors()
    test_get_city_weather()
    test_post_regional_weather()
    
    print("\n" + "="*70)
    print("✅ TESTES CONCLUÍDOS")
    print("="*70)
