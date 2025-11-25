# OpenWeather API Integration

## Visão Geral

A aplicação integra-se com **OpenWeather Forecast API** para obter previsões meteorológicas de 5 dias com intervalos de 3 horas.

**API Details:**
- **Provider:** OpenWeather (openweathermap.org)
- **Plan:** Free tier (60 calls/minute)
- **Endpoint:** `https://api.openweathermap.org/data/2.5/forecast`
- **Data:** Previsões de 5 dias, intervalos de 3 horas (40 previsões)
- **Unidades:** Metric (Celsius, km/h)
- **Idioma:** Português (pt_br)

---

## API Configuration

### Environment Variables

```bash
# OpenWeather API Key
OPENWEATHER_API_KEY=your_api_key_here

# Base URL (optional, default: https://api.openweathermap.org/data/2.5)
OPENWEATHER_BASE_URL=https://api.openweathermap.org/data/2.5

# Units (optional, default: metric)
OPENWEATHER_UNITS=metric

# Language (optional, default: pt_br)
OPENWEATHER_LANG=pt_br
```

### Configuration File

```python
# lambda/config.py

import os

# OpenWeather API Configuration
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
OPENWEATHER_BASE_URL = os.getenv(
    'OPENWEATHER_BASE_URL',
    'https://api.openweathermap.org/data/2.5'
)
OPENWEATHER_UNITS = os.getenv('OPENWEATHER_UNITS', 'metric')
OPENWEATHER_LANG = os.getenv('OPENWEATHER_LANG', 'pt_br')

# Validation
if not OPENWEATHER_API_KEY:
    raise ValueError("OPENWEATHER_API_KEY environment variable is required")
```

### Terraform Configuration

```hcl
# terraform/main.tf

resource "aws_lambda_function" "weather_forecast" {
  # ... other configuration ...
  
  environment {
    variables = {
      OPENWEATHER_API_KEY = var.openweather_api_key
      OPENWEATHER_UNITS   = "metric"
      OPENWEATHER_LANG    = "pt_br"
    }
  }
}
```

---

## API Endpoints

### Forecast Endpoint

**URL:** `GET https://api.openweathermap.org/data/2.5/forecast`

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `lat` | float | ✅ | Latitude (-90 to 90) |
| `lon` | float | ✅ | Longitude (-180 to 180) |
| `appid` | string | ✅ | API key |
| `units` | string | ❌ | Units (metric, imperial, standard) |
| `lang` | string | ❌ | Language code (pt_br, en, es, ...) |

**Example Request:**

```bash
curl "https://api.openweathermap.org/data/2.5/forecast?lat=-22.7572&lon=-49.9439&appid=YOUR_API_KEY&units=metric&lang=pt_br"
```

**Response Format:**

