"""
Script de teste local do Lambda
Simula invocações do API Gateway
Usando cidade 3543204 (Ribeirão do Sul)
"""
from lambda_function import lambda_handler
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
    print("(Ribeirão do Sul e vizinhos)")
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
    print("TEST 2: GET /api/weather/city/3543204")
    print("(Previsão de Ribeirão do Sul - próxima disponível)")
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
    
    print(f"\nStatus: {response['statusCode']}")
    
    body = json.loads(response['body'])
    
    if response['statusCode'] == 200:
        print(f"Cidade: {body.get('cityName')}")
        print(f"Data/Hora: {body.get('timestamp')}")
        print(f"Temperatura: {body.get('temperature')}°C")
        print(f"Umidade: {body.get('humidity')}%")
        print(f"Vento: {body.get('windSpeed')} km/h")
        print(f"Probabilidade de chuva: {body.get('rainfallIntensity')}%")
    else:
        print(f"Erro: {body}")
    
    return response


def test_get_city_weather_with_date():
    """Testa rota GET /api/weather/city/{cityId} com data específica"""
    print("\n" + "="*70)
    print("TEST 3: GET /api/weather/city/3543204?date=YYYY-MM-DD&time=15:00")
    print("(Previsão para amanhã às 15:00)")
    print("="*70)
    
    # Calcular data de amanhã
    tomorrow = datetime.now() + timedelta(days=1)
    date_str = tomorrow.strftime('%Y-%m-%d')
    
    event = {
        'resource': '/api/weather/city/{city_id}',
        'path': '/api/weather/city/3543204',
        'httpMethod': 'GET',
        'headers': {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        'queryStringParameters': {
            'date': date_str,
            'time': '15:00'
        },
        'pathParameters': {
            'city_id': '3543204'
        },
        'body': None,
        'isBase64Encoded': False
    }
    
    context = MockContext()
    response = lambda_handler(event, context)
    
    print(f"\nData solicitada: {date_str} 15:00")
    print(f"Status: {response['statusCode']}")
    
    body = json.loads(response['body'])
    
    if response['statusCode'] == 200:
        print(f"Cidade: {body.get('cityName')}")
        print(f"Data/Hora da previsão: {body.get('timestamp')}")
        print(f"Temperatura: {body.get('temperature')}°C")
        print(f"Probabilidade de chuva: {body.get('rainfallIntensity')}%")
    else:
        print(f"Erro: {body}")
    
    return response


def test_post_regional_weather():
    """Testa rota POST /api/weather/regional"""
    print("\n" + "="*70)
    print("TEST 4: POST /api/weather/regional")
    print("(Ribeirão do Sul, São Carlos, Campinas)")
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
    
    print(f"\nStatus: {response['statusCode']}")
    
    body = json.loads(response['body'])
    
    if response['statusCode'] == 200:
        print(f"Cidades processadas: {len(body)}")
        
        for weather in body:
            print(f"\n  {weather.get('cityName')}:")
            print(f"    Temperatura: {weather.get('temperature')}°C")
            print(f"    Umidade: {weather.get('humidity')}%")
            print(f"    Probabilidade de chuva: {weather.get('rainfallIntensity')}%")
    else:
        print(f"Erro: {body}")
    
    return response


def test_post_regional_weather_with_date():
    """Testa rota POST /api/weather/regional com data específica"""
    print("\n" + "="*70)
    print("TEST 5: POST /api/weather/regional?date=YYYY-MM-DD")
    print("(Previsão regional para depois de amanhã ao meio-dia)")
    print("="*70)
    
    # Calcular data depois de amanhã
    day_after_tomorrow = datetime.now() + timedelta(days=2)
    date_str = day_after_tomorrow.strftime('%Y-%m-%d')
    
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
        'queryStringParameters': {
            'date': date_str
        },
        'pathParameters': None,
        'body': json.dumps(body_data),
        'isBase64Encoded': False
    }
    
    context = MockContext()
    response = lambda_handler(event, context)
    
    print(f"\nData solicitada: {date_str} 12:00 (padrão)")
    print(f"Status: {response['statusCode']}")
    
    body = json.loads(response['body'])
    
    if response['statusCode'] == 200:
        print(f"Cidades processadas: {len(body)}")
        
        for weather in body:
            print(f"\n  {weather.get('cityName')} ({weather.get('timestamp')}):")
            print(f"    Temperatura: {weather.get('temperature')}°C")
            print(f"    Probabilidade de chuva: {weather.get('rainfallIntensity')}%")
    else:
        print(f"Erro: {body}")
    
    return response


if __name__ == '__main__':
    print("="*70)
    print("🧪 TESTES DO LAMBDA WEATHER FORECAST API")
    print("   Cidade de teste: Ribeirão do Sul (ID: 3543204)")
    print("="*70)
    
    # Executar testes
    test_get_city_weather()
    
    print("\n" + "="*70)
    print("✅ TESTES CONCLUÍDOS")
    print("="*70)
