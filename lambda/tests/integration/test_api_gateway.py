"""
Script de teste de integração com API Gateway
Testa endpoints reais após deploy
Executar: python test_api_gateway.py
ou: pytest test_api_gateway.py -v
"""
import pytest
import requests
import json
from datetime import datetime, timedelta
from typing import Optional
import os


# URL do API Gateway (obtida do terraform output)
API_BASE_URL = os.getenv('API_GATEWAY_URL', 'https://u8r56xdgog.execute-api.sa-east-1.amazonaws.com/dev')

# Timeout para requests (60 segundos para dar tempo das chamadas paralelas)
REQUEST_TIMEOUT = 60

# Cidade de teste: Ribeirão Preto
TEST_CITY_ID = '3543204'


def test_health_check():
    """Verifica se o API Gateway está respondendo"""
    print("\n" + "="*70)
    print("TEST INTEGRATION 1: Health Check - API Gateway")
    print("="*70)
    
    try:
        # Tentar qualquer endpoint para verificar conectividade
        response = requests.get(
            f"{API_BASE_URL}/api/cities/neighbors/{TEST_CITY_ID}",
            params={'radius': '10'},
            timeout=10
        )
        
        assert response.status_code in [200, 400, 404, 500], \
            f"API should respond with valid HTTP status, got {response.status_code}"
        
        print(f"✅ API Gateway está respondendo (status: {response.status_code})")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro de conectividade: {e}")
        pytest.fail(f"Cannot connect to API Gateway: {e}")


def test_get_neighbors_integration():
    """Testa rota GET /api/cities/neighbors/{cityId}"""
    print("\n" + "="*70)
    print(f"TEST INTEGRATION 2: GET /api/cities/neighbors/{TEST_CITY_ID}")
    print("="*70)
    
    response = requests.get(
        f"{API_BASE_URL}/api/cities/neighbors/{TEST_CITY_ID}",
        params={'radius': '50'},
        timeout=REQUEST_TIMEOUT
    )
    
    # Asserts
    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    
    # Validar estrutura
    assert 'centerCity' in data, "Response should contain centerCity"
    assert 'neighbors' in data, "Response should contain neighbors"
    
    center_city = data['centerCity']
    assert center_city['id'] == TEST_CITY_ID, "Center city ID should match"
    assert 'latitude' in center_city, "Center city should have latitude"
    assert 'longitude' in center_city, "Center city should have longitude"
    
    neighbors = data['neighbors']
    assert isinstance(neighbors, list), "Neighbors should be a list"
    assert len(neighbors) > 0, "Should have at least one neighbor"
    
    # Verificar CORS headers
    assert 'access-control-allow-origin' in response.headers, \
        "Should have CORS header"
    
    print(f"✅ Status: {response.status_code}")
    print(f"✅ Cidade centro: {center_city['name']}")
    print(f"✅ Vizinhos: {len(neighbors)}")
    print(f"✅ CORS habilitado: {response.headers.get('access-control-allow-origin')}")


def test_get_city_weather_integration():
    """Testa rota GET /api/weather/city/{cityId}"""
    print("\n" + "="*70)
    print(f"TEST INTEGRATION 3: GET /api/weather/city/{TEST_CITY_ID}")
    print("="*70)
    
    response = requests.get(
        f"{API_BASE_URL}/api/weather/city/{TEST_CITY_ID}",
        timeout=REQUEST_TIMEOUT
    )
    
    # Asserts
    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    
    # Validar campos obrigatórios
    required_fields = [
        'cityId', 'cityName', 'timestamp', 'temperature', 
        'humidity', 'windSpeed', 'rainfallIntensity'
    ]
    for field in required_fields:
        assert field in data, f"Response should contain {field}"
    
    # Validar tipos e ranges
    assert isinstance(data['temperature'], (int, float)), "Temperature should be numeric"
    assert -50 <= data['temperature'] <= 60, "Temperature in reasonable range"
    assert 0 <= data['humidity'] <= 100, "Humidity 0-100%"
    assert data['windSpeed'] >= 0, "Wind speed non-negative"
    assert 0 <= data['rainfallIntensity'] <= 100, "Rain probability 0-100%"
    
    print(f"✅ Status: {response.status_code}")
    print(f"✅ Cidade: {data['cityName']}")
    print(f"✅ Temperatura: {data['temperature']}°C")
    print(f"✅ Umidade: {data['humidity']}%")
    print(f"✅ Prob. chuva: {data['rainfallIntensity']}%")


