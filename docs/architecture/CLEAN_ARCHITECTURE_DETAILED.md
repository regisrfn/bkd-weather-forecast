# Arquitetura da Aplicação - Clean Architecture

## Visão Geral

A aplicação segue os princípios da **Clean Architecture (Arquitetura Hexagonal)** proposta por Robert C. Martin, garantindo separação de responsabilidades, testabilidade e independência de frameworks.

## Camadas da Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                     API Gateway (AWS)                        │
│                  HTTP Requests / Responses                   │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                   PRESENTATION LAYER                         │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │   lambda_handler.py (APIGatewayRestResolver)           │ │
│  │   - Route handlers                                     │ │
│  │   - Exception handlers (@app.exception_handler)        │ │
│  │   - HTTP request/response mapping                      │ │
│  └────────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                   APPLICATION LAYER                          │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │   Use Cases (Business Logic)                           │ │
│  │   - AsyncGetNeighborCitiesUseCase                      │ │
│  │   - AsyncGetCityWeatherUseCase                         │ │
│  │   - AsyncGetRegionalWeatherUseCase                     │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │   Ports (Interfaces)                                   │ │
│  │   - IUseCase                                           │ │
│  │   - IRepository                                        │ │
│  └────────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                     DOMAIN LAYER                             │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │   Entities (Business Objects)                          │ │
│  │   - City                                               │ │
│  │   - NeighborCity                                       │ │
│  │   - Weather                                            │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │   Domain Exceptions                                    │ │
│  │   - CityNotFoundException                              │ │
│  │   - CoordinatesNotFoundException                       │ │
│  │   - InvalidRadiusException                             │ │
│  │   - InvalidDateTimeException                           │ │
│  │   - WeatherDataNotFoundException                       │ │
│  └────────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                 INFRASTRUCTURE LAYER                         │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │   Adapters (Output)                                    │ │
│  │   - AsyncWeatherRepository (aiohttp)                   │ │
│  │   - MunicipalitiesRepository (JSON in-memory)          │ │
│  │   - AsyncDynamoDBCache (aioboto3)                      │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │   External Services                                    │ │
│  │   - OpenWeather API (Forecast 5 days)                  │ │
│  │   - AWS DynamoDB (Cache)                               │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      SHARED LAYER                            │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │   Utilities                                            │ │
│  │   - DateTimeParser                                     │ │
│  │   - RadiusValidator                                    │ │
│  │   - CityIdValidator                                    │ │
│  │   - haversine_distance()                               │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │   Configuration                                        │ │
│  │   - Settings (constants)                               │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Princípios Aplicados

### 1. Dependency Rule (Regra de Dependência)

**Dependências apontam sempre para dentro (do externo para o interno):**

```
Infrastructure → Application → Domain
     ↓               ↓            ↓
  Adapters      Use Cases    Entities
                              Exceptions
```

- **Domain** não conhece nada externo (puro Python, zero dependências)
- **Application** conhece apenas Domain (usa entidades e exceções)
- **Infrastructure** conhece Application e Domain (implementa interfaces)

### 2. Interface Segregation

Interfaces pequenas e específicas no lugar de interfaces grandes:

```python
# application/ports/use_case.py
class IUseCase(ABC):
    @abstractmethod
    async def execute(self, *args, **kwargs):
        pass

# application/ports/repository.py
class IRepository(ABC):
    @abstractmethod
    def get_by_id(self, id: str):
        pass
```

### 3. Inversion of Control (IoC)

Use cases dependem de **abstrações** (interfaces), não de implementações concretas:

```python
# Use case depende da interface, não da implementação
class AsyncGetCityWeatherUseCase:
    def __init__(
        self,
        city_repository: IRepository,  # Interface
        weather_repository: IRepository  # Interface
    ):
        self._city_repo = city_repository
        self._weather_repo = weather_repository
```

### 4. Single Responsibility Principle (SRP)

Cada camada tem uma única responsabilidade:

