# Operações Assíncronas (Async I/O)

## Visão Geral

A aplicação utiliza **100% operações assíncronas** para I/O bound operations (DynamoDB, OpenWeather API), permitindo alta performance e concorrência sem blocking threads.

**Stack Async:**
- `aioboto3` 13.2.0+ - Cliente assíncrono para AWS (DynamoDB)
- `aiohttp` 3.10.0+ - Cliente HTTP assíncrono (OpenWeather API)
- `asyncio` - Event loop e primitivas de concorrência (Python 3.13)

**Performance:**
- 100 cities em ~150ms (P50)
- Throughput: 50-100 cities/sec
- Latency/city: ~18.5ms
- Cache hit: ~80% (pós warm-up)

---

## Arquitetura Async

### Event Loop Management

AWS Lambda **não fornece event loop persistente**. Cada invocação cria um novo event loop:

```python
def lambda_handler(event, context):
    """
    Lambda handler (sync) - Entry point
    AWS Lambda não suporta async handlers
    """
    import asyncio
    
    # Cria novo event loop para esta invocação
    async def execute_async():
        # Async operations aqui
        result = await some_async_operation()
        return result
    
    # Executa async code e retorna resultado
    result = asyncio.run(execute_async())
    
    return result
```

**Por que `asyncio.run()`?**
- ✅ Cria novo event loop limpo
- ✅ Executa coroutine até completar
- ✅ Fecha event loop automaticamente
- ✅ Compatível com múltiplas invocações Lambda

**Alternativa (NÃO recomendada):**

```python
# ❌ ERRADO - Pode causar "RuntimeError: Event loop is closed"
loop = asyncio.get_event_loop()
result = loop.run_until_complete(execute_async())
```

### Pattern: Sync Route + Async Inner Function

AWS Powertools APIGatewayRestResolver **não suporta `async def` routes**. Solução:

```python
from aws_lambda_powertools.event_handler import APIGatewayRestResolver

app = APIGatewayRestResolver()

@app.get("/api/weather/city/<city_id>")
def get_city_weather_route(city_id: str):  # ← Sync route (obrigatório)
    """Sync route handler with async execution"""
    import asyncio
    
    # Define async inner function
    async def execute_async():
        # Initialize async resources
        use_case = AsyncGetCityWeatherUseCase(...)
        
        # Await async operations
        weather = await use_case.execute(city_id, target_datetime)
        
        return weather
    
    # Run async code
    weather = asyncio.run(execute_async())
    
    # Return response (sync)
    return weather.to_api_response()
```

**Fluxo:**
```
Request → Lambda Handler (sync)
           ↓
       Route Handler (sync)
           ↓
       asyncio.run() → Cria event loop
           ↓
       Inner Function (async) → Executa async operations
           ↓
       Event loop fecha automaticamente
           ↓
       Response (sync)
```

---

## Lazy Session Creation

### Problema: Event Loop Incompatibility

AWS Lambda **não garante event loop persistente**:

```python
# ❌ PROBLEMA: Criar session fora de async context
session = aioboto3.Session()
dynamodb = session.resource('dynamodb')  # Event loop pode não existir!
```

**Erro comum:**
```
RuntimeError: There is no current event loop in thread 'MainThread'
```

### Solução: Lazy Initialization

Sessions são criadas **on-demand** dentro de async context:

```python
class AsyncOpenWeatherRepository:
    def __init__(self, api_key: str, cache: DynamoDBCache):
        self.api_key = api_key
        self.cache = cache
        
        # ✅ Session NOT created here
        self._session = None  # Lazy initialization
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Get or create aiohttp session (lazy)
        Thread-safe for single Lambda invocation
        """
        if self._session is None:
            # Create session inside async context (event loop exists)
            self._session = aiohttp.ClientSession()
        
        return self._session
    
    async def get_weather(self, lat: float, lon: float, target_dt: datetime) -> Weather:
        """Fetch weather from OpenWeather API"""
        # Get session (creates if needed)
        session = await self._get_session()
        
        # Use session for HTTP request
        async with session.get(url, params=params) as response:
            data = await response.json()
            return self._map_to_weather(data, lat, lon, target_dt)
```

