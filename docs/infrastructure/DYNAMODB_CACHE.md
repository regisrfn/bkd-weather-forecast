# DynamoDB Cache Strategy

## Visão Geral

A aplicação utiliza **DynamoDB como cache de previsões meteorológicas** da API OpenWeather, reduzindo latência e custos de chamadas à API externa.

**Características:**
- ✅ Cache TTL de 3 horas (configurável)
- ✅ Cache key baseado em lat/lon/datetime
- ✅ Async I/O com aioboto3
- ✅ Lazy resource creation
- ✅ Cache hit rate ~80% (pós warm-up)
- ✅ Latency: ~20-30ms (vs ~200-500ms API)

**Tabela DynamoDB:**
```
Table name: weather-forecast-cache-prod
Partition key: cacheKey (String)
TTL attribute: ttl (Number)
Billing mode: PAY_PER_REQUEST
Region: sa-east-1
```

---

## Arquitetura do Cache

### Cache Key Strategy

```python
def _generate_cache_key(self, lat: float, lon: float, target_dt: datetime) -> str:
    """
    Generate cache key for weather data
    
    Format: weather_{lat}_{lon}_{timestamp}
    Example: weather_-22.7572_-49.9439_1732647600
    
    Rationale:
    - lat/lon: Unique location identifier
    - timestamp: Rounded to hour (previsões de 3 em 3 horas)
    
    Collision: Baixa (lat/lon com 4 casas + timestamp único)
    """
    # Round target datetime to nearest hour
    rounded_dt = target_dt.replace(minute=0, second=0, microsecond=0)
    
    # Convert to Unix timestamp
    timestamp = int(rounded_dt.timestamp())
    
    # Format cache key
    return f"weather_{lat:.4f}_{lon:.4f}_{timestamp}"
```

**Exemplos:**

| Lat | Lon | DateTime | Cache Key |
|-----|-----|----------|-----------|
| -22.7572 | -49.9439 | 2025-11-26 15:23:45 | `weather_-22.7572_-49.9439_1732647600` |
| -22.7572 | -49.9439 | 2025-11-26 15:47:12 | `weather_-22.7572_-49.9439_1732647600` |
| -23.5505 | -46.6333 | 2025-11-26 18:00:00 | `weather_-23.5505_-46.6333_1732658400` |

**Por que arredondar para hora:**
- OpenWeather retorna previsões de 3 em 3 horas (00:00, 03:00, 06:00, ...)
- Requests para 15:23 e 15:47 buscam mesma previsão (15:00)
- Aumenta cache hit rate

### Item Structure

```python
{
    'cacheKey': 'weather_-22.7572_-49.9439_1732647600',  # Partition key
    'data': {
        'temperature': 28.3,
        'humidity': 65.0,
        'windSpeed': 12.5,
        'rainfallIntensity': 35.5,
        'weatherDescription': 'Parcialmente nublado',
        'timestamp': '2025-11-26T15:00:00'
    },
    'ttl': 1732658400,  # Unix timestamp (expires in 3 hours)
    'createdAt': '2025-11-26T15:12:34.567890+00:00'
}
```

**Campos:**

| Campo | Tipo | Descrição | Tamanho |
|-------|------|-----------|---------|
| `cacheKey` | String | Partition key (lat_lon_timestamp) | ~50 bytes |
| `data` | Map | Weather data (JSON) | ~200 bytes |
| `ttl` | Number | TTL attribute (Unix timestamp) | 8 bytes |
| `createdAt` | String | ISO 8601 creation timestamp | ~30 bytes |

**Tamanho total:** ~300 bytes/item

---

## DynamoDB Cache Implementation

### Class Structure

```python
class DynamoDBCache:
    """
    DynamoDB cache for weather data with TTL support
    Uses aioboto3 for async operations
    """
    
    def __init__(self, table_name: str):
        """
        Initialize cache (lazy resource creation)
        
        Args:
            table_name: DynamoDB table name
        """
        self.table_name = table_name
        
        # Lazy initialization (created on first async call)
        self._session = None
        self._table = None
    
    async def _get_table(self):
        """
        Get or create DynamoDB table resource (lazy)
        Thread-safe for single Lambda invocation
        """
        if self._table is None:
            # Create session inside async context
            self._session = aioboto3.Session()
            
            # Create resource
            async with self._session.resource('dynamodb', region_name='sa-east-1') as dynamodb:
                self._table = await dynamodb.Table(self.table_name)
        
        return self._table
    
    async def get(self, key: str) -> Optional[Dict]:
        """Get item from cache (with TTL check)"""
        ...
    
    async def put(self, key: str, value: Dict, ttl_hours: int = 3):
        """Save item to cache with TTL"""
        ...
```

