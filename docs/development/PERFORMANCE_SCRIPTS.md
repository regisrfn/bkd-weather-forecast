# Performance Testing Scripts

## Visão Geral

Scripts para testes de performance da Weather Forecast API, com foco em medir a eficiência da implementação assíncrona e do cache DynamoDB.

**Localização:** `/scripts`

---

## Scripts Ativos

### 1. `test_async_performance.py` - Teste de Performance Assíncrono

Script principal para medir performance do sistema com 100 cidades simultâneas.

**Uso:**
```bash
cd lambda
pytest tests/performance/test_async_performance.py -v -s
```

**O que testa:**
- ✅ Busca assíncrona de 100 cidades simultâneas
- ✅ Cache DynamoDB (hit rate)
- ✅ Latência média por requisição
- ✅ Throughput total

**Exemplo de output:**
```
Test Async Performance - 100 Cities
====================================
Cities tested: 100
Total time: 1.834s
Average time per city: 0.018s
Fastest: 0.003s
Slowest: 0.287s

Cache Performance:
------------------
Cache hits: 89/100 (89.00%)
Cache misses: 11/100 (11.00%)

Throughput:
-----------
Cities/second: 54.53
```

**Métricas principais:**
- **Total time:** Tempo total para processar 100 cidades (~1.8s)
- **Average time:** Tempo médio por cidade (~0.018s)
- **Cache hit rate:** % de requisições atendidas pelo cache (~89%)
- **Throughput:** Requisições por segundo (~54 cities/s)

---

### 2. `performance_test_100_cities.py` - Teste HTTP da API

Script para testar a API via HTTP com 100 cidades reais.

**Uso:**
```bash
# Via pytest
pytest scripts/performance_test_100_cities.py -v -s

# Via Python direto
python scripts/performance_test_100_cities.py
```

**O que testa:**
- ✅ API Gateway + Lambda E2E
- ✅ 100 requisições HTTP reais
- ✅ Latência fim-a-fim (com overhead de rede)
- ✅ Taxa de sucesso

**Exemplo de output:**
```
Testing API: https://xxxxx.execute-api.sa-east-1.amazonaws.com/prod

Testing 100 cities via HTTP...
Progress: [####################] 100/100

Results:
========
Total time: 15.234s
Successful requests: 100/100 (100.00%)
Failed requests: 0/100 (0.00%)
Average latency: 0.152s
Min latency: 0.089s
Max latency: 1.234s
Requests/second: 6.56
```

**Diferenças em relação ao test_async_performance.py:**
- ❌ **Não usa cache local** (testa cache do DynamoDB real)
- ✅ **Mede latência real** (incluindo rede, API Gateway, cold starts)
- ✅ **Testa infraestrutura completa** (não apenas código)

---

## Comparação: Threads vs Async

### Histórico de Performance

#### Sistema Anterior (Threads)
```python
# Implementação com ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=100) as executor:
    futures = [executor.submit(get_weather, city_id) for city_id in cities]
    results = [future.result() for future in futures]
```

**Resultados:**
- ⏱️ Tempo total: **180 segundos**
- 📊 Throughput: **0.55 cities/s**
- 💾 Overhead de threads: Alto
- 🔥 Uso de CPU: 100%

#### Sistema Atual (Async)
```python
# Implementação com asyncio
tasks = [get_weather_async(city_id) for city_id in cities]
results = await asyncio.gather(*tasks)
```

**Resultados:**
- ⏱️ Tempo total: **1.8 segundos**
- 📊 Throughput: **54.5 cities/s**
- 💾 Overhead: Mínimo
- 🔥 Uso de CPU: 15%

**Melhoria:** 🚀 **99% mais rápido** (180s → 1.8s)

---

## Estrutura dos Testes

### Organização

```
lambda/tests/performance/
├── __init__.py
├── test_async_performance.py    # Teste principal (100 cidades)
└── conftest.py                   # Fixtures compartilhadas

scripts/
└── performance_test_100_cities.py   # Teste HTTP da API
```

### Fixtures Compartilhadas

```python
# conftest.py
@pytest.fixture
def sample_city_ids():
    """100 city IDs para testes de performance"""
    return [
        3543402,  # Ribeirão Preto
        3543204,  # Ribeirão Bonito
        # ... mais 98 cidades
    ]

@pytest.fixture
async def weather_service():
    """Serviço configurado para performance tests"""
    service = AsyncWeatherService()
    yield service
    await service.cleanup()
```

---

## Métricas Detalhadas

### Cache Performance

**Medições:**
- **Cache hit rate:** Percentual de requisições atendidas pelo cache
- **Cache miss rate:** Percentual de requisições que precisaram consultar a API externa
- **TTL effectiveness:** Taxa de reuso antes da expiração (3 horas)

**Exemplo:**
```python
Cache Performance:
------------------
Cache hits: 89/100 (89.00%)    # ✅ Servido pelo DynamoDB
Cache misses: 11/100 (11.00%)  # 🔄 Consultou OpenWeather API
Average cache latency: 0.003s
Average API latency: 0.287s
```

**Interpretação:**
- **>80% hit rate:** ✅ Cache funcionando bem
- **<50% hit rate:** ⚠️ Investigar TTL ou padrão de acesso
- **0% hit rate:** ❌ Cache não está funcionando

### Latency Distribution

**P50, P90, P99:**
```python
Latency Distribution:
---------------------
P50 (median): 0.015s    # 50% das requisições
P90: 0.045s             # 90% das requisições
P99: 0.287s             # 99% das requisições
Max: 0.287s             # Pior caso
```

