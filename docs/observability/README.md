# 📊 Observability - Documentação

Sistema de observabilidade customizado com rastreamento distribuído e análise de performance.

## 📚 Documentação Disponível

### [TRACE_ANALYSIS.md](./TRACE_ANALYSIS.md)
**Guia completo de análise de traces**

Como usar o sistema de rastreamento com decorators `@trace_operation`:
- ✅ Arquitetura de tracing (API Layer + Use Case Layer)
- ✅ Como gerar relatórios de performance
- ✅ Interpretação de métricas
- ✅ Troubleshooting
- ✅ Monitoramento contínuo
- ✅ Alertas de performance

### [TRACE_ANALYSIS_REPORT.md](./TRACE_ANALYSIS_REPORT.md)
**Exemplo de relatório gerado**

Relatório real com análise de traces coletados:
- 📊 Overview: 49 logs, 28 traces, 4 spans
- 🎯 Performance por Span:
  - `api_get_city_weather`: 89.80ms (min: 41ms, max: 180ms)
  - `api_post_regional_weather`: 329ms (min: 234ms, max: 424ms)
- 🔄 Traces detalhados com timeline completa

## 🚀 Quick Start

### 1. Coletar Logs
```bash
NOW=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
START=$(date -u -d '1 hour ago' +'%Y-%m-%dT%H:%M:%SZ')

curl -s "https://szcszohdub.execute-api.sa-east-1.amazonaws.com/dev/logs/query?service_name=api-lambda-weather-forecast&start_time=$START&end_time=$NOW&limit=1000" \
  | jq '.' > observability_logs.json
```

### 2. Gerar Relatório
```bash
python3 scripts/analyze_traces.py
```

### 3. Visualizar
```bash
cat trace_analysis.md
```

## 🎯 Spans Disponíveis

### API Layer
- `api_get_neighbors` - GET /api/cities/neighbors/:id
- `api_get_city_weather` - GET /weather/:id
- `api_post_regional_weather` - POST /api/weather/regional

### Use Case Layer
- `use_case_get_neighbors` - GetNeighborCitiesUseCase.execute()
- `use_case_get_city_weather` - GetCityWeatherUseCase.execute()
- `use_case_get_regional_weather` - GetRegionalWeatherUseCase.execute()

## 📈 Métricas Importantes

| Métrica | Descrição |
|---------|-----------|
| **Execuções** | Quantas vezes o span foi executado |
| **Média** | Tempo médio de execução (ms) |
| **Min/Max** | Tempo mínimo e máximo |
| **Traces** | Número de traces únicos |

## 🔗 Links Úteis

- **Observability API**: https://szcszohdub.execute-api.sa-east-1.amazonaws.com/dev
- **Weather API**: https://u8r56xdgog.execute-api.sa-east-1.amazonaws.com/dev
- **Shared Tracing Library**: [../../lambda/shared/tracing.py](../../lambda/shared/tracing.py)
- **Script de Análise**: [../../scripts/analyze_traces.py](../../scripts/analyze_traces.py)

## 📦 Arquivos

```
docs/observability/
├── README.md                      # Este arquivo
├── TRACE_ANALYSIS.md              # Guia completo
└── TRACE_ANALYSIS_REPORT.md       # Exemplo de relatório

scripts/
└── analyze_traces.py              # Script Python de análise

lambda/shared/
└── tracing.py                     # Biblioteca de tracing
```

## 🎓 Conceitos

### Trace
Um trace representa uma requisição completa, do início ao fim. Identificado por `trace_id`.

### Span
Um span representa uma operação dentro de um trace. Identificado por `span_name` (via `@trace_operation`).

### Exemplo
```
Trace: c2f12add-2937-...
├── Span: api_get_neighbors (72ms)
│   ├── Log: "Buscando vizinhos de 3550308"
│   └── Log: "Encontradas 41 cidades"
└── Span: use_case_get_neighbors (60ms)
    ├── Log: "Executando GetNeighborCitiesUseCase"
    └── Log: "Cálculo de distâncias concluído"
```

## 💡 Dicas

1. **Performance boa**: API < 150ms, Use Case < 80ms
2. **Use janela ampla**: Pelo menos 1 hora de logs
3. **Execute após mudanças**: Para validar impacto
4. **Compare relatórios**: Identificar regressões
5. **Monitore tendências**: Use scripts automatizados

## 🐛 Problemas Comuns

| Problema | Solução |
|----------|---------|
| Span não aparece | Verificar deploy e janela de tempo |
| Duração sempre 0ms | Adicionar mais logs no span |
| Poucos traces | Gerar mais requisições |
| Dados desatualizados | Aguardar 30s após requisição |

## 🔮 Roadmap

- [ ] Dashboard visual com gráficos
- [ ] Alertas automáticos de performance
- [ ] Comparação entre deploys
- [ ] Exportação para Grafana
- [ ] Percentis (P50, P95, P99)
- [ ] Rastreamento de erros por span

---

**Custo**: $0/mês (usando infraestrutura própria)
**Latência**: ~30s (ingestão CloudWatch → DynamoDB)
**Retenção**: 7 dias (configurável)
