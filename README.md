# Backend Weather Forecast - Clean Architecture

Backend API em Python para fornecer dados meteorológicos com arquitetura hexagonal (Ports and Adapters) para AWS Lambda.

## � Estrutura do Projeto

```
bkd-weather-forecast/
├── lambda/                    # Código da aplicação
│   ├── application/           # Camada de Aplicação
│   │   ├── ports/            # Interfaces (input/output)
│   │   └── use_cases/        # Lógica de negócio
│   ├── domain/               # Entidades de domínio
│   ├── infrastructure/       # Adapters (HTTP, DB, APIs)
│   └── data/                 # Dados estáticos
├── tests/                    # Testes unit e integration
├── scripts/                  # Scripts utilitários (.sh)
├── docs/                     # Documentação completa
└── terraform/                # IaC AWS
```

## 🚀 Quick Start

### 1. Setup

```bash
# Ativar ambiente virtual
source .venv/bin/activate

# Instalar dependências
pip install -r lambda/requirements.txt
```

### 2. Configurar .env

```bash
OPENWEATHER_API_KEY=sua_chave
CORS_ORIGIN=http://seu-dominio.com
ENVIRONMENT=development
```

### 3. Executar Testes

```bash
# Todos os testes (unit + integration)
bash scripts/run_tests.sh all

# Apenas unitários
bash scripts/run_tests.sh unit
```

### 4. Deploy

```bash
bash scripts/deploy-main.sh
```

## 📡 Endpoints

### 1. GET /api/cities/neighbors/{cityId}?radius=50
Retorna a cidade centro e suas cidades vizinhas dentro de um raio (em km).

**Parâmetros:**
- `cityId` (path): Código IBGE da cidade
- `radius` (query, opcional): Raio em km (padrão: 50)

**Exemplo:**
```bash
GET /api/cities/neighbors/3543204?radius=50
```

**Resposta:**
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
      "latitude": -22.8978,
      "longitude": -49.7433,
      "distance": 17.8
    }
  ]
}
```

---

### 2. GET /api/weather/city/{cityId}
Retorna previsão meteorológica de uma cidade específica.

**Parâmetros:**
- `cityId` (path): Código IBGE da cidade
- `date` (query, opcional): Data no formato YYYY-MM-DD (ex: 2025-11-20)
- `time` (query, opcional): Hora no formato HH:MM (ex: 15:00)

**Comportamento:**
- Sem parâmetros: retorna próxima previsão disponível
- Apenas `date`: retorna previsão para meio-dia (12:00)
- Apenas `time`: retorna previsão para hoje no horário especificado
- `date` + `time`: retorna previsão para data/hora específica

**Exemplos:**
```bash
# Próxima previsão disponível
GET /api/weather/city/3543204

# Previsão para amanhã ao meio-dia
GET /api/weather/city/3543204?date=2025-11-20

# Previsão para amanhã às 15h
GET /api/weather/city/3543204?date=2025-11-20&time=15:00
```

**Resposta:**
```json
{
  "cityId": "3543204",
  "cityName": "Ribeirão do Sul",
  "timestamp": "2025-11-20T15:00:00",
  "temperature": 28.3,
  "humidity": 65.0,
  "windSpeed": 12.5,
  "rainfallIntensity": 35.5
}
```

**Campos:**
- `rainfallIntensity`: Probabilidade de chuva (0-100%) baseada no campo `pop` da OpenWeather API
- `timestamp`: Data/hora da previsão (ISO 8601)
- `temperature`: Temperatura em °C
- `humidity`: Umidade relativa (%)
- `windSpeed`: Velocidade do vento (km/h)

---

### 3. POST /api/weather/regional
Retorna previsões meteorológicas de múltiplas cidades.

**Parâmetros:**
- `cityIds` (body): Array de códigos IBGE
- `date` (query, opcional): Data no formato YYYY-MM-DD
- `time` (query, opcional): Hora no formato HH:MM

**Exemplos:**
```bash
# Próxima previsão disponível para múltiplas cidades
POST /api/weather/regional
Content-Type: application/json

{
  "cityIds": ["3543204", "3548708", "3509502"]
}

# Previsão para data/hora específica
POST /api/weather/regional?date=2025-11-20&time=15:00
Content-Type: application/json