**Análise:**
- **P50 baixo (0.015s):** ✅ Cache funcionando (hit)
- **P99 alto (0.287s):** ⚠️ Cold start ou cache miss
- **Max >> P99:** Possível outlier (timeout, throttling)

### Throughput

**Cálculo:**
```python
throughput = total_cities / total_time_seconds
# 100 cidades / 1.834s = 54.53 cities/s
```

**Benchmarks:**
- **>50 cities/s:** ✅ Performance excelente
- **20-50 cities/s:** ✅ Performance boa
- **<20 cities/s:** ⚠️ Investigar gargalos

---

## Diagnóstico e Troubleshooting

### Cenário 1: Cache Hit Rate Baixo (<50%)

**Sintomas:**
```
Cache hits: 23/100 (23.00%)
Average time: 0.250s
```

**Possíveis causas:**
1. TTL muito curto (3 horas)
2. Primeiro acesso às cidades
3. Cache recém-limpo

**Soluções:**
```python
# 1. Aumentar TTL
CACHE_TTL_HOURS = 6  # De 3 para 6 horas

# 2. Warm-up do cache
await warm_up_cache(popular_cities)

# 3. Verificar se DynamoDB está acessível
```

### Cenário 2: Latência Alta (>0.5s avg)

**Sintomas:**
```
Average time: 0.872s
P90: 1.234s
Throughput: 8.5 cities/s
```

**Possíveis causas:**
1. Cold start do Lambda
2. Throttling do DynamoDB
3. Rate limiting da OpenWeather API
4. Timeout de conexão

**Soluções:**
```python
# 1. Provisioned concurrency (evitar cold starts)
resource "aws_lambda_provisioned_concurrency_config" "example" {
  function_name = aws_lambda_function.main.function_name
  provisioned_concurrent_executions = 2
}

# 2. Aumentar DynamoDB capacity
read_capacity  = 10  # Aumentar de 5 para 10
write_capacity = 5

# 3. Implementar retry com backoff
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def fetch_weather(city_id):
    ...
```

### Cenário 3: Falhas Intermitentes

**Sintomas:**
```
Successful: 87/100 (87.00%)
Failed: 13/100 (13.00%)
Errors: TimeoutError, ConnectionError
```

**Possíveis causas:**
1. Timeout muito curto
2. Limite de conexões simultâneas
3. Throttling da API externa

**Soluções:**
```python
# 1. Aumentar timeout
timeout = aiohttp.ClientTimeout(total=30)

# 2. Limitar concorrência
semaphore = asyncio.Semaphore(50)  # Máx 50 requisições simultâneas

# 3. Implementar circuit breaker
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def fetch_weather(city_id):
    ...
```

---

## Monitoramento Contínuo

### CloudWatch Metrics

**Métricas importantes:**
```bash
# Latência do Lambda
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=weather-forecast-api \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T23:59:59Z \
  --period 3600 \
  --statistics Average,Maximum

# DynamoDB consumed capacity
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedReadCapacityUnits \
  --dimensions Name=TableName,Value=weather-cache \
  --period 300 \
  --statistics Sum
```

### Alarmes CloudWatch

**Exemplo de configuração:**
```hcl
resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "weather-api-high-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Average"
  threshold           = 500  # 500ms
  alarm_description   = "Lambda latency above 500ms"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
```

---

## Scripts Legados (Referência)

### `test_aws_parallelism.py` [DEPRECATED]

Script antigo para diagnóstico de paralelismo no AWS.

**Por que foi descontinuado:**
- ❌ Usava `concurrent.futures` (threads)
- ❌ Performance 99% pior que async
- ❌ Alto overhead de CPU e memória

**Migração para async:**
```python
# ANTES (threads)
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(fetch, city) for city in cities]
    results = [f.result() for f in futures]

# DEPOIS (async)
tasks = [fetch_async(city) for city in cities]
results = await asyncio.gather(*tasks)
```

**Resultado:** Redução de 180s para 1.8s 🚀

---

## Boas Práticas

### ✅ DO

1. **Sempre rodar testes localmente antes do deploy**
   ```bash
   pytest tests/performance/test_async_performance.py -v
   ```

2. **Monitorar cache hit rate em produção**
   ```python
   # Target: >80% hit rate
   cache_hits / total_requests >= 0.80
   ```

3. **Estabelecer baselines de performance**
   ```bash
   # Salvar baseline
   pytest tests/performance/ --benchmark-save=baseline
   
   # Comparar com baseline
   pytest tests/performance/ --benchmark-compare=baseline
   ```

4. **Testar com dados reais**
   ```python
   # Usar IDs de cidades reais do municipalities_db.json
   sample_cities = random.sample(all_cities, 100)
   ```

### ❌ DON'T

1. **❌ Não rodar performance tests em CI/CD**
   ```yaml
   # Apenas smoke tests no CI
   pytest tests/unit/ tests/integration/ -v
   ```

2. **❌ Não testar com API key inválida**
   ```python
   # Sempre validar configuração antes
   assert os.getenv("OPENWEATHER_API_KEY"), "API key required"
   ```

3. **❌ Não ignorar falhas intermitentes**
   ```python
   # Investigar mesmo que seja 1% de falha
   assert success_rate >= 0.99, "Too many failures"
   ```

---

## Referências

- **Testing Guide:** [TESTING.md](TESTING.md)
- **Async Operations:** [../infrastructure/ASYNC_OPERATIONS.md](../infrastructure/ASYNC_OPERATIONS.md)
- **DynamoDB Cache:** [../infrastructure/DYNAMODB_CACHE.md](../infrastructure/DYNAMODB_CACHE.md)

📊 **Benchmarks históricos:** `/output/test_baseline_*.json`
