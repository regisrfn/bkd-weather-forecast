# Open-Meteo Hourly Integration

## 📋 Visão Geral

Integração com **Open-Meteo Hourly Forecast API** para enriquecer os dados de clima atual com previsões horárias precisas. A estratégia de **enriquecimento híbrido** combina o melhor de dois mundos:

- **OpenWeather**: Fornece base completa (visibility, pressure, feels_like)
- **Open-Meteo Hourly**: Enriquece com dados precisos na hora exata

## 🎯 Problema Resolvido

### Limitação do OpenWeather

- **Granularidade**: Intervalos de 3 em 3 horas
- **Imprecisão**: Dados podem estar 1.5h desatualizados na média
- **Exemplo**: Às 14:00, OpenWeather retorna dados de 12:00 ou 15:00

### Solução Open-Meteo Hourly

- **Granularidade**: Hora em hora (168 horas = 7 dias)
- **Precisão**: Dados da hora exata solicitada
- **Exemplo**: Às 14:00, retorna dados de 14:00

## 🏗️ Arquitetura

### Fluxo de Enriquecimento

```
1. Use Case (AsyncGetCityDetailedForecastUseCase)
   ↓
2. Parallel API Calls (asyncio.gather)
   ├─→ OpenWeather API (base data)
   ├─→ Open-Meteo Daily API (daily forecasts)
   └─→ Open-Meteo Hourly API (hourly forecasts)
   ↓
3. Enrichment (HourlyWeatherProcessor)
   ├─→ Find closest hour
   ├─→ Merge data (preserve OpenWeather fields)
   └─→ Calculate daily metrics
   ↓
4. Response
   ├─→ currentWeather (enriched)
   ├─→ dailyForecasts (16 days)
   └─→ hourlyForecasts (168 hours)
```

### Componentes

#### 1. Repository Layer

```python
# lambda/infrastructure/adapters/output/async_openmeteo_repository.py
class AsyncOpenMeteoRepository:
    async def get_hourly_forecast(
        self,
        latitude: float,
        longitude: float
    ) -> List[HourlyForecast]:
        """
        Busca 168 horas (7 dias) de previsões horárias
        Cache TTL: 1 hora (3600s)
        """
```

**Parâmetros da API:**
- `hourly`: `temperature_2m`, `precipitation`, `precipitation_probability`, `relative_humidity_2m`, `wind_speed_10m`, `wind_direction_10m`, `cloud_cover`, `weather_code`
- `forecast_hours`: 168 (7 dias)

#### 2. Domain Entity

```python
# lambda/domain/entities/hourly_forecast.py
@dataclass
class HourlyForecast:
    timestamp: datetime           # Hora exata
    temperature: float           # °C
    precipitation: float         # mm
    precipitation_probability: int  # %
    humidity: int               # %
    wind_speed: float           # km/h
    wind_direction: int         # 0-360°
    cloud_cover: int            # %
    weather_code: int           # WMO code
```

#### 3. Enrichment Logic

```python
# lambda/infrastructure/adapters/helpers/hourly_weather_processor.py
class HourlyWeatherProcessor:
    @staticmethod
    def enrich_weather_with_hourly(
        base_weather: Weather,
        hourly_forecasts: List[HourlyForecast]
    ) -> Weather:
        """
        Estratégia de enriquecimento:
        1. Preserva campos únicos do OpenWeather (visibility, pressure, feels_like)
        2. Sobrescreve com dados hourly mais precisos (temp, wind, etc)
        3. Calcula métricas diárias (rain accumulation, temp extremes)
        """
```

## 📊 Dados Enriquecidos

### Campos Enriquecidos (Open-Meteo)

| Campo | Origem | Precisão |
|-------|--------|----------|
| `temperature` | Open-Meteo hourly | Hora exata |
| `wind_speed` | Open-Meteo hourly | Hora exata |
| `wind_direction` | Open-Meteo hourly | 0-360° |
| `humidity` | Open-Meteo hourly | Hora exata |
| `clouds` | Open-Meteo hourly | Hora exata |
| `rain_1h` | Open-Meteo hourly | mm na hora |
| `rain_accumulated_day` | Calculado | Soma do dia |
| `temp_min` | Calculado | Mínima do dia |
| `temp_max` | Calculado | Máxima do dia |

### Campos Preservados (OpenWeather)

| Campo | Por quê preservar? |
|-------|--------------------|
| `visibility` | Open-Meteo não fornece |
| `pressure` | Open-Meteo não fornece |
| `feels_like` | Open-Meteo não fornece |