- **Domain**: Regras de negócio puras (entidades, validações)
- **Application**: Orquestração de casos de uso
- **Infrastructure**: Comunicação com o mundo externo (APIs, DB, cache)
- **Presentation**: Conversão HTTP ↔ Domínio

## Estrutura de Diretórios

```
lambda/
├── domain/                          # Camada de Domínio
│   ├── entities/
│   │   ├── __init__.py
│   │   ├── city.py                 # Entidade City
│   │   └── weather.py              # Entidade Weather
│   ├── __init__.py
│   └── exceptions.py               # Exceções de domínio
│
├── application/                     # Camada de Aplicação
│   ├── ports/
│   │   ├── __init__.py
│   │   ├── use_case.py            # Interface IUseCase
│   │   └── repository.py          # Interface IRepository
│   ├── use_cases/
│   │   ├── __init__.py
│   │   ├── async_get_neighbor_cities.py
│   │   ├── async_get_city_weather.py
│   │   └── get_regional_weather.py
│   └── __init__.py
│
├── infrastructure/                  # Camada de Infraestrutura
│   ├── adapters/
│   │   ├── input/
│   │   │   ├── __init__.py
│   │   │   └── lambda_handler.py  # Entry point (routing)
│   │   ├── output/
│   │   │   ├── __init__.py
│   │   │   ├── async_weather_repository.py
│   │   │   └── municipalities_repository.py
│   │   ├── cache/
│   │   │   ├── __init__.py
│   │   │   └── async_dynamodb_cache.py
│   │   └── __init__.py
│   ├── external/
│   │   └── __init__.py
│   └── __init__.py
│
├── shared/                          # Utilitários compartilhados
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py            # Constantes de configuração
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── datetime_parser.py     # Parser de data/hora
│   │   ├── validators.py          # Validadores de input
│   │   └── haversine.py          # Cálculo de distância
│   └── __init__.py
│
├── data/
│   ├── municipalities_db.json     # Base de 5.571 municípios
│   └── test_100_municipalities.json
│
├── tests/
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── conftest.py           # Fixtures compartilhadas
│   │   ├── assertions.py         # Helpers de assertions
│   │   └── test_lambda_integration.py
│   └── unit/
│       ├── __init__.py
│       ├── test_city_entity.py
│       ├── test_weather_entity.py
│       └── test_haversine.py
│
├── lambda_function.py              # Entry point AWS Lambda
├── config.py                       # (deprecated, usar shared/config)
├── requirements.txt
└── requirements-dev.txt
```

## Fluxo de Dados

### Request Flow (Entrada)

```
1. API Gateway
   ↓ (HTTP Request)
2. lambda_handler.py (@app.get("/api/..."))
   ↓ (Extract params, body)
3. Use Case (async execute())
   ↓ (Business logic)
4. Repositories (fetch data)
   ↓ (External APIs/DB)
5. Domain Entities (City, Weather)
   ↓ (to_api_response())
6. lambda_handler.py (return Response)
   ↓ (JSON)
7. API Gateway
   ↓ (HTTP Response)
8. Client
```

### Exemplo Concreto: GET /api/weather/city/{cityId}

