# API - Rotas e Endpoints

## Visão Geral

A API expõe 3 endpoints REST para consulta de dados meteorológicos e cidades vizinhas, implementados com **AWS API Gateway + Lambda** usando **AWS Powertools APIGatewayRestResolver**.

**Base URL (produção):**
```
https://{api-id}.execute-api.sa-east-1.amazonaws.com/prod
```

## Arquitetura de Rotas

### AWS Powertools APIGatewayRestResolver

```python
from aws_lambda_powertools.event_handler import APIGatewayRestResolver

app = APIGatewayRestResolver()

@app.get("/api/cities/neighbors/<city_id>")
def get_neighbors_route(city_id: str):
    # Route handler
    pass

def lambda_handler(event, context):
    return app.resolve(event, context)
```

**Benefícios:**
- ✅ Roteamento automático baseado em decorators
- ✅ Extração automática de path params (`<city_id>`)
- ✅ Suporte a query strings (`app.current_event.get_query_string_value()`)
- ✅ Exception handlers com `@app.exception_handler`
- ✅ CORS configurado via `cors` parameter

### Pattern: Sync Routes + Async Execution

Como AWS Powertools não suporta `async def` routes, usamos o pattern:

```python
@app.get("/api/weather/city/<city_id>")
def get_city_weather_route(city_id: str):  # Sync route
    import asyncio
    
    # Define async inner function
    async def execute_async():
        use_case = AsyncGetCityWeatherUseCase(...)
        weather = await use_case.execute(city_id, target_datetime)
        return weather
    
    # Run async code
    weather = asyncio.run(execute_async())
    
    # Return response
    return weather.to_api_response()
```

**Por que funciona:**
- Cada invocação Lambda é independente
- `asyncio.run()` cria um novo event loop para cada request
- Lazy session creation garante compatibilidade com múltiplas invocações

---

## 1. GET /api/cities/neighbors/{cityId}

### Descrição

Busca a cidade centro e suas cidades vizinhas dentro de um raio especificado.

### Request

**Method:** `GET`

**Path Parameters:**
- `cityId` (string, required): Código IBGE da cidade (7 dígitos)

**Query Parameters:**
- `radius` (integer, optional): Raio em km (min: 1, max: 500, default: 50)

**Headers:**
```
Accept: application/json
```

### Response

**Success (200 OK):**

```json
{
  "centerCity": {
    "id": "3543204",
    "name": "Ribeirão do Sul",
    "state": "SP",
    "latitude": -22.7572,
    "longitude": -49.9439
  },
  "neighbors": [
    {
      "id": "3550506",
      "name": "São Pedro do Turvo",
      "state": "SP",
      "latitude": -22.8978,
      "longitude": -49.7433,
      "distance": 17.8
    },
    {
      "id": "3513504",
      "name": "Chavantes",
      "state": "SP",
      "latitude": -23.0392,
      "longitude": -49.7089,
      "distance": 32.5
    }
  ]
}
```

**Error (404 Not Found):**

```json
{
  "type": "CityNotFoundException",
  "error": "City not found",
  "message": "City not found",
  "details": {
    "city_id": "9999999"
  }
}
```

**Error (400 Bad Request):**

```json
{
  "type": "InvalidRadiusException",
  "error": "Invalid radius",
  "message": "Radius must be between 1.0 and 500.0 km",
  "details": {
    "radius": 999.0,
    "min": 1.0,
    "max": 500.0
  }
}
```

### Exemplos

```bash
# Buscar vizinhos em 50km (default)
curl "https://api.example.com/api/cities/neighbors/3543204"

# Buscar vizinhos em 100km
curl "https://api.example.com/api/cities/neighbors/3543204?radius=100"

# Buscar vizinhos em raio mínimo (1km)
curl "https://api.example.com/api/cities/neighbors/3543204?radius=1"
```

### Implementação

```python
@app.get("/api/cities/neighbors/<city_id>")
def get_neighbors_route(city_id: str):
    """
    GET /api/cities/neighbors/{cityId}?radius=50
    Returns center city and neighbor cities within radius
    """
    import asyncio
    
    logger.info("Get neighbors", city_id=city_id)
    
    # Extract radius from query string
    radius_str = app.current_event.get_query_string_value(name="radius", default_value="50")
    
    # Validate radius (throws InvalidRadiusException)
    radius = RadiusValidator.validate(radius_str)
    
    # Get repository (singleton)
    city_repository = get_repository()
    
    # Execute use case (async)
    async def execute_async():
        use_case = AsyncGetNeighborCitiesUseCase(city_repository)
        result = await use_case.execute(city_id, radius)
        return result
    
    # Run async code
    result = asyncio.run(execute_async())
    
    # Log success
    logger.info(
        "Neighbors found",
        city_id=city_id,
        city_name=result['centerCity']['name'],
        neighbors_count=len(result['neighbors'])
    )
    
    return result
```

