# Backend Weather Forecast - Lambda AWS

Backend API em Python para fornecer dados meteorológicos em tempo real para a aplicação Weather Forecast.

## 🚀 Arquitetura

- **AWS Lambda**: Função serverless em Python 3.11+
- **API Gateway**: Gerenciamento de rotas REST
- **Terraform**: Infraestrutura como código

## 📡 Endpoints

### 1. GET /api/cities/neighbors/{cityId}?radius=50
Retorna a cidade centro e suas cidades vizinhas dentro de um raio.

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
    "latitude": -22.7572,
    "longitude": -49.9439
  },
  "neighbors": [
    {
      "id": "3550506",
      "name": "São Pedro do Turvo",
      "latitude": -22.8978,
      "longitude": -49.7433,
      "distance": 17.8
    }
  ]
}
```

### 2. GET /api/weather/city/{cityId}
Retorna dados climáticos de uma cidade específica.

**Exemplo:**
```bash
GET /api/weather/city/3543204
```

**Resposta:**
```json
{
  "cityId": "3543204",
  "cityName": "Ribeirão do Sul",
  "temperature": 24.5,
  "humidity": 65.0,
  "windSpeed": 12.5,
  "rainfallIntensity": 45.0,
  "timestamp": "2025-11-18T18:30:00Z"
}
```

### 3. POST /api/weather/regional
Retorna dados climáticos de múltiplas cidades.

**Exemplo:**
```bash
POST /api/weather/regional
Content-Type: application/json

{
  "cityIds": ["3543204", "3550506", "3545407"]
}
```

**Resposta:**
```json
[
  {
    "cityId": "3543204",
    "cityName": "Ribeirão do Sul",
    "temperature": 24.5,
    "humidity": 65.0,
    "windSpeed": 12.5,
    "rainfallIntensity": 45.0,
    "timestamp": "2025-11-18T18:30:00Z"
  },
  {
    "cityId": "3550506",
    "cityName": "São Pedro do Turvo",
    "temperature": 23.8,
    "humidity": 70.0,
    "windSpeed": 10.2,
    "rainfallIntensity": 38.5,
    "timestamp": "2025-11-18T18:30:00Z"
  }
]
```

## 📁 Estrutura do Projeto

```
lambda/
├── lambda_function.py      # Função principal (router)
├── cities_data.py          # Base de dados de cidades
├── cities_service.py       # Lógica de negócio - cidades
├── weather_service.py      # Lógica de negócio - clima
├── utils.py                # Funções utilitárias
├── config.py               # Configurações
└── requirements.txt        # Dependências Python
```

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
cd lambda
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente (opcional)
```bash
export OPENWEATHER_API_KEY=your_api_key_here
```

**Nota**: Se não configurar a API key, a aplicação usa dados mockados automaticamente.

### 4. Testar localmente
```bash
python test_lambda.py
```

## ☁️ Deploy na AWS

### Pré-requisitos
- AWS CLI configurado
- Terraform instalado
- Permissões IAM necessárias

### Deploy com Terraform
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

### Deploy manual (alternativo)
```bash
cd lambda
zip -r function.zip .
aws lambda update-function-code \
  --function-name weather-forecast-api \
  --zip-file fileb://function.zip
```

## 🔐 Variáveis de Ambiente (Lambda)

Configurar no AWS Lambda Console ou Terraform:

| Variável | Descrição | Obrigatório |
|----------|-----------|-------------|
| `OPENWEATHER_API_KEY` | Chave da API OpenWeatherMap | Não* |
| `CORS_ORIGIN` | Origem permitida para CORS | Não |

\* Se não configurado, usa dados mockados

## 🧪 Dados Mockados

Quando `OPENWEATHER_API_KEY` não está configurada, a API retorna dados aleatórios realistas para desenvolvimento:

- **Temperatura**: 18°C a 30°C
- **Umidade**: 40% a 85%
- **Vento**: 5 km/h a 25 km/h
- **Intensidade de Chuva**: 0% a 100%

## 🗺️ Cidades Disponíveis

| Código IBGE | Nome | Estado |
|-------------|------|--------|
| 3543204 | Ribeirão do Sul | SP |
| 3550506 | São Pedro do Turvo | SP |
| 3545407 | Salto Grande | SP |
| 3534708 | Ourinhos | SP |
| 3510153 | Canitar | SP |
| 3546405 | Santa Cruz do Rio Pardo | SP |
| 3538808 | Piraju | SP |

## 📊 Fórmula de Haversine

A distância entre cidades é calculada usando a fórmula de Haversine:

```python
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0  # Raio da Terra em km
    # ... cálculo da distância geodésica
    return distance
```

## 🔗 Integração com Frontend

No frontend (`app-weather-forecast`), configure:

```typescript
// src/config/app.ts
export const APP_CONFIG = {
  API_BASE_URL: 'https://your-api-gateway-url.amazonaws.com/prod',
  USE_MOCK: false,  // Desabilitar mock
  // ...
}
```

## 🐛 Troubleshooting

### Erro: "Module not found"
```bash
cd lambda
pip install -r requirements.txt -t .
```

### Teste de rota específica
```bash
aws lambda invoke \
  --function-name weather-forecast-api \
  --payload '{"httpMethod":"GET","path":"/api/cities/neighbors/3543204"}' \
  response.json
cat response.json
```

### Ver logs
```bash
aws logs tail /aws/lambda/weather-forecast-api --follow
```

## 📝 Licença

MIT
