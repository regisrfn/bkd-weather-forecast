# 🏗️ Clean Architecture - Weather Forecast Backend

## 📚 Visão Geral

Este projeto segue os princípios de **Clean Architecture** (Arquitetura Limpa) para garantir:

- ✅ **Separação de responsabilidades** clara entre camadas
- ✅ **Independência de frameworks** e bibliotecas externas
- ✅ **Testabilidade** facilitada através de injeção de dependências
- ✅ **Manutenibilidade** com código organizado e desacoplado
- ✅ **Escalabilidade** para crescer com novos requisitos

---

## 📂 Estrutura de Diretórios

```
lambda/
├── domain/                      # Camada de Domínio (Entidades + Interfaces)
│   ├── entities/               # Entidades de negócio
│   │   ├── city.py            # City, NeighborCity
│   │   └── weather.py         # Weather
│   └── repositories/           # Interfaces dos repositórios
│       ├── city_repository.py
│       └── weather_repository.py
│
├── application/                 # Camada de Aplicação (Casos de Uso)
│   └── use_cases/
│       ├── get_neighbor_cities.py
│       ├── get_city_weather.py
│       └── get_regional_weather.py
│
├── infrastructure/              # Camada de Infraestrutura (Implementações)
│   ├── repositories/
│   │   ├── municipalities_repository.py
│   │   └── weather_repository.py
│   └── external/
│
├── presentation/                # Camada de Apresentação (Handlers HTTP)
│   └── handlers/
│
├── shared/                      # Código compartilhado
│   └── utils/
│       └── haversine.py        # Cálculo de distância
│
├── lambda_function.py           # Entry point do Lambda (Presentation)
├── config.py                    # Configurações
└── test_lambda.py              # Testes
```

---

## 🎯 Camadas da Arquitetura

### 1️⃣ **Domain Layer** (Camada de Domínio)

**Localização:** `domain/`

**Responsabilidade:** Contém as **entidades de negócio** e **interfaces dos repositórios**

**Características:**
- ✅ Não depende de nenhuma outra camada
- ✅ Regras de negócio puras
- ✅ Entidades imutáveis (dataclasses)
- ✅ Interfaces (contratos) que serão implementadas na infraestrutura

**Arquivos:**
```python
# domain/entities/city.py
@dataclass
class City:
    id: str
    name: str
    state: str
    region: str
    latitude: float
    longitude: float
    
    def has_coordinates(self) -> bool:
        return self.latitude is not None and self.longitude is not None

# domain/repositories/city_repository.py
class ICityRepository(ABC):
    @abstractmethod
    def get_by_id(self, city_id: str) -> Optional[City]:
        pass
```

---

### 2️⃣ **Application Layer** (Camada de Aplicação)

**Localização:** `application/`

**Responsabilidade:** Contém os **casos de uso** (regras de negócio da aplicação)

**Características:**
- ✅ Orquestra o fluxo de dados entre camadas
- ✅ Usa interfaces do domínio (dependency inversion)
- ✅ Não conhece detalhes de implementação (HTTP, DB, APIs externas)
- ✅ Facilita testes unitários

**Arquivos:**
```python
# application/use_cases/get_neighbor_cities.py
class GetNeighborCitiesUseCase:
    def __init__(self, city_repository: ICityRepository):
        self.city_repository = city_repository
    
    def execute(self, center_city_id: str, radius: float) -> dict:
        # 1. Validar entrada
        # 2. Buscar dados
        # 3. Aplicar regras de negócio
        # 4. Retornar resultado
        ...
```

**Use Cases disponíveis:**
- `GetNeighborCitiesUseCase` - Buscar cidades vizinhas
- `GetCityWeatherUseCase` - Buscar clima de uma cidade
- `GetRegionalWeatherUseCase` - Buscar clima de múltiplas cidades

---

### 3️⃣ **Infrastructure Layer** (Camada de Infraestrutura)

**Localização:** `infrastructure/`

**Responsabilidade:** Contém as **implementações concretas** dos repositórios e integrações externas

**Características:**
- ✅ Implementa as interfaces definidas no domínio
- ✅ Lida com detalhes técnicos (JSON, HTTP, Database)
- ✅ Pode ser facilmente substituída (ex: trocar API de weather)
- ✅ Usa padrão Singleton para otimizar Lambda cold starts