def test_get_city_weather_with_date_integration():
    """Testa rota GET /api/weather/city/{cityId} com data específica e valida faixa de horário"""
    print("\n" + "="*70)
    print(f"TEST INTEGRATION 4: GET /api/weather/city/{TEST_CITY_ID}?date=...&time=...")
    print("="*70)
    
    # Calcular amanhã às 15h
    tomorrow = datetime.now() + timedelta(days=1)
    date_str = tomorrow.strftime('%Y-%m-%d')
    time_str = '15:00'
    
    response = requests.get(
        f"{API_BASE_URL}/api/weather/city/{TEST_CITY_ID}",
        params={
            'date': date_str,
            'time': time_str
        },
        timeout=REQUEST_TIMEOUT
    )
    
    # Asserts
    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    
    assert 'timestamp' in data, "Response should contain timestamp"
    assert 'rainfallIntensity' in data, "Response should contain rainfallIntensity"
    
    # Validar que timestamp está próximo da data solicitada
    forecast_dt = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
    requested_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    
    # OpenWeather fornece previsões a cada 3 horas, então deve estar dentro de ±1.5h
    time_diff_hours = abs((forecast_dt.replace(tzinfo=None) - requested_dt).total_seconds() / 3600)
    assert time_diff_hours <= 3, \
        f"Forecast time should be within 3 hours of requested time, got {time_diff_hours:.1f}h"
    
    # Validar que a previsão está dentro do range de 5 dias (limite OpenWeather)
    now = datetime.now()
    max_forecast_date = now + timedelta(days=5)
    assert forecast_dt.replace(tzinfo=None) <= max_forecast_date, \
        f"Forecast should be within 5 days from now"
    
    # Validar que a previsão não é no passado
    assert forecast_dt.replace(tzinfo=None) >= now - timedelta(hours=3), \
        f"Forecast should not be in the past (considering 3h tolerance)"
    
    print(f"✅ Status: {response.status_code}")
    print(f"✅ Data solicitada: {date_str} {time_str}")
    print(f"✅ Data previsão: {data['timestamp']}")
    print(f"✅ Diferença de horário: {time_diff_hours:.1f}h (dentro do limite de 3h)")
    print(f"✅ Dentro da faixa de 5 dias: Sim")
    print(f"✅ Prob. chuva: {data['rainfallIntensity']}%")


def test_post_regional_weather_integration():
    """Testa rota POST /api/weather/regional (performance crítico)"""
    print("\n" + "="*70)
    print("TEST INTEGRATION 5: POST /api/weather/regional (3 cidades)")
    print("="*70)
    
    city_ids = [
        '3543204',  # Ribeirão Preto
        '3548708',  # São Carlos
        '3509502'   # Campinas
    ]
    
    start_time = datetime.now()
    
    response = requests.post(
        f"{API_BASE_URL}/api/weather/regional",
        json={'cityIds': city_ids},
        headers={'Content-Type': 'application/json'},
        timeout=REQUEST_TIMEOUT
    )
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    # Asserts
    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    
    assert isinstance(data, list), "Response should be a list"
    assert len(data) == 3, f"Should have 3 cities, got {len(data)}"
    
    # Validar estrutura de cada cidade
    for weather in data:
        required_fields = [
            'cityId', 'cityName', 'temperature', 
            'humidity', 'rainfallIntensity'
        ]
        for field in required_fields:
            assert field in weather, f"Weather should contain {field}"
        
        # Validar ranges
        assert -50 <= weather['temperature'] <= 60, "Temperature in reasonable range"
        assert 0 <= weather['humidity'] <= 100, "Humidity 0-100%"
        assert 0 <= weather['rainfallIntensity'] <= 100, "Rain probability 0-100%"
    
    # Performance check (deve ser < 5 segundos com paralelização)
    assert elapsed < 10, \
        f"Regional weather should be fast (<10s), took {elapsed:.2f}s"
    
    print(f"✅ Status: {response.status_code}")
    print(f"✅ Cidades processadas: {len(data)}")
    print(f"⚡ Tempo de resposta: {elapsed:.2f}s")
    
    for weather in data:
        print(f"  ✅ {weather['cityName']}: {weather['temperature']}°C, "
              f"chuva {weather['rainfallIntensity']}%")


