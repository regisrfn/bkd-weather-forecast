"""
Testes de integração com API Gateway
Testa endpoints reais após deploy na AWS
"""
import pytest
import pytest_asyncio
import httpx
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, List, Dict, Any
import os


# URL do API Gateway (obtida do terraform output ou arquivo API_URL.txt)
def get_api_url() -> str:
    """Obtém URL da API de variável de ambiente ou arquivo"""
    # 1. Tenta variável de ambiente
    if url := os.getenv('API_GATEWAY_URL'):
        return url.rstrip('/')
    
    # 2. Tenta ler de API_URL.txt na raiz do projeto
    try:
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        api_url_file = os.path.join(root_dir, 'API_URL.txt')
        if os.path.exists(api_url_file):
            with open(api_url_file, 'r') as f:
                return f.read().strip().rstrip('/')
    except:
        pass
    
    # 3. Fallback para URL antiga (se existir)
    return 'https://u8r56xdgog.execute-api.sa-east-1.amazonaws.com/dev'


API_BASE_URL = get_api_url()

# Timeout para requests (60 segundos para dar tempo das chamadas paralelas)
REQUEST_TIMEOUT = 60.0

# Cidade de teste: Ribeirão Preto
TEST_CITY_ID = '3543204'


# ============================================================================
# FIXTURES
# ============================================================================

@pytest_asyncio.fixture
async def http_client():
    """Cliente HTTP assíncrono para testes de integração"""
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        yield client


@pytest.fixture
def sample_city_ids() -> List[str]:
    """IDs de cidades para testes"""
    return [
        '3543204',  # Ribeirão Preto
        '3548708',  # São Carlos
        '3509502'   # Campinas
    ]


@pytest.fixture
def brazil_tz():
    """Timezone do Brasil"""
    return ZoneInfo("America/Sao_Paulo")


# ============================================================================
# TESTES DE HEALTH CHECK
# ============================================================================

@pytest.mark.asyncio
async def test_health_check(http_client: httpx.AsyncClient):
    """Verifica se o API Gateway está respondendo"""
    response = await http_client.get(
        f"{API_BASE_URL}/api/cities/neighbors/{TEST_CITY_ID}",
        params={'radius': '10'}
    )
    
    assert response.status_code in [200, 400, 404, 500], \
        f"API should respond with valid HTTP status, got {response.status_code}"


# ============================================================================
# TESTES DE ENDPOINTS - GET
# ============================================================================

@pytest.mark.asyncio
async def test_get_neighbors(http_client: httpx.AsyncClient):
    """Testa rota GET /api/cities/neighbors/{cityId}"""
    response = await http_client.get(
        f"{API_BASE_URL}/api/cities/neighbors/{TEST_CITY_ID}",
        params={'radius': '50'}
    )
    
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


@pytest.mark.asyncio
async def test_get_city_weather(http_client: httpx.AsyncClient):
    """Testa rota GET /api/weather/city/{cityId}"""
    response = await http_client.get(
        f"{API_BASE_URL}/api/weather/city/{TEST_CITY_ID}"
    )
    
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
    
    # Validar temperaturas mínima e máxima do dia
    assert 'tempMin' in data, "Response should contain tempMin"
    assert 'tempMax' in data, "Response should contain tempMax"
    assert isinstance(data['tempMin'], (int, float)), "tempMin should be numeric"
    assert isinstance(data['tempMax'], (int, float)), "tempMax should be numeric"
    assert data['tempMin'] <= data['temperature'] <= data['tempMax'], \
        "Current temp should be between min and max"
    assert data['tempMin'] <= data['tempMax'], "tempMin should be <= tempMax"