```json
{
  "cod": "200",
  "message": 0,
  "cnt": 40,
  "list": [
    {
      "dt": 1732647600,
      "main": {
        "temp": 28.3,
        "feels_like": 29.1,
        "temp_min": 27.8,
        "temp_max": 28.3,
        "pressure": 1012,
        "humidity": 65
      },
      "weather": [
        {
          "id": 802,
          "main": "Clouds",
          "description": "nublado",
          "icon": "03d"
        }
      ],
      "clouds": {
        "all": 40
      },
      "wind": {
        "speed": 3.47,
        "deg": 180,
        "gust": 4.23
      },
      "pop": 0.35,
      "sys": {
        "pod": "d"
      },
      "dt_txt": "2025-11-26 15:00:00"
    }
    // ... 39 more forecasts
  ],
  "city": {
    "id": 3443631,
    "name": "Ribeirão do Sul",
    "coord": {
      "lat": -22.7572,
      "lon": -49.9439
    },
    "country": "BR",
    "timezone": -10800,
    "sunrise": 1732604580,
    "sunset": 1732653720
  }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `dt` | integer | Unix timestamp (UTC) |
| `dt_txt` | string | DateTime string (ISO 8601) |
| `main.temp` | float | Temperature (°C) |
| `main.humidity` | integer | Humidity (%) |
| `wind.speed` | float | Wind speed (m/s) |
| `pop` | float | Probability of precipitation (0-1) |
| `weather[0].description` | string | Weather description (localized) |

---

## Repository Implementation

### AsyncOpenWeatherRepository

```python
class AsyncOpenWeatherRepository:
    """
    Async repository for OpenWeather API
    Implements caching and error handling
    """
    
    def __init__(self, api_key: str, cache: DynamoDBCache):
        """
        Initialize repository
        
        Args:
            api_key: OpenWeather API key
            cache: DynamoDB cache instance
        """
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.cache = cache
        
        # Lazy session creation
        self._session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    'Accept': 'application/json',
                    'User-Agent': 'Weather-Forecast-API/1.0'
                }
            )
        
        return self._session
    
    async def get_weather(
        self,
        lat: float,
        lon: float,
        target_dt: datetime
    ) -> Weather:
        """
        Get weather forecast for coordinates and datetime
        
        Args:
            lat: Latitude
            lon: Longitude
            target_dt: Target datetime for forecast
        
        Returns:
            Weather entity
        
        Raises:
            WeatherDataNotFoundException: If no forecast found
        """
        # Check cache first
        cache_key = self._generate_cache_key(lat, lon, target_dt)
        cached = await self.cache.get(cache_key)
        
        if cached:
            logger.info("Cache hit", cache_key=cache_key)
            return self._deserialize_weather(cached['data'])
        
        logger.info("Cache miss", cache_key=cache_key)
        
        # Fetch from API
        weather = await self._fetch_from_api(lat, lon, target_dt)
        
        # Save to cache (fire-and-forget)
        asyncio.create_task(
            self.cache.put(cache_key, self._serialize_weather(weather))
        )
        
        return weather
    
    async def _fetch_from_api(
        self,
        lat: float,
        lon: float,
        target_dt: datetime
    ) -> Weather:
        """Fetch weather data from OpenWeather API"""
        session = await self._get_session()
        
        url = f"{self.base_url}/forecast"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': self.api_key,
            'units': 'metric',
            'lang': 'pt_br'
        }
        
        try:
            async with session.get(url, params=params) as response:
                # Check status
                if response.status == 404:
                    raise WeatherDataNotFoundException(lat, lon, target_dt)
                
                # Raise for other errors
                response.raise_for_status()
                
                # Parse JSON
                data = await response.json()
                
                # Map to Weather entity
                return self._map_to_weather(data, lat, lon, target_dt)
        
        except aiohttp.ClientError as e:
            logger.error("HTTP error", url=url, error=str(e))
            raise WeatherDataNotFoundException(lat, lon, target_dt)
        
        except asyncio.TimeoutError:
            logger.error("Request timeout", url=url)
            raise WeatherDataNotFoundException(lat, lon, target_dt)
```

---

## Data Mapping

### OpenWeather → Domain Entity

```python
def _map_to_weather(
    self,
    data: Dict,
    lat: float,
    lon: float,
    target_dt: datetime
) -> Weather:
    """
    Map OpenWeather API response to Weather domain entity
    
    Args:
        data: OpenWeather API response
        lat: Request latitude
        lon: Request longitude
        target_dt: Target datetime
    
    Returns:
        Weather entity
    
    Raises:
        WeatherDataNotFoundException: If no forecast found for target_dt
    """
    # Extract forecast list
    forecasts = data.get('list', [])
    
    if not forecasts:
        raise WeatherDataNotFoundException(lat, lon, target_dt)
    
    # Convert dt to datetime
    for forecast in forecasts:
        forecast['dt_datetime'] = datetime.fromtimestamp(
            forecast['dt'],
            tz=timezone.utc
        )
    
    # Find closest forecast to target_dt
    closest = self._find_closest_forecast(forecasts, target_dt)
    
    # Map fields
    return Weather(
        temperature=closest['main']['temp'],
        humidity=closest['main']['humidity'],
        wind_speed=self._convert_wind_speed(closest['wind']['speed']),
        rainfall_intensity=self._convert_pop_to_percentage(closest.get('pop', 0)),
        weather_description=closest['weather'][0]['description'],
        timestamp=closest['dt_datetime']
    )