### Get Operation

```python
async def get(self, key: str) -> Optional[Dict]:
    """
    Get item from DynamoDB cache
    
    Args:
        key: Cache key (format: weather_{lat}_{lon}_{timestamp})
    
    Returns:
        Dict with cached data or None if not found/expired
    
    Performance: ~20-30ms
    """
    table = await self._get_table()
    
    try:
        # Async get_item
        response = await table.get_item(
            Key={'cacheKey': key}
        )
        
        # Check if item exists
        item = response.get('Item')
        if not item:
            return None
        
        # Check TTL (double-check, DynamoDB TTL has delay)
        ttl = item.get('ttl', 0)
        current_timestamp = int(datetime.now(timezone.utc).timestamp())
        
        if ttl > 0 and ttl < current_timestamp:
            logger.info("Cache item expired", cache_key=key, ttl=ttl)
            return None
        
        # Return data
        return item
    
    except ClientError as e:
        logger.error("DynamoDB get error", cache_key=key, error=str(e))
        return None  # Fail open (return None, fetch from API)
```

**Fluxo:**
```
get(key)
  ↓
Get DynamoDB table resource
  ↓
table.get_item(Key={'cacheKey': key})
  ↓
  ├─ Item not found → Return None
  │
  ├─ Item found + TTL expired → Return None
  │
  └─ Item found + TTL valid → Return item
```

### Put Operation

```python
async def put(self, key: str, value: Dict, ttl_hours: int = 3):
    """
    Save item to DynamoDB cache with TTL
    
    Args:
        key: Cache key
        value: Data to cache (JSON serializable)
        ttl_hours: Time to live in hours (default: 3)
    
    Performance: ~15-25ms (fire-and-forget)
    """
    table = await self._get_table()
    
    try:
        # Calculate TTL (Unix timestamp)
        ttl_timestamp = int(
            (datetime.now(timezone.utc) + timedelta(hours=ttl_hours)).timestamp()
        )
        
        # Prepare item
        item = {
            'cacheKey': key,
            'data': value,
            'ttl': ttl_timestamp,
            'createdAt': datetime.now(timezone.utc).isoformat()
        }
        
        # Async put_item
        await table.put_item(Item=item)
        
        logger.info("Cache saved", cache_key=key, ttl_hours=ttl_hours)
    
    except ClientError as e:
        logger.error("DynamoDB put error", cache_key=key, error=str(e))
        # Fail open (don't raise, just log)
```

**Fluxo:**
```
put(key, value, ttl_hours=3)
  ↓
Calculate TTL timestamp (now + 3 hours)
  ↓
Prepare item (cacheKey, data, ttl, createdAt)
  ↓
table.put_item(Item=item)
  ↓
Log success (or error)
```

---

## Cache Integration

### AsyncOpenWeatherRepository

```python
class AsyncOpenWeatherRepository:
    def __init__(self, api_key: str, cache: DynamoDBCache):
        self.api_key = api_key
        self.cache = cache
        self._session = None
    
    async def get_weather(self, lat: float, lon: float, target_dt: datetime) -> Weather:
        """
        Get weather forecast with cache
        
        Flow:
        1. Generate cache key
        2. Check DynamoDB cache (async)
        3. If HIT: Deserialize and return (~20-30ms)
        4. If MISS: Fetch from API (~200-500ms)
        5. Save to cache (fire-and-forget)
        6. Return weather
        """
        # 1. Generate cache key
        cache_key = self._generate_cache_key(lat, lon, target_dt)
        
        # 2. Check cache
        cached = await self.cache.get(cache_key)
        if cached:
            logger.info("Cache hit", cache_key=cache_key)
            return self._deserialize_weather(cached['data'])
        
        logger.info("Cache miss", cache_key=cache_key)
        
        # 3. Fetch from API
        weather = await self._fetch_from_api(lat, lon, target_dt)
        
        # 4. Save to cache (fire-and-forget)
        asyncio.create_task(
            self.cache.put(cache_key, self._serialize_weather(weather))
        )
        
        return weather
    
    def _serialize_weather(self, weather: Weather) -> Dict:
        """Convert Weather entity to cacheable dict"""
        return {
            'temperature': weather.temperature,
            'humidity': weather.humidity,
            'windSpeed': weather.wind_speed,
            'rainfallIntensity': weather.rainfall_intensity,
            'weatherDescription': weather.weather_description,
            'timestamp': weather.timestamp.isoformat()
        }
    
    def _deserialize_weather(self, data: Dict) -> Weather:
        """Convert cached dict to Weather entity"""
        return Weather(
            temperature=data['temperature'],
            humidity=data['humidity'],
            wind_speed=data['windSpeed'],
            rainfall_intensity=data['rainfallIntensity'],
            weather_description=data['weatherDescription'],
            timestamp=datetime.fromisoformat(data['timestamp'])
        )
```

