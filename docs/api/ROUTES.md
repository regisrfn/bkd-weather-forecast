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
| `rainfallIntensity` | float | Intensidade de chuva composta (volume × probabilidade) | 0-100 (100 = 30mm/h a 100% prob) |
| `rainfallProbability` | float | Probabilidade de chuva | % (0-100) |
| `rainVolumeHour` | float | Volume de chuva | mm/h |
| `dailyRainAccumulation` | float | Acumulado de chuva esperado no dia | mm |
| `weatherDescription` | string | Descrição do clima | - |
| `weatherAlert` | array | Lista de alertas climáticos | - |
| `feelsLike` | float | Sensação térmica | °C |
| `pressure` | float | Pressão atmosférica | hPa |
| `visibility` | float | Visibilidade | metros |
| `clouds` | float | Cobertura de nuvens | % (0-100) |
| `cloudsDescription` | string | Descrição da cobertura de nuvens | - |
| `tempMin` | float | Temperatura mínima do dia | °C |
| `tempMax` | float | Temperatura máxima do dia | °C |

**Exemplo de resposta completa com alertas:**

```json
{
  "cityId": "3543204",
  "cityName": "Ribeirão do Sul",
  "timestamp": "2025-11-27T15:00:00-03:00",
  "temperature": 28.3,
  "humidity": 65.0,
  "windSpeed": 12.5,
  "rainfallIntensity": 35.5,
  "description": "céu limpo",
  "feelsLike": 29.0,
  "pressure": 1013.0,
  "visibility": 10000,
  "clouds": 2.0,
  "cloudsDescription": "Céu limpo",
  "weatherAlert": [
    {
      "code": "MODERATE_RAIN",
      "severity": "warning",
      "description": "🌧️ Chuva moderada",
      "timestamp": "2025-11-27T18:00:00-03:00",
      "details": {
        "rain_mm_h": 15.5
      }
    },
    {
      "code": "STRONG_WIND",
      "severity": "alert",
      "description": "💨 ALERTA: Ventos fortes",
      "timestamp": "2025-11-27T21:00:00-03:00",
      "details": {
        "wind_speed_kmh": 65.0
      }
    }
  ],
  "tempMin": 18.5,
  "tempMax": 32.1
}
```

### Alertas Meteorológicos

A API retorna alertas climáticos estruturados no campo `weatherAlert` baseados nas previsões dos próximos 5 dias.

#### Estrutura de um Alerta

```json
{
  "code": "MODERATE_RAIN",
  "severity": "warning",
  "description": "🌧️ Chuva moderada",
  "timestamp": "2025-11-27T18:00:00-03:00",
  "details": {
    "rain_mm_h": 15.5,
    "probability_percent": 85.0
  }
}
```

**Campos:**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `code` | string | Código único do alerta (ver tabela abaixo) |
| `severity` | string | Nível de severidade: `info`, `warning`, `alert`, `danger` |
| `description` | string | Descrição em português com emoji |
| `timestamp` | string | Data/hora quando o alerta se aplica (ISO 8601) |
| `details` | object | Informações adicionais (opcional) |

#### Níveis de Severidade

| Severidade | Cor Sugerida | Uso |
|------------|--------------|-----|
| `info` | 🔵 Azul | Informativo, sem necessidade de ação |
| `warning` | 🟡 Amarelo | Atenção, preparação recomendada |
| `alert` | 🟠 Laranja | Alerta, ação necessária |
| `danger` | 🔴 Vermelho | Perigo, ação imediata necessária |

#### Códigos de Alerta Disponíveis

##### 🌧️ Alertas de Precipitação (baseados em volume mm/h)

| Código | Severidade | Descrição | Limiar | Details |
|--------|-----------|-----------|---------|---------|
| `DRIZZLE` | info | 🌦️ Garoa | < 2.5 mm/h | `rain_mm_h` |
| `LIGHT_RAIN` | info | 🌧️ Chuva fraca | 2.5-10 mm/h | `rain_mm_h` |
| `MODERATE_RAIN` | warning | 🌧️ Chuva moderada | 10-50 mm/h | `rain_mm_h` |
| `HEAVY_RAIN` | alert | ⚠️ ALERTA: Chuva forte | > 50 mm/h | `rain_mm_h` |
| `RAIN_EXPECTED` | info | 🌧️ Alta probabilidade de chuva | Probabilidade ≥ 70% | `probability_percent` |