@pytest.mark.asyncio
async def test_get_city_weather_with_date(http_client: httpx.AsyncClient, brazil_tz):
    """Testa rota GET /api/weather/city/{cityId} com data específica"""
    now_brazil = datetime.now(tz=brazil_tz)
    
    # Calcular amanhã às 15h
    tomorrow = now_brazil + timedelta(days=1)
    date_str = tomorrow.strftime('%Y-%m-%d')
    time_str = '15:00'
    
    response = await http_client.get(
        f"{API_BASE_URL}/api/weather/city/{TEST_CITY_ID}",
        params={
            'date': date_str,
            'time': time_str
        }
    )
    
    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    
    assert 'timestamp' in data, "Response should contain timestamp"
    assert 'rainfallIntensity' in data, "Response should contain rainfallIntensity"
    
    # Validar que timestamp está próximo da data solicitada
    forecast_dt = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
    requested_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    
    # OpenWeather fornece previsões a cada 3 horas
    time_diff_hours = abs((forecast_dt.replace(tzinfo=None) - requested_dt).total_seconds() / 3600)
    assert time_diff_hours <= 3, \
        f"Forecast time should be within 3 hours of requested time, got {time_diff_hours:.1f}h"
    
    # Validar que a previsão está dentro do range de 5 dias
    now = datetime.now()
    max_forecast_date = now + timedelta(days=5)
    assert forecast_dt.replace(tzinfo=None) <= max_forecast_date, \
        f"Forecast should be within 5 days from now"
    
    # Validar que a previsão não é no passado
    assert forecast_dt.replace(tzinfo=None) >= now - timedelta(hours=3), \
        f"Forecast should not be in the past (considering 3h tolerance)"
    
    # Validar campos de temperatura
    assert 'tempMin' in data and 'tempMax' in data, \
        "Response should contain tempMin and tempMax"
    assert data['tempMin'] <= data['tempMax'], \
        f"tempMin ({data['tempMin']}) should be <= tempMax ({data['tempMax']})"


# ============================================================================
# TESTES DE ENDPOINTS - POST
# ============================================================================

@pytest.mark.asyncio
async def test_post_regional_weather(http_client: httpx.AsyncClient, sample_city_ids: List[str]):
    """Testa rota POST /api/weather/regional"""
    start_time = datetime.now()
    
    response = await http_client.post(
        f"{API_BASE_URL}/api/weather/regional",
        json={'cityIds': sample_city_ids},
        headers={'Content-Type': 'application/json'}
    )
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
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
    
    # Performance check (deve ser < 10 segundos com paralelização)
    assert elapsed < 10, \
        f"Regional weather should be fast (<10s), took {elapsed:.2f}s"


@pytest.mark.asyncio
async def test_post_regional_weather_with_date(
    http_client: httpx.AsyncClient, 
    sample_city_ids: List[str],
    brazil_tz
):
    """Testa rota POST /api/weather/regional com data específica"""
    now_brazil = datetime.now(tz=brazil_tz)
    
    # Calcular depois de amanhã
    day_after_tomorrow = now_brazil + timedelta(days=2)
    date_str = day_after_tomorrow.strftime('%Y-%m-%d')
    
    response = await http_client.post(
        f"{API_BASE_URL}/api/weather/regional",
        params={'date': date_str},
        json={'cityIds': sample_city_ids},
        headers={'Content-Type': 'application/json'}
    )
    
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
        
        # Validar diferença de data
        date_diff = abs((forecast_dt.date() - requested_date).days)
        assert date_diff <= 1, \
            f"Forecast date should be within 1 day of requested, got {date_diff} days for {weather['cityName']}"
        
        # Validar que a previsão está dentro do range de 5 dias
        assert forecast_dt.replace(tzinfo=None) <= max_forecast_date, \
            f"Forecast for {weather['cityName']} should be within 5 days from now"
        
        # Validar que a previsão não é no passado
        assert forecast_dt.replace(tzinfo=None) >= now - timedelta(hours=3), \
            f"Forecast for {weather['cityName']} should not be in the past"
        
        # Validar temperaturas consistentes
        assert 'tempMin' in weather and 'tempMax' in weather, \
            f"Weather for {weather['cityName']} should contain tempMin and tempMax"
        assert weather['tempMin'] <= weather['temperature'] <= weather['tempMax'], \
            f"Temperature for {weather['cityName']} should be between min and max"


# ============================================================================
# TESTES DE VALIDAÇÃO E ERROR HANDLING
# ============================================================================