### Algoritmo de Busca

1. **Validar city_id** (CityIdValidator)
2. **Validar radius** (RadiusValidator: 1-500km)
3. **Buscar cidade centro** (raises CityNotFoundException)
4. **Filtrar cidades do mesmo estado** (otimização)
5. **Calcular distâncias** (fórmula de Haversine)
6. **Filtrar por raio**
7. **Ordenar por distância** (ascendente)
8. **Retornar resultado**

**Complexidade:** O(n) onde n = cidades do estado

---

## 2. GET /api/weather/city/{cityId}

### Descrição

Retorna previsão meteorológica de uma cidade específica. Suporta busca por data/hora específica ou próxima previsão disponível.

### Request

**Method:** `GET`

**Path Parameters:**
- `cityId` (string, required): Código IBGE da cidade

**Query Parameters:**
- `date` (string, optional): Data no formato `YYYY-MM-DD` (ex: `2025-11-26`)
- `time` (string, optional): Hora no formato `HH:MM` (ex: `15:00`)

**Headers:**
```
Accept: application/json
```

**Comportamento de date/time:**

| date | time | Comportamento |
|------|------|--------------|
| ❌ None | ❌ None | Retorna próxima previsão disponível |
| ✅ Set | ❌ None | Retorna previsão para meio-dia (12:00) da data |
| ❌ None | ✅ Set | Retorna previsão para hoje no horário |
| ✅ Set | ✅ Set | Retorna previsão para data/hora específica |

### Response

**Success (200 OK):**

```json
{
  "cityId": "3543204",
  "cityName": "Ribeirão do Sul",
  "timestamp": "2025-11-26T15:00:00",
  "temperature": 28.3,
  "humidity": 65.0,
  "windSpeed": 12.5,
  "rainfallIntensity": 35.5,
  "weatherDescription": "Parcialmente nublado"
}
```

**Campos:**

| Campo | Tipo | Descrição | Unidade |
|-------|------|-----------|---------|
| `cityId` | string | Código IBGE | - |
| `cityName` | string | Nome do município | - |
| `timestamp` | string | Data/hora da previsão (ISO 8601) | - |
| `temperature` | float | Temperatura | °C |
| `humidity` | float | Umidade relativa | % (0-100) |
| `windSpeed` | float | Velocidade do vento | km/h |
| `rainfallIntensity` | float | Probabilidade de chuva | % (0-100) |
| `weatherDescription` | string | Descrição do clima | - |

**Error (404 Not Found):**

```json
{
  "type": "CityNotFoundException",
  "error": "City not found",
  "message": "City not found",
  "details": {
    "city_id": "9999999"
  }
}
```

```json
{
  "type": "WeatherDataNotFoundException",
  "error": "Weather data not found",
  "message": "No forecast available for the requested date/time",
  "details": {
    "city_id": "3543204",
    "requested_datetime": "2025-12-30T15:00:00"
  }
}
```

**Error (400 Bad Request):**

```json
{
  "type": "InvalidDateTimeException",
  "error": "Invalid datetime",
  "message": "Invalid date format. Expected YYYY-MM-DD",
  "details": {
    "date": "26/11/2025"
  }
}
```

### Exemplos

```bash
# Próxima previsão disponível
curl "https://api.example.com/api/weather/city/3543204"

# Previsão para amanhã ao meio-dia
curl "https://api.example.com/api/weather/city/3543204?date=2025-11-26"

# Previsão para amanhã às 15h
curl "https://api.example.com/api/weather/city/3543204?date=2025-11-26&time=15:00"

# Previsão para hoje às 18h
curl "https://api.example.com/api/weather/city/3543204?time=18:00"
```

### Implementação