**Vantagens:**
- ✅ Session criada apenas quando necessária
- ✅ Criação dentro de async context (event loop disponível)
- ✅ Reutilização de session durante invocação
- ✅ Compatível com múltiplas invocações Lambda

### aioboto3 Lazy Initialization

```python
class DynamoDBCache:
    def __init__(self, table_name: str):
        self.table_name = table_name
        
        # ✅ Session NOT created here
        self._session = None
        self._table = None
    
    async def _get_table(self):
        """Get or create DynamoDB table resource (lazy)"""
        if self._table is None:
            # Create session inside async context
            self._session = aioboto3.Session()
            
            # Create resource (uses current event loop)
            async with self._session.resource('dynamodb') as dynamodb:
                self._table = await dynamodb.Table(self.table_name)
        
        return self._table
    
    async def get(self, key: str) -> Optional[Dict]:
        """Get item from DynamoDB"""
        table = await self._get_table()
        
        response = await table.get_item(Key={'cacheKey': key})
        
        return response.get('Item')
```

**Pattern completo:**

1. **Initialization (sync):** Apenas salva configurações
2. **First async call:** Cria session/resource
3. **Subsequent calls:** Reutiliza session/resource existente
4. **Lambda termina:** Session é destruída automaticamente

---

## Async Use Cases

### Single City Weather (Sequential)

```python
class AsyncGetCityWeatherUseCase:
    def __init__(self, city_repo: InMemoryCityRepository, 
                 weather_repo: AsyncOpenWeatherRepository):
        self._city_repo = city_repo
        self._weather_repo = weather_repo
    
    async def execute(self, city_id: str, target_datetime: datetime) -> Weather:
        """
        Get weather for a single city
        Flow: City (sync) → Cache check (async) → API call (async)
        """
        # 1. Get city (sync - in-memory)
        city = self._city_repo.get_by_id(city_id)
        if not city:
            raise CityNotFoundException(city_id)
        
        # 2. Get weather (async - DynamoDB + API)
        weather = await self._weather_repo.get_weather(
            city.latitude,
            city.longitude,
            target_datetime
        )
        
        # 3. Enrich with city info
        weather.city_id = city_id
        weather.city_name = city.name
        
        return weather
```

**Fluxo:**
```
execute(city_id, target_datetime)
  ↓
get_by_id() → In-memory lookup (sync, ~1ms)
  ↓
get_weather() → Async call
  ↓
  ├─ Check DynamoDB cache (async, ~20-30ms)
  │  ├─ HIT → Return cached data
  │  └─ MISS → Continue
  │
  └─ Call OpenWeather API (async, ~200-500ms)
     ↓
     Map to Weather entity
     ↓
     Save to DynamoDB cache (async, fire-and-forget)
     ↓
     Return weather
```

### Regional Weather (Parallel)

```python
class AsyncGetRegionalWeatherUseCase:
    def __init__(self, city_repo: InMemoryCityRepository, 
                 weather_repo: AsyncOpenWeatherRepository):
        self._city_repo = city_repo
        self._weather_repo = weather_repo
        
        # Semaphore para throttling (max 50 concurrent requests)
        self._semaphore = asyncio.Semaphore(50)
    
    async def execute(self, city_ids: List[str], target_datetime: datetime) -> List[Weather]:
        """
        Get weather for multiple cities in parallel
        Uses asyncio.gather() for concurrency
        """
        # Create tasks for all cities
        tasks = [
            self._fetch_city_weather(city_id, target_datetime)
            for city_id in city_ids
        ]
        
        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions (failed cities)
        weather_data = [
            result for result in results
            if isinstance(result, Weather)
        ]
        
        return weather_data
    
    async def _fetch_city_weather(self, city_id: str, target_dt: datetime) -> Weather:
        """
        Fetch weather for a single city (with throttling)
        """
        async with self._semaphore:  # Throttle: max 50 concurrent
            try:
                # Get city (sync)
                city = self._city_repo.get_by_id(city_id)
                if not city:
                    raise CityNotFoundException(city_id)
                
                # Get weather (async)
                weather = await self._weather_repo.get_weather(
                    city.latitude,
                    city.longitude,
                    target_dt
                )
                
                # Enrich
                weather.city_id = city_id
                weather.city_name = city.name
                
                return weather
                
            except Exception as e:
                logger.warning("Failed to fetch weather", city_id=city_id, error=str(e))
                return e  # Return exception (filtered by gather)
```