def _find_closest_forecast(
    self,
    forecasts: List[Dict],
    target_dt: datetime
) -> Dict:
    """
    Find forecast closest to target datetime
    
    OpenWeather returns forecasts every 3 hours:
    00:00, 03:00, 06:00, 09:00, 12:00, 15:00, 18:00, 21:00
    
    Algorithm: Find forecast with minimum time difference
    
    Example:
        target_dt = 2025-11-26 14:30:00
        forecasts = [
            2025-11-26 12:00:00 (diff: 2h 30m),
            2025-11-26 15:00:00 (diff: 30m) ← CLOSEST,
            2025-11-26 18:00:00 (diff: 3h 30m)
        ]
    
    Args:
        forecasts: List of forecast dicts with 'dt_datetime' field
        target_dt: Target datetime
    
    Returns:
        Closest forecast dict
    
    Raises:
        WeatherDataNotFoundException: If no forecasts available
    """
    if not forecasts:
        raise WeatherDataNotFoundException(
            details={'reason': 'No forecasts available'}
        )
    
    # Find minimum time difference
    closest = min(
        forecasts,
        key=lambda f: abs((f['dt_datetime'] - target_dt).total_seconds())
    )
    
    return closest

def _convert_wind_speed(self, speed_ms: float) -> float:
    """
    Convert wind speed from m/s to km/h
    
    Args:
        speed_ms: Wind speed in m/s
    
    Returns:
        Wind speed in km/h
    
    Example:
        3.47 m/s → 12.49 km/h
    """
    return round(speed_ms * 3.6, 2)

def _convert_pop_to_percentage(self, pop: float) -> float:
    """
    Convert probability of precipitation from decimal to percentage
    
    Args:
        pop: Probability (0.0 - 1.0)
    
    Returns:
        Percentage (0.0 - 100.0)
    
    Example:
        0.35 → 35.0%
    """
    return round(pop * 100, 1)
```

### Field Mapping Table

| OpenWeather | Type | Domain Entity | Type | Transformation |
|-------------|------|---------------|------|----------------|
| `main.temp` | float | `temperature` | float | Direct (°C) |
| `main.humidity` | int | `humidity` | float | Cast to float (%) |
| `wind.speed` | float | `wind_speed` | float | m/s → km/h (*3.6) |
| `pop` | float | `rainfall_intensity` | float | Decimal → % (*100) |
| `weather[0].description` | string | `weather_description` | string | Direct (localized) |
| `dt` | int | `timestamp` | datetime | Unix → datetime.fromtimestamp() |

---

## Forecast Selection Algorithm

### Problem Statement

OpenWeather retorna 40 previsões (5 dias × 8 previsões/dia = 40 previsões), mas o usuário pode solicitar qualquer datetime dentro desse período.

**Challenge:** Como selecionar a previsão mais apropriada?

### Solution: Closest Forecast Algorithm

```python
def _find_closest_forecast(forecasts, target_dt):
    """
    Find forecast with minimum absolute time difference
    
    Complexity: O(n) where n = number of forecasts (typically 40)
    """
    closest = min(
        forecasts,
        key=lambda f: abs((f['dt_datetime'] - target_dt).total_seconds())
    )
    
    return closest