##### ⛈️ Alertas de Tempestade

| Código | Severidade | Descrição | Condição | Details |
|--------|-----------|-----------|----------|---------|
| `STORM` | danger | ⚠️ ALERTA: Tempestade com raios | Códigos 200-212, 221 | `weather_code`, `rain_mm_h` |
| `STORM_RAIN` | alert | ⚠️ Tempestade com chuva | Outros códigos 2xx | `weather_code`, `rain_mm_h` |

##### 💨 Alertas de Vento

| Código | Severidade | Descrição | Limiar | Details |
|--------|-----------|-----------|---------|---------|
| `MODERATE_WIND` | info | 💨 Ventos moderados | 30-49 km/h | `wind_speed_kmh` |
| `STRONG_WIND` | alert | 💨 ALERTA: Ventos fortes | ≥ 50 km/h | `wind_speed_kmh` |

##### 🌡️ Alertas de Temperatura

| Código | Severidade | Descrição | Limiar | Details |
|--------|-----------|-----------|---------|---------|
| `COLD` | alert | 🧊 Frio | < 12°C | `temperature_c` |
| `VERY_COLD` | danger | 🥶 ALERTA: Frio intenso | < 8°C | `temperature_c` |
| `TEMP_DROP` | warning | 🌡️ Queda de temperatura | Variação > 8°C entre dias | `day_1_date`, `day_1_max_c`, `day_2_date`, `day_2_max_c`, `variation_c` |
| `TEMP_RISE` | info | 🌡️ Aumento de temperatura | Variação > 8°C entre dias | `day_1_date`, `day_1_max_c`, `day_2_date`, `day_2_max_c`, `variation_c` |

##### ❄️ Outros Alertas

| Código | Severidade | Descrição | Condição | Details |
|--------|-----------|-----------|----------|---------|
| `SNOW` | info | ❄️ Neve (raro no Brasil) | Códigos 600-699 | `weather_code`, `temperature_c` |

#### Exemplos de Details por Tipo de Alerta

**Precipitação:**
```json
{
  "details": {
    "rain_mm_h": 15.5
  }
}
```

**Vento:**
```json
{
  "details": {
    "wind_speed_kmh": 65.0
  }
}
```

**Temperatura:**
```json
{
  "details": {
    "temperature_c": 10.5
  }
}
```

**Variação de temperatura:**
```json
{
  "details": {
    "day_1_date": "2025-11-27",
    "day_1_max_c": 28.0,
    "day_2_date": "2025-11-28",
    "day_2_max_c": 18.0,
    "variation_c": -10.0
  }
}
```

**Tempestade:**
```json
{
  "details": {
    "weather_code": 210,
    "rain_mm_h": 20.0
  }
}
```

**Probabilidade de chuva:**
```json
{
  "details": {
    "probability_percent": 85.0
  }
}
```

#### Características dos Alertas

- **Deduplição**: Cada código de alerta aparece apenas uma vez na lista
- **Múltiplos alertas**: Uma previsão pode ter vários alertas simultâneos (ex: tempestade + vento forte + frio)
- **Campo opcional**: O campo `details` é opcional e pode não estar presente em alguns alertas
- **Horário Brasil**: Todos os `timestamp` dos alertas estão em horário de Brasília (America/Sao_Paulo)
- **Próximos 5 dias**: Alertas são coletados de todas as previsões futuras (até 5 dias)
- **Limiares brasileiros**: Alertas de frio consideram o contexto climático brasileiro

#### Uso Recomendado no Frontend