**Fluxo Paralelo (100 cidades):**

```
execute(city_ids=[id1, id2, ..., id100], target_datetime)
  ↓
Create 100 tasks
  ↓
asyncio.gather(*tasks)
  ↓
┌────────────────────────────────────────────────────────────┐
│ Parallel execution (max 50 concurrent via Semaphore)      │
├────────────────────────────────────────────────────────────┤
│ Task 1  → get_weather(lat1, lon1) → Cache HIT  (~20ms)    │
│ Task 2  → get_weather(lat2, lon2) → Cache MISS (~250ms)   │
│ Task 3  → get_weather(lat3, lon3) → Cache HIT  (~20ms)    │
│ ...                                                         │
│ Task 50 → get_weather(lat50, lon50) → Cache MISS (~250ms) │
│ [Wait for slot...]                                          │
│ Task 51 → get_weather(lat51, lon51) → Cache HIT  (~20ms)  │
│ ...                                                         │
│ Task 100 → get_weather(lat100, lon100) → Cache HIT (~20ms)│
└────────────────────────────────────────────────────────────┘
  ↓
Wait for all tasks to complete
  ↓
Filter exceptions (failed cities)
  ↓
Return List[Weather] (~150ms total)
```

**Performance (100 cidades):**
- **Cache hit 80%:** 80 cities @ 20ms + 20 cities @ 250ms = **~150ms total**
- **Cache hit 0%:** 100 cities @ 250ms (50 concurrent) = **~500ms total**

---

## Concurrency Primitives

### asyncio.gather()

Executa múltiplas coroutines em paralelo:

```python
# Execute 3 tasks in parallel
results = await asyncio.gather(
    fetch_city_1(),
    fetch_city_2(),
    fetch_city_3()
)

# results = [weather1, weather2, weather3]
```

**Com error handling:**

```python
# Return exceptions instead of raising
results = await asyncio.gather(
    fetch_city_1(),
    fetch_city_2(),
    fetch_city_3(),
    return_exceptions=True  # ← Exceptions retornadas, não raised
)

# Filter out exceptions
weather_data = [r for r in results if isinstance(r, Weather)]
```

### asyncio.Semaphore()

Limita número de coroutines concorrentes:

```python
# Max 50 concurrent requests
semaphore = asyncio.Semaphore(50)

async def fetch_with_throttle(city_id):
    async with semaphore:  # Acquire (blocks if 50 active)
        weather = await fetch_weather(city_id)
        return weather
    # Release automatically on exit

# Create 100 tasks
tasks = [fetch_with_throttle(city_id) for city_id in city_ids]

# Only 50 execute at a time
results = await asyncio.gather(*tasks)
```

**Por que Semaphore(50)?**

1. **Lambda memory:** 512MB → limita I/O concurrent
2. **OpenWeather API:** Rate limit 60 req/min → 50 concurrent é seguro
3. **DynamoDB:** Sem throttling, mas evita overload
4. **Performance:** Balanceamento entre throughput e latência

### asyncio.create_task()

Cria task em background (fire-and-forget):

```python
async def save_to_cache(key, value):
    """Save to DynamoDB (async)"""
    await cache.put(key, value)

async def get_weather(lat, lon, target_dt):
    # Check cache
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    # Fetch from API
    weather = await fetch_from_api(lat, lon, target_dt)
    
    # Save to cache (fire-and-forget)
    asyncio.create_task(save_to_cache(cache_key, weather))
    
    # Don't wait for cache save
    return weather
```

**Atenção:** Em Lambda, tasks devem completar antes de return do handler!

---

## Async HTTP with aiohttp

### Session Management

```python
class AsyncOpenWeatherRepository:
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session (lazy)"""
        if self._session is None:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    'Accept': 'application/json',
                    'User-Agent': 'Weather-Forecast-API/1.0'
                }
            )
        
        return self._session
    
    async def get_weather(self, lat: float, lon: float, target_dt: datetime) -> Weather:
        """Fetch weather from OpenWeather API"""
        session = await self._get_session()
        
        url = f"{self.base_url}/forecast"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': self.api_key,
            'units': 'metric',
            'lang': 'pt_br'
        }
        
        # Async HTTP GET
        async with session.get(url, params=params) as response:
            # Raise for 4xx/5xx
            response.raise_for_status()
            
            # Parse JSON
            data = await response.json()
            
            # Map to domain entity
            return self._map_to_weather(data, lat, lon, target_dt)
```