@pytest.mark.asyncio
async def test_error_invalid_city(http_client: httpx.AsyncClient):
    """Testa erro com cidade inválida"""
    response = await http_client.get(
        f"{API_BASE_URL}/api/weather/city/INVALID_ID"
    )
    
    # A API pode retornar 200 com erro no body ou status de erro
    if response.status_code == 200:
        body = response.json()
        # Se retornar 200, deve haver indicador de erro
        assert 'error' in body or 'message' in body or 'cityId' not in body, \
            "Should indicate error for invalid city"
    else:
        assert response.status_code in [400, 404, 500], \
            f"Should return error for invalid city, got {response.status_code}"


@pytest.mark.asyncio
async def test_error_invalid_body(http_client: httpx.AsyncClient):
    """Testa erro com body inválido no POST"""
    response = await http_client.post(
        f"{API_BASE_URL}/api/weather/regional",
        json={'invalid': 'data'},
        headers={'Content-Type': 'application/json'}
    )
    
    # A API valida e retorna erro estruturado
    if response.status_code == 200:
        body = response.json()
        if isinstance(body, dict) and 'statusCode' in body:
            assert body['statusCode'] in [400, 500], \
                f"Should return error statusCode for invalid body"
        elif isinstance(body, list):
            assert len(body) == 0, "Should return empty list for invalid body"
    else:
        assert response.status_code in [400, 500], \
            f"Should return error for invalid body, got {response.status_code}"


@pytest.mark.asyncio
async def test_forecast_date_limits(http_client: httpx.AsyncClient, brazil_tz):
    """Testa limites de data de previsão e comportamento de última previsão disponível"""
    now_brazil = datetime.now(tz=brazil_tz)
    
    # Teste 1: Data no limite (4 dias - dentro do limite da OpenWeather)
    four_days = now_brazil + timedelta(days=4)
    date_str = four_days.strftime('%Y-%m-%d')
    
    response = await http_client.get(
        f"{API_BASE_URL}/api/weather/city/{TEST_CITY_ID}",
        params={'date': date_str, 'time': '12:00'}
    )
    
    assert response.status_code == 200, \
        f"Should return 200 for 4-day forecast, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert 'timestamp' in data, "Response should contain timestamp"
    forecast_dt = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
    diff_days = (forecast_dt.replace(tzinfo=None) - now_brazil.replace(tzinfo=None)).days
    assert diff_days <= 5, \
        f"Forecast should not exceed 5 days, got {diff_days} days"
    
    # Teste 2: Data muito no futuro (10 dias - ALÉM do limite)
    # Deve retornar a ÚLTIMA previsão disponível (dia 5)
    far_future = now_brazil + timedelta(days=10)
    date_str = far_future.strftime('%Y-%m-%d')
    
    response = await http_client.get(
        f"{API_BASE_URL}/api/weather/city/{TEST_CITY_ID}",
        params={'date': date_str, 'time': '12:00'}
    )
    
    assert response.status_code == 200, \
        f"Should return 200 with last available forecast, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert 'timestamp' in data, "Response should contain timestamp"
    
    forecast_dt = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
    now = datetime.now()
    
    # A previsão retornada deve estar dentro do limite de 5 dias
    diff_days = (forecast_dt.replace(tzinfo=None) - now).days
    assert 0 <= diff_days <= 5, \
        f"When requesting far future date, should return last available forecast (day 5), got day {diff_days}"
    
    # Validar que é realmente a última previsão (mais próxima do dia 5)
    assert diff_days >= 4, \
        f"Last available forecast should be around day 4-5, got day {diff_days}"
    
    print(f"✓ Far future date test: Requested +10 days, got +{diff_days} days (last available)")
    
    # Teste 3: Data no passado
    past = now_brazil - timedelta(days=1)
    date_str = past.strftime('%Y-%m-%d')
    
    response = await http_client.get(
        f"{API_BASE_URL}/api/weather/city/{TEST_CITY_ID}",
        params={'date': date_str, 'time': '12:00'}
    )
    
    assert response.status_code == 200, \
        f"Should return 200 for past date (returns first future forecast), got {response.status_code}"
    
    data = response.json()
    assert 'timestamp' in data, "Response should contain timestamp"
    forecast_dt = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
    
    # Não deve retornar previsão no passado
    assert forecast_dt.replace(tzinfo=None) >= now - timedelta(hours=3), \
        f"Should not return forecast in the past, got {forecast_dt}"
    
    print(f"✓ Past date test: Requested yesterday, got forecast for {forecast_dt.strftime('%Y-%m-%d %H:%M')}")