### Hourly Forecasts Array

```json
"hourlyForecasts": [
  {
    "timestamp": "2025-12-01T14:00:00Z",
    "temperature": 28.5,
    "precipitation": 0.2,
    "precipitationProbability": 30,
    "humidity": 65,
    "windSpeed": 12.5,
    "windDirection": 180,
    "cloudCover": 40,
    "weatherCode": 2,
    "description": "Partly cloudy"
  }
  // ... 167 more hours
]
```

## 🔧 Implementação

### 1. Busca Paralela

```python
# lambda/application/use_cases/async_get_city_detailed_forecast.py
async def execute(self, city_id: str, target_datetime: Optional[datetime] = None):
    # 3 calls paralelas
    current_weather, extended_forecast, hourly_forecasts = await asyncio.gather(
        self._get_current_weather(city_id, target_datetime),
        self._get_extended_forecast(city_id),
        self._get_hourly_forecast(city.latitude, city.longitude),
        return_exceptions=True
    )
    
    # Enriquecimento
    if not isinstance(hourly_forecasts, Exception):
        current_weather = HourlyWeatherProcessor.enrich_weather_with_hourly(
            current_weather,
            hourly_forecasts
        )
```

### 2. Encontrar Hora Mais Próxima

```python
def _find_closest_hourly(
    hourly_forecasts: List[HourlyForecast],
    target_time: datetime
) -> Optional[HourlyForecast]:
    """
    Encontra previsão horária mais próxima do timestamp alvo
    Usa diferença absoluta de tempo
    """
    closest = min(
        hourly_forecasts,
        key=lambda h: abs((h.timestamp - target_time).total_seconds())
    )
    
    # Valida diferença (max 1.5h)
    diff_seconds = abs((closest.timestamp - target_time).total_seconds())
    if diff_seconds > 5400:  # 1.5 horas
        return None
    
    return closest
```

### 3. Mesclar Dados

```python
def enrich_weather_with_hourly(
    base_weather: Weather,
    hourly_forecasts: List[HourlyForecast]
) -> Weather:
    closest_hourly = _find_closest_hourly(hourly_forecasts, base_weather.timestamp)
    
    if not closest_hourly:
        return base_weather
    
    # Sobrescrever com dados hourly (mais precisos)
    base_weather.temperature = closest_hourly.temperature
    base_weather.wind_speed = closest_hourly.wind_speed
    base_weather.wind_direction = closest_hourly.wind_direction
    base_weather.humidity = closest_hourly.humidity
    base_weather.clouds = closest_hourly.cloud_cover
    base_weather.rain_1h = closest_hourly.precipitation
    
    # Calcular métricas diárias
    base_weather.rain_accumulated_day = _calculate_daily_rain_accumulation(...)
    base_weather.temp_min, base_weather.temp_max = _calculate_daily_temp_extremes(...)
    
    # Preservar campos do OpenWeather
    # (visibility, pressure, feels_like já estão em base_weather)
    
    return base_weather
```

## 🎯 Campos de Vento

### wind_speed_10m e wind_direction_10m

Open-Meteo fornece múltiplas alturas de medição:
- `wind_speed_10m` / `wind_direction_10m` → **Padrão meteorológico** (10m altura) ✅
- `wind_speed_80m` / `wind_direction_80m` → Para energia eólica
- `wind_speed_100m` / `wind_direction_100m` → Para aplicações industriais

**Por que 10m?**
- Padrão da Organização Meteorológica Mundial (WMO)
- Mesma altura das estações meteorológicas
- Comparável com outras fontes de dados

### Conversão para API Response

```python
# wind_direction_10m (0-360°) → windDirection (0-360°)
# Nenhuma conversão necessária, apenas renomear

api_response = {
    "windSpeed": hourly.wind_speed * 3.6,  # m/s → km/h
    "windDirection": hourly.wind_direction  # 0-360°
}
```

### Pontos Cardeais

| Graus | Direção |
|-------|---------|
| 0° / 360° | Norte (N) |
| 45° | Nordeste (NE) |
| 90° | Leste (E) |
| 135° | Sudeste (SE) |
| 180° | Sul (S) |
| 225° | Sudoeste (SW) |
| 270° | Oeste (W) |
| 315° | Noroeste (NW) |

## 💾 Cache Strategy

### TTL Diferenciado

```python
# Hourly forecast: 1 hora (mais volátil)
CACHE_TTL_HOURLY = 3600  # 1 hora

# Daily forecast: 6 horas (menos volátil)
CACHE_TTL_DAILY = 21600  # 6 horas
```