```javascript
// Exemplo de processamento de alertas
weather.weatherAlert.forEach(alert => {
  // Filtrar por severidade
  if (alert.severity === 'danger' || alert.severity === 'alert') {
    showNotification(alert.description);
  }
  
  // Exibir detalhes se disponíveis
  if (alert.details) {
    if (alert.details.rain_mm_h) {
      console.log(`Precipitação: ${alert.details.rain_mm_h} mm/h`);
    }
    if (alert.details.wind_speed_kmh) {
      console.log(`Vento: ${alert.details.wind_speed_kmh} km/h`);
    }
  }
});

// Agrupar por severidade
const criticalAlerts = weather.weatherAlert.filter(a => 
  a.severity === 'danger' || a.severity === 'alert'
);

// Verificar se há alerta específico
const hasColdAlert = weather.weatherAlert.some(a => 
  a.code === 'COLD' || a.code === 'VERY_COLD'
);
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

## 4. GET /api/weather/city/{cityId}/detailed

### Descrição

Retorna previsão meteorológica detalhada com dados estendidos de até 16 dias. Combina dados do **OpenWeather** (5 dias, 3h intervalo) com **Open-Meteo** (16 dias, dados diários) para fornecer informações astronômicas (nascer/pôr do sol, fase da lua), índice UV, e previsões de longo prazo.

**Performance:** P99 <300ms (2 APIs em paralelo)

### Request

**Method:** `GET`

**Path Parameters:**
- `cityId` (string, required): Código IBGE da cidade

**Query Parameters:**
- `date` (string, optional): Data no formato `YYYY-MM-DD`
- `time` (string, optional): Hora no formato `HH:MM`

**Headers:**
```
Accept: application/json
```

### Response

**Success (200 OK):**

```json
{
  "cityInfo": {
    "cityId": "3543204",
    "cityName": "Ribeirão do Sul",
    "state": "SP",
    "latitude": -22.7572,
    "longitude": -49.9439
  },
  "currentWeather": {
    "temperature": 28.3,
    "feelsLike": 29.0,
    "humidity": 65.0,
    "pressure": 1013.0,
    "windSpeed": 12.5,
    "clouds": 40.0,
    "visibility": 10000,
    "weatherDescription": "Parcialmente nublado",
    "timestamp": "2025-11-30T15:00:00-03:00"
  },
  "dailyForecasts": [
    {
      "date": "2025-11-30",
      "tempMax": 32.1,
      "tempMin": 18.5,
      "precipitation": 2.5,
      "precipitationProbability": 30.0,
      "precipitationHours": 2.0,
      "windSpeedMax": 15.5,
      "uvIndexMax": 8.5,
      "uvRiskLevel": "Alto",
      "uvRiskColor": "#FF6B00",
      "sunrise": "05:45:00",
      "sunset": "18:32:00",
      "daylightHours": 12.78,
      "moonPhase": "Lua Crescente",
      "weatherDescription": "Parcialmente nublado"
    },
    {
      "date": "2025-12-01",
      "tempMax": 30.5,
      "tempMin": 19.2,
      "precipitation": 15.8,
      "precipitationProbability": 80.0,
      "precipitationHours": 6.0,
      "windSpeedMax": 22.3,
      "uvIndexMax": 6.2,
      "uvRiskLevel": "Moderado",
      "uvRiskColor": "#FFD700",
      "sunrise": "05:44:00",
      "sunset": "18:33:00",
      "daylightHours": 12.81,
      "moonPhase": "Quarto Crescente",
      "weatherDescription": "Chuva moderada"
    }
  ],
  "extendedAvailable": true
}
```

**Campos da resposta:**

#### `cityInfo` (object)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `cityId` | string | Código IBGE da cidade |
| `cityName` | string | Nome do município |
| `state` | string | Sigla do estado (UF) |
| `latitude` | float | Latitude da cidade |
| `longitude` | float | Longitude da cidade |

#### `currentWeather` (object)

| Campo | Tipo | Descrição | Unidade |
|-------|------|-----------|---------|
| `temperature` | float | Temperatura atual | °C |
| `feelsLike` | float | Sensação térmica | °C |
| `humidity` | float | Umidade relativa | % (0-100) |
| `pressure` | float | Pressão atmosférica | hPa |
| `windSpeed` | float | Velocidade do vento | km/h |
| `clouds` | float | Cobertura de nuvens | % (0-100) |
| `visibility` | float | Visibilidade | metros |
| `weatherDescription` | string | Descrição do clima | - |
| `timestamp` | string | Data/hora da previsão (ISO 8601) | - |

#### `dailyForecasts` (array)

Array com até 16 elementos (dias) ordenados por data crescente.

| Campo | Tipo | Descrição | Unidade |
|-------|------|-----------|---------|
| `date` | string | Data da previsão (YYYY-MM-DD) | - |
| `tempMax` | float | Temperatura máxima do dia | °C |
| `tempMin` | float | Temperatura mínima do dia | °C |
| `precipitation` | float | Precipitação acumulada | mm |
| `precipitationProbability` | float | Probabilidade de precipitação | % (0-100) |
| `precipitationHours` | float | Horas de precipitação estimadas | horas |
| `windSpeedMax` | float | Velocidade máxima do vento | km/h |
| `uvIndexMax` | float | Índice UV máximo | 0-11+ |
| `uvRiskLevel` | string | Nível de risco UV: "Baixo", "Moderado", "Alto", "Muito Alto", "Extremo" | - |
| `uvRiskColor` | string | Cor hexadecimal do risco UV para UI | - |
| `sunrise` | string | Horário do nascer do sol (HH:MM:SS) | - |
| `sunset` | string | Horário do pôr do sol (HH:MM:SS) | - |
| `daylightHours` | float | Duração do dia (sunset - sunrise) | horas |
| `moonPhase` | string | Fase da lua: "Lua Nova", "Quarto Crescente", "Lua Cheia", "Quarto Minguante", "Lua Crescente", "Lua Minguante" | - |
| `weatherDescription` | string | Descrição do clima previsto | - |

#### `extendedAvailable` (boolean)

Indica se dados estendidos (Open-Meteo) estão disponíveis:
- `true`: Resposta inclui até 16 dias de previsão
- `false`: Apenas dados do OpenWeather (5 dias) disponíveis

### Índice UV - Níveis de Risco

| UV Index | Nível | Cor | Recomendação |
|----------|-------|-----|--------------|
| 0-2 | Baixo | `#00E400` (Verde) | Seguro permanecer ao ar livre |
| 3-5 | Moderado | `#FFFF00` (Amarelo) | Use protetor solar |
| 6-7 | Alto | `#FF6B00` (Laranja) | Proteção extra necessária |
| 8-10 | Muito Alto | `#FF0000` (Vermelho) | Evite exposição ao sol |
| 11+ | Extremo | `#B000B0` (Roxo) | Evite sair ao ar livre |

