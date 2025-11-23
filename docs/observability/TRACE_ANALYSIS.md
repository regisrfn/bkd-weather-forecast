# 📊 Análise de Traces - Guia de Uso

## Visão Geral

Este documento explica como usar o sistema de análise de traces para monitorar a performance da aplicação através dos decorators `@trace_operation`.

## Arquitetura de Tracing

### Decorators Aplicados

Nossa aplicação usa o decorator `@trace_operation` em dois níveis:

#### 1. **API Layer** (Lambda Handler)
Rastreia as requisições HTTP recebidas:

```python
# lambda/infrastructure/adapters/input/lambda_handler.py

@app.get("/api/cities/neighbors/<city_id>")
@trace_operation("api_get_neighbors")
def get_neighbors_route(city_id: str):
    # Rastreia tempo total da requisição HTTP
    pass

@app.get("/weather/<city_id>")
@trace_operation("api_get_city_weather")
def get_city_weather_route(city_id: str):
    # Rastreia tempo total da requisição HTTP
    pass

@app.post("/api/weather/regional")
@trace_operation("api_post_regional_weather")
def post_regional_weather_route():
    # Rastreia tempo total da requisição HTTP
    pass
```

#### 2. **Use Case Layer**
Rastreia a execução da lógica de negócio:

```python
# lambda/application/use_cases/

class GetNeighborCitiesUseCase:
    @trace_operation("use_case_get_neighbors")
    def execute(self, center_city_id: str, radius: float):
        # Rastreia tempo de execução do caso de uso
        pass

class GetCityWeatherUseCase:
    @trace_operation("use_case_get_city_weather")
    def execute(self, city_id: str, target_datetime: Optional[datetime]):
        # Rastreia tempo de execução do caso de uso
        pass

class GetRegionalWeatherUseCase:
    @trace_operation("use_case_get_regional_weather")
    def execute(self, city_ids: List[str], target_datetime: Optional[datetime]):
        # Rastreia tempo de execução do caso de uso
        pass
```

### Como Funciona

1. **Decorator adiciona span_name ao contexto do logger**
   ```python
   @trace_operation("span_name")
   def my_function():
       logger.info("Processing...")  # Este log terá span_name="span_name"
   ```

2. **Logs são enviados ao CloudWatch com metadata**
   - `trace_id`: Identificador único do request
   - `span_name`: Nome da operação (do decorator)
   - `timestamp`: Timestamp do log
   - `message`: Mensagem do log
   - `level`: Nível do log (INFO, ERROR, etc)

3. **Platform de Observabilidade ingere e indexa**
   - Logs são coletados do CloudWatch
   - Armazenados no DynamoDB
   - Disponibilizados via API REST

## Gerando Relatório de Análise

### Modo Automático (Recomendado)

O script busca automaticamente os logs dos **últimos 15 minutos**:

```bash
# Buscar logs e gerar relatório
python3 scripts/analyze_traces.py

# Ou explicitamente usando API
python3 scripts/analyze_traces.py --api
```

**Saída:**
- Relatório: `trace_analysis_YYYYMMDD_HHMMSS.md`
- Logs são buscados automaticamente da API
- Não é necessário baixar manualmente

**Configuração:**
Para alterar a janela de tempo, edite o script:
```python
# scripts/analyze_traces.py
TIME_WINDOW_MINUTES = 15  # Altere para 5, 30, 60, etc.
```

### Modo Manual (Arquivo)

Use arquivo JSON pré-baixado:

```bash
# 1. Baixar logs manualmente
NOW=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
START=$(date -u -d '1 hour ago' +'%Y-%m-%dT%H:%M:%SZ')

curl -s "https://szcszohdub.execute-api.sa-east-1.amazonaws.com/dev/logs/query?service_name=api-lambda-weather-forecast&start_time=$START&end_time=$NOW&limit=1000" \
  | jq '.' > logs.json

# 2. Processar arquivo
python3 scripts/analyze_traces.py logs.json
```

**Saída:**
- Relatório: `logs_analysis.md` (mesmo nome do arquivo JSON)

## Estrutura do Relatório

### 📊 Overview
Estatísticas gerais:
- Total de logs processados
- Total de traces identificados
- Total de spans detectados
- Média de logs por trace

### 🎯 Análise de Spans (@trace_operation)

#### Tabela de Performance
| Span | Execuções | Traces | Média (ms) | Min (ms) | Max (ms) | Total (ms) |
|------|-----------|--------|------------|----------|----------|------------|
| `api_get_city_weather` | 5 | 6 | 89.80 | 41.00 | 180.00 | 449.00 |
| `api_post_regional_weather` | 2 | 3 | 329.00 | 234.00 | 424.00 | 658.00 |

**Colunas:**
- **Execuções**: Número de vezes que o span executou (com múltiplos logs)
- **Traces**: Número de traces únicos que contêm este span
- **Média**: Tempo médio de execução (primeiro → último log do span)
- **Min/Max**: Tempo mínimo e máximo de execução
- **Total**: Tempo total acumulado

#### Detalhes por Span
Para cada span:
- Total de logs gerados
- Estatísticas de performance
- Exemplos de mensagens de log

### 🔄 Traces Detalhados
Os 10 traces com mais logs, mostrando:
- ID do trace
- Duração total
- Spans envolvidos
- Timeline completa com timestamps

## Métricas de Performance

### API Layer (api_*)
Mede o tempo total da requisição HTTP, incluindo:
- Validação de parâmetros
- Execução do use case
- Serialização da resposta
- Overhead do API Gateway