**Arquivos:**
```python
# infrastructure/repositories/municipalities_repository.py
class MunicipalitiesRepository(ICityRepository):
    def __init__(self, json_path: str):
        # Carrega JSON e cria índices
        ...
    
    def get_by_id(self, city_id: str) -> Optional[City]:
        # Implementação real
        data = self._index_by_id.get(city_id)
        return self._dict_to_entity(data) if data else None

# infrastructure/repositories/weather_repository.py
class OpenWeatherRepository(IWeatherRepository):
    def get_current_weather(self, lat: float, lon: float, city_name: str):
        # Chama API do OpenWeatherMap
        response = requests.get(url, params=params)
        return Weather(...)
```

---

### 4️⃣ **Presentation Layer** (Camada de Apresentação)

**Localização:** `lambda_function.py`

**Responsabilidade:** Gerenciar **requisições HTTP** e **respostas**

**Características:**
- ✅ Entry point do AWS Lambda
- ✅ Usa AWS Lambda Powertools para routing
- ✅ Injeta dependências nos use cases
- ✅ Converte entidades para formato JSON da API
- ✅ Trata erros e retorna códigos HTTP apropriados

**Arquivo:**
```python
# lambda_function.py
# Dependency Injection
city_repository = get_repository()
weather_repository = get_weather_repository()

get_neighbors_use_case = GetNeighborCitiesUseCase(city_repository)

@app.get("/api/cities/neighbors/<city_id>")
def get_neighbors_route(city_id: str):
    result = get_neighbors_use_case.execute(city_id, radius)
    return {
        'centerCity': result['centerCity'].to_api_response(),
        'neighbors': [n.to_api_response() for n in result['neighbors']]
    }
```

---

### 5️⃣ **Shared Layer** (Camada Compartilhada)

**Localização:** `shared/`

**Responsabilidade:** Código **utilitário** usado por múltiplas camadas

**Arquivos:**
- `shared/utils/haversine.py` - Cálculo de distância entre coordenadas

---

## 🔄 Fluxo de Requisição

```
┌─────────────────┐
│   HTTP Request  │
│ API Gateway     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│  Presentation Layer         │ lambda_function.py
│  - Parse request            │
│  - Validate input           │
│  - Call use case            │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Application Layer          │ use_cases/
│  - Business logic           │
│  - Orchestrate flow         │
│  - Use repositories         │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Infrastructure Layer       │ repositories/
│  - Query database           │
│  - Call external APIs       │
│  - Return entities          │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Domain Layer               │ entities/
│  - City, Weather objects    │
│  - Business rules           │
└─────────────────────────────┘
```

---

## 🧪 Dependency Injection

O projeto usa **Injeção de Dependência manual** para desacoplar as camadas:

```python
# 1. Criar repositórios (Infrastructure)
city_repository = MunicipalitiesRepository('data/municipalities_db.json')
weather_repository = OpenWeatherRepository(api_key='...')

# 2. Injetar nos use cases (Application)
use_case = GetCityWeatherUseCase(
    city_repository=city_repository,
    weather_repository=weather_repository
)

# 3. Executar use case (Presentation)
result = use_case.execute(city_id='3550308')
```

**Benefícios:**
- ✅ Facilita testes unitários (injetar mocks)
- ✅ Permite trocar implementações sem alterar use cases
- ✅ Segue o princípio SOLID de inversão de dependência

---

## 🧩 Princípios SOLID Aplicados

### **S - Single Responsibility Principle**
Cada classe tem uma única responsabilidade:
- `City` → representa uma cidade
- `MunicipalitiesRepository` → acessa dados de cidades
- `GetNeighborCitiesUseCase` → buscar vizinhos

### **O - Open/Closed Principle**
Aberto para extensão, fechado para modificação:
- Interfaces permitem adicionar novas implementações sem alterar código existente

### **L - Liskov Substitution Principle**
Implementações podem ser substituídas:
- `OpenWeatherRepository` pode ser trocado por `MockWeatherRepository` sem quebrar o código

### **I - Interface Segregation Principle**
Interfaces pequenas e específicas:
- `ICityRepository` e `IWeatherRepository` separadas