**Justificativa:**
- Dados horários mudam frequentemente → cache menor
- Dados diários são mais estáveis → cache maior
- Balance entre freshness e performance

### Cache Keys

```python
cache_key_hourly = f"openmeteo_hourly_{city_id}"
cache_key_daily = f"openmeteo_{city_id}"
```

## 🧪 Testes

### Unit Tests (29 total)

1. **test_hourly_forecast_entity.py** (3 testes)
   - ✅ Criação de entidade
   - ✅ Formato API response
   - ✅ Validação wind_direction (0-360°)

2. **test_hourly_weather_processor.py** (17 testes)
   - ✅ Preserva campos OpenWeather (visibility, pressure, feels_like)
   - ✅ Encontra hora mais próxima
   - ✅ Calcula rain accumulation diária
   - ✅ Calcula temperature extremes diárias
   - ✅ WMO weather code descriptions

3. **test_async_openmeteo_hourly.py** (5 testes)
   - ✅ get_hourly_forecast() retorna 168 horas
   - ✅ Cache com TTL de 1 hora
   - ✅ Handling de dados faltantes
   - ✅ Validação de limites

4. **test_wind_direction_fields.py** (4 testes)
   - ✅ HourlyForecast usa wind_direction_10m
   - ✅ Weather entity tem wind_direction
   - ✅ Pontos cardeais corretos
   - ✅ Validação de range (0-360°)

### Integration Tests (8 total)

1. **test_detailed_forecast_endpoint.py** (4 testes)
   - ✅ Sucesso com dados reais
   - ✅ Cidade não encontrada (404)
   - ✅ ID inválido (400)
   - ✅ Query param `date` funcional

2. **test_hourly_enrichment.py** (4 testes)
   - ✅ Current weather enriquecido com hourly
   - ✅ Array de 168 hourly forecasts disponível
   - ✅ Backward compatibility (18 campos + 2 novos)
   - ✅ Graceful degradation (API funciona se hourly falhar)

**Status:** ✅ **37/37 testes passando**

## 🔄 Graceful Degradation

### Estratégia de Fallback

```python
try:
    hourly_forecasts = await openmeteo_repo.get_hourly_forecast(lat, lng)
    current_weather = HourlyWeatherProcessor.enrich_weather_with_hourly(
        current_weather,
        hourly_forecasts
    )
except Exception as e:
    logger.warning(f"Failed to enrich with hourly data: {e}")
    # Continua com dados do OpenWeather (base)
    pass

return ExtendedForecast(
    current_weather=current_weather,          # OpenWeather ou enriched
    daily_forecasts=daily_forecasts,         # Open-Meteo daily
    hourly_forecasts=hourly_forecasts or []  # Empty se falhar
)
```

**Resultado:**
- API **nunca falha** por causa de hourly data
- Clientes recebem ao menos dados do OpenWeather
- Backward compatible com clientes antigos

## 📈 Benefícios

### ✅ Precisão

- Dados da **hora exata** vs intervalo 3h
- Temperatura, vento e precipitação mais precisos
- Wind direction disponível (Open Weather não fornecia)

### ✅ Granularidade

- **168 horas** de previsões detalhadas
- Frontend pode criar carrosséis hora a hora
- Melhor UX para visualização temporal

### ✅ Completude

- **Híbrido**: Melhor dos dois mundos
- Preserva campos únicos do OpenWeather
- Adiciona precisão do Open-Meteo

### ✅ Performance

- Cache de 1h para hourly
- Lazy evaluation (só busca se solicitado)
- Não degrada performance do endpoint

## 🔗 Recursos

- **Open-Meteo API Docs**: https://open-meteo.com/en/docs
- **WMO Weather Codes**: https://open-meteo.com/en/docs#weathervariables
- **API Endpoint**: `https://api.open-meteo.com/v1/forecast`

## 📝 Próximos Passos

### Possíveis Melhorias

- [ ] Adicionar mais variáveis (UV index, dew point)
- [ ] Implementar ensemble forecast (múltiplos modelos)
- [ ] Adicionar minutely precipitation (próximos 60 minutos)
- [ ] Historical data (últimos 30 dias)

---

**Documentação relacionada:**
- [AsyncOpenMeteoRepository](../infrastructure/OPENWEATHER_INTEGRATION.md)
- [Cache Strategy](../infrastructure/DYNAMODB_CACHE.md)
- [Testing Guide](../development/TESTING.md)