```

### Example Scenarios

**Scenario 1: Exact Match**

```
target_dt = 2025-11-26 15:00:00
forecasts = [
    2025-11-26 12:00:00 (diff: 3h = 10800s),
    2025-11-26 15:00:00 (diff: 0h = 0s) ← SELECTED,
    2025-11-26 18:00:00 (diff: 3h = 10800s)
]
```

**Scenario 2: Between Forecasts**

```
target_dt = 2025-11-26 14:30:00
forecasts = [
    2025-11-26 12:00:00 (diff: 2h30m = 9000s),
    2025-11-26 15:00:00 (diff: 30m = 1800s) ← SELECTED,
    2025-11-26 18:00:00 (diff: 3h30m = 12600s)
]
```

**Scenario 3: Edge Case (Very Early)**

```
target_dt = 2025-11-26 00:30:00
forecasts = [
    2025-11-26 00:00:00 (diff: 30m = 1800s) ← SELECTED,
    2025-11-26 03:00:00 (diff: 2h30m = 9000s),
    2025-11-26 06:00:00 (diff: 5h30m = 19800s)
]
```

### Time Bounds

```python
# OpenWeather forecast window: 5 days from now
now = datetime.now(timezone.utc)
min_forecast_time = now
max_forecast_time = now + timedelta(days=5)

# Example
now = 2025-11-26 00:00:00
min_forecast_time = 2025-11-26 00:00:00
max_forecast_time = 2025-12-01 00:00:00

# Valid requests
target_dt = 2025-11-27 15:00:00  # ✅ Within window
target_dt = 2025-12-05 15:00:00  # ❌ Outside window (WeatherDataNotFoundException)
```

---

## Error Handling

### HTTP Status Codes

| Status | Meaning | Action |
|--------|---------|--------|
| 200 | Success | Parse and return data |
| 401 | Invalid API key | Log error, raise exception |
| 404 | Location not found | Raise WeatherDataNotFoundException |
| 429 | Rate limit exceeded | Log warning, retry or fail |
| 500 | Server error | Log error, raise exception |
| 503 | Service unavailable | Log error, raise exception |

### Error Handling Implementation

```python
async def _fetch_from_api(self, lat, lon, target_dt):
    """Fetch with comprehensive error handling"""
    try:
        async with session.get(url, params=params) as response:
            # Handle specific status codes
            if response.status == 401:
                logger.error("Invalid API key")
                raise InvalidAPIKeyException()
            
            if response.status == 404:
                logger.warning("Location not found", lat=lat, lon=lon)
                raise WeatherDataNotFoundException(lat, lon, target_dt)
            
            if response.status == 429:
                logger.warning("Rate limit exceeded")
                raise RateLimitException()
            
            # Raise for other 4xx/5xx
            response.raise_for_status()
            
            # Parse JSON
            data = await response.json()
            
            return self._map_to_weather(data, lat, lon, target_dt)
    
    except aiohttp.ClientError as e:
        logger.error("HTTP client error", error=str(e))
        raise WeatherDataNotFoundException(lat, lon, target_dt)
    
    except asyncio.TimeoutError:
        logger.error("Request timeout", url=url)
        raise WeatherDataNotFoundException(lat, lon, target_dt)
    
    except json.JSONDecodeError as e:
        logger.error("JSON decode error", error=str(e))
        raise WeatherDataNotFoundException(lat, lon, target_dt)
```

### Retry Strategy

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def _fetch_from_api_with_retry(self, lat, lon, target_dt):
    """
    Fetch with automatic retry
    
    Retry policy:
    - Max 3 attempts
    - Exponential backoff: 2s, 4s, 8s
    - Only retry on transient errors (429, 500, 503)
    """
    try:
        return await self._fetch_from_api(lat, lon, target_dt)
    
    except RateLimitException:
        logger.warning("Rate limit, retrying...")
        raise  # Retry
    
    except WeatherDataNotFoundException:
        logger.error("No data found")
        raise  # Don't retry (permanent error)
```

---

## Rate Limiting

### OpenWeather Free Tier Limits

| Metric | Limit |
|--------|-------|
| Calls/minute | 60 |
| Calls/day | Unlimited |
| Forecast window | 5 days |
| Update frequency | 3 hours |

### Application Rate Limiting

**Semaphore Throttling:**

```python
# Limit concurrent API calls to 50
semaphore = asyncio.Semaphore(50)

async def _fetch_with_throttle(self, lat, lon, target_dt):
    """Fetch with concurrency limit"""
    async with semaphore:  # Max 50 concurrent
        return await self._fetch_from_api(lat, lon, target_dt)
```

