"""
Script de teste local para a Lambda
"""
import json
from lambda_function import lambda_handler


class MockContext:
    """Mock do contexto Lambda para testes locais"""
    def __init__(self):
        self.function_name = "weather-forecast-api"
        self.function_version = "$LATEST"
        self.invoked_function_arn = "arn:aws:lambda:sa-east-1:123456789:function:weather-forecast-api"
        self.memory_limit_in_mb = 128
        self.aws_request_id = "test-request-id"
        self.log_group_name = "/aws/lambda/weather-forecast-api"
        self.log_stream_name = "test-stream"
    
    def get_remaining_time_in_millis(self):
        return 300000


def test_get_neighbors():
    """Testa a rota GET /api/cities/neighbors/{cityId}"""
    print("\n=== Testando GET /api/cities/neighbors/3543204?radius=50 ===")
    
    event = {
        'httpMethod': 'GET',
        'path': '/api/cities/neighbors/3543204',
        'pathParameters': {'city_id': '3543204'},
        'queryStringParameters': {'radius': '50'},
        'headers': {},
        'body': None
    }
    
    response = lambda_handler(event, MockContext())
    print(f"Status: {response['statusCode']}")
    print(f"Body: {json.dumps(json.loads(response['body']), indent=2, ensure_ascii=False)}")


def test_get_city_weather():
    """Testa a rota GET /api/weather/city/{cityId}"""
    print("\n=== Testando GET /api/weather/city/3543204 ===")
    
    event = {
        'httpMethod': 'GET',
        'path': '/api/weather/city/3543204',
        'pathParameters': {'city_id': '3543204'},
        'headers': {},
        'body': None
    }
    
    response = lambda_handler(event, MockContext())
    print(f"Status: {response['statusCode']}")
    print(f"Body: {json.dumps(json.loads(response['body']), indent=2, ensure_ascii=False)}")


def test_post_regional_weather():
    """Testa a rota POST /api/weather/regional"""
    print("\n=== Testando POST /api/weather/regional ===")
    
    event = {
        'httpMethod': 'POST',
        'path': '/api/weather/regional',
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'cityIds': ['3543204', '3550506', '3545407']
        })
    }
    
    response = lambda_handler(event, MockContext())
    print(f"Status: {response['statusCode']}")
    print(f"Body: {json.dumps(json.loads(response['body']), indent=2, ensure_ascii=False)}")


if __name__ == '__main__':
    print("🧪 Testando Lambda Weather Forecast API (AWS Powertools)")
    print("=" * 60)
    
    test_get_neighbors()
    test_get_city_weather()
    test_post_regional_weather()
    
    print("\n" + "=" * 60)
    print("✅ Testes concluídos!")
