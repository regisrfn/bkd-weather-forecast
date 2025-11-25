# 🚀 Guia de Teste de Performance da API

## 📊 Resultados Atuais (25/11/2025)

### ✅ Performance em Produção:

| Endpoint | Cenário | Latência Total | Latência/Cidade | Performance |
|----------|---------|----------------|-----------------|-------------|
| **Neighbors** | 1 cidade | 283-454ms | - | ✅ Ótimo |
| **Single Weather** | 10 cidades | 3.5s | 353ms/cidade | ⚠️ Lento (sequencial) |
| **Single Weather** | 100 cidades | 28.9s | 289ms/cidade | ⚠️ Muito lento |
| **Regional** | 10 cidades | 580ms | **58ms/cidade** | ✅ Excelente |
| **Regional** | 50 cidades | 1.3s | **27ms/cidade** | ✅ Excelente |
| **Regional** | 100 cidades | 2.4s | **24ms/cidade** | ✅ Excelente |

### 🎯 Destaques:
- ⚡ **Regional endpoint é 12.2x mais rápido** que chamadas individuais
- 🚀 **Cache DynamoDB otimizado**: ~20ms por operação
- 💪 **Processamento paralelo**: 100 cidades em apenas 2.4s (24ms/cidade)

---

## 🧪 Como Testar a API

### 1️⃣ Teste Completo (Todos os Endpoints)
```bash
# Executa todos os testes e salva baseline
python scripts/test_performance.py

# Resultado: Testa 9 cenários (neighbors, single, regional com 10/50/100 cidades)
```

### 2️⃣ Teste Específico por Endpoint
```bash
# Testar apenas endpoint regional
python scripts/test_performance.py --endpoint regional

# Testar apenas neighbors
python scripts/test_performance.py --endpoint neighbors

# Testar apenas single city
python scripts/test_performance.py --endpoint single
```

### 3️⃣ Teste Específico por Quantidade de Cidades
```bash
# Testar apenas com 100 cidades
python scripts/test_performance.py --scenario 100

# Testar apenas com 10 cidades
python scripts/test_performance.py --scenario 10
```

### 4️⃣ Comparar com Baseline (Detectar Regressões)
```bash
# Primeiro, rode um teste completo para salvar baseline
python scripts/test_performance.py

# Depois de fazer mudanças, compare:
python scripts/test_performance.py --compare

# Se houver regressão > 20%, o script retorna erro (exit code 1)
```

---

## 📈 Visualizar Resultados Salvos

### Ver Último Baseline
```bash
cat output/performance_baseline_*.json | tail -1 | python -m json.tool
```

### Comparar Dois Baselines
```bash
# Lista todos os baselines
ls -lht output/performance_baseline_*.json

# Ver específico
cat output/performance_baseline_20251125_140641.json | python -m json.tool
```

---

## 🔍 Teste Manual com cURL

### 1. Neighbors Endpoint
```bash
API_URL=$(cat API_URL.txt)
curl -X GET "$API_URL/api/cities/neighbors/3531803?radius=50" \
  -H "Accept: application/json" \
  -w "\nTime: %{time_total}s\n"
```

### 2. Single Weather Endpoint
```bash
API_URL=$(cat API_URL.txt)
curl -X GET "$API_URL/api/weather/city/3531803" \
  -H "Accept: application/json" \
  -w "\nTime: %{time_total}s\n"
```

### 3. Regional Weather Endpoint (10 cidades)
```bash
API_URL=$(cat API_URL.txt)
curl -X POST "$API_URL/api/weather/regional" \
  -H "Content-Type: application/json" \
  -d '{"cityIds": ["3531803", "3513009", "3509502", "3550308", "3554003", "3547304", "3552205", "3552403", "3505708", "3522208"]}' \
  -w "\nTime: %{time_total}s\n"
```

### 4. Regional Weather Endpoint (100 cidades) - Performance Test
```bash
API_URL=$(cat API_URL.txt)

# Carregar 100 IDs de teste
CITY_IDS=$(python3 -c "
import json
with open('lambda/data/test_100_municipalities.json', 'r') as f:
    data = json.load(f)
    ids = [m['id'] for m in data[:100]]
    print(json.dumps({'cityIds': ids}))
")

# Executar request
curl -X POST "$API_URL/api/weather/regional" \
  -H "Content-Type: application/json" \
  -d "$CITY_IDS" \
  -w "\nTime: %{time_total}s\n" \
  -o /tmp/regional_response.json

# Ver estatísticas
echo "Cidades retornadas: $(cat /tmp/regional_response.json | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')"
```