```python
@app.get("/api/weather/city/<city_id>")
def get_city_weather_route(city_id: str):
    """
    GET /api/weather/city/{cityId}?date=2025-11-26&time=15:00
    Returns weather forecast for a specific city
    """
    import asyncio
    
    logger.info("Get city weather", city_id=city_id)
    
    # Extract date and time from query string
    date_str = app.current_event.get_query_string_value(name="date", default_value=None)
    time_str = app.current_event.get_query_string_value(name="time", default_value=None)
    
    # Parse datetime (throws InvalidDateTimeException)
    target_datetime = DateTimeParser.from_query_params(date_str, time_str)
    
    # Get repositories (singletons)
    city_repository = get_repository()
    weather_repository = get_async_weather_repository()
    
    # Execute use case (async)
    async def execute_async():
        use_case = AsyncGetCityWeatherUseCase(city_repository, weather_repository)
        weather = await use_case.execute(city_id, target_datetime)
        return weather
    
    # Run async code
    weather = asyncio.run(execute_async())
    
    # Log success
    logger.info(
        "Weather fetched",
        city_id=city_id,
        city_name=weather.city_name,
        temperature=weather.temperature
    )
    
    # Convert to API response
    return weather.to_api_response()
```

### Fluxo de Cache

```
1. Request → lambda_handler
2. Parse datetime
3. Generate cache key: f"weather_{city_id}_{lat}_{lon}_{timestamp}"
4. Check DynamoDB cache
   ├─ HIT → Return cached weather (latency: ~20-30ms)
   └─ MISS → Continue to step 5
5. Fetch from OpenWeather API (latency: ~200-500ms)
6. Find closest forecast to target_datetime
7. Map to Weather entity
8. Save to DynamoDB cache (TTL: 3 hours)
9. Return weather
```

### Algoritmo de Busca de Previsão

OpenWeather retorna previsões de 3 em 3 horas. Para encontrar a mais próxima:

```python
def _find_closest_forecast(self, forecasts, target_dt):
    """
    Find forecast closest to target datetime
    
    Example:
        target_dt = 2025-11-26 15:00
        forecasts = [
            2025-11-26 12:00 (diff: 3h),
            2025-11-26 15:00 (diff: 0h) ← CLOSEST,
            2025-11-26 18:00 (diff: 3h)
        ]
    """
    closest = min(
        forecasts,
        key=lambda f: abs((f['dt_datetime'] - target_dt).total_seconds())
    )
    return closest
```

---

## 3. POST /api/weather/regional

### Descrição

Retorna previsões meteorológicas de múltiplas cidades em paralelo. Ideal para buscar clima de uma região inteira (até 100 cidades).

**Performance:** P99 <200ms para 100 cidades

### Request

**Method:** `POST`

**Headers:**
```
Content-Type: application/json
Accept: application/json
```

**Query Parameters:**
- `date` (string, optional): Data no formato `YYYY-MM-DD`
- `time` (string, optional): Hora no formato `HH:MM`

**Body:**

```json
{
  "cityIds": [
    "3543204",
    "3548708",
    "3509502"
  ]
}
```

**Limites:**
- Mínimo: 0 cidades (retorna `[]`)
- Máximo: 100 cidades (recomendado)
- Limite técnico: Sem limite hard, mas performance degrada após 100 cidades

### Response

**Success (200 OK):**

```json
[
  {
    "cityId": "3543204",
    "cityName": "Ribeirão do Sul",
    "timestamp": "2025-11-26T15:00:00",
    "temperature": 28.3,
    "humidity": 65.0,
    "windSpeed": 12.5,
    "rainfallIntensity": 35.5
  },
  {
    "cityId": "3548708",
    "cityName": "São Carlos",
    "timestamp": "2025-11-26T15:00:00",
    "temperature": 27.1,
    "humidity": 58.0,
    "windSpeed": 15.2,
    "rainfallIntensity": 20.0
  },
  {
    "cityId": "3509502",
    "cityName": "Campinas",
    "timestamp": "2025-11-26T15:00:00",
    "temperature": 29.5,
    "humidity": 62.0,
    "windSpeed": 10.8,
    "rainfallIntensity": 15.0
  }
]
```

**Lista vazia (200 OK):**

```json
[]
```

**Error (400 Bad Request):**

```json
{
  "type": "InvalidDateTimeException",
  "error": "Invalid datetime",
  "message": "cityIds must be an array of strings",
  "details": {
    "body": {
      "cityIds": "not-an-array"
    }
  }
}
```

### Exemplos

```bash
# Próxima previsão para múltiplas cidades
curl -X POST "https://api.example.com/api/weather/regional" \
  -H "Content-Type: application/json" \
  -d '{
    "cityIds": ["3543204", "3548708", "3509502"]
  }'

# Previsão para data/hora específica
curl -X POST "https://api.example.com/api/weather/regional?date=2025-11-26&time=15:00" \
  -H "Content-Type: application/json" \
  -d '{
    "cityIds": ["3543204", "3548708", "3509502"]
  }'

# Lista vazia (válido)
curl -X POST "https://api.example.com/api/weather/regional" \
  -H "Content-Type: application/json" \
  -d '{
    "cityIds": []
  }'
```