```python
# 1. API Gateway recebe request
GET /api/weather/city/3543204?date=2025-11-26&time=15:00

# 2. lambda_handler.py - Route handler
@app.get("/api/weather/city/<city_id>")
def get_city_weather_route(city_id: str):
    # Extract query params
    date_str = app.current_event.get_query_string_value("date")
    time_str = app.current_event.get_query_string_value("time")
    
    # Parse datetime (usa DateTimeParser.from_query_params)
    target_datetime = DateTimeParser.from_query_params(date_str, time_str)
    
    # Get repositories (singletons)
    city_repo = get_repository()
    weather_repo = get_async_weather_repository()
    
    # Execute async use case
    async def execute_async():
        use_case = AsyncGetCityWeatherUseCase(city_repo, weather_repo)
        weather = await use_case.execute(city_id, target_datetime)
        return weather
    
    # Run async code
    weather = asyncio.run(execute_async())
    
    # Convert to API response
    return weather.to_api_response()

# 3. Use Case - Business logic
class AsyncGetCityWeatherUseCase:
    async def execute(self, city_id: str, target_datetime: Optional[datetime]):
        # Validate city_id
        CityIdValidator.validate(city_id)
        
        # Get city (raises CityNotFoundException)
        city = self._city_repo.get_by_id(city_id)
        
        # Get weather (async, with cache)
        weather = await self._weather_repo.get_weather(
            city.latitude,
            city.longitude,
            target_datetime
        )
        
        # Return domain entity
        return weather

# 4. Repository - Fetch data
class AsyncWeatherRepository:
    async def get_weather(self, lat, lon, target_dt):
        # Try cache first
        weather = await self._cache.get(cache_key)
        if weather:
            return weather
        
        # Fetch from OpenWeather API (aiohttp)
        data = await self._fetch_forecast(lat, lon)
        
        # Find closest forecast to target_dt
        forecast = self._find_closest_forecast(data, target_dt)
        
        # Map to domain entity
        weather = Weather(...)
        
        # Save to cache
        await self._cache.set(cache_key, weather)
        
        return weather

# 5. Domain Entity
@dataclass
class Weather:
    city_id: str
    city_name: str
    temperature: float
    humidity: float
    # ...
    
    def to_api_response(self) -> dict:
        return {
            "cityId": self.city_id,
            "cityName": self.city_name,
            "temperature": self.temperature,
            # ...
        }

# 6. Response
{
  "cityId": "3543204",
  "cityName": "Ribeirão do Sul",
  "temperature": 28.3,
  "humidity": 65.0,
  "rainfallIntensity": 35.5
}
```

## Benefícios da Arquitetura

### 1. Testabilidade

Cada camada pode ser testada isoladamente:

```python
# Unit test - Domain entity (sem dependências externas)
def test_weather_creation():
    weather = Weather(
        city_id="123",
        city_name="Test",
        temperature=25.0,
        # ...
    )
    assert weather.temperature == 25.0

# Integration test - Use case com mocks
async def test_get_weather_use_case():
    mock_city_repo = Mock()
    mock_weather_repo = Mock()
    
    use_case = AsyncGetCityWeatherUseCase(mock_city_repo, mock_weather_repo)
    weather = await use_case.execute("123", None)
    
    assert mock_city_repo.get_by_id.called

# Integration test - Full flow (real APIs)
def test_lambda_handler():
    event = build_weather_event(city_id="3543204")
    response = lambda_handler(event, mock_context)
    
    assert response['statusCode'] == 200
```

### 2. Manutenibilidade

Mudanças em uma camada não afetam outras:

- **Trocar DynamoDB por Redis**: Apenas `AsyncDynamoDBCache` muda
- **Trocar OpenWeather por outra API**: Apenas `AsyncWeatherRepository` muda
- **Adicionar novo endpoint**: Apenas adicionar rota em `lambda_handler.py`
- **Mudar regra de negócio**: Apenas use case muda

### 3. Escalabilidade

Fácil adicionar novas features:

```python
# Novo use case: Get weather history
class AsyncGetWeatherHistoryUseCase:
    def __init__(self, city_repo, history_repo):
        self._city_repo = city_repo
        self._history_repo = history_repo
    
    async def execute(self, city_id, start_date, end_date):
        # Business logic
        pass

# Nova rota
@app.get("/api/weather/history/<city_id>")
def get_weather_history_route(city_id: str):
    # Route handler
    pass
```

### 4. Independência de Framework

Core business logic (Domain + Application) não depende de:
- AWS Lambda
- API Gateway
- DynamoDB
- OpenWeather API

Poderia rodar em:
- FastAPI
- Flask
- Django
- Kubernetes
- Serverless Functions (Azure, GCP)

### 5. Performance

Separação de responsabilidades permite otimizações locais:

- **Cache na camada de infraestrutura** (DynamoDB)
- **Async I/O na camada de repositórios** (aiohttp, aioboto3)
- **Throttling na camada de use cases** (Semaphore)
- **Singleton pattern nos repositórios** (warm Lambda starts)