---

## 📊 Monitoramento em Produção

### CloudWatch Logs
```bash
# Ver logs da Lambda
aws logs tail /aws/lambda/weather-forecast-lambda --follow

# Filtrar por métricas de cache
aws logs tail /aws/lambda/weather-forecast-lambda --follow | grep "Cache HIT\|Cache MISS"

# Ver latências
aws logs tail /aws/lambda/weather-forecast-lambda --follow | grep "latency_ms"
```

### Métricas CloudWatch
```bash
# Ver invocações Lambda (últimas 6 horas)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=weather-forecast-lambda \
  --start-time $(date -u -d '6 hours ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum

# Ver duração média (últimas 6 horas)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=weather-forecast-lambda \
  --start-time $(date -u -d '6 hours ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Average,Maximum
```

---

## 🎯 Metas de Performance

### Latências Alvo:
- ✅ **Cache DynamoDB**: < 30ms por operação (atual: ~20ms)
- ✅ **Regional 100 cidades**: < 3s total (atual: 2.4s = 24ms/cidade)
- ✅ **Neighbors**: < 500ms (atual: ~370ms média)
- ⚠️ **Single weather**: < 200ms por cidade (atual: ~290-350ms)

### Throughput:
- ✅ **Regional paralelo**: ~42 cidades/segundo (100 em 2.4s)
- ⚠️ **Single sequencial**: ~3 cidades/segundo (100 em 28.9s)

---

## 🔧 Troubleshooting

### API Não Responde
```bash
# Verificar se URL está correta
cat API_URL.txt

# Testar conectividade básica
curl -I $(cat API_URL.txt)/api/health

# Ver status da Lambda
aws lambda get-function --function-name weather-forecast-lambda
```

### Performance Degradada
```bash
# 1. Testar cache DynamoDB
export CACHE_TABLE_NAME="weather-forecast-cache-prod"
python scripts/analyze_cache_performance.py

# 2. Verificar cold starts no CloudWatch
aws logs filter-log-events \
  --log-group-name /aws/lambda/weather-forecast-lambda \
  --filter-pattern "INIT_START" \
  --start-time $(date -u -d '1 hour ago' +%s)000

# 3. Verificar erros de conexão
aws logs filter-log-events \
  --log-group-name /aws/lambda/weather-forecast-lambda \
  --filter-pattern "error" \
  --start-time $(date -u -d '1 hour ago' +%s)000
```

### Cache Hit Rate Baixo
```bash
# Verificar cache hits/misses
aws logs filter-log-events \
  --log-group-name /aws/lambda/weather-forecast-lambda \
  --filter-pattern "Cache HIT" \
  --start-time $(date -u -d '1 hour ago' +%s)000 | grep -c "Cache HIT"

aws logs filter-log-events \
  --log-group-name /aws/lambda/weather-forecast-lambda \
  --filter-pattern "Cache MISS" \
  --start-time $(date -u -d '1 hour ago' +%s)000 | grep -c "Cache MISS"
```

---

## 📝 Interpreting Results

### ✅ Bom:
- Latência < 30ms para cache
- Regional < 50ms/cidade
- Taxa de sucesso 100%
- Cache hit rate > 80%

### ⚠️ Atenção:
- Latência 30-100ms para cache
- Regional 50-100ms/cidade
- Taxa de sucesso 90-99%
- Cache hit rate 50-80%

### 🔴 Problema:
- Latência > 100ms para cache
- Regional > 100ms/cidade
- Taxa de sucesso < 90%
- Cache hit rate < 50%

---

## 🚀 Próximos Passos

Para melhorar ainda mais a performance:

1. **Ativar DAX (DynamoDB Accelerator)** - reduzir cache latency para < 1ms
2. **Implementar ElastiCache Redis** - cache em memória compartilhado
3. **Aumentar timeout de cache** - atualmente 3h, considerar 6-12h
4. **API Gateway caching** - cache de respostas HTTP (5min-1h)
5. **CloudFront CDN** - distribuição global e edge caching

---

**Última atualização**: 25/11/2025  
**Versão API**: v1.0  
**Lambda**: weather-forecast-lambda  
**Região**: sa-east-1