### Implementação

```python
@app.post("/api/weather/regional")
def post_regional_weather_route():
    """
    POST /api/weather/regional?date=2025-11-26&time=15:00
    Body: { "cityIds": ["3543204", "3548708", "3509502"] }
    
    Returns weather forecasts for multiple cities (parallel)
    """
    import asyncio
    
    logger.info("POST regional weather - ASYNC")
    
    # Extract cityIds from body
    body = app.current_event.json_body
    city_ids = body.get('cityIds', [])
    
    logger.info("Regional request", city_count=len(city_ids))
    
    # Validate cityIds format
    if not isinstance(city_ids, list):
        raise InvalidDateTimeException(
            "cityIds must be an array of strings",
            details={"body": body}
        )
    
    # Validate all city IDs
    for city_id in city_ids:
        CityIdValidator.validate(city_id)
    
    # Extract date and time from query string
    date_str = app.current_event.get_query_string_value(name="date", default_value=None)
    time_str = app.current_event.get_query_string_value(name="time", default_value=None)
    
    # Parse datetime
    target_datetime = DateTimeParser.from_query_params(date_str, time_str)
    
    # Get repositories (singletons)
    city_repository = get_repository()
    weather_repository = get_async_weather_repository()
    
    # Execute async use case
    async def execute_async():
        use_case = AsyncGetRegionalWeatherUseCase(city_repository, weather_repository)
        weather_list = await use_case.execute(city_ids, target_datetime)
        return weather_list
    
    # Run async code
    weather_list = asyncio.run(execute_async())
    
    # Convert to API format
    response = [weather.to_api_response() for weather in weather_list]
    
    # Log success
    success_rate = (len(response) / len(city_ids)) * 100 if city_ids else 0
    logger.info(
        "Regional ASYNC completed",
        success_count=len(response),
        total_count=len(city_ids),
        success_rate=f"{success_rate:.1f}%"
    )
    
    return response
```

### Execução Paralela

```python
class AsyncGetRegionalWeatherUseCase:
    async def execute(self, city_ids, target_datetime):
        # Fetch all cities in parallel with throttling
        weather_data = await self._fetch_all_cities(city_ids, target_datetime)
        return weather_data
    
    async def _fetch_all_cities(self, city_ids, target_dt):
        """
        Fetch weather for multiple cities in parallel
        Uses Semaphore(50) to limit concurrent requests
        """
        tasks = [
            self._fetch_city_weather(city_id, target_dt)
            for city_id in city_ids
        ]
        
        # Execute with asyncio.gather
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        weather_data = [r for r in results if isinstance(r, Weather)]
        
        return weather_data
    
    async def _fetch_city_weather(self, city_id, target_dt):
        """Fetch weather for a single city (with throttling)"""
        async with self._semaphore:  # Semaphore(50)
            try:
                city = self._city_repo.get_by_id(city_id)
                weather = await self._weather_repo.get_weather(
                    city.latitude,
                    city.longitude,
                    target_dt
                )
                weather.city_id = city_id
                weather.city_name = city.name
                return weather
            except Exception as e:
                logger.warning("Failed to fetch city", city_id=city_id, error=str(e))
                return e  # Return exception (filtered later)
```

### Performance Characteristics

**Benchmarks (100 cidades):**

| Métrica | Valor |
|---------|-------|
| Latência P50 | ~150ms |
| Latência P99 | <200ms |
| Latência média/cidade | ~18.5ms |
| Throughput | 50-100 cities/sec |
| Cache hit rate | ~80% (após warm-up) |

**Throttling:**
- Semaphore(50) limita a 50 requests simultâneas
- Previne sobrecarga do Lambda (512MB memory)
- Previne rate limiting da OpenWeather API

---

## Exception Handlers

Todos os endpoints usam exception handlers centralizados com AWS Powertools:

```python
@app.exception_handler(CityNotFoundException)
def handle_city_not_found(ex: CityNotFoundException):
    """Handle 404 - City not found"""
    logger.warning("City not found", error=str(ex), details=ex.details)
    return Response(
        status_code=404,
        content_type="application/json",
        body=json.dumps({
            "type": "CityNotFoundException",
            "error": "City not found",
            "message": str(ex),
            "details": ex.details
        })
    )

@app.exception_handler(InvalidRadiusException)
def handle_invalid_radius(ex: InvalidRadiusException):
    """Handle 400 - Invalid radius"""
    logger.warning("Invalid radius", error=str(ex), details=ex.details)
    return Response(
        status_code=400,
        content_type="application/json",
        body=json.dumps({
            "type": "InvalidRadiusException",
            "error": "Invalid radius",
            "message": str(ex),
            "details": ex.details
        })
    )

@app.exception_handler(Exception)
def handle_unexpected_error(ex: Exception):
    """Handle 500 - Unexpected error"""
    logger.error("Unexpected error", error=str(ex), exc_info=True)
    return Response(
        status_code=500,
        content_type="application/json",
        body=json.dumps({
            "type": "InternalServerError",
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        })
    )
```