**Cache Strategy:**

```python
# Cache reduces API calls by ~80%
cache_hit_rate = 0.80

# Requests/minute
total_requests = 100
api_calls = total_requests * (1 - cache_hit_rate)  # 20 calls
api_calls < 60  # ✅ Within limit
```

### Monitoring Rate Limits

```python
from aws_lambda_powertools import Metrics

metrics = Metrics(namespace="WeatherForecastAPI")

# Track API calls
metrics.add_metric(name="OpenWeatherAPICalls", unit="Count", value=1)

# Track rate limit errors
if response.status == 429:
    metrics.add_metric(name="RateLimitErrors", unit="Count", value=1)
```

---

## Performance Optimization

### Caching Strategy

```python
# 3-level cache
1. Check DynamoDB cache (~20-30ms)
   ├─ HIT → Return cached data (80% of requests)
   └─ MISS → Continue to step 2

2. Call OpenWeather API (~200-500ms)
   └─ Parse and map data

3. Save to DynamoDB cache (fire-and-forget)
   └─ TTL: 3 hours
```

**Performance Impact:**

| Scenario | Latency | API Calls |
|----------|---------|-----------|
| 100 requests, 80% cache hit | ~150ms total | 20 calls |
| 100 requests, 0% cache hit | ~450ms total | 100 calls |

### Connection Pooling

```python
# aiohttp automatically pools connections
session = aiohttp.ClientSession(
    connector=aiohttp.TCPConnector(
        limit=100,              # Max 100 total connections
        limit_per_host=50,      # Max 50 per host
        keepalive_timeout=30    # Keep alive 30s
    )
)
```

**Benefits:**
- ✅ Reuse TCP connections
- ✅ Avoid SSL handshake overhead
- ✅ Reduce latency by ~100ms per request

### Batch Requests

```python
# Fetch multiple cities in parallel
async def fetch_multiple_cities(city_ids, target_dt):
    """Fetch weather for multiple cities concurrently"""
    tasks = [
        fetch_city_weather(city_id, target_dt)
        for city_id in city_ids
    ]
    
    # Execute in parallel (max 50 concurrent)
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return results
```

**Performance (100 cities):**
- Sequential: ~20 seconds (100 × 200ms)
- Parallel (50 concurrent): ~400ms (2 batches × 200ms)
- **Improvement: 50x faster**

---

## Testing

### Unit Tests

```python
@pytest.mark.asyncio
async def test_fetch_from_api():
    """Test OpenWeather API integration"""
    # Mock aiohttp response
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
    
    # Mock cache
    mock_cache = Mock()
    mock_cache.get = AsyncMock(return_value=None)
    
    # Create repository
    repo = AsyncOpenWeatherRepository(api_key="test", cache=mock_cache)
    
    # Mock session
    with patch.object(repo, '_fetch_from_api', return_value=Weather(...)):
        weather = await repo.get_weather(-22.7572, -49.9439, datetime.now())
    
    assert weather.temperature == 28.3
    assert weather.humidity == 65.0
```

### Integration Tests

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_api_call():
    """Test real OpenWeather API call"""
    cache = DynamoDBCache(table_name="test-cache")
    repo = AsyncOpenWeatherRepository(
        api_key=os.getenv('OPENWEATHER_API_KEY'),
        cache=cache
    )
    
    weather = await repo.get_weather(
        lat=-22.7572,
        lon=-49.9439,
        target_dt=datetime.now(timezone.utc)
    )
    
    assert weather is not None
    assert weather.temperature > -50
    assert weather.temperature < 60
    assert 0 <= weather.humidity <= 100
```

---

## Monitoring & Observability

### CloudWatch Metrics

```python
from aws_lambda_powertools import Metrics

metrics = Metrics(namespace="WeatherForecastAPI")