**Performance:**

| Scenario | Latency | Operations |
|----------|---------|------------|
| Cache HIT | ~20-30ms | 1x DynamoDB get_item |
| Cache MISS | ~200-500ms | 1x DynamoDB get_item + 1x OpenWeather API + 1x DynamoDB put_item (async) |

---

## TTL Configuration

### DynamoDB TTL

**Configuração:**
```hcl
# terraform/modules/dynamodb/main.tf

resource "aws_dynamodb_table" "weather_cache" {
  name           = "weather-forecast-cache-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "cacheKey"
  
  attribute {
    name = "cacheKey"
    type = "S"
  }
  
  # TTL configuration
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
  
  tags = {
    Name        = "Weather Forecast Cache"
    Environment = var.environment
  }
}
```

**Como TTL funciona:**

1. **Item criado:** `ttl = 1732658400` (3 horas no futuro)
2. **DynamoDB verifica TTL:** Background process (delay ~48 horas)
3. **Item expirado:** DynamoDB marca para deletion
4. **Item deletado:** Automaticamente (sem custo)

**Importante:**
- ⚠️ TTL deletion tem delay (~48 horas)
- ✅ Implementamos check manual no `get()` (double-check)
- ✅ Items expirados retornam `None` mesmo antes de deletion

### TTL Calculation

```python
def _calculate_ttl(hours: int = 3) -> int:
    """
    Calculate TTL timestamp (Unix epoch)
    
    Args:
        hours: Hours from now (default: 3)
    
    Returns:
        Unix timestamp (seconds since epoch)
    
    Example:
        now = 2025-11-26 15:00:00 UTC
        ttl = _calculate_ttl(3)
        ttl = 2025-11-26 18:00:00 UTC = 1732647600
    """
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(hours=hours)
    return int(expiry.timestamp())
```

**Por que 3 horas?**

- OpenWeather previsões atualizam a cada 3 horas
- Balance entre cache hit rate e data freshness
- Reduz custos de API calls (~80% reduction)

**Configurável via variável de ambiente:**

```python
# lambda/config.py
CACHE_TTL_HOURS = int(os.getenv('CACHE_TTL_HOURS', '3'))

# Usage
await cache.put(key, value, ttl_hours=CACHE_TTL_HOURS)
```

---

## Cache Patterns

### Read-Through Cache

```python
async def get_weather(self, lat: float, lon: float, target_dt: datetime) -> Weather:
    """
    Read-through cache pattern
    
    Flow:
    1. Try to read from cache
    2. If miss, fetch from source (API)
    3. Write to cache
    4. Return data
    """
    cache_key = self._generate_cache_key(lat, lon, target_dt)
    
    # Read from cache
    cached = await self.cache.get(cache_key)
    if cached:
        return self._deserialize_weather(cached['data'])
    
    # Fetch from source
    weather = await self._fetch_from_api(lat, lon, target_dt)
    
    # Write to cache (async)
    asyncio.create_task(
        self.cache.put(cache_key, self._serialize_weather(weather))
    )
    
    return weather
```

### Cache-Aside Pattern

```python
async def get_weather_with_explicit_cache(self, lat: float, lon: float, target_dt: datetime) -> Weather:
    """
    Cache-aside pattern (explicit cache management)
    
    Application explicitly manages cache read/write
    """
    cache_key = self._generate_cache_key(lat, lon, target_dt)
    
    # 1. Application checks cache
    cached = await self.cache.get(cache_key)
    if cached:
        logger.info("Cache hit")
        return self._deserialize_weather(cached['data'])
    
    logger.info("Cache miss")
    
    # 2. Application fetches from source
    weather = await self._fetch_from_api(lat, lon, target_dt)
    
    # 3. Application writes to cache
    await self.cache.put(cache_key, self._serialize_weather(weather))
    
    # 4. Return data
    return weather
```

### Write-Behind Cache (Fire-and-Forget)

```python
async def get_weather(self, lat: float, lon: float, target_dt: datetime) -> Weather:
    """
    Write-behind cache pattern
    
    Write to cache asynchronously (don't wait)
    """
    cache_key = self._generate_cache_key(lat, lon, target_dt)
    
    # Check cache
    cached = await self.cache.get(cache_key)
    if cached:
        return self._deserialize_weather(cached['data'])
    
    # Fetch from API
    weather = await self._fetch_from_api(lat, lon, target_dt)
    
    # Write to cache (fire-and-forget)
    asyncio.create_task(
        self.cache.put(cache_key, self._serialize_weather(weather))
    )
    
    # Return immediately (don't wait for cache write)
    return weather
```

