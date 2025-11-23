# 🔍 Análise de Traces - Observability Platform

**Gerado em:** 2025-11-23 01:34:52

## 📊 Overview

- **Total de logs:** 49
- **Total de traces:** 28
- **Total de spans:** 4
- **Média de logs/trace:** 1.8

## 🎯 Análise de Spans (@trace_operation)

### Performance por Span

| Span | Execuções | Traces | Média (ms) | Min (ms) | Max (ms) | Total (ms) |
|------|-----------|--------|------------|----------|----------|------------|
| `api_get_city_weather` | 5 | 6 | 89.80 | 41.00 | 180.00 | 449.00 |
| `api_post_regional_weather` | 2 | 3 | 329.00 | 234.00 | 424.00 | 658.00 |

### Detalhes por Span

#### 📍 api_get_city_weather

**Total de logs:** 11
**Execuções:** 5
**Performance:** 89.80ms (min: 41.00ms, max: 180.00ms)

**Mensagens:**
- [04:31:11] Dados climáticos de Ribeirão do Sul: 23.16°C, probabilidade de chuva: 0.0%
- [04:31:11] Buscando dados climáticos de 3543204
- [04:31:11] Dados climáticos de Ribeirão do Sul: 23.18°C, probabilidade de chuva: 0.0%
- [04:31:10] Buscando dados climáticos de INVALID_ID
- [04:31:09] Dados climáticos de Ribeirão do Sul: 26.17°C, probabilidade de chuva: 24.0%
- _(e mais 1 logs...)_

#### 📍 api_get_neighbors

**Total de logs:** 3

**Mensagens:**
- [04:31:22] Buscando vizinhos de 3550308
- [04:31:08] Buscando vizinhos de 3543204

#### 📍 api_post_regional_weather

**Total de logs:** 5
**Execuções:** 2
**Performance:** 329.00ms (min: 234.00ms, max: 424.00ms)

**Mensagens:**
- [04:31:10] Buscando dados climáticos regionais
- [04:31:10] Dados climáticos regionais: 3 cidades

#### 📍 use_case_get_neighbors

**Total de logs:** 3

**Mensagens:**
- [04:31:22] Encontradas 41 cidades vizinhas de São Paulo
- [04:31:08] Encontradas 21 cidades vizinhas de Ribeirão do Sul
- [04:31:08] Encontradas 0 cidades vizinhas de Ribeirão do Sul

## 🔄 Traces Detalhados

_Mostrando os primeiros 10 traces com mais logs_

### Trace #1: `efd89b2d-8a0...`
**Duração total:** 72.00ms | **Logs:** 2

**Spans:** `api_get_neighbors`, `use_case_get_neighbors`

**Timeline:**
1. [04:31:22.253] **[api_get_neighbors]** INFO: Buscando vizinhos de 3550308
2. [04:31:22.325] **[use_case_get_neighbors]** INFO: Encontradas 41 cidades vizinhas de São Paulo

### Trace #2: `ff0280b6-a2d...`
**Duração total:** 50.00ms | **Logs:** 2

**Spans:** `api_get_city_weather`

**Timeline:**
1. [04:31:11.214] **[api_get_city_weather]** INFO: Buscando dados climáticos de 3543204
2. [04:31:11.264] **[api_get_city_weather]** INFO: Dados climáticos de Ribeirão do Sul: 23.16°C, probabilidade de chuva: 0.0%

### Trace #3: `9e68910e-293...`
**Duração total:** 45.00ms | **Logs:** 2

**Spans:** `api_get_city_weather`

**Timeline:**
1. [04:31:11.019] **[api_get_city_weather]** INFO: Buscando dados climáticos de 3543204
2. [04:31:11.064] **[api_get_city_weather]** INFO: Dados climáticos de Ribeirão do Sul: 23.18°C, probabilidade de chuva: 0.0%

### Trace #4: `c2c4ff01-15c...`
**Duração total:** 41.00ms | **Logs:** 2

**Spans:** `api_get_city_weather`

**Timeline:**
1. [04:31:10.845] **[api_get_city_weather]** INFO: Buscando dados climáticos de 3543204
2. [04:31:10.886] **[api_get_city_weather]** INFO: Dados climáticos de Ribeirão do Sul: 23.18°C, probabilidade de chuva: 0.0%

### Trace #5: `9883b8c9-4b1...`
**Duração total:** 234.00ms | **Logs:** 2

**Spans:** `api_post_regional_weather`

**Timeline:**
1. [04:31:10.151] **[api_post_regional_weather]** INFO: Buscando dados climáticos regionais
2. [04:31:10.385] **[api_post_regional_weather]** INFO: Dados climáticos regionais: 3 cidades

### Trace #6: `d0417a36-674...`
**Duração total:** 424.00ms | **Logs:** 2

**Spans:** `api_post_regional_weather`

**Timeline:**
1. [04:31:09.461] **[api_post_regional_weather]** INFO: Buscando dados climáticos regionais
2. [04:31:09.885] **[api_post_regional_weather]** INFO: Dados climáticos regionais: 3 cidades

### Trace #7: `707d6b51-bc8...`
**Duração total:** 133.00ms | **Logs:** 2

**Spans:** `api_get_city_weather`

**Timeline:**
1. [04:31:09.053] **[api_get_city_weather]** INFO: Buscando dados climáticos de 3543204
2. [04:31:09.186] **[api_get_city_weather]** INFO: Dados climáticos de Ribeirão do Sul: 26.17°C, probabilidade de chuva: 24.0%

### Trace #8: `e01c8cb5-e6d...`
**Duração total:** 180.00ms | **Logs:** 2

**Spans:** `api_get_city_weather`

**Timeline:**
1. [04:31:08.626] **[api_get_city_weather]** INFO: Buscando dados climáticos de 3543204
2. [04:31:08.806] **[api_get_city_weather]** INFO: Dados climáticos de Ribeirão do Sul: 23.16°C, probabilidade de chuva: 0.0%

### Trace #9: `7bee894a-f56...`
**Duração total:** 99.00ms | **Logs:** 2

**Spans:** `api_get_neighbors`, `use_case_get_neighbors`

**Timeline:**
1. [04:31:08.324] **[api_get_neighbors]** INFO: Buscando vizinhos de 3543204
2. [04:31:08.423] **[use_case_get_neighbors]** INFO: Encontradas 21 cidades vizinhas de Ribeirão do Sul

### Trace #10: `63103c5d-51d...`
**Duração total:** 104.00ms | **Logs:** 2

**Spans:** `api_get_neighbors`, `use_case_get_neighbors`

**Timeline:**
1. [04:31:08.040] **[api_get_neighbors]** INFO: Buscando vizinhos de 3543204
2. [04:31:08.144] **[use_case_get_neighbors]** INFO: Encontradas 0 cidades vizinhas de Ribeirão do Sul