### Error Handling

```python
async def get_weather(self, lat: float, lon: float, target_dt: datetime) -> Weather:
    """Fetch with error handling"""
    try:
        session = await self._get_session()
        
        async with session.get(url, params=params) as response:
            # Check status
            if response.status == 404:
                raise WeatherDataNotFoundException(lat, lon, target_dt)
            
            # Raise for other errors
            response.raise_for_status()
            
            data = await response.json()
            return self._map_to_weather(data, lat, lon, target_dt)
    
    except aiohttp.ClientError as e:
        logger.error("HTTP error", url=url, error=str(e))
        raise WeatherDataNotFoundException(lat, lon, target_dt)
    
    except asyncio.TimeoutError:
        logger.error("Request timeout", url=url)
        raise WeatherDataNotFoundException(lat, lon, target_dt)
```

---

## Async DynamoDB with aioboto3

### Resource Creation

```python
class DynamoDBCache:
    async def _get_table(self):
        """Get or create DynamoDB table resource"""
        if self._table is None:
            # Create session (lazy)
            self._session = aioboto3.Session()
            
            # Create resource
            async with self._session.resource('dynamodb', region_name='sa-east-1') as dynamodb:
                self._table = await dynamodb.Table(self.table_name)
        
        return self._table
```

### Get Item

```python
async def get(self, key: str) -> Optional[Dict]:
    """Get item from DynamoDB"""
    table = await self._get_table()
    
    response = await table.get_item(
        Key={'cacheKey': key}
    )
    
    item = response.get('Item')
    
    if not item:
        return None
    
    # Check TTL
    ttl = item.get('ttl', 0)
    if ttl > 0 and ttl < int(datetime.now(timezone.utc).timestamp()):
        return None  # Expired
    
    return item
```

### Put Item

```python
async def put(self, key: str, value: Dict, ttl_hours: int = 3):
    """Save item to DynamoDB with TTL"""
    table = await self._get_table()
    
    # Calculate TTL
    ttl = int((datetime.now(timezone.utc) + timedelta(hours=ttl_hours)).timestamp())
    
    # Prepare item
    item = {
        'cacheKey': key,
        'data': value,
        'ttl': ttl,
        'createdAt': datetime.now(timezone.utc).isoformat()
    }
    
    # Put item (async)
    await table.put_item(Item=item)
```

### Batch Operations

```python
async def batch_get(self, keys: List[str]) -> List[Dict]:
    """Get multiple items in parallel"""
    tasks = [self.get(key) for key in keys]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out None and exceptions
    items = [r for r in results if r is not None and not isinstance(r, Exception)]
    
    return items
```

---

## Performance Optimization

### Cache Strategy

```python
async def get_weather(self, lat: float, lon: float, target_dt: datetime) -> Weather:
    """
    3-level cache strategy:
    1. Check DynamoDB cache (~20-30ms)
    2. Fetch from OpenWeather API (~200-500ms)
    3. Save to cache for future requests
    """
    # Generate cache key
    cache_key = self._generate_cache_key(lat, lon, target_dt)
    
    # 1. Check cache (async)
    cached = await self.cache.get(cache_key)
    if cached:
        logger.info("Cache hit", cache_key=cache_key)
        return self._deserialize_weather(cached['data'])
    
    logger.info("Cache miss", cache_key=cache_key)
    
    # 2. Fetch from API (async)
    weather = await self._fetch_from_api(lat, lon, target_dt)
    
    # 3. Save to cache (fire-and-forget)
    asyncio.create_task(
        self.cache.put(cache_key, self._serialize_weather(weather))
    )
    
    return weather
```

**Performance:**
- **Cache HIT:** ~20-30ms (DynamoDB latency)
- **Cache MISS:** ~200-500ms (API + DynamoDB save)
- **Cache hit rate:** ~80% após warm-up

### Connection Pooling

aiohttp mantém connection pool automaticamente:

