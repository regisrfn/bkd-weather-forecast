# Testing Guide

## Visão Geral

A aplicação possui suite completa de testes cobrindo 3 níveis:

1. **Unit Tests** - Testes isolados de componentes individuais
2. **Integration Tests** - Testes de integração entre camadas
3. **Performance Tests** - Testes de carga e benchmark

**Cobertura:** 34 testes (100% passing)

**Stack:**
- `pytest` 8.3.4 - Framework de testes
- `pytest-asyncio` 0.24.0 - Suporte a testes async
- `pytest-cov` - Cobertura de código
- `moto` - Mock de serviços AWS

---

## Estrutura de Testes

```
lambda/tests/
├── __init__.py
├── conftest.py                    # Fixtures compartilhadas
├── unit/                          # Testes unitários
│   ├── __init__.py
│   ├── test_city_repository.py
│   ├── test_datetime_parser.py
│   ├── test_domain_entities.py
│   ├── test_radius_validator.py
│   └── test_weather_mapper.py
├── integration/                   # Testes de integração
│   ├── __init__.py
│   ├── test_lambda_integration.py
│   └── test_use_cases.py
└── performance/                   # Testes de performance
    ├── __init__.py
    └── test_regional_performance.py
```

---

## Setup de Ambiente

### 1. Configurar Python Environment

```bash
# Configure o ambiente Python
cd /home/regis/GIT/bkd-weather-forecast/lambda
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependências
pip install -r requirements-dev.txt
```

### 2. Environment Variables

```bash
# .env file
OPENWEATHER_API_KEY=your_api_key_here
DYNAMODB_CACHE_TABLE=weather-forecast-cache-test
AWS_DEFAULT_REGION=sa-east-1

# Ou export direto
export OPENWEATHER_API_KEY=your_api_key
export DYNAMODB_CACHE_TABLE=weather-forecast-cache-test
```

### 3. Verificar Instalação

```bash
# Verificar pytest
pytest --version
# pytest 8.3.4

# Verificar pytest-asyncio
pytest --markers | grep asyncio
# @pytest.mark.asyncio: mark test as async
```

---

## Executando Testes

### Todos os Testes

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with output capture disabled (see prints)
pytest -s
```

### Testes por Nível

```bash
# Unit tests only
pytest lambda/tests/unit/ -v

# Integration tests only
pytest lambda/tests/integration/ -v

# Performance tests only
pytest lambda/tests/performance/ -v
```

### Testes por Arquivo

```bash
# Run specific file
pytest lambda/tests/unit/test_city_repository.py -v

# Run specific test class
pytest lambda/tests/integration/test_lambda_integration.py::TestNeighborsEndpoint -v

# Run specific test method
pytest lambda/tests/integration/test_lambda_integration.py::TestNeighborsEndpoint::test_get_neighbors_success -v
```

### Filtros por Marcadores

```bash
# Run only async tests
pytest -m asyncio

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

### Com Cobertura

```bash
# Run with coverage
pytest --cov=lambda --cov-report=html

# Open coverage report
open htmlcov/index.html

# Show missing lines
pytest --cov=lambda --cov-report=term-missing
```

---

## Unit Tests

### Test Structure

```python
import pytest
from lambda.domain.entities.city import City

class TestCityEntity:
    """Test suite for City entity"""
    
    def test_create_city(self):
        """Test city creation with valid data"""
        # Arrange
        city_id = "3543204"
        name = "Ribeirão do Sul"
        state = "SP"
        lat = -22.7572
        lon = -49.9439
        
        # Act
        city = City(
            id=city_id,
            name=name,
            state=state,
            latitude=lat,
            longitude=lon
        )
        
        # Assert
        assert city.id == city_id
        assert city.name == name
        assert city.state == state
        assert city.latitude == lat
        assert city.longitude == lon
    
    def test_city_to_dict(self):
        """Test city serialization"""
        # Arrange
        city = City(
            id="3543204",
            name="Ribeirão do Sul",
            state="SP",
            latitude=-22.7572,
            longitude=-49.9439
        )
        
        # Act
        city_dict = city.to_dict()
        
        # Assert
        assert city_dict['id'] == "3543204"
        assert city_dict['name'] == "Ribeirão do Sul"
        assert city_dict['state'] == "SP"
        assert city_dict['latitude'] == -22.7572
        assert city_dict['longitude'] == -49.9439
```

