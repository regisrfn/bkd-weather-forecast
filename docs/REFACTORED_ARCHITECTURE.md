# Arquitetura Refatorada - Backend Weather Forecast

## 📐 Estrutura do Projeto

A arquitetura segue o padrão **Hexagonal (Ports and Adapters)** com **Clean Architecture**:

```
bkd-weather-forecast/
├── lambda/
│   ├── application/           # Camada de Aplicação
│   │   ├── ports/
│   │   │   ├── input/         # Interfaces de Use Cases
│   │   │   │   ├── get_neighbor_cities_port.py
│   │   │   │   ├── get_city_weather_port.py
│   │   │   │   └── get_regional_weather_port.py
│   │   │   └── output/        # Interfaces de Repositórios
│   │   │       ├── city_repository_port.py
│   │   │       └── weather_repository_port.py
│   │   └── use_cases/         # Implementações dos Use Cases
│   │       ├── get_neighbor_cities.py
│   │       ├── get_city_weather.py
│   │       └── get_regional_weather.py
│   │
│   ├── domain/                # Camada de Domínio
│   │   └── entities/          # Entidades de Negócio
│   │       ├── city.py
│   │       └── weather.py
│   │
│   ├── infrastructure/        # Camada de Infraestrutura
│   │   └── adapters/
│   │       ├── input/         # Adapters de Entrada
│   │       │   └── lambda_handler.py
│   │       └── output/        # Adapters de Saída
│   │           ├── municipalities_repository.py
│   │           └── weather_repository.py
│   │
│   ├── shared/                # Código compartilhado
│   │   └── utils/
│   │       └── haversine.py
│   │
│   ├── config.py              # Configurações
│   └── lambda_function.py     # Entry point AWS Lambda
│
└── tests/                     # Testes
    ├── unit/                  # Testes Unitários
    │   ├── test_city_entity.py
    │   ├── test_weather_entity.py
    │   ├── test_get_neighbor_cities.py
    │   ├── test_get_city_weather.py
    │   └── test_haversine.py
    └── integration/           # Testes de Integração
        └── test_lambda_integration.py
```

## 🎯 Princípios da Arquitetura

### 1. **Application Layer (Camada de Aplicação)**

#### Ports Input (application/ports/input/)
- **Interfaces que definem contratos dos Use Cases**
- Define o que a aplicação pode fazer
- Independente de detalhes de implementação

Exemplo:
```python
class IGetCityWeatherUseCase(ABC):
    @abstractmethod
    def execute(self, city_id: str, target_datetime: Optional[datetime] = None) -> Weather:
        pass
```

#### Ports Output (application/ports/output/)
- **Interfaces que definem contratos de comunicação externa**
- Repositórios, APIs externas, etc.
- Implementadas pela camada de infraestrutura

Exemplo:
```python
class ICityRepository(ABC):
    @abstractmethod
    def get_by_id(self, city_id: str) -> Optional[City]:
        pass
```

#### Use Cases (application/use_cases/)
- **Implementam a lógica de negócio**
- Implementam interfaces dos Ports Input
- Dependem apenas de Ports Output (interfaces)
- Orquestram entidades e repositórios

### 2. **Domain Layer (Camada de Domínio)**

#### Entities (domain/entities/)
- **Entidades de negócio puras**
- Sem dependências externas
- Contêm lógica de negócio específica da entidade

Exemplos: `City`, `Weather`, `NeighborCity`

### 3. **Infrastructure Layer (Camada de Infraestrutura)**

#### Adapters Input (infrastructure/adapters/input/)
- **Implementam entrada de dados na aplicação**
- HTTP Handler, CLI, etc.
- Convertem requisições externas em chamadas de Use Cases

Exemplo: `lambda_handler.py` - Adapter HTTP para AWS Lambda

#### Adapters Output (infrastructure/adapters/output/)
- **Implementam interfaces dos Ports Output**
- Acesso a banco de dados, APIs externas, etc.
- Isolam detalhes técnicos da aplicação

Exemplos:
- `municipalities_repository.py` - Implementa ICityRepository
- `weather_repository.py` - Implementa IWeatherRepository

## 🔄 Fluxo de Dados

