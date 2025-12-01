# Weather Forecast API ☁️

API Backend em Python para previsões meteorológicas com **Clean Architecture** e **100% async** rodando em AWS Lambda.

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![AWS Lambda](https://img.shields.io/badge/AWS-Lambda-orange.svg)](https://aws.amazon.com/lambda/)
[![Architecture](https://img.shields.io/badge/Architecture-Clean-green.svg)](docs/architecture/CLEAN_ARCHITECTURE_DETAILED.md)
[![Async](https://img.shields.io/badge/100%25-Async-purple.svg)](docs/infrastructure/ASYNC_OPERATIONS.md)
[![Tests](https://img.shields.io/badge/Tests-37%2F37-success.svg)](docs/development/TESTING.md)

## 🚀 Quick Start

```bash
# 1. Setup
source .venv/bin/activate
pip install -r lambda/requirements.txt

# 2. Configurar .env
cp .env.example .env
nano .env  # Adicionar OPENWEATHER_API_KEY

# 3. Executar testes
pytest lambda/tests/ -v

# 4. Deploy
bash scripts/deploy-main.sh
```

## 📡 API Endpoints

**Documentação completa:** [API Routes](docs/api/ROUTES.md) | [Alertas Meteorológicos](docs/api/WEATHER_ALERTS.md)

### 1. GET `/api/cities/neighbors/{cityId}?radius=50`
Busca cidades vizinhas dentro de um raio (1-500km).

```bash
curl "https://api.example.com/api/cities/neighbors/3543204?radius=50"
```

<details>
<summary>Ver resposta</summary>

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
      "distance": 17.8
    }
  ]
}
```
</details>

### 2. GET `/api/weather/city/{cityId}`
Previsão meteorológica de uma cidade.

```bash
# Próxima previsão disponível
curl "https://api.example.com/api/weather/city/3543204"

# Previsão para data/hora específica
curl "https://api.example.com/api/weather/city/3543204?date=2025-11-26&time=15:00"
```

<details>
<summary>Ver resposta</summary>

```json
{
  "cityId": "3543204",
  "cityName": "Ribeirão do Sul",
  "timestamp": "2025-11-26T15:00:00-03:00",
  "temperature": 28.3,
  "humidity": 65.0,
  "windSpeed": 12.5,
  "rainfallIntensity": 35.5,
  "weatherAlert": [
    {
      "code": "MODERATE_RAIN",
      "severity": "warning",
      "description": "🌧️ Chuva moderada",
      "timestamp": "2025-11-26T18:00:00-03:00",
      "details": {
        "rain_mm_h": 15.5
      }
    }
  ],
  "tempMin": 18.5,
  "tempMax": 32.1
}
```

**Alertas Meteorológicos:**

A API inclui alertas climáticos estruturados baseados nas previsões dos próximos 5 dias:

| Categoria | Códigos | Exemplos |
|-----------|---------|----------|
| 🌧️ **Precipitação** | `DRIZZLE`, `LIGHT_RAIN`, `MODERATE_RAIN`, `HEAVY_RAIN` | Baseados em mm/h |
| ⛈️ **Tempestade** | `STORM`, `STORM_RAIN` | Raios e chuva intensa |
| 💨 **Vento** | `MODERATE_WIND`, `STRONG_WIND` | 30+ km/h e 50+ km/h |
| 🌡️ **Temperatura** | `COLD`, `VERY_COLD`, `TEMP_DROP`, `TEMP_RISE` | Frio e variações |
| ❄️ **Neve** | `SNOW` | Raro no Brasil |

Ver [documentação completa de alertas](docs/api/ROUTES.md#alertas-meteorológicos) para todos os códigos, limiares e exemplos.

</details>

### 3. POST `/api/weather/regional`
Previsão para múltiplas cidades em paralelo (até 100 cidades, P99 <200ms).

```bash
curl -X POST "https://api.example.com/api/weather/regional" \
  -H "Content-Type: application/json" \
  -d '{"cityIds": ["3543204", "3548708", "3509502"]}'
```

<details>
<summary>Ver resposta</summary>

```json
[
  {
    "cityId": "3543204",
    "cityName": "Ribeirão do Sul",
    "temperature": 28.3,
    "humidity": 65.0,
    "rainfallIntensity": 35.5
  },
  {
    "cityId": "3548708",
    "cityName": "São Carlos",
    "temperature": 27.1,
    "humidity": 58.0,
    "rainfallIntensity": 20.0
  }
]
```
</details>

## 🏗️ Arquitetura

### Clean Architecture (Hexagonal)

```
lambda/
├── domain/              # Entidades de negócio (City, Weather)
│   ├── entities/
│   └── exceptions.py
├── application/         # Casos de uso (100% async)
│   ├── ports/
│   └── use_cases/
├── infrastructure/      # Adapters (HTTP, DynamoDB, OpenWeather)
│   ├── adapters/
│   └── external/
└── shared/              # Utilitários compartilhados
    ├── config/
    └── utils/
```

**📖 Documentação detalhada:** [Clean Architecture Guide](docs/architecture/CLEAN_ARCHITECTURE_DETAILED.md)

### Stack Tecnológica

| Layer | Tecnologias |
|-------|------------|
| **Runtime** | Python 3.13, AWS Lambda (512MB) |
| **Framework** | AWS Powertools (Logger, APIGatewayRestResolver, Exception Handlers) |
| **Async I/O** | `aioboto3` (DynamoDB), `aiohttp` (HTTP), `asyncio` |
| **Cache** | DynamoDB com TTL (3 horas) |
| **Weather API** | OpenWeather Forecast (5 dias, 3h interval) |
| **Deploy** | Terraform, AWS API Gateway |
| **Testing** | pytest, pytest-asyncio (37/37 testes passando) |
| **Observability** | AWS Powertools Logger (structured logs) |

## 🧪 Testes

### Executar testes

```bash
# Todos os testes
pytest lambda/tests/ -v

# Integration tests
pytest lambda/tests/integration/ -v

# Unit tests
pytest lambda/tests/unit/ -v

# Performance tests
python scripts/performance_test_100_cities.py
```

### Status atual

✅ **37/37 testes passando**
- Integration tests - Endpoints completos (8 testes)
- Unit tests - Entidades, helpers, repositories (29 testes)

📖 **Guia completo de testes:** [Testing Guide](docs/development/TESTING.md)

## 🚀 Deploy

### Pré-requisitos

- AWS CLI configurado
- Terraform >= 1.0
- OpenWeather API key ([obter aqui](https://openweathermap.org/api))

### Deploy automatizado

```bash
bash scripts/deploy-main.sh
```

**O script executa:**
1. ✅ Validações de ambiente
2. ✅ Build do pacote Lambda
3. ✅ Terraform apply
4. ✅ Salva API Gateway URL em `API_URL.txt`

### Deploy manual (Terraform)

```bash
cd terraform

# Configurar variáveis
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars

# Deploy
terraform init
terraform plan
terraform apply
```

📖 **Guia completo:** [Deployment Workflow](docs/development/WORKFLOW.md#deployment-workflow)

## ⚡ Performance

### Benchmark (Regional endpoint - 100 cidades)

| Métrica | Valor |
|---------|-------|
| **Latência P99** | <200ms |
| **Latência média** | ~18.5ms/cidade |
| **Throughput** | 50-100 cidades/segundo |
| **Cold start** | ~500ms |
| **Warm start** | ~10ms |

**Otimizações aplicadas:**
- ✅ 100% async (aioboto3 + aiohttp)
- ✅ Lazy session creation com event loop check
- ✅ DynamoDB cache (TTL 3h, 80% hit rate)
- ✅ Throttling com Semaphore(50)
- ✅ Singleton repositories

📖 **Documentação técnica:**
- [Operações Assíncronas](docs/infrastructure/ASYNC_OPERATIONS.md)
- [Cache DynamoDB](docs/infrastructure/DYNAMODB_CACHE.md)

## 📊 Base de Dados

### Municípios (5.571 cidades)

**Fonte:** IBGE (Instituto Brasileiro de Geografia e Estatística)

```json
{
  "id": "3543204",
  "name": "Ribeirão do Sul",
  "state": "SP",
  "region": "Sudeste",
  "latitude": -22.7572,
  "longitude": -49.9439
}
```

**Otimizações:**
- Índices em memória (O(1) lookup)
- Índices por estado
- Lazy loading
- Singleton pattern

### Cálculo de distância (Haversine)

```python
def haversine_distance(lat1, lon1, lat2, lon2) -> float:
    """Calcula distância geodésica entre coordenadas (em km)"""
    # Precisão: ~99.5% para distâncias < 1000km
```

## 📚 Documentação

### 🏛️ Arquitetura
- [Clean Architecture Detalhada](docs/architecture/CLEAN_ARCHITECTURE_DETAILED.md) - Estrutura completa, padrões e fluxos

### 📡 API
- [Rotas e Endpoints](docs/api/ROUTES.md) - Documentação completa de todas as rotas

### ⚙️ Infraestrutura
- [Operações Assíncronas](docs/infrastructure/ASYNC_OPERATIONS.md) - Como async funciona no Lambda
- [Cache DynamoDB](docs/infrastructure/DYNAMODB_CACHE.md) - Estratégia de cache com TTL
- [Integração OpenWeather](docs/infrastructure/OPENWEATHER_INTEGRATION.md) - API externa e mapeamento

### 🛠️ Desenvolvimento
- [Testing Guide](docs/development/TESTING.md) - Guia completo de testes
- [Workflow](docs/development/WORKFLOW.md) - Setup, desenvolvimento e deploy

## 🛠️ Desenvolvimento Local

### Setup

```bash
# 1. Clonar repositório
git clone https://github.com/regisrfn/bkd-weather-forecast.git
cd bkd-weather-forecast

# 2. Criar ambiente virtual
python -m venv .venv
source .venv/bin/activate

# 3. Instalar dependências
pip install -r lambda/requirements.txt
pip install -r lambda/requirements-dev.txt

# 4. Configurar variáveis
cp .env.example .env
nano .env  # Adicionar OPENWEATHER_API_KEY
```

### Estrutura de diretórios

```
bkd-weather-forecast/
├── lambda/                 # Código da aplicação
│   ├── application/
│   ├── domain/
│   ├── infrastructure/
│   ├── shared/
│   └── tests/
├── scripts/               # Scripts utilitários
│   ├── deploy-main.sh
│   └── test_performance.py
├── terraform/             # Infrastructure as Code
├── docs/                  # Documentação completa
└── README.md              # Este arquivo
```

## 🐛 Troubleshooting

### Erro: "OPENWEATHER_API_KEY não configurada"

```bash
# Local
echo "OPENWEATHER_API_KEY=your_key_here" > .env

# AWS Lambda
# Configure via Terraform ou AWS Console
```

### Erro: "Event loop is closed"

**Solução:** Já implementado! Lazy session creation com event loop check.

```python
# infrastructure/adapters/output/async_weather_repository.py
def _get_session(self):
    # Check if session exists and if event loop matches
    if self._session:
        session_loop = getattr(self._session, '_loop', None)
        current_loop = asyncio.get_running_loop()
        if session_loop != current_loop:
            recreate_session = True
```

### Ver logs do Lambda

```bash
# Logs em tempo real
aws logs tail /aws/lambda/weather-forecast-api --follow

# Logs das últimas 10 minutos
aws logs tail /aws/lambda/weather-forecast-api --since 10m
```

## 🎯 Features

### ✅ Implementado

- [x] Clean Architecture (Domain, Application, Infrastructure, Shared)
- [x] 100% async migration (aioboto3 + aiohttp)
- [x] DynamoDB cache com TTL (3 horas, 80% hit rate)
- [x] AWS Powertools (Logger, APIGatewayRestResolver, Exception Handlers)
- [x] Throttling com Semaphore (50 concurrent requests)
- [x] 34 testes (integration + unit + performance)
- [x] Terraform IaC (Lambda + API Gateway + DynamoDB)
- [x] Documentação técnica completa

### 🔜 Roadmap

- [ ] Rate limiting por IP/API key
- [ ] Autenticação JWT
- [ ] Webhooks para alertas meteorológicos
- [ ] API de histórico de previsões
- [ ] CI/CD com GitHub Actions
- [ ] Métricas customizadas (CloudWatch)

## 📝 Licença

MIT

## 👥 Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/AmazingFeature`)
3. Commit (`git commit -m 'Add AmazingFeature'`)
4. Push (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📁 Estrutura do Projeto

```
bkd-weather-forecast/
├── lambda/                    # Código da aplicação
│   ├── application/           # Casos de uso (100% async)
│   ├── domain/               # Entidades e exceções
│   ├── infrastructure/       # Adapters (DynamoDB, OpenWeather, HTTP)
│   ├── shared/               # Utilitários compartilhados
│   ├── data/                 # Dados estáticos (5.571 municípios)
│   └── tests/                # Testes (integration + unit + performance)
├── scripts/                  # Scripts de deploy e performance
├── docs/                     # Documentação técnica completa
│   ├── architecture/         # Documentação de arquitetura
│   ├── api/                  # Documentação de rotas
│   ├── infrastructure/       # Async, cache, integrações
│   └── development/          # Testes e workflow
├── terraform/                # Infrastructure as Code
└── README.md                 # Este arquivo
```

## 🛠️ Desenvolvimento Local

### Setup

```bash
# 1. Clonar repositório
git clone https://github.com/regisrfn/bkd-weather-forecast.git
cd bkd-weather-forecast

# 2. Criar ambiente virtual
python3.13 -m venv .venv
source .venv/bin/activate

# 3. Instalar dependências
pip install -r lambda/requirements.txt
pip install -r lambda/requirements-dev.txt

# 4. Configurar variáveis
export OPENWEATHER_API_KEY=your_key_here
export DYNAMODB_CACHE_TABLE=weather-forecast-cache-dev
```

### Executar testes

```bash
# Todos os testes
pytest lambda/tests/ -v

# Com cobertura
pytest lambda/tests/ --cov=lambda --cov-report=html
```

📖 **Guia completo:** [Development Workflow](docs/development/WORKFLOW.md)

## 🐛 Troubleshooting

### Erro: "OPENWEATHER_API_KEY não configurada"

```bash
# Local
export OPENWEATHER_API_KEY=your_key_here

# AWS Lambda
# Configure via Terraform ou AWS Console > Lambda > Environment variables
```

### Ver logs do Lambda

```bash
# Logs em tempo real
aws logs tail /aws/lambda/weather-forecast-lambda-prod --follow

# Logs das últimas 10 minutos
aws logs tail /aws/lambda/weather-forecast-lambda-prod --since 10m
```

📖 **Mais troubleshooting:** [Workflow Guide - Troubleshooting](docs/development/WORKFLOW.md#troubleshooting)

## 🎯 Features

### ✅ Implementado

- [x] Clean Architecture (Domain, Application, Infrastructure, Shared)
- [x] 100% async migration (aioboto3 + aiohttp)
- [x] DynamoDB cache com TTL (3 horas, 80% hit rate)
- [x] AWS Powertools (Logger, APIGatewayRestResolver, Exception Handlers)
- [x] Throttling com Semaphore (50 concurrent requests)
- [x] 34 testes (integration + unit + performance)
- [x] Terraform IaC (Lambda + API Gateway + DynamoDB)
- [x] Documentação técnica completa

### 🔜 Roadmap

- [ ] Rate limiting por IP/API key
- [ ] Autenticação JWT
- [ ] Webhooks para alertas meteorológicos
- [ ] API de histórico de previsões
- [ ] CI/CD com GitHub Actions
- [ ] Métricas customizadas (CloudWatch)

## 📝 Licença

MIT

## 👥 Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/AmazingFeature`)
3. Commit (`git commit -m 'Add AmazingFeature'`)
4. Push (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

---

**⭐ Se este projeto foi útil, considere dar uma estrela!**

````