**Mapeamento de Exceções:**

| Exception | Status Code | Type |
|-----------|-------------|------|
| `CityNotFoundException` | 404 | City/coordinates not found |
| `CoordinatesNotFoundException` | 404 | No coordinates for city |
| `WeatherDataNotFoundException` | 404 | No forecast for date/time |
| `InvalidRadiusException` | 400 | Radius out of range (1-500) |
| `InvalidDateTimeException` | 400 | Invalid date/time format |
| `Exception` (catch-all) | 500 | Unexpected error |

---

## CORS Configuration

```python
app = APIGatewayRestResolver(
    cors=CORSConfig(
        allow_origin="*",  # Configurado via variável de ambiente
        max_age=300,
        allow_headers=["Content-Type", "Authorization"],
        expose_headers=["x-amzn-RequestId"]
    )
)
```

**Headers CORS automáticos:**
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Max-Age: 300
```

---

## Rate Limiting

**Atual:** Sem rate limiting implementado

**Futuras implementações:**
1. API Gateway throttling (AWS nativo)
2. Lambda concurrency limits
3. DynamoDB rate limiting (contador de requests)
4. Redis rate limiting (Token Bucket algorithm)

---

## Monitoring & Logging

Todos os endpoints usam AWS Powertools Logger com structured logging:

```python
from aws_lambda_powertools import Logger

logger = Logger()

# Start of request
logger.info("Lambda invoked", path=event['path'], method=event['httpMethod'])

# Business events
logger.info("Neighbors found", city_id=city_id, neighbors_count=21)

# Errors
logger.warning("City not found", city_id=city_id, error=str(ex))
logger.error("Unexpected error", error=str(ex), exc_info=True)

# End of request
logger.info("Lambda completed", status_code=200, latency_ms="73.4")
```

**CloudWatch Insights queries:**

```sql
# Requests por endpoint
fields @timestamp, path, method, status_code
| filter path like /api/
| stats count() by path

# Latência média por endpoint
fields @timestamp, path, latency_ms
| filter path like /api/
| stats avg(latency_ms) as avg_latency by path

# Erros 4xx/5xx
fields @timestamp, path, status_code, error
| filter status_code >= 400
| sort @timestamp desc
```

---

## Segurança

### Validação de Input

Todos os inputs são validados antes do processamento:

```python
# City ID (7 dígitos)
CityIdValidator.validate("3543204")  # OK
CityIdValidator.validate("123")      # Exception

# Radius (1-500km)
RadiusValidator.validate("50")    # OK
RadiusValidator.validate("999")   # Exception

# Date/Time (ISO 8601)
DateTimeParser.from_query_params("2025-11-26", "15:00")  # OK
DateTimeParser.from_query_params("26/11/2025", "15:00")  # Exception
```

### Sanitização

Todos os dados de output são sanitizados via `json.dumps()`:

```python
return Response(
    status_code=200,
    content_type="application/json",
    body=json.dumps(response_data)  # Safe serialization
)
```

### Headers de Segurança

```python
# Configurado no API Gateway
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Strict-Transport-Security: max-age=31536000
```

---

## Versionamento

**Atual:** v1 (sem prefixo de versão)

**Futuro:** Adicionar prefixo `/v1` ou `/v2`:

```
GET /api/v1/weather/city/{cityId}
GET /api/v2/weather/city/{cityId}
```

**Estratégias:**
1. URL versioning (`/v1/`, `/v2/`)
2. Header versioning (`X-API-Version: 1`)
3. Accept header (`Accept: application/vnd.api+json;version=1`)

---

## Testes de API

Todos os endpoints têm testes de integração:

```bash
# Run integration tests
pytest lambda/tests/integration/ -v

# Run with coverage
pytest lambda/tests/integration/ --cov=lambda

# Test specific endpoint
pytest lambda/tests/integration/test_lambda_integration.py::TestWeatherEndpoint -v
```

Ver documentação completa: [docs/development/TESTING.md](../development/TESTING.md)