### Test Patterns

**1. Arrange-Act-Assert (AAA)**

```python
def test_validate_radius_valid():
    # Arrange
    radius_str = "50"
    
    # Act
    radius = RadiusValidator.validate(radius_str)
    
    # Assert
    assert radius == 50.0
```

**2. Given-When-Then**

```python
def test_parse_datetime_with_date_and_time():
    # Given valid date and time strings
    date_str = "2025-11-26"
    time_str = "15:00"
    
    # When parsing datetime
    result = DateTimeParser.from_query_params(date_str, time_str)
    
    # Then result should match expected datetime
    expected = datetime(2025, 11, 26, 15, 0, 0, tzinfo=timezone.utc)
    assert result == expected
```

**3. Parameterized Tests**

```python
@pytest.mark.parametrize("radius_str,expected", [
    ("1", 1.0),
    ("50", 50.0),
    ("500", 500.0),
    ("100.5", 100.5),
])
def test_validate_radius_valid_values(radius_str, expected):
    """Test radius validation with multiple valid values"""
    result = RadiusValidator.validate(radius_str)
    assert result == expected
```

### Exception Testing

```python
def test_validate_radius_too_large():
    """Test radius validation with value > 500"""
    with pytest.raises(InvalidRadiusException) as exc_info:
        RadiusValidator.validate("999")
    
    assert "500.0" in str(exc_info.value)
    assert exc_info.value.details['radius'] == 999.0

def test_city_not_found():
    """Test city not found exception"""
    repo = InMemoryCityRepository()
    
    with pytest.raises(CityNotFoundException) as exc_info:
        repo.get_by_id("9999999")
    
    assert exc_info.value.details['city_id'] == "9999999"
```

---

## Integration Tests

### Test Structure with Fixtures

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch

@pytest.fixture
def mock_city_repository():
    """Fixture for city repository"""
    repo = InMemoryCityRepository()
    # Repository already loaded with data
    return repo

@pytest.fixture
def mock_weather_repository():
    """Fixture for weather repository"""
    mock_cache = Mock()
    mock_cache.get = AsyncMock(return_value=None)
    mock_cache.put = AsyncMock()
    
    repo = AsyncOpenWeatherRepository(
        api_key="test_key",
        cache=mock_cache
    )
    return repo

@pytest.mark.asyncio
async def test_get_city_weather(mock_city_repository, mock_weather_repository):
    """Test get city weather use case"""
    # Arrange
    city_id = "3543204"
    target_dt = datetime.now(timezone.utc)
    
    use_case = AsyncGetCityWeatherUseCase(
        mock_city_repository,
        mock_weather_repository
    )
    
    # Mock weather repository response
    mock_weather = Weather(
        temperature=28.3,
        humidity=65.0,
        wind_speed=12.5,
        rainfall_intensity=35.0,
        weather_description="Parcialmente nublado",
        timestamp=target_dt
    )
    
    with patch.object(
        mock_weather_repository,
        'get_weather',
        return_value=mock_weather
    ):
        # Act
        weather = await use_case.execute(city_id, target_dt)
    
    # Assert
    assert weather.city_id == city_id
    assert weather.temperature == 28.3
    assert weather.humidity == 65.0