@pytest.mark.asyncio
async def test_last_available_forecast_behavior(http_client: httpx.AsyncClient, brazil_tz):
    """Testa comportamento específico de retornar última previsão disponível para datas futuras"""
    now_brazil = datetime.now(tz=brazil_tz)
    
    # Testa várias datas além do limite (6, 7, 15, 30 dias)
    test_future_days = [6, 7, 15, 30]
    
    for days_ahead in test_future_days:
        future_date = now_brazil + timedelta(days=days_ahead)
        date_str = future_date.strftime('%Y-%m-%d')
        
        response = await http_client.get(
            f"{API_BASE_URL}/api/weather/city/{TEST_CITY_ID}",
            params={'date': date_str, 'time': '12:00'}
        )
        
        assert response.status_code == 200, \
            f"Should return 200 for +{days_ahead} days, got {response.status_code}"
        
        data = response.json()
        assert 'timestamp' in data, f"Response should contain timestamp for +{days_ahead} days"
        
        forecast_dt = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        now = datetime.now()
        
        # Validar que sempre retorna dentro do limite de 5 dias
        diff_days = (forecast_dt.replace(tzinfo=None) - now).days
        assert 0 <= diff_days <= 5, \
            f"For +{days_ahead} days request, should return last available (≤5 days), got {diff_days} days"
        
        # Para datas muito além do limite, deve estar próximo do dia 5
        if days_ahead >= 7:
            assert diff_days >= 4, \
                f"For +{days_ahead} days request, last forecast should be around day 4-5, got {diff_days}"
        
        print(f"✓ Requested +{days_ahead} days → Got +{diff_days} days forecast (last available)")
    
    print("\n✓ All far future dates correctly return last available forecast (day 4-5)")


@pytest.mark.asyncio
async def test_regional_last_available_forecast(
    http_client: httpx.AsyncClient,
    sample_city_ids: List[str],
    brazil_tz
):
    """Testa que endpoint regional também retorna última previsão para datas futuras"""
    now_brazil = datetime.now(tz=brazil_tz)
    
    # Data muito no futuro (20 dias)
    far_future = now_brazil + timedelta(days=20)
    date_str = far_future.strftime('%Y-%m-%d')
    
    response = await http_client.post(
        f"{API_BASE_URL}/api/weather/regional",
        params={'date': date_str},
        json={'cityIds': sample_city_ids},
        headers={'Content-Type': 'application/json'}
    )
    
    assert response.status_code == 200, \
        f"Should return 200 for far future regional request, got {response.status_code}"
    
    data = response.json()
    assert isinstance(data, list) and len(data) == 3, \
        f"Should return data for all 3 cities"
    
    now = datetime.now()
    
    for weather in data:
        assert 'timestamp' in weather, f"Weather for {weather['cityName']} should have timestamp"
        
        forecast_dt = datetime.fromisoformat(weather['timestamp'].replace('Z', '+00:00'))
        diff_days = (forecast_dt.replace(tzinfo=None) - now).days
        
        # Todas as cidades devem retornar última previsão disponível
        assert 0 <= diff_days <= 5, \
            f"{weather['cityName']}: Should return last available forecast (≤5 days), got {diff_days} days"
        
        # Deve estar próximo do dia 5
        assert diff_days >= 4, \
            f"{weather['cityName']}: Last forecast should be around day 4-5, got {diff_days}"
        
        print(f"✓ {weather['cityName']}: Requested +20 days → Got +{diff_days} days (last available)")
    
    print("\n✓ Regional endpoint: All cities correctly return last available forecast")