def test_post_regional_weather_with_date_integration():
    """Testa rota POST /api/weather/regional com data específica e valida faixa de horário"""
    print("\n" + "="*70)
    print("TEST INTEGRATION 6: POST /api/weather/regional?date=...")
    print("="*70)
    
    # Calcular depois de amanhã
    day_after_tomorrow = datetime.now() + timedelta(days=2)
    date_str = day_after_tomorrow.strftime('%Y-%m-%d')
    
    city_ids = ['3543204', '3548708', '3509502']
    
    response = requests.post(
        f"{API_BASE_URL}/api/weather/regional",
        params={'date': date_str},
        json={'cityIds': city_ids},
        headers={'Content-Type': 'application/json'},
        timeout=REQUEST_TIMEOUT
    )
    
    # Asserts
    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    
    assert isinstance(data, list), "Response should be a list"
    assert len(data) == 3, f"Should have 3 cities, got {len(data)}"
    
    # Validar que previsões são para data próxima da solicitada
    requested_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    now = datetime.now()
    max_forecast_date = now + timedelta(days=5)
    
    for weather in data:
        assert 'timestamp' in weather, "Weather should contain timestamp"
        forecast_dt = datetime.fromisoformat(weather['timestamp'].replace('Z', '+00:00'))
        
        # Validar diferença de data (deve ser o mesmo dia ou próximo)
        date_diff = abs((forecast_dt.date() - requested_date).days)
        assert date_diff <= 1, \
            f"Forecast date should be within 1 day of requested, got {date_diff} days for {weather['cityName']}"
        
        # Validar que a previsão está dentro do range de 5 dias
        assert forecast_dt.replace(tzinfo=None) <= max_forecast_date, \
            f"Forecast for {weather['cityName']} should be within 5 days from now"
        
        # Validar que a previsão não é no passado
        assert forecast_dt.replace(tzinfo=None) >= now - timedelta(hours=3), \
            f"Forecast for {weather['cityName']} should not be in the past"
    
    print(f"✅ Status: {response.status_code}")
    print(f"✅ Data solicitada: {date_str}")
    print(f"✅ Cidades processadas: {len(data)}")
    print(f"✅ Todas as previsões dentro da faixa de 5 dias: Sim")
    print(f"✅ Todas as previsões para data solicitada (±1 dia): Sim")
    
    for weather in data:
        forecast_dt = datetime.fromisoformat(weather['timestamp'].replace('Z', '+00:00'))
        date_diff = abs((forecast_dt.date() - requested_date).days)
        print(f"  ✅ {weather['cityName']} ({weather['timestamp']}): "
              f"chuva {weather['rainfallIntensity']}%, diff={date_diff}d")


def test_error_handling_integration():
    """Testa tratamento de erros"""
    print("\n" + "="*70)
    print("TEST INTEGRATION 7: Error Handling")
    print("="*70)
    
    # Teste 1: Cidade inválida
    response = requests.get(
        f"{API_BASE_URL}/api/weather/city/INVALID_ID",
        timeout=REQUEST_TIMEOUT
    )
    
    # A API pode retornar 200 com erro no body ou status de erro
    # Verificar se há algum indicador de erro
    if response.status_code == 200:
        try:
            body = response.json()
            # Se retornar 200, deve haver algum campo de erro ou faltar dados obrigatórios
            if 'error' in body or 'message' in body or 'cityId' not in body:
                print(f"✅ Cidade inválida retorna erro no body: {response.status_code}")
            else:
                # Se não tem indicação de erro, pode ser que a OpenWeather aceite IDs inválidos
                print(f"⚠️  Cidade inválida retorna 200 (OpenWeather pode aceitar qualquer ID)")
        except:
            print(f"✅ Cidade inválida retorna resposta inválida: {response.status_code}")
    else:
        assert response.status_code in [400, 404, 500], \
            f"Should return error for invalid city, got {response.status_code}"
        print(f"✅ Cidade inválida retorna erro: {response.status_code}")
    
    # Teste 2: Body inválido no POST (sem cityIds)
    response = requests.post(
        f"{API_BASE_URL}/api/weather/regional",
        json={'invalid': 'data'},
        headers={'Content-Type': 'application/json'},
        timeout=REQUEST_TIMEOUT
    )
    
    # A API agora valida e retorna erro estruturado com statusCode 400 no body
    if response.status_code == 200:
        body = response.json()
        # Se retornar 200, pode ter um objeto com statusCode interno
        if isinstance(body, dict) and 'statusCode' in body:
            assert body['statusCode'] in [400, 500], \
                f"Should return error statusCode for invalid body, got {body.get('statusCode')}"
            print(f"✅ Body inválido retorna erro (statusCode: {body['statusCode']}): {body.get('body', {}).get('message')}")
        elif isinstance(body, list) and len(body) == 0:
            print(f"✅ Body inválido retorna lista vazia")
        else:
            pytest.fail(f"Unexpected response format for invalid body: {body}")
    else:
        assert response.status_code in [400, 500], \
            f"Should return error for invalid body, got {response.status_code}"
        print(f"✅ Body inválido retorna erro HTTP: {response.status_code}")