### **D - Dependency Inversion Principle**
Use cases dependem de abstrações, não de implementações concretas:
- `GetCityWeatherUseCase` depende de `IWeatherRepository` (interface), não de `OpenWeatherRepository` (implementação)

---

## 🧪 Testabilidade

A Clean Architecture facilita testes em todos os níveis:

### **Testes Unitários (Use Cases)**
```python
def test_get_neighbor_cities():
    # Criar mocks
    mock_repository = MockCityRepository()
    use_case = GetNeighborCitiesUseCase(mock_repository)
    
    # Testar
    result = use_case.execute('3550308', radius=50)
    
    # Validar
    assert len(result['neighbors']) > 0
```

### **Testes de Integração (Repositories)**
```python
def test_municipalities_repository():
    repo = MunicipalitiesRepository('test_data.json')
    city = repo.get_by_id('3550308')
    
    assert city.name == 'São Paulo'
    assert city.has_coordinates()
```

### **Testes End-to-End (Lambda Handler)**
```python
def test_lambda_handler():
    event = create_api_gateway_event('/api/cities/neighbors/3550308')
    response = lambda_handler(event, mock_context)
    
    assert response['statusCode'] == 200
```

---

## 🚀 Como Adicionar uma Nova Funcionalidade

### Exemplo: Adicionar busca de previsão do tempo

**1. Criar entidade (Domain)**
```python
# domain/entities/forecast.py
@dataclass
class Forecast:
    city_id: str
    date: datetime
    temperature: float
    ...
```

**2. Criar interface do repositório (Domain)**
```python
# domain/repositories/forecast_repository.py
class IForecastRepository(ABC):
    @abstractmethod
    def get_forecast(self, city_id: str, days: int) -> List[Forecast]:
        pass
```

**3. Criar use case (Application)**
```python
# application/use_cases/get_forecast.py
class GetForecastUseCase:
    def __init__(self, forecast_repository: IForecastRepository):
        self.forecast_repository = forecast_repository
    
    def execute(self, city_id: str, days: int):
        return self.forecast_repository.get_forecast(city_id, days)
```

**4. Implementar repositório (Infrastructure)**
```python
# infrastructure/repositories/forecast_repository.py
class OpenWeatherForecastRepository(IForecastRepository):
    def get_forecast(self, city_id: str, days: int):
        # Chamar API
        ...
```

**5. Criar rota (Presentation)**
```python
# lambda_function.py
forecast_use_case = GetForecastUseCase(forecast_repository)

@app.get("/api/weather/forecast/<city_id>")
def get_forecast_route(city_id: str):
    result = forecast_use_case.execute(city_id, days=5)
    return [f.to_api_response() for f in result]
```

---

## 📊 Benefícios da Arquitetura

### ✅ **Manutenibilidade**
- Código organizado e fácil de entender
- Cada camada tem responsabilidade clara

### ✅ **Testabilidade**
- Use cases isolados e testáveis
- Fácil criar mocks e stubs

### ✅ **Escalabilidade**
- Adicionar features sem quebrar código existente
- Trocar implementações sem afetar lógica de negócio

### ✅ **Independência de Frameworks**
- Lógica de negócio não depende de AWS Lambda
- Pode ser portada para outro ambiente facilmente

### ✅ **Reutilização de Código**
- Use cases podem ser usados em diferentes contextos
- Repositórios podem ser compartilhados

---

## 🔧 Otimizações para AWS Lambda

### **Singleton Pattern**
Repositórios são carregados uma vez e reutilizados entre invocações (Lambda warm starts):

```python
_repository_instance = None

def get_repository():
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = MunicipalitiesRepository()
    return _repository_instance
```

### **Lazy Loading**
Dados são carregados apenas quando necessário

### **Índices em Memória**
Busca O(1) para melhor performance

---

## 📚 Referências

- [Clean Architecture - Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)

---

## 🎯 Próximos Passos

- [ ] Adicionar camada de cache (Redis/DynamoDB)
- [ ] Implementar padrão Repository com cache decorator
- [ ] Adicionar testes unitários completos
- [ ] Implementar logging estruturado
- [ ] Adicionar métricas e observabilidade
- [ ] Criar factories para simplificar DI