{
  "cityIds": ["3543204", "3548708", "3509502"]
}
```

**Resposta:**
```json
[
  {
    "cityId": "3543204",
    "cityName": "Ribeirão do Sul",
    "timestamp": "2025-11-20T15:00:00",
    "temperature": 28.3,
    "humidity": 65.0,
    "windSpeed": 12.5,
    "rainfallIntensity": 35.5
  },
  {
    "cityId": "3548708",
    "cityName": "São Carlos",
    "timestamp": "2025-11-20T15:00:00",
    "temperature": 27.1,
    "humidity": 58.0,
    "windSpeed": 15.2,
    "rainfallIntensity": 20.0
  }
]
```

---

## 📁 Estrutura do Projeto (Clean Architecture)

```
lambda/
├── domain/                      # Camada de Domínio
│   ├── entities/
│   │   ├── city.py             # Entidade City
│   │   └── weather.py          # Entidade Weather
│   └── repositories/           # Interfaces
│       ├── city_repository.py
│       └── weather_repository.py
│
├── application/                 # Camada de Aplicação
│   └── use_cases/
│       ├── get_neighbor_cities.py
│       ├── get_city_weather.py
│       └── get_regional_weather.py
│
├── infrastructure/              # Camada de Infraestrutura
│   ├── repositories/
│   │   ├── municipalities_repository.py  # JSON com 5.571 cidades
│   │   └── weather_repository.py         # OpenWeather Forecast API
│   └── external/
│
├── presentation/                # Camada de Apresentação
│   └── handlers/
│
├── shared/                      # Utilitários
│   └── utils/
│       └── haversine.py        # Cálculo de distância
│
├── data/
│   └── municipalities_db.json  # Base de dados de cidades
│
├── lambda_function.py          # Entry point (Router)
├── config.py                   # Configurações
├── test_lambda.py              # Testes
└── requirements.txt            # Dependências
```

**Documentação detalhada:** Ver [CLEAN_ARCHITECTURE.md](lambda/CLEAN_ARCHITECTURE.md)

---

## 🔧 Desenvolvimento Local

### 1. Criar ambiente virtual
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate     # Windows
```

### 2. Instalar dependências
```bash
pip install -r lambda/requirements.txt
```

### 3. Configurar variáveis de ambiente
Crie um arquivo `.env` na raiz do projeto:

```bash
# .env
OPENWEATHER_API_KEY=your_api_key_here
CORS_ORIGIN=http://localhost:5173
ENVIRONMENT=development
```

Carregue as variáveis:
```bash
cd lambda
source load_env.sh
```