**Por que fire-and-forget?**
- ✅ Reduz latência (não espera cache write)
- ✅ Cache write é "nice to have" (não crítico)
- ⚠️ Risk: Lambda pode terminar antes de write completar

**Solução:** Garantir task completion antes de return do Lambda handler.

---

## Cache Performance

### Metrics

**Cache Hit Rate:**

```python
# Fórmula
cache_hit_rate = (cache_hits / total_requests) * 100

# Exemplo (após warm-up)
cache_hits = 80
total_requests = 100
cache_hit_rate = 80%
```

**Latency Distribution:**

| Percentile | Cache HIT | Cache MISS | Improvement |
|------------|-----------|------------|-------------|
| P50 | ~25ms | ~250ms | **10x faster** |
| P90 | ~35ms | ~400ms | **11x faster** |
| P99 | ~50ms | ~500ms | **10x faster** |

**Cost Savings:**

```python
# OpenWeather API pricing
api_call_cost = $0.0001  # Por chamada

# Requests mensais
total_requests = 1_000_000
cache_hit_rate = 0.80

# Requests evitadas
api_calls_avoided = total_requests * cache_hit_rate  # 800,000

# Savings
savings = api_calls_avoided * api_call_cost
savings = $80.00 / month
```

### Benchmarks

**Test setup:**
- 100 cities
- 50 concurrent requests (Semaphore)
- Lambda 512MB memory
- Region: sa-east-1

**Results:**

| Scenario | P50 | P90 | P99 | Mean |
|----------|-----|-----|-----|------|
| 100% Cache HIT | ~150ms | ~180ms | ~200ms | ~155ms |
| 50% Cache HIT | ~200ms | ~300ms | ~400ms | ~225ms |
| 0% Cache MISS | ~450ms | ~550ms | ~650ms | ~475ms |

**Ver:** [scripts/performance_test_100_cities.py](../../scripts/performance_test_100_cities.py)

---

## Cache Invalidation

### Time-Based (TTL)

**Automatic:** DynamoDB TTL deletes expired items

```python
# Item criado com TTL de 3 horas
item = {
    'cacheKey': 'weather_-22.7572_-49.9439_1732647600',
    'data': {...},
    'ttl': 1732658400  # 3 hours from now
}

# Após 3 horas, DynamoDB marca para deletion
# Após ~48 horas, DynamoDB deleta item
```

**Manual:** Double-check TTL no `get()`

```python
async def get(self, key: str) -> Optional[Dict]:
    # Get item
    item = response.get('Item')
    
    # Check TTL manually
    ttl = item.get('ttl', 0)
    current_timestamp = int(datetime.now(timezone.utc).timestamp())
    
    if ttl > 0 and ttl < current_timestamp:
        return None  # Expired
    
    return item
```

### Manual Invalidation

```python
async def invalidate(self, key: str):
    """Delete item from cache"""
    table = await self._get_table()
    
    try:
        await table.delete_item(
            Key={'cacheKey': key}
        )
        
        logger.info("Cache invalidated", cache_key=key)
    
    except ClientError as e:
        logger.error("Cache invalidation error", cache_key=key, error=str(e))
```

**Use cases:**
- Weather data updated (rare)
- Manual cache flush
- Testing/debugging

### Batch Invalidation

```python
async def invalidate_pattern(self, pattern: str):
    """
    Invalidate all items matching pattern
    
    Example: invalidate_pattern("weather_-22.7572_-49.9439_*")
    """
    table = await self._get_table()
    
    # Scan table (expensive!)
    response = await table.scan(
        FilterExpression="begins_with(cacheKey, :pattern)",
        ExpressionAttributeValues={':pattern': pattern}
    )
    
    # Delete items
    items = response.get('Items', [])
    for item in items:
        await table.delete_item(
            Key={'cacheKey': item['cacheKey']}
        )
    
    logger.info("Cache pattern invalidated", pattern=pattern, count=len(items))
```

**⚠️ Cuidado:** Scan é caro (PAY_PER_REQUEST billing mode)

---

## Monitoring

### CloudWatch Metrics

**DynamoDB Metrics:**

```python
# Namespace: AWS/DynamoDB
# Dimensions: TableName=weather-forecast-cache-prod

# Read/Write Units
ConsumedReadCapacityUnits
ConsumedWriteCapacityUnits

# Latency
SuccessfulRequestLatency (GetItem, PutItem)

# Throttling
UserErrors (400 errors)
SystemErrors (500 errors)
```