```

### Lambda Integration Tests

```python
class TestLambdaIntegration:
    """Integration tests for Lambda handler"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup environment variables"""
        os.environ['OPENWEATHER_API_KEY'] = 'test_key'
        os.environ['DYNAMODB_CACHE_TABLE'] = 'test-cache'
        yield
        # Cleanup
        del os.environ['OPENWEATHER_API_KEY']
        del os.environ['DYNAMODB_CACHE_TABLE']
    
    def test_get_neighbors_success(self):
        """Test GET /api/cities/neighbors/{cityId}"""
        # Arrange
        event = {
            'httpMethod': 'GET',
            'path': '/api/cities/neighbors/3543204',
            'pathParameters': {'city_id': '3543204'},
            'queryStringParameters': {'radius': '50'},
            'headers': {}
        }
        context = {}
        
        # Act
        response = lambda_handler(event, context)
        
        # Assert
        assert response['statusCode'] == 200
        
        body = json.loads(response['body'])
        assert 'centerCity' in body
        assert 'neighbors' in body
        assert body['centerCity']['id'] == '3543204'
        assert len(body['neighbors']) > 0
    
    def test_get_city_weather_success(self):
        """Test GET /api/weather/city/{cityId}"""
        # Arrange
        event = {
            'httpMethod': 'GET',
            'path': '/api/weather/city/3543204',
            'pathParameters': {'city_id': '3543204'},
            'queryStringParameters': None,
            'headers': {}
        }
        context = {}
        
        # Mock OpenWeather API
        with patch('lambda.infrastructure.adapters.async_openweather_repository.aiohttp'):
            # Act
            response = lambda_handler(event, context)
        
        # Assert
        assert response['statusCode'] == 200
        
        body = json.loads(response['body'])
        assert body['cityId'] == '3543204'
        assert 'temperature' in body
        assert 'humidity' in body
```

### Async Integration Tests

```python
import pytest

@pytest.mark.asyncio
class TestAsyncUseCases:
    """Test async use cases"""
    
    @pytest.fixture
    def city_repository(self):
        return InMemoryCityRepository()
    
    @pytest.fixture
    def mock_cache(self):
        mock = Mock()
        mock.get = AsyncMock(return_value=None)
        mock.put = AsyncMock()
        return mock
    
    @pytest.fixture
    def weather_repository(self, mock_cache):
        return AsyncOpenWeatherRepository(
            api_key="test_key",
            cache=mock_cache
        )
    
    async def test_get_regional_weather(
        self,
        city_repository,
        weather_repository
    ):
        """Test regional weather use case (parallel)"""
        # Arrange
        city_ids = ["3543204", "3548708", "3509502"]
        target_dt = datetime.now(timezone.utc)
        
        use_case = AsyncGetRegionalWeatherUseCase(
            city_repository,
            weather_repository
        )
        
        # Mock weather repository
        mock_weather = Weather(
            temperature=28.3,
            humidity=65.0,
            wind_speed=12.5,
            rainfall_intensity=35.0,
            weather_description="Nublado",
            timestamp=target_dt
        )
        
        with patch.object(
            weather_repository,
            'get_weather',
            return_value=mock_weather
        ):
            # Act
            weather_list = await use_case.execute(city_ids, target_dt)
        
        # Assert
        assert len(weather_list) == 3
        assert all(isinstance(w, Weather) for w in weather_list)
        assert all(w.temperature == 28.3 for w in weather_list)
```

---

## Performance Tests

### Regional Weather Performance

```python
import pytest
import time
from statistics import mean, median