### Fases da Lua

Calculadas com base no ciclo lunar de 29.53 dias a partir de uma referência conhecida:

| Fase | Descrição | Ícone sugerido |
|------|-----------|----------------|
| Lua Nova | 0-1 dias após lua nova | 🌑 |
| Lua Crescente | 1-7 dias (crescente) | 🌒 |
| Quarto Crescente | 7-8 dias | 🌓 |
| Lua Crescente | 8-14 dias (ainda crescendo) | 🌔 |
| Lua Cheia | 14-15 dias | 🌕 |
| Lua Minguante | 15-21 dias (minguando) | 🌖 |
| Quarto Minguante | 21-22 dias | 🌗 |
| Lua Minguante | 22-29 dias (ainda minguando) | 🌘 |

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

**Error (500 Internal Server Error):**

```json
{
  "type": "WeatherAPIException",
  "error": "Failed to fetch weather data",
  "message": "Both OpenWeather and Open-Meteo APIs failed",
  "details": {
    "city_id": "3543204"
  }
}
```

### Exemplos

```bash
# Previsão detalhada atual
curl "https://api.example.com/api/weather/city/3543204/detailed"

# Previsão detalhada para data específica
curl "https://api.example.com/api/weather/city/3543204/detailed?date=2025-12-01"

# Previsão detalhada para data/hora específica
curl "https://api.example.com/api/weather/city/3543204/detailed?date=2025-12-01&time=15:00"
```

### Implementação