# API call metrics
metrics.add_metric(name="OpenWeatherAPICalls", unit="Count", value=1)
metrics.add_metric(name="OpenWeatherAPILatency", unit="Milliseconds", value=234.5)

# Error metrics
metrics.add_metric(name="OpenWeatherAPIErrors", unit="Count", value=1)
metrics.add_metric(name="RateLimitErrors", unit="Count", value=1)

# Cache metrics
metrics.add_metric(name="CacheHitRate", unit="Percent", value=80.0)
```

### Structured Logging

```python
from aws_lambda_powertools import Logger

logger = Logger()

# API call logging
logger.info(
    "OpenWeather API call",
    lat=lat,
    lon=lon,
    target_datetime=target_dt.isoformat(),
    latency_ms=234.5
)

# Error logging
logger.error(
    "OpenWeather API error",
    status_code=429,
    error="Rate limit exceeded",
    lat=lat,
    lon=lon
)
```

### CloudWatch Insights Queries

```sql
# API call volume
fields @timestamp, message
| filter message like /OpenWeather API call/
| stats count() as calls by bin(5m)

# Average latency
fields @timestamp, latency_ms
| filter message like /OpenWeather API call/
| stats avg(latency_ms) as avg_latency, pct(latency_ms, 99) as p99

# Error rate
fields @timestamp, message
| filter message like /OpenWeather API error/
| stats count() as errors by status_code
```

---

## Cost Analysis

### OpenWeather API Costs

**Free Tier:**
- ✅ 60 calls/minute
- ✅ Unlimited calls/day
- ✅ $0.00/month

**Paid Tier (not used):**
- 1000 calls/day: $40/month
- 100,000 calls/day: $200/month

### Cost Savings via Cache

```python
# Monthly estimates
total_requests = 1_000_000  # 1M requests/month
cache_hit_rate = 0.80

# API calls without cache
api_calls_no_cache = total_requests  # 1,000,000 calls

# API calls with cache
api_calls_with_cache = total_requests * (1 - cache_hit_rate)  # 200,000 calls

# Calls avoided
calls_avoided = api_calls_no_cache - api_calls_with_cache  # 800,000 calls

# If using paid tier
cost_per_call = 0.0001  # $0.0001 per call
savings = calls_avoided * cost_per_call  # $80.00/month
```

---

## Best Practices

### ✅ DO

1. **Cache API responses**
   ```python
   cached = await cache.get(cache_key)
   if cached:
       return cached
   ```

2. **Handle rate limits gracefully**
   ```python
   if response.status == 429:
       logger.warning("Rate limit exceeded")
       # Implement backoff or return cached data
   ```

3. **Use lazy session creation**
   ```python
   async def _get_session(self):
       if self._session is None:
           self._session = aiohttp.ClientSession()
       return self._session
   ```

4. **Log all API calls**
   ```python
   logger.info("API call", lat=lat, lon=lon, latency_ms=200)
   ```

5. **Validate coordinates**
   ```python
   if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
       raise InvalidCoordinatesException()
   ```

### ❌ DON'T

1. **❌ Don't hardcode API key**
   ```python
   # ❌ ERRADO
   api_key = "1234567890abcdef"
   
   # ✅ CORRETO
   api_key = os.getenv('OPENWEATHER_API_KEY')
   ```

2. **❌ Don't ignore rate limits**
   ```python
   # ❌ ERRADO
   # Infinite retry without backoff
   ```

3. **❌ Don't skip caching**
   ```python
   # ❌ ERRADO
   # Every request hits API (expensive + slow)
   ```

4. **❌ Don't expose raw API data**
   ```python
   # ❌ ERRADO
   return api_response  # Coupling to external API
   
   # ✅ CORRETO
   return Weather(...)  # Domain entity
   ```

---

## References

- **OpenWeather API Docs:** https://openweathermap.org/forecast5
- **API Pricing:** https://openweathermap.org/price
- **aiohttp Docs:** https://docs.aiohttp.org/
- **Rate Limiting Best Practices:** https://cloud.google.com/architecture/rate-limiting-strategies-techniques