@pytest.mark.performance
@pytest.mark.asyncio
class TestRegionalPerformance:
    """Performance tests for regional weather endpoint"""
    
    @pytest.fixture
    def city_ids_100(self):
        """Load 100 city IDs for testing"""
        with open('lambda/data/test_100_municipalities.json') as f:
            data = json.load(f)
        return [city['id'] for city in data[:100]]
    
    async def test_regional_weather_100_cities(
        self,
        city_ids_100,
        city_repository,
        weather_repository
    ):
        """Test performance with 100 cities"""
        # Arrange
        target_dt = datetime.now(timezone.utc)
        use_case = AsyncGetRegionalWeatherUseCase(
            city_repository,
            weather_repository
        )
        
        # Mock weather repository (simulate cache hits)
        mock_weather = Weather(...)
        with patch.object(
            weather_repository,
            'get_weather',
            return_value=mock_weather
        ):
            # Act - Measure latency
            start = time.time()
            weather_list = await use_case.execute(city_ids_100, target_dt)
            elapsed = (time.time() - start) * 1000  # ms
        
        # Assert
        assert len(weather_list) == 100
        assert elapsed < 200  # P99 target: <200ms
        
        print(f"Latency: {elapsed:.1f}ms")
        print(f"Per city: {elapsed/100:.1f}ms")
    
    async def test_regional_weather_latency_distribution(
        self,
        city_ids_100,
        city_repository,
        weather_repository
    ):
        """Test latency distribution across multiple runs"""
        # Arrange
        target_dt = datetime.now(timezone.utc)
        use_case = AsyncGetRegionalWeatherUseCase(
            city_repository,
            weather_repository
        )
        
        # Run 10 iterations
        latencies = []
        
        for _ in range(10):
            start = time.time()
            await use_case.execute(city_ids_100, target_dt)
            elapsed = (time.time() - start) * 1000
            latencies.append(elapsed)
        
        # Calculate statistics
        p50 = median(latencies)
        p90 = sorted(latencies)[int(0.9 * len(latencies))]
        p99 = sorted(latencies)[int(0.99 * len(latencies))]
        avg = mean(latencies)
        
        # Assert
        assert p50 < 150  # P50 target
        assert p99 < 200  # P99 target
        
        print(f"P50: {p50:.1f}ms")
        print(f"P90: {p90:.1f}ms")
        print(f"P99: {p99:.1f}ms")
        print(f"Avg: {avg:.1f}ms")
```

### Load Testing Script

```python
# scripts/performance_test_100_cities.py

import asyncio
import time
import json
from statistics import mean, median, stdev

async def run_performance_test():
    """Run performance test with 100 cities"""
    # Load city IDs
    with open('lambda/data/test_100_municipalities.json') as f:
        data = json.load(f)
    
    city_ids = [city['id'] for city in data[:100]]
    
    # Initialize repositories
    city_repo = InMemoryCityRepository()
    cache = DynamoDBCache(table_name="weather-forecast-cache-test")
    weather_repo = AsyncOpenWeatherRepository(
        api_key=os.getenv('OPENWEATHER_API_KEY'),
        cache=cache
    )
    
    # Initialize use case
    use_case = AsyncGetRegionalWeatherUseCase(city_repo, weather_repo)
    
    # Run multiple iterations
    iterations = 10
    latencies = []
    
    for i in range(iterations):
        start = time.time()
        
        weather_list = await use_case.execute(
            city_ids,
            datetime.now(timezone.utc)
        )
        
        elapsed = (time.time() - start) * 1000
        latencies.append(elapsed)
        
        print(f"Iteration {i+1}: {elapsed:.1f}ms ({len(weather_list)} cities)")
    
    # Calculate statistics
    p50 = median(latencies)
    p90 = sorted(latencies)[int(0.9 * len(latencies))]
    p99 = sorted(latencies)[int(0.99 * len(latencies))]
    avg = mean(latencies)
    std = stdev(latencies)
    
    # Print report
    print("\n" + "="*50)
    print("PERFORMANCE TEST RESULTS")
    print("="*50)
    print(f"Cities: 100")
    print(f"Iterations: {iterations}")
    print(f"P50: {p50:.1f}ms")
    print(f"P90: {p90:.1f}ms")
    print(f"P99: {p99:.1f}ms")
    print(f"Avg: {avg:.1f}ms")
    print(f"StdDev: {std:.1f}ms")
    print(f"Min: {min(latencies):.1f}ms")
    print(f"Max: {max(latencies):.1f}ms")
    print("="*50)
    
    # Save results
    results = {
        'timestamp': datetime.now().isoformat(),
        'cities': 100,
        'iterations': iterations,
        'metrics': {
            'p50': p50,
            'p90': p90,
            'p99': p99,
            'avg': avg,
            'std': std,
            'min': min(latencies),
            'max': max(latencies)
        },
        'latencies': latencies
    }
    
    filename = f"output/test_baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to {filename}")

if __name__ == "__main__":
    asyncio.run(run_performance_test())
```

**Run:**

```bash
python scripts/performance_test_100_cities.py
```

---

## Fixtures

### Global Fixtures (conftest.py)

```python
# lambda/tests/conftest.py