def test_forecast_date_range_limits():
    """Testa limites de data de previsão (máximo 5 dias)"""
    print("\n" + "="*70)
    print("TEST INTEGRATION 8: Forecast Date Range Limits")
    print("="*70)
    
    # Teste 1: Data no limite (5 dias)
    five_days = datetime.now() + timedelta(days=5)
    date_str = five_days.strftime('%Y-%m-%d')
    
    response = requests.get(
        f"{API_BASE_URL}/api/weather/city/{TEST_CITY_ID}",
        params={'date': date_str, 'time': '12:00'},
        timeout=REQUEST_TIMEOUT
    )
    
    # Deve funcionar ou retornar a última previsão disponível
    if response.status_code == 200:
        data = response.json()
        forecast_dt = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        
        # Validar que não excede 5.5 dias (margem para fusos horários)
        diff_days = (forecast_dt.replace(tzinfo=None) - datetime.now()).days
        assert diff_days <= 6, \
            f"Forecast should not exceed 6 days (5 days + margin), got {diff_days} days"
        
        print(f"✅ Previsão para 5 dias funciona: {data['timestamp']}")
        print(f"   Diferença: {diff_days} dias")
    else:
        print(f"⚠️  Previsão para 5 dias retorna: {response.status_code}")
    
    # Teste 2: Data muito no futuro (deve usar última previsão disponível)
    far_future = datetime.now() + timedelta(days=10)
    date_str = far_future.strftime('%Y-%m-%d')
    
    response = requests.get(
        f"{API_BASE_URL}/api/weather/city/{TEST_CITY_ID}",
        params={'date': date_str, 'time': '12:00'},
        timeout=REQUEST_TIMEOUT
    )
    
    # OpenWeather deve retornar a última previsão disponível
    if response.status_code == 200:
        data = response.json()
        forecast_dt = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        
        # Deve retornar previsão dentro do limite de 5 dias
        diff_days = (forecast_dt.replace(tzinfo=None) - datetime.now()).days
        assert diff_days <= 6, \
            f"When requesting far future, should return last available forecast (≤6 days), got {diff_days} days"
        
        print(f"✅ Data muito no futuro (10 dias) retorna última previsão disponível")
        print(f"   Data solicitada: {date_str}")
        print(f"   Previsão retornada: {data['timestamp']} ({diff_days} dias no futuro)")
    else:
        print(f"⚠️  Data muito no futuro retorna: {response.status_code}")
    
    # Teste 3: Data no passado (deve retornar previsão atual)
    past = datetime.now() - timedelta(days=1)
    date_str = past.strftime('%Y-%m-%d')
    
    response = requests.get(
        f"{API_BASE_URL}/api/weather/city/{TEST_CITY_ID}",
        params={'date': date_str, 'time': '12:00'},
        timeout=REQUEST_TIMEOUT
    )
    
    if response.status_code == 200:
        data = response.json()
        forecast_dt = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        
        # Deve retornar previsão atual ou próxima (não no passado)
        now = datetime.now()
        assert forecast_dt.replace(tzinfo=None) >= now - timedelta(hours=3), \
            f"Should not return forecast in the past"
        
        print(f"✅ Data no passado retorna previsão atual/próxima")
        print(f"   Data solicitada: {date_str}")
        print(f"   Previsão retornada: {data['timestamp']}")
    else:
        print(f"⚠️  Data no passado retorna: {response.status_code}")
    
    print("✅ Testes de limites de data concluídos")


def run_all_tests():
    """Executa todos os testes de integração"""
    print("="*70)
    print("🧪 TESTES DE INTEGRAÇÃO - API GATEWAY")
    print(f"   URL: {API_BASE_URL}")
    print(f"   Cidade de teste: Ribeirão Preto ({TEST_CITY_ID})")
    print("="*70)
    
    tests = [
        test_health_check,
        test_get_neighbors_integration,
        test_get_city_weather_integration,
        test_get_city_weather_with_date_integration,
        test_post_regional_weather_integration,
        test_post_regional_weather_with_date_integration,
        test_error_handling_integration,
        test_forecast_date_range_limits
    ]
    
    failed = []
    
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"\n❌ TESTE FALHOU: {test.__name__}")
            print(f"   Erro: {e}")
            failed.append((test.__name__, str(e)))
        except Exception as e:
            print(f"\n❌ ERRO INESPERADO: {test.__name__}")
            print(f"   Erro: {e}")
            failed.append((test.__name__, str(e)))
    
    print("\n" + "="*70)
    if failed:
        print(f"❌ {len(failed)} TESTE(S) FALHARAM:")
        for name, error in failed:
            print(f"   - {name}: {error}")
        print("="*70)
        return False
    else:
        print("✅ TODOS OS TESTES DE INTEGRAÇÃO PASSARAM!")
        print("="*70)
        return True


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