## Design Patterns Utilizados

### 1. Repository Pattern

Abstrai acesso a dados:

```python
class IRepository(ABC):
    @abstractmethod
    def get_by_id(self, id: str):
        pass

class MunicipalitiesRepository(IRepository):
    def get_by_id(self, id: str) -> City:
        # Implementação com JSON in-memory
        pass

class AsyncWeatherRepository(IRepository):
    async def get_weather(self, lat, lon, dt):
        # Implementação com OpenWeather API
        pass
```

### 2. Singleton Pattern

Reutiliza recursos entre invocações Lambda:

```python
_city_repository_instance = None

def get_repository():
    global _city_repository_instance
    if _city_repository_instance is None:
        _city_repository_instance = MunicipalitiesRepository()
    return _city_repository_instance
```

### 3. Strategy Pattern

Diferentes estratégias de cache:

```python
class ICache(ABC):
    @abstractmethod
    async def get(self, key: str):
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int):
        pass

class AsyncDynamoDBCache(ICache):
    async def get(self, key: str):
        # DynamoDB implementation
        pass

class RedisCache(ICache):  # Future
    async def get(self, key: str):
        # Redis implementation
        pass
```

### 4. Factory Pattern

Criação de entidades complexas:

```python
@staticmethod
def from_api_response(data: dict, city_id: str, city_name: str) -> 'Weather':
    """Factory method para criar Weather a partir de API response"""
    return Weather(
        city_id=city_id,
        city_name=city_name,
        timestamp=datetime.fromisoformat(data['dt_txt']),
        temperature=data['main']['temp'],
        # ...
    )
```

### 5. Adapter Pattern

Adapta APIs externas para interfaces internas:

```python
# External API response
{
  "main": {"temp": 25.5, "humidity": 65},
  "wind": {"speed": 3.5},
  "pop": 0.35
}

# Adapted to domain entity
Weather(
    temperature=25.5,
    humidity=65.0,
    wind_speed=12.6,  # converted to km/h
    rainfall_intensity=35.0  # pop * 100
)
```

## Considerações de Performance

### 1. Lazy Loading

Repositórios carregam dados apenas quando necessário:

```python
class MunicipalitiesRepository:
    def __init__(self):
        self._municipalities = None  # Lazy
        self._indices = None
    
    def _ensure_loaded(self):
        if self._municipalities is None:
            self._load_municipalities()
```

### 2. Async I/O

Todas as operações de I/O são assíncronas:

```python
# Paralelo (asyncio.gather)
async def _fetch_all_cities(self, city_ids, target_dt):
    tasks = [
        self._fetch_city_weather(city_id, target_dt)
        for city_id in city_ids
    ]
    return await asyncio.gather(*tasks, return_exceptions=True)
```

### 3. Cache Strategy

3 níveis de cache:

1. **Lambda warm start** (singleton repositories, ~10-50ms)
2. **DynamoDB cache** (TTL 3h, ~20-30ms)
3. **OpenWeather API** (fallback, ~200-500ms)

### 4. Throttling

Controle de concorrência:

```python
# Limitar a 50 requests simultâneas
self._semaphore = asyncio.Semaphore(50)

async with self._semaphore:
    weather = await self._weather_repo.get_weather(...)
```

## Evolução da Arquitetura

### Versão 1.0 (Inicial)
- Sync I/O (requests)
- Lambda handler monolítico
- Cache inexistente

### Versão 2.0 (Refatoração Clean Architecture)
- Separação em camadas
- Domain exceptions
- Ports & Adapters

### Versão 3.0 (Atual - 100% Async)
- ✅ Async I/O (aiohttp, aioboto3)
- ✅ DynamoDB cache
- ✅ AWS Powertools
- ✅ Lazy session creation
- ✅ Event loop check
- ✅ Structured logging

## Referências

- [Clean Architecture - Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Hexagonal Architecture - Alistair Cockburn](https://alistair.cockburn.us/hexagonal-architecture/)
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [AWS Powertools Python](https://docs.powertools.aws.dev/lambda/python/latest/)