import pytest
import os
from unittest.mock import Mock, AsyncMock

@pytest.fixture(scope="session")
def event_loop_policy():
    """Configure event loop policy for async tests"""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()

@pytest.fixture
def mock_env_vars():
    """Setup environment variables for tests"""
    os.environ['OPENWEATHER_API_KEY'] = 'test_key'
    os.environ['DYNAMODB_CACHE_TABLE'] = 'test-cache'
    os.environ['AWS_DEFAULT_REGION'] = 'sa-east-1'
    
    yield
    
    # Cleanup
    del os.environ['OPENWEATHER_API_KEY']
    del os.environ['DYNAMODB_CACHE_TABLE']
    del os.environ['AWS_DEFAULT_REGION']

@pytest.fixture
def city_repository():
    """Fixture for in-memory city repository"""
    return InMemoryCityRepository()

@pytest.fixture
def mock_cache():
    """Fixture for mocked DynamoDB cache"""
    mock = Mock()
    mock.get = AsyncMock(return_value=None)
    mock.put = AsyncMock()
    return mock

@pytest.fixture
def weather_repository(mock_cache):
    """Fixture for weather repository with mocked cache"""
    return AsyncOpenWeatherRepository(
        api_key="test_key",
        cache=mock_cache
    )
```

### Custom Fixtures

```python
@pytest.fixture
def sample_city():
    """Fixture for sample city"""
    return City(
        id="3543204",
        name="Ribeirão do Sul",
        state="SP",
        latitude=-22.7572,
        longitude=-49.9439
    )

@pytest.fixture
def sample_weather():
    """Fixture for sample weather"""
    return Weather(
        temperature=28.3,
        humidity=65.0,
        wind_speed=12.5,
        rainfall_intensity=35.0,
        weather_description="Parcialmente nublado",
        timestamp=datetime.now(timezone.utc)
    )

@pytest.fixture
def api_gateway_event():
    """Fixture for API Gateway event"""
    return {
        'httpMethod': 'GET',
        'path': '/api/cities/neighbors/3543204',
        'pathParameters': {'city_id': '3543204'},
        'queryStringParameters': {'radius': '50'},
        'headers': {}
    }
```

---

## Mocking

### Mock External APIs

```python
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_fetch_weather_from_api():
    """Test weather fetching with mocked HTTP client"""
    # Arrange
    mock_response = {
        'cod': '200',
        'list': [
            {
                'dt': 1732647600,
                'main': {'temp': 28.3, 'humidity': 65},
                'wind': {'speed': 3.47},
                'pop': 0.35,
                'weather': [{'description': 'nublado'}]
            }
        ]
    }
    
    # Mock aiohttp
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_get.return_value.__aenter__.return_value.json = AsyncMock(
            return_value=mock_response
        )
        mock_get.return_value.__aenter__.return_value.status = 200
        
        # Act
        weather = await weather_repo.get_weather(-22.7572, -49.9439, datetime.now())
    
    # Assert
    assert weather.temperature == 28.3
```

### Mock AWS Services

```python
from moto import mock_dynamodb
import boto3