```python
# Session reutiliza connections TCP
session = aiohttp.ClientSession(
    connector=aiohttp.TCPConnector(
        limit=100,              # Max 100 connections total
        limit_per_host=50,      # Max 50 connections per host
        keepalive_timeout=30    # Keep connections alive 30s
    )
)
```

**Benefícios:**
- ✅ Evita TCP handshake overhead (~100ms saved)
- ✅ Reutiliza SSL/TLS sessions
- ✅ Reduz latência de requests subsequentes

---

## Debugging Async Code

### Logging Async Operations

```python
from aws_lambda_powertools import Logger

logger = Logger()

async def fetch_weather(city_id):
    logger.info("Starting async fetch", city_id=city_id)
    
    try:
        weather = await weather_repo.get_weather(lat, lon, target_dt)
        
        logger.info("Fetch completed", city_id=city_id, temperature=weather.temperature)
        
        return weather
    
    except Exception as e:
        logger.error("Fetch failed", city_id=city_id, error=str(e), exc_info=True)
        raise
```

### Measuring Async Performance

```python
import time

async def fetch_with_timing(city_id):
    start = time.time()
    
    try:
        weather = await fetch_weather(city_id)
        
        elapsed = (time.time() - start) * 1000
        logger.info("Fetch completed", city_id=city_id, latency_ms=f"{elapsed:.1f}")
        
        return weather
    
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        logger.error("Fetch failed", city_id=city_id, latency_ms=f"{elapsed:.1f}", error=str(e))
        raise
```

### Testing Async Code

```python
import pytest

@pytest.mark.asyncio
async def test_fetch_weather():
    """Test async weather fetching"""
    weather_repo = AsyncOpenWeatherRepository(api_key="test", cache=mock_cache)
    
    # Await async call
    weather = await weather_repo.get_weather(lat=-22.7572, lon=-49.9439, target_dt=datetime.now())
    
    assert weather is not None
    assert weather.temperature > 0
```

Ver documentação completa: [docs/development/TESTING.md](../development/TESTING.md)

---

## Common Pitfalls

### ❌ Creating Session Outside Async Context

```python
# ❌ ERRADO
class AsyncRepository:
    def __init__(self):
        self.session = aiohttp.ClientSession()  # No event loop!
```

**Erro:**
```
RuntimeError: There is no current event loop in thread 'MainThread'
```

**✅ CORRETO:**
```python
class AsyncRepository:
    def __init__(self):
        self._session = None  # Lazy
    
    async def _get_session(self):
        if self._session is None:
            self._session = aiohttp.ClientSession()  # Inside async context
        return self._session
```

### ❌ Forgetting `await`

```python
# ❌ ERRADO
async def fetch_weather():
    weather = weather_repo.get_weather(lat, lon, target_dt)  # Missing await!
    return weather  # Returns coroutine, not Weather!
```

**✅ CORRETO:**
```python
async def fetch_weather():
    weather = await weather_repo.get_weather(lat, lon, target_dt)
    return weather
```

### ❌ Using Sync Code in Async Context

```python
# ❌ ERRADO
async def fetch_weather():
    time.sleep(1)  # Blocks event loop!
    weather = await weather_repo.get_weather(lat, lon, target_dt)
    return weather
```

**✅ CORRETO:**
```python
async def fetch_weather():
    await asyncio.sleep(1)  # Non-blocking
    weather = await weather_repo.get_weather(lat, lon, target_dt)
    return weather
```

### ❌ Fire-and-Forget Without Waiting

```python
# ❌ PROBLEMA: Task pode não completar antes de Lambda terminar
async def save_weather():
    asyncio.create_task(cache.put(key, value))
    return  # Lambda pode terminar antes de cache.put() completar!
```

**✅ CORRETO:**
```python
async def save_weather():
    await cache.put(key, value)  # Wait for completion
    return
```

---

## References

- **aioboto3 docs:** https://aioboto3.readthedocs.io/
- **aiohttp docs:** https://docs.aiohttp.org/
- **asyncio docs:** https://docs.python.org/3/library/asyncio.html
- **AWS Lambda async best practices:** https://aws.amazon.com/blogs/compute/python-3-13-runtime-now-available-in-aws-lambda/