**Custom Metrics:**

```python
from aws_lambda_powertools import Metrics

metrics = Metrics(namespace="WeatherForecastAPI")

# Cache hit/miss
metrics.add_metric(name="CacheHit", unit="Count", value=1)
metrics.add_metric(name="CacheMiss", unit="Count", value=1)

# Cache latency
metrics.add_metric(name="CacheLatency", unit="Milliseconds", value=25.3)
```

### Logging

```python
from aws_lambda_powertools import Logger

logger = Logger()

# Cache operations
logger.info("Cache hit", cache_key=cache_key, latency_ms=25.3)
logger.info("Cache miss", cache_key=cache_key, latency_ms=30.1)
logger.info("Cache saved", cache_key=cache_key, ttl_hours=3)

# Cache errors
logger.error("DynamoDB error", cache_key=cache_key, error=str(e))
```

**CloudWatch Insights:**

```sql
# Cache hit rate
fields @timestamp, message
| filter message like /Cache hit|Cache miss/
| stats count() as requests by message
| sort requests desc

# Cache latency distribution
fields @timestamp, latency_ms
| filter message = "Cache hit"
| stats avg(latency_ms) as avg, pct(latency_ms, 50) as p50, pct(latency_ms, 99) as p99
```

---

## Cost Analysis

### DynamoDB Pricing (PAY_PER_REQUEST)

**Read Request Units (RRU):**
- $0.25 per million read requests
- 1 RRU = up to 4 KB

**Write Request Units (WRU):**
- $1.25 per million write requests
- 1 WRU = up to 1 KB

**Storage:**
- $0.25 per GB-month

**Example (1M requests/month):**

```python
# Assumptions
total_requests = 1_000_000
cache_hit_rate = 0.80
cache_miss_rate = 0.20

# Operations
cache_hits = total_requests * cache_hit_rate  # 800,000
cache_misses = total_requests * cache_miss_rate  # 200,000

# DynamoDB operations
read_requests = total_requests  # 1M (all requests check cache)
write_requests = cache_misses  # 200,000 (only misses write)

# Costs
read_cost = (read_requests / 1_000_000) * 0.25  # $0.25
write_cost = (write_requests / 1_000_000) * 1.25  # $0.25
storage_cost = (0.3 * 0.25)  # ~300 MB = $0.08

total_cost = read_cost + write_cost + storage_cost
total_cost = $0.58 / month
```

**OpenWeather API cost avoided:**

```python
# API calls avoided
api_calls_avoided = cache_hits  # 800,000

# Savings
savings = (api_calls_avoided / 1_000_000) * 100  # $80.00

# Net benefit
net_benefit = savings - total_cost
net_benefit = $80.00 - $0.58 = $79.42 / month
```

**ROI:** ~13,700% 🚀

---

## Best Practices

### ✅ DO

1. **Use TTL for automatic cleanup**
   ```python
   await cache.put(key, value, ttl_hours=3)
   ```

2. **Fail open on cache errors**
   ```python
   try:
       cached = await cache.get(key)
   except Exception:
       return None  # Fetch from API instead
   ```

3. **Use lazy resource creation**
   ```python
   async def _get_table(self):
       if self._table is None:
           self._table = await create_table()
       return self._table
   ```

4. **Double-check TTL manually**
   ```python
   if ttl < current_timestamp:
       return None  # Expired
   ```

5. **Log cache operations**
   ```python
   logger.info("Cache hit", cache_key=key)
   ```

### ❌ DON'T

1. **❌ Don't block on cache writes**
   ```python
   # ❌ ERRADO
   await cache.put(key, value)
   return weather  # Blocks on cache write
   
   # ✅ CORRETO
   asyncio.create_task(cache.put(key, value))
   return weather  # Fire-and-forget
   ```

2. **❌ Don't use scan operations**
   ```python
   # ❌ ERRADO (expensive!)
   response = await table.scan()
   ```

3. **❌ Don't cache sensitive data**
   ```python
   # ❌ ERRADO
   await cache.put(key, {'api_key': api_key})
   ```

4. **❌ Don't rely on TTL for immediate deletion**
   ```python
   # ❌ ERRADO (TTL has ~48h delay)
   # ✅ CORRETO: Implement manual check
   ```

---

## References

- **DynamoDB TTL:** https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html
- **aioboto3 docs:** https://aioboto3.readthedocs.io/
- **DynamoDB best practices:** https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html
- **Cache patterns:** https://aws.amazon.com/caching/best-practices/
