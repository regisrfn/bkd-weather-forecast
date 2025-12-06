#!/usr/bin/env python3
"""
Servidor Local para Desenvolvimento
Simula AWS Lambda + API Gateway localmente usando Flask

Pré-requisitos:
    - Ambiente virtual ativado: source .venv/bin/activate
    - Dependências instaladas: pip install -r requirements-dev.txt
    - Arquivo .env configurado no diretório raiz

Como usar:
    cd lambda
    ./start_local.sh
    # ou
    python local_server.py

Endpoints disponíveis:
    GET  http://localhost:8000/api/cities/neighbors/{cityId}?radius=50
    GET  http://localhost:8000/api/weather/city/{cityId}?date=2025-11-20&time=15:00
    GET  http://localhost:8000/api/weather/city/{cityId}/detailed?date=2025-11-20&time=15:00
    POST http://localhost:8000/api/weather/regional?date=2025-11-20&time=15:00
         Body: { "cityIds": ["3543204", "3550506"] }
"""
import os
import sys
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

# Garantir que o diretório lambda está no path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar o lambda_handler
from lambda_function import lambda_handler

app = Flask(__name__)
# Habilitar CORS para todos os endpoints e origens (desenvolvimento local)
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

class MockLambdaContext:
    """Mock do contexto Lambda para testes locais"""
    def __init__(self):
        self.aws_request_id = f"local-{datetime.now().timestamp()}"
        self.function_name = "local-weather-forecast"
        self.function_version = "$LATEST"
        self.invoked_function_arn = "arn:aws:lambda:local:000000000000:function:local-weather-forecast"
        self.memory_limit_in_mb = "512"
        self.log_group_name = "/aws/lambda/local-weather-forecast"
        self.log_stream_name = "local"
        
    def get_remaining_time_in_millis(self):
        return 300000  # 5 minutos


def flask_to_lambda_event(flask_request):
    """Converte requisição Flask para evento Lambda/API Gateway"""
    
    # Extrair query string parameters
    query_string_parameters = {}
    for key, value in flask_request.args.items():
        query_string_parameters[key] = value
    
    # Extrair headers
    headers = {}
    for key, value in flask_request.headers.items():
        headers[key] = value
    
    # Extrair body (se existir)
    body = None
    if flask_request.data:
        body = flask_request.data.decode('utf-8')
    
    # Construir evento Lambda
    event = {
        'resource': flask_request.path,
        'path': flask_request.path,
        'httpMethod': flask_request.method,
        'headers': headers,
        'queryStringParameters': query_string_parameters if query_string_parameters else None,
        'body': body,
        'isBase64Encoded': False,
        'requestContext': {
            'accountId': '000000000000',
            'apiId': 'local',
            'protocol': 'HTTP/1.1',
            'httpMethod': flask_request.method,
            'path': flask_request.path,
            'stage': 'local',
            'requestId': f"local-{datetime.now().timestamp()}",
            'requestTime': datetime.now().isoformat(),
            'requestTimeEpoch': int(datetime.now().timestamp() * 1000),
            'identity': {
                'sourceIp': flask_request.remote_addr,
                'userAgent': flask_request.headers.get('User-Agent', '')
            }
        }
    }
    
    return event


def lambda_to_flask_response(lambda_response):
    """Converte resposta Lambda para resposta Flask"""
    status_code = lambda_response.get('statusCode', 200)
    headers = lambda_response.get('headers', {})
    body = lambda_response.get('body', '')
    
    # Se body é string JSON, converter para dict
    try:
        body_dict = json.loads(body) if isinstance(body, str) else body
        return jsonify(body_dict), status_code, headers
    except (json.JSONDecodeError, TypeError):
        return body, status_code, headers


@app.route('/api/cities/neighbors/<city_id>', methods=['GET', 'OPTIONS'])
def get_neighbors(city_id):
    """GET /api/cities/neighbors/{cityId}?radius=50"""
    if request.method == 'OPTIONS':
        return '', 200
    
    # Construir path com city_id
    original_path = request.path
    flask_request_copy = request
    flask_request_copy.path = original_path
    
    # Converter para evento Lambda
    event = flask_to_lambda_event(flask_request_copy)
    event['pathParameters'] = {'city_id': city_id}
    
    # Chamar lambda_handler
    context = MockLambdaContext()
    response = lambda_handler(event, context)
    
    return lambda_to_flask_response(response)