**Exemplo:**
```
api_get_neighbors: 72ms
├─ Validação: ~5ms
├─ use_case_get_neighbors: 60ms
└─ Resposta: ~7ms
```

### Use Case Layer (use_case_*)
Mede apenas a lógica de negócio:
- Busca no repositório
- Cálculos e transformações
- Chamadas externas (API OpenWeather)

**Exemplo:**
```
use_case_get_neighbors: 60ms
├─ Busca cidade: ~10ms
├─ Busca todas cidades: ~15ms
├─ Cálculo distâncias: ~30ms
└─ Ordenação: ~5ms
```

## Interpretando os Resultados

### 🟢 Performance Boa
- `api_get_neighbors`: < 100ms
- `api_get_city_weather`: < 150ms
- `use_case_*`: < 80% do tempo da API

### 🟡 Performance Aceitável
- `api_get_neighbors`: 100-200ms
- `api_get_city_weather`: 150-300ms
- `use_case_*`: 80-90% do tempo da API

### 🔴 Performance Ruim
- `api_get_neighbors`: > 200ms
- `api_get_city_weather`: > 300ms
- `use_case_*`: > 90% do tempo da API
- `api_post_regional_weather`: > 1000ms

## Troubleshooting

### Span não aparece no relatório

**Problema**: Decorator aplicado mas span não aparece na análise.

**Verificações:**
1. Deploy foi executado após adicionar decorator?
   ```bash
   cd /path/to/bkd-weather-forecast
   bash scripts/deploy-main.sh
   ```

2. Logs foram gerados após deploy?
   ```bash
   # Fazer requisição de teste
   curl "https://API_URL/weather/3543204"
   
   # Aguardar 30s para ingestão
   sleep 30
   
   # Verificar se span_name está presente
   curl "https://OBSERVABILITY_URL/logs/query?..." | jq '.logs[0].span_name'
   ```

3. Janela de tempo do query inclui os logs?
   ```bash
   # Use janela mais ampla
   START=$(date -u -d '2 hours ago' +'%Y-%m-%dT%H:%M:%SZ')
   ```

### Duração sempre 0ms

**Problema**: Span aparece mas com duração 0ms.

**Causa**: Span tem apenas 1 log (necessário 2+ para calcular duração).

**Solução**: Adicionar pelo menos 2 logs no escopo do decorator:
```python
@trace_operation("my_span")
def my_function():
    logger.info("Starting operation")  # Log 1
    # ... processamento ...
    logger.info("Operation completed")  # Log 2
```

### Múltiplas execuções mas poucos traces

**Problema**: Span tem muitas execuções mas poucos traces únicos.

**Causa**: Múltiplos spans no mesmo trace (ex: api_* e use_case_* no mesmo request).

**Esperado**: 
- 1 request = 1 trace
- 1 trace pode ter múltiplos spans
- Exemplo: trace com `api_get_neighbors` + `use_case_get_neighbors`

## Monitoramento Contínuo

### Script Automatizado

Criar cronjob para gerar relatórios periódicos:

```bash
#!/bin/bash
# scripts/daily_trace_report.sh

REPORT_DIR="./reports/traces"
mkdir -p "$REPORT_DIR"

DATE=$(date +'%Y-%m-%d')
NOW=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
START=$(date -u -d '24 hours ago' +'%Y-%m-%dT%H:%M:%SZ')

# Baixar logs
curl -s "https://szcszohdub.execute-api.sa-east-1.amazonaws.com/dev/logs/query?service_name=api-lambda-weather-forecast&start_time=$START&end_time=$NOW&limit=10000" \
  | jq '.' > "$REPORT_DIR/logs_$DATE.json"

# Gerar relatório
sed -i "s|input_file = .*|input_file = '$REPORT_DIR/logs_$DATE.json'|" scripts/analyze_traces.py
sed -i "s|output_file = .*|output_file = '$REPORT_DIR/report_$DATE.md'|" scripts/analyze_traces.py

python3 scripts/analyze_traces.py

echo "✅ Relatório gerado: $REPORT_DIR/report_$DATE.md"
```

### Alertas de Performance

Criar alertas baseados nos SLOs:

```python
# scripts/performance_alerts.py
import json

with open('trace_analysis.json', 'r') as f:
    stats = json.load(f)

THRESHOLDS = {
    'api_get_neighbors': 200,      # ms
    'api_get_city_weather': 300,   # ms
    'api_post_regional_weather': 1000,
}

for span, threshold in THRESHOLDS.items():
    if span in stats and stats[span]['avg'] > threshold:
        print(f"⚠️  ALERTA: {span} acima do SLO!")
        print(f"   Média: {stats[span]['avg']:.2f}ms (limite: {threshold}ms)")
```

## Próximos Passos

1. **Adicionar mais spans**
   - Repository layer (db queries)
   - External API calls (OpenWeather)
   - Cache operations (DynamoDB)

2. **Dashboard visual**
   - Gráficos de tendência
   - Distribuição de latências (P50, P95, P99)
   - Comparação entre spans

3. **Integração com CI/CD**
   - Validar performance em cada deploy
   - Falhar build se degradação > 20%
   - Gerar relatório automático em PRs

## Referências

- [DynamoDB Architecture](./DYNAMODB_ARCHITECTURE.md)
- [Shared Tracing Library](../../lambda/shared/tracing.py)
- [Observability API](https://szcszohdub.execute-api.sa-east-1.amazonaws.com/dev)
- [Relatório Exemplo](./TRACE_ANALYSIS_REPORT.md)