```python
@app.get("/api/weather/city/<city_id>/detailed")
def get_city_detailed_forecast_route(city_id: str):
    """
    GET /api/weather/city/{cityId}/detailed?date=2025-11-30&time=15:00
    Returns detailed forecast with 16-day extended data
    """
    import asyncio
    
    logger.info("Get city detailed forecast", city_id=city_id)
    
    # Extract date and time from query string
    date_str = app.current_event.get_query_string_value(name="date", default_value=None)
    time_str = app.current_event.get_query_string_value(name="time", default_value=None)
    
    # Parse datetime
    target_datetime = DateTimeParser.from_query_params(date_str, time_str)
    
    # Get repositories (singletons)
    city_repository = get_repository()
    weather_repository = get_async_weather_repository()
    openmeteo_repository = get_async_openmeteo_repository()
    
    # Execute use case (async)
    async def execute_async():
        use_case = AsyncGetCityDetailedForecastUseCase(
            city_repository,
            weather_repository,
            openmeteo_repository
        )
        forecast = await use_case.execute(city_id, target_datetime)
        return forecast
    
    # Run async code
    forecast = asyncio.run(execute_async())
    
    # Log success
    logger.info(
        "Detailed forecast fetched",
        city_id=city_id,
        city_name=forecast['cityInfo']['cityName'],
        forecast_days=len(forecast['dailyForecasts']),
        extended_available=forecast['extendedAvailable']
    )
    
    return forecast
```

### Fluxo de Execução

```
1. Request → lambda_handler
2. Parse datetime (date/time query params)
3. Validate city_id (CityIdValidator)
4. Fetch city from repository (CityNotFoundException se não encontrar)
5. Execute asyncio.gather() paralelo:
   ├─ OpenWeather API (current + 5 days forecast)
   └─ Open-Meteo API (16 days extended forecast)
6. Se Open-Meteo falhar:
   ├─ Log warning
   └─ Continue com dados OpenWeather apenas (extendedAvailable: false)
7. Combinar dados:
   ├─ cityInfo (do repositório de cidades)
   ├─ currentWeather (do OpenWeather)
   └─ dailyForecasts (do Open-Meteo ou OpenWeather)
8. Calcular dados derivados:
   ├─ uvRiskLevel e uvRiskColor (baseado em uvIndexMax)
   ├─ daylightHours (sunset - sunrise)
   └─ moonPhase (algoritmo simplificado)
9. Cache DynamoDB (TTL: 6 horas)
10. Return ExtendedForecast
```

### Cache Strategy

```python
# Cache key format
cache_key = f"openmeteo_{city_id}_{forecast_days}"

# TTL: 6 horas (mais longo que weather normal)
ttl = datetime.now() + timedelta(hours=6)

# DynamoDB structure
{
  "pk": cache_key,
  "data": {...},
  "ttl": 1732998000
}
```

**Cache separado:**
- Endpoint `/detailed`: Cache de 6h (dados mudam menos)
- Endpoint `/city/{id}`: Cache de 3h (dados mudam mais)

### Performance

**Benchmarks:**

| Métrica | Valor |
|---------|-------|
| Cold start | ~800-1000ms |
| Warm cache hit | ~50-80ms |
| Warm cache miss (parallel APIs) | ~250-350ms |
| Open-Meteo API latency | ~150-200ms |
| OpenWeather API latency | ~200-300ms |

**Otimizações:**
- ✅ APIs chamadas em paralelo com `asyncio.gather()`
- ✅ Cache DynamoDB com TTL de 6h
- ✅ Singleton factories (reutilização de sessions)
- ✅ Graceful degradation (se Open-Meteo falhar, continua com OpenWeather)

### Fontes de Dados

#### OpenWeather Forecast API
- **URL:** `https://api.openweathermap.org/data/2.5/forecast`
- **Cobertura:** 5 dias, intervalos de 3h (40 pontos)
- **Uso:** `currentWeather` (primeira previsão)
- **Rate limit:** 1000 calls/day (free tier)

#### Open-Meteo API
- **URL:** `https://api.open-meteo.com/v1/forecast`
- **Cobertura:** 16 dias, dados diários
- **Parâmetros:** `temperature_2m_max`, `temperature_2m_min`, `precipitation_sum`, `precipitation_probability_max`, `precipitation_hours`, `windspeed_10m_max`, `uv_index_max`, `sunrise`, `sunset`
- **Uso:** `dailyForecasts` (até 16 dias)
- **Rate limit:** Ilimitado (free tier)

**Por que usar duas APIs?**
- OpenWeather: Dados horários precisos, atual + curto prazo
- Open-Meteo: Dados diários estendidos, free tier generoso, dados astronômicos

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