@app.route('/api/weather/city/<city_id>', methods=['GET', 'OPTIONS'])
def get_city_weather(city_id):
    """GET /api/weather/city/{cityId}?date=2025-11-20&time=15:00"""
    if request.method == 'OPTIONS':
        return '', 200
    
    # Construir path com city_id
    original_path = request.path
    flask_request_copy = request
    flask_request_copy.path = original_path
    
    # Converter para evento Lambda
    event = flask_to_lambda_event(flask_request_copy)
    event['pathParameters'] = {'city_id': city_id}
    
    # Chamar lambda_handler
    context = MockLambdaContext()
    response = lambda_handler(event, context)
    
    return lambda_to_flask_response(response)


@app.route('/api/weather/city/<city_id>/detailed', methods=['GET', 'OPTIONS'])
def get_city_detailed_forecast(city_id):
    """GET /api/weather/city/{cityId}/detailed?date=2025-11-20&time=15:00"""
    if request.method == 'OPTIONS':
        return '', 200
    
    # Construir path com city_id
    original_path = request.path
    flask_request_copy = request
    flask_request_copy.path = original_path
    
    # Converter para evento Lambda
    event = flask_to_lambda_event(flask_request_copy)
    event['pathParameters'] = {'city_id': city_id}
    
    # Chamar lambda_handler
    context = MockLambdaContext()
    response = lambda_handler(event, context)
    
    return lambda_to_flask_response(response)


@app.route('/api/weather/regional', methods=['POST', 'OPTIONS'])
def post_regional_weather():
    """POST /api/weather/regional?date=2025-11-20&time=15:00"""
    if request.method == 'OPTIONS':
        return '', 200
    
    # Converter para evento Lambda
    event = flask_to_lambda_event(request)
    
    # Chamar lambda_handler
    context = MockLambdaContext()
    response = lambda_handler(event, context)
    
    return lambda_to_flask_response(response)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'weather-forecast-local',
        'timestamp': datetime.now().isoformat()
    })


@app.errorhandler(404)
def not_found(error):
    """Handler para rotas não encontradas"""
    return jsonify({
        'error': 'Not Found',
        'message': f"Route {request.path} not found",
        'available_routes': [
            'GET /api/cities/neighbors/{cityId}',
            'GET /api/weather/city/{cityId}',
            'GET /api/weather/city/{cityId}/detailed',
            'POST /api/weather/regional',
            'GET /health'
        ]
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handler para erros internos"""
    return jsonify({
        'error': 'Internal Server Error',
        'message': str(error)
    }), 500


if __name__ == '__main__':
    # Verificar variáveis de ambiente necessárias
    required_env_vars = ['OPENWEATHER_API_KEY']
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"⚠️  AVISO: Variáveis de ambiente faltando: {', '.join(missing_vars)}")
        print("Certifique-se de que o arquivo .env está configurado corretamente\n")
    
    port = int(os.environ.get('PORT', 8000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    print("=" * 70)
    print("🚀 Servidor Local - Weather Forecast API")
    print("=" * 70)
    print(f"\n📍 Rodando em: http://{host}:{port}")
    print("\n📋 Endpoints disponíveis:")
    print(f"   • GET  http://localhost:{port}/api/cities/neighbors/{{cityId}}?radius=50")
    print(f"   • GET  http://localhost:{port}/api/weather/city/{{cityId}}?date=2025-11-20&time=15:00")
    print(f"   • GET  http://localhost:{port}/api/weather/city/{{cityId}}/detailed?date=2025-11-20&time=15:00")
    print(f"   • POST http://localhost:{port}/api/weather/regional?date=2025-11-20&time=15:00")
    print(f"   • GET  http://localhost:{port}/health")
    print("\n💡 Exemplo de uso:")
    print(f"   curl http://localhost:{port}/api/weather/city/3543204")
    print("\n" + "=" * 70 + "\n")
    
    # Rodar servidor Flask
    app.run(
        host=host,
        port=port,
        debug=True,
        use_reloader=True
    )