### 4. Obter API Key da OpenWeather
1. Acesse [OpenWeatherMap](https://openweathermap.org/api)
2. Crie uma conta gratuita
3. Gere uma API key
4. Configure no arquivo `.env`

**Nota:** A API gratuita permite:
- 1.000 chamadas/dia
- Previsão de 5 dias (3 em 3 horas)

### 5. Testar localmente
```bash
cd lambda
python test_lambda.py
```

O script `test_lambda.py` simula todas as rotas do API Gateway:
- ✅ Buscar cidades vizinhas
- ✅ Previsão próxima disponível
- ✅ Previsão para data/hora específica
- ✅ Previsão regional (múltiplas cidades)
- ✅ Previsão regional para data específica

---

## ☁️ Deploy na AWS

### Pré-requisitos
- AWS CLI configurado
- Terraform instalado (>= 1.0)
- Permissões IAM necessárias:
  - Lambda: Create, Update, Invoke
  - API Gateway: Create, Update
  - IAM: Create roles
  - CloudWatch: Create log groups

### Deploy com Terraform

```bash
cd terraform

# Inicializar Terraform
terraform init

# Configurar variáveis (editar terraform.tfvars)
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars

# Planejar deploy
terraform plan

# Aplicar mudanças
terraform apply
```

**Variáveis necessárias no `terraform.tfvars`:**
```hcl
aws_region = "sa-east-1"
openweather_api_key = "your_api_key_here"
cors_origin = "https://your-frontend-domain.com"
environment = "production"
```

### Build e Deploy da Lambda

O Terraform executa automaticamente o script `build-lambda.sh` que:
1. Instala dependências em `build/package/`
2. Copia código fonte
3. Cria arquivo ZIP otimizado
4. Faz deploy no AWS Lambda

**Deploy manual (alternativo):**
```bash
cd terraform
./build-lambda.sh
```

### Verificar Deploy
```bash
# Ver outputs do Terraform
terraform output

# Testar API
curl https://your-api-id.execute-api.sa-east-1.amazonaws.com/prod/api/cities/neighbors/3543204?radius=50
```

---

## 🔐 Variáveis de Ambiente

### Lambda (Produção)

Configuradas via Terraform ou AWS Console:

| Variável | Descrição | Obrigatório | Padrão |
|----------|-----------|-------------|--------|
| `OPENWEATHER_API_KEY` | Chave da API OpenWeather | ✅ Sim | - |
| `CORS_ORIGIN` | Origem permitida para CORS | Não | `*` |
| `ENVIRONMENT` | Ambiente (development/production) | Não | `production` |

### Local (Desenvolvimento)

Arquivo `.env`:
```bash
OPENWEATHER_API_KEY=your_key_here
CORS_ORIGIN=http://localhost:5173
ENVIRONMENT=development
```

---

## 🌦️ API OpenWeather - Forecast

### Endpoint Usado
```
GET https://api.openweathermap.org/data/2.5/forecast
```

### Parâmetros
- `lat`, `lon`: Coordenadas da cidade
- `appid`: API key
- `units=metric`: Temperaturas em Celsius
- `lang=pt_br`: Descrições em português

### Resposta
```json
{
  "list": [
    {
      "dt": 1637280000,
      "main": {
        "temp": 25.5,
        "humidity": 65
      },
      "wind": {
        "speed": 3.5
      },
      "pop": 0.35,  // Probability of Precipitation (0-1)
      "rain": {
        "3h": 1.5
      }
    }
  ]
}
```

### Limites da API Gratuita
- 1.000 chamadas/dia
- Previsões de 3 em 3 horas
- Até 5 dias à frente
- Dados atualizados a cada 10 minutos

**Otimização no Lambda:**
- Cache de repositórios (singleton)
- Reutilização de conexões HTTP
- Busca pela previsão mais próxima da data solicitada

---

## 🗺️ Base de Dados de Cidades

### Arquivo: `data/municipalities_db.json`

**Fonte:** IBGE (Instituto Brasileiro de Geografia e Estatística)

**Conteúdo:**
- 5.571 municípios brasileiros
- Todos os 27 estados
- Coordenadas (latitude/longitude) validadas
- Tamanho: ~1.5MB

**Formato:**
```json
{
  "municipalities": [
    {
      "id": "3543204",
      "name": "Ribeirão do Sul",
      "state": "SP",
      "region": "Sudeste",
      "latitude": -22.7572,
      "longitude": -49.9439
    }
  ]
}
```

**Otimizações:**
- Índices em memória (O(1) lookup por ID)
- Índices por estado
- Cache global no Lambda (warm starts)
- Lazy loading apenas quando necessário

**Estratégia de busca de vizinhos:**
1. Filtrar cidades do mesmo estado (otimização regional)
2. Calcular distância com fórmula de Haversine
3. Filtrar por raio
4. Ordenar por distância

---

## 📊 Fórmula de Haversine

Calcula a distância geodésica entre duas coordenadas na superfície da Terra:

```python
def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula distância entre duas coordenadas usando fórmula de Haversine
    
    Returns:
        float: Distância em quilômetros
    """
    R = 6371.0  # Raio médio da Terra em km
    
    # Converter para radianos
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Diferenças
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Fórmula de Haversine
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c
```

**Precisão:** ~99.5% para distâncias < 1000km

---

## 🧪 Testes

### Estrutura de Testes

```bash
lambda/
└── test_lambda.py          # Testes de integração (simula API Gateway)
```

### Executar Testes

```bash
# Carregar variáveis de ambiente
cd lambda
source load_env.sh

# Executar testes
cd ..
python lambda/test_lambda.py
```

### Testes Disponíveis

1. **test_get_neighbors()** - Buscar cidades vizinhas (raio 50km)
2. **test_get_city_weather()** - Previsão próxima disponível
3. **test_get_city_weather_with_date()** - Previsão para data/hora específica
4. **test_post_regional_weather()** - Previsão regional (múltiplas cidades)
5. **test_post_regional_weather_with_date()** - Previsão regional para data específica

### Cidade de Teste

**Ribeirão do Sul (SP)**
- Código IBGE: `3543204`
- Coordenadas: -22.7572, -49.9439
- Estado: São Paulo
- Região: Sudeste

### Output Esperado

```
======================================================================
🧪 TESTES DO LAMBDA WEATHER FORECAST API
   Cidade de teste: Ribeirão do Sul (ID: 3543204)
======================================================================

TEST 1: GET /api/cities/neighbors/3543204?radius=50
Status: 200
Cidade centro: Ribeirão do Sul
Vizinhos encontrados: 21

TEST 2: GET /api/weather/city/3543204
Status: 200
Temperatura: 17.2°C
Probabilidade de chuva: 0%

...

✅ TESTES CONCLUÍDOS
======================================================================
```

---

## 🔗 Integração com Frontend

### Vue 3 + TypeScript

No frontend (`app-weather-forecast`), configure:

```typescript
// src/config/app.ts
export const APP_CONFIG = {
  API_BASE_URL: 'https://your-api-id.execute-api.sa-east-1.amazonaws.com/prod',
  USE_MOCK: false,  // Desabilitar mock local
  DEFAULT_RADIUS: 50,
  IBGE_API_URL: 'https://servicodados.ibge.gov.br/api/v1'
}
```

### Chamadas de API

```typescript
// src/services/apiService.ts
import axios from 'axios'
import { APP_CONFIG } from '@/config/app'

const api = axios.create({
  baseURL: APP_CONFIG.API_BASE_URL,
  timeout: 10000
})

// Buscar vizinhos
export async function getNeighborCities(cityId: string, radius: number = 50) {
  const response = await api.get(`/api/cities/neighbors/${cityId}`, {
    params: { radius }
  })
  return response.data
}

// Previsão de uma cidade
export async function getCityWeather(cityId: string, date?: string, time?: string) {
  const response = await api.get(`/api/weather/city/${cityId}`, {
    params: { date, time }
  })
  return response.data
}

// Previsão regional
export async function getRegionalWeather(cityIds: string[], date?: string, time?: string) {
  const response = await api.post('/api/weather/regional', 
    { cityIds },
    { params: { date, time } }
  )
  return response.data
}
```

---

## 🐛 Troubleshooting

### Erro: "OPENWEATHER_API_KEY não configurada"

**Solução:**
```bash
# Local
cd lambda
source load_env.sh

# AWS Lambda
# Configure via Terraform ou AWS Console > Lambda > Configuration > Environment variables
```

### Erro: "Nenhuma previsão disponível para a data/hora solicitada"

**Causas possíveis:**
- Data solicitada está além dos 5 dias de previsão
- Data no passado
- Formato de data inválido

**Solução:**
```bash
# Formato correto
?date=2025-11-20&time=15:00

# Verificar previsões disponíveis
curl "https://api.openweathermap.org/data/2.5/forecast?lat=-22.75&lon=-49.94&appid=YOUR_KEY"
```

### Erro: "Module not found"

**Solução:**
```bash
cd lambda
pip install -r requirements.txt
```

## 🧪 Testes

### Estrutura de Testes

O projeto possui dois níveis de testes automatizados:

#### 1. Testes Locais (Pré-Deploy)
**Arquivo:** `lambda/test_lambda.py`

Testa a função Lambda localmente **antes** do deploy, simulando eventos do API Gateway.

**Executar:**
```bash
# Entrar no diretório lambda
cd lambda

# Executar com Python
python test_lambda.py

# Ou com pytest (recomendado)
pytest test_lambda.py -v
```

**Cobertura:**
- ✅ GET /api/cities/neighbors/{cityId}
- ✅ GET /api/weather/city/{cityId}
- ✅ GET /api/weather/city/{cityId}?date=...&time=...
- ✅ POST /api/weather/regional
- ✅ POST /api/weather/regional?date=...
- ✅ Validações de estrutura de resposta
- ✅ Validações de ranges (temperatura, umidade, etc.)
- ✅ Validações de timestamps

**Quando falham:** O deploy é **cancelado** automaticamente.

#### 2. Testes de Integração (Pós-Deploy)
**Arquivo:** `lambda/test_api_gateway.py`

Testa a API real no API Gateway **após** o deploy na AWS.

**Executar:**
```bash
# Exportar URL da API (obtida do terraform output)
export API_GATEWAY_URL="https://sua-api.execute-api.sa-east-1.amazonaws.com/dev"

# Entrar no diretório lambda
cd lambda

# Executar
python test_api_gateway.py

# Ou com pytest
pytest test_api_gateway.py -v
```

**Cobertura:**
- ✅ Health check (conectividade com API Gateway)
- ✅ Todos os endpoints (GET e POST)
- ✅ Validações CORS
- ✅ Validações de performance (< 10s para regional)
- ✅ Tratamento de erros (cidades inválidas, body malformado)
- ✅ Previsões com data/hora específica
- ✅ Medição de tempo de resposta

**Quando falham:** O deploy continua, mas um aviso é exibido.

### Deploy Automatizado com Testes

O script `terraform/deploy.sh` executa testes automaticamente:

```bash
cd terraform
bash deploy.sh
```

**Fluxo de Deploy:**
1. 🧪 **Testes Locais** - Valida código antes de buildar
2. 📦 **Build** - Cria pacote Lambda com dependências
3. 🔧 **Terraform** - Valida e planeja mudanças
4. 🚀 **Deploy** - Aplica mudanças na AWS
5. 🧪 **Testes de Integração** - Valida API real no Gateway

**Se testes locais falham:** Deploy é **cancelado**.  
**Se testes de integração falham:** Deploy continua, mas você é **alertado**.

### Testes Manuais com pytest

```bash
# Instalar dependências de teste
pip install pytest pytest-cov

# Executar todos os testes locais com cobertura
pytest lambda/test_lambda.py -v --cov=lambda

# Executar testes de integração (após deploy)
pytest lambda/test_api_gateway.py -v
```

### Lambda Cold Start Lento

**Otimizações aplicadas:**
- Singleton pattern nos repositórios
- Lazy loading de dados
- Índices em memória
- Reutilização de conexões HTTP

**Cold start típico:** 200-500ms  
**Warm start típico:** 10-50ms

### Testar Lambda na AWS

```bash
# Invocar diretamente
aws lambda invoke \
  --function-name weather-forecast-api \
  --payload '{"httpMethod":"GET","path":"/api/cities/neighbors/3543204","queryStringParameters":{"radius":"50"}}' \
  response.json

cat response.json | jq
```

### Ver Logs do Lambda

```bash
# Logs em tempo real
aws logs tail /aws/lambda/weather-forecast-api --follow

# Logs das últimas 10 minutos
aws logs tail /aws/lambda/weather-forecast-api --since 10m
```

### Depurar Localmente

```python
# test_lambda.py
import json
from lambda_function import lambda_handler

# Ativar debug
import logging
logging.basicConfig(level=logging.DEBUG)

# Executar
event = {...}
response = lambda_handler(event, MockContext())
print(json.dumps(response, indent=2))
```

---

## 📚 Documentação Adicional

- [Clean Architecture](lambda/CLEAN_ARCHITECTURE.md) - Detalhes da arquitetura em camadas
- [Database Strategy](docs/DATABASE_STRATEGY.md) - Estratégia de dados em memória
- [Deploy Guide](terraform/DEPLOY_GUIDE.md) - Guia completo de deploy

---

## 🎯 Roadmap

### ✅ Implementado
- [x] Clean Architecture (Domain, Application, Infrastructure, Presentation)
- [x] Busca de cidades vizinhas (Haversine)
- [x] Previsão meteorológica (OpenWeather Forecast API)
- [x] Previsão para data/hora específica
- [x] Previsão regional (múltiplas cidades)
- [x] Base de dados de 5.571 municípios brasileiros
- [x] Deploy automatizado com Terraform
- [x] Testes de integração

### 🔜 Próximas Features
- [ ] Cache de previsões (Redis/DynamoDB)
- [ ] Rate limiting
- [ ] Autenticação JWT
- [ ] Webhooks para alertas de chuva
- [ ] API de histórico meteorológico
- [ ] Suporte a múltiplos idiomas
- [ ] Métricas e dashboards (CloudWatch)
- [ ] CI/CD com GitHub Actions

### ✅ Testes Implementados
- [x] Testes unitários locais (pré-deploy)
- [x] Testes de integração (pós-deploy)
- [x] Validações com asserts e pytest
- [x] Deploy automatizado com testes
- [x] Validações de performance
- [x] Tratamento de erros

---

## 📝 Licença

MIT

---

## 👥 Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

---

## 📧 Contato

Para dúvidas ou sugestões, abra uma issue no repositório.

````