```
┌─────────────────────────────────────────────────────────────┐
│                    AWS API Gateway                          │
│                  (Requisição HTTP)                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Infrastructure Layer                           │
│  ┌────────────────────────────────────────────────────┐    │
│  │  lambda_handler.py (Input Adapter)                 │    │
│  │  - Recebe evento HTTP                              │    │
│  │  - Parseia parâmetros                              │    │
│  │  - Chama Use Case                                  │    │
│  └────────────┬───────────────────────────────────────┘    │
└───────────────┼────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│              Application Layer                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Use Case (implementa Port Input)                  │    │
│  │  - Executa lógica de negócio                       │    │
│  │  - Valida regras                                   │    │
│  │  - Chama Ports Output (interfaces)                 │    │
│  └────────────┬───────────────────────────────────────┘    │
└───────────────┼────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│              Domain Layer                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Entities (City, Weather)                          │    │
│  │  - Lógica de negócio pura                          │    │
│  │  - Validações de domínio                           │    │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│              Infrastructure Layer                           │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Repository (Output Adapter)                       │    │
│  │  - Implementa Port Output (interface)              │    │
│  │  - Acessa dados externos                           │    │
│  │  - Converte para entidades de domínio              │    │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 🧪 Testes

### Testes Unitários (`tests/unit/`)
- Testam entidades de domínio isoladamente
- Testam use cases com mocks
- Testam utilidades (haversine)
- Não dependem de infraestrutura externa

**Executar:**
```bash
cd tests/unit
pytest -v
```

### Testes de Integração (`tests/integration/`)
- Testam fluxo completo end-to-end
- Simulam requisições HTTP
- Validam integração entre camadas

**Executar:**
```bash
cd tests/integration
pytest test_lambda_integration.py -v
# ou
python test_lambda_integration.py
```

## 🚀 Benefícios da Arquitetura

### 1. **Separação de Responsabilidades**
- Cada camada tem uma responsabilidade clara
- Fácil de entender e manter

### 2. **Testabilidade**
- Use cases podem ser testados com mocks
- Não precisa de infraestrutura para testes unitários

### 3. **Flexibilidade**
- Fácil trocar implementações (ex: trocar OpenWeather por outra API)
- Basta criar novo adapter implementando o Port Output

### 4. **Independência de Frameworks**
- Lógica de negócio não depende de AWS Lambda
- Pode migrar para outro framework facilmente

### 5. **Ports Bem Definidos**
- **Input Ports** em `application/ports/input/` - O que a aplicação pode fazer
- **Output Ports** em `application/ports/output/` - O que a aplicação precisa
- Contratos claros entre camadas

## 📝 Exemplo de Adição de Nova Funcionalidade

### Adicionar "Buscar Clima Histórico"

1. **Criar Port Input** (`application/ports/input/get_historical_weather_port.py`)
```python
class IGetHistoricalWeatherUseCase(ABC):
    @abstractmethod
    def execute(self, city_id: str, date: datetime) -> Weather:
        pass
```

2. **Criar Port Output se necessário** (`application/ports/output/historical_weather_port.py`)
```python
class IHistoricalWeatherRepository(ABC):
    @abstractmethod
    def get_historical_weather(self, lat: float, lon: float, date: datetime) -> Weather:
        pass
```

3. **Implementar Use Case** (`application/use_cases/get_historical_weather.py`)
```python
class GetHistoricalWeatherUseCase(IGetHistoricalWeatherUseCase):
    def __init__(self, city_repo, historical_weather_repo):
        self.city_repo = city_repo
        self.historical_weather_repo = historical_weather_repo
    
    def execute(self, city_id: str, date: datetime) -> Weather:
        # Lógica de negócio
        pass
```

4. **Implementar Adapter Output** (`infrastructure/adapters/output/historical_weather_repository.py`)
```python
class HistoricalWeatherRepository(IHistoricalWeatherRepository):
    def get_historical_weather(self, lat, lon, date):
        # Chamada para API externa
        pass
```

5. **Adicionar rota no Adapter Input** (`infrastructure/adapters/input/lambda_handler.py`)
```python
@app.get("/api/weather/historical/<city_id>")
def get_historical_weather_route(city_id: str):
    # Parsear parâmetros, chamar use case, retornar resposta
    pass
```

## 📦 Deploy

A aplicação está pronta para deploy usando Terraform:

```bash
cd terraform
./deploy.sh
```

O script já existe e faz:
1. Build do pacote Lambda
2. Deploy da infraestrutura (API Gateway + Lambda)
3. Configuração de variáveis de ambiente