@pytest.fixture
@mock_dynamodb
def dynamodb_table():
    """Fixture for mocked DynamoDB table"""
    # Create mock table
    dynamodb = boto3.resource('dynamodb', region_name='sa-east-1')
    
    table = dynamodb.create_table(
        TableName='test-cache',
        KeySchema=[
            {'AttributeName': 'cacheKey', 'KeyType': 'HASH'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'cacheKey', 'AttributeType': 'S'}
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    
    yield table
    
    # Cleanup
    table.delete()

@pytest.mark.asyncio
async def test_cache_with_mocked_dynamodb(dynamodb_table):
    """Test DynamoDB cache with moto"""
    cache = DynamoDBCache(table_name='test-cache')
    
    # Put item
    await cache.put('test_key', {'data': 'test_value'})
    
    # Get item
    item = await cache.get('test_key')
    
    assert item is not None
    assert item['data'] == 'test_value'
```

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml

name: Run Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.13'
    
    - name: Install dependencies
      run: |
        cd lambda
        pip install -r requirements-dev.txt
    
    - name: Run unit tests
      run: |
        cd lambda
        pytest tests/unit/ -v --cov=lambda --cov-report=xml
    
    - name: Run integration tests
      env:
        OPENWEATHER_API_KEY: ${{ secrets.OPENWEATHER_API_KEY }}
      run: |
        cd lambda
        pytest tests/integration/ -v
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./lambda/coverage.xml
```

### Local CI Script

```bash
#!/bin/bash
# scripts/run_tests.sh

set -e

echo "Running test suite..."

# Activate virtual environment
source .venv/bin/activate

# Run unit tests
echo "Running unit tests..."
pytest lambda/tests/unit/ -v --cov=lambda

# Run integration tests
echo "Running integration tests..."
pytest lambda/tests/integration/ -v

# Run performance tests
echo "Running performance tests..."
pytest lambda/tests/performance/ -v -m performance

echo "All tests passed! ✅"
```

**Run:**

```bash
chmod +x scripts/run_tests.sh
./scripts/run_tests.sh
```

---

## Best Practices

### ✅ DO

1. **Use fixtures for reusable test data**
   ```python
   @pytest.fixture
   def sample_city():
       return City(...)
   ```

2. **Test one thing per test**
   ```python
   def test_validate_radius_valid():
       # Test only valid radius
   
   def test_validate_radius_invalid():
       # Test only invalid radius
   ```

3. **Use descriptive test names**
   ```python
   def test_get_neighbors_returns_cities_within_radius():
       # Clear what's being tested
   ```

4. **Mock external dependencies**
   ```python
   with patch('aiohttp.ClientSession.get'):
       # Test without hitting real API
   ```

5. **Use parametrized tests for multiple inputs**
   ```python
   @pytest.mark.parametrize("input,expected", [...])
   def test_multiple_inputs(input, expected):
       ...
   ```

### ❌ DON'T

1. **❌ Don't test implementation details**
   ```python
   # ❌ ERRADO
   def test_internal_method():
       obj._private_method()
   
   # ✅ CORRETO
   def test_public_behavior():
       result = obj.public_method()
       assert result == expected
   ```

2. **❌ Don't share state between tests**
   ```python
   # ❌ ERRADO
   shared_data = []  # Global state
   
   def test_1():
       shared_data.append(1)
   
   def test_2():
       assert len(shared_data) == 1  # Depends on test_1!
   ```

3. **❌ Don't skip cleanup**
   ```python
   # ✅ CORRETO
   @pytest.fixture
   def resource():
       r = create_resource()
       yield r
       r.cleanup()  # Always cleanup
   ```

4. **❌ Don't use real external services**
   ```python
   # ❌ ERRADO
   def test_with_real_api():
       response = requests.get('https://real-api.com')
   
   # ✅ CORRETO
   def test_with_mocked_api():
       with patch('requests.get'):
           ...
   ```

---

## Troubleshooting

### Common Issues

**1. RuntimeError: Event loop is closed**

```python
# Problem: Event loop not properly managed

# Solution: Use pytest-asyncio
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

**2. ImportError: No module named 'lambda'**

```bash
# Problem: Python path not configured

# Solution: Install package in editable mode
cd lambda
pip install -e .
```

**3. AWS credentials not found**

```bash
# Problem: AWS credentials missing

# Solution: Use moto for mocking
from moto import mock_dynamodb

@mock_dynamodb
def test_with_mocked_aws():
    ...
```

**4. Tests passing locally but failing in CI**

```yaml
# Problem: Environment differences

# Solution: Use same Python version
- uses: actions/setup-python@v4
  with:
    python-version: '3.13'  # Match local version
```

---

## References

- **pytest docs:** https://docs.pytest.org/
- **pytest-asyncio:** https://pytest-asyncio.readthedocs.io/
- **pytest-cov:** https://pytest-cov.readthedocs.io/
- **moto (AWS mocking):** https://docs.getmoto.org/
- **Testing best practices:** https://docs.python-guide.org/writing/tests/
