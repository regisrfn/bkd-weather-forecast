# Testes de Integração

Organização dos testes de integração por fase de deploy.

## 📁 Estrutura

```
integration/
├── pre_deploy/          # Testes executados ANTES do deploy (8 testes)
│   ├── test_detailed_forecast_endpoint.py    # 4 testes
│   └── test_hourly_enrichment.py             # 4 testes
├── post_deploy/         # Testes executados APÓS o deploy (1 teste)
│   └── test_api_gateway.py                   # Valida API Gateway
├── test_lambda_integration.py                # Teste legacy
├── conftest.py          # Fixtures compartilhadas
└── assertions.py        # Funções de validação

Total: 8 testes pré-deploy + testes pós-deploy
```

## 🧪 Tipos de Testes

### Pre-Deploy (`pre_deploy/`)

Executados **antes** do build e deploy na AWS. Validam:

#### `test_detailed_forecast_endpoint.py` (4 testes)
- ✅ Sucesso com dados reais de API externa
- ✅ Cidade não encontrada (404)
- ✅ ID inválido (400)
- ✅ Query parameter `date` funcional

**O que valida:**
- Lambda handler funciona corretamente
- Integração com Open-Meteo API (daily + hourly)
- Extração de current a partir do hourly
- Cache DynamoDB (TTL 1h para hourly, 6h para daily)
- Tratamento de erros

#### `test_hourly_enrichment.py` (4 testes)
- ✅ Current weather enriquecido com hourly data
- ✅ Array de 168 hourly forecasts disponível
- ✅ Backward compatibility (18 campos originais + 2 novos)
- ✅ Graceful degradation (funciona se hourly falhar)

**O que valida:**
- Enriquecimento mantém campos essenciais (visibility, pressure, feels_like)
- Wind direction de Open-Meteo hourly (0-360°)
- Cálculos diários (rain accumulation, temp extremes)

### Post-Deploy (`post_deploy/`)

Executados **após** o deploy na AWS. Validam:

#### `test_api_gateway.py`
- ✅ API Gateway respondendo
- ✅ Lambda invocada corretamente
- ✅ Endpoints acessíveis via HTTPS

**Requer:** `API_GATEWAY_URL` env var ou `API_URL.txt`

## 🚀 Executando os Testes

### Via Script

```bash
# Apenas testes pré-deploy (usado no deploy-main.sh)
bash scripts/run_tests.sh pre-deploy

# Apenas testes pós-deploy
bash scripts/run_tests.sh post-deploy

# Todos os testes de integração
bash scripts/run_tests.sh integration
```

### Via Pytest

```bash
# Testes pré-deploy
python -m pytest lambda/tests/integration/pre_deploy/ -v

# Testes pós-deploy
export API_GATEWAY_URL="https://..."
python -m pytest lambda/tests/integration/post_deploy/ -v

# Todos
python -m pytest lambda/tests/integration/ -v
```

## ⚙️ Uso no Deploy

O script `deploy-main.sh` usa esta estrutura:

```bash
# FASE 1: Testes Pré-Build
bash scripts/run_tests.sh pre-deploy
# → 29 unit tests + 8 integration pre-deploy = 37 testes

# FASE 2-4: Build + Terraform + Deploy

# FASE 5: Testes Pós-Deploy
bash scripts/run_tests.sh post-deploy
# → Valida API Gateway
```

## 📝 Adicionando Novos Testes

### Teste Pré-Deploy

Adicione em `pre_deploy/` se o teste:
- ✅ Valida lógica de negócio
- ✅ Testa integração com APIs externas
- ✅ Valida cache/persistência
- ✅ **NÃO** requer API Gateway

### Teste Pós-Deploy

Adicione em `post_deploy/` se o teste:
- ✅ Valida API Gateway
- ✅ Testa endpoints HTTPS
- ✅ Valida infraestrutura AWS
- ✅ **REQUER** deploy completo

## 🔧 Benefícios da Organização

### ✅ Clareza
- Fácil identificar quando cada teste roda
- Separação clara de responsabilidades

### ✅ Performance
- Testes pré-deploy rodam localmente (rápido)
- Testes pós-deploy só quando necessário (após deploy)

### ✅ CI/CD Ready
- Fácil integrar em pipelines
- Separação de stages (build vs deploy)

### ✅ Manutenção
- Pytest descobre automaticamente por pasta
- Fácil adicionar/remover testes

## 📊 Cobertura

| Camada | Cobertura | Testes |
|--------|-----------|--------|
| **Unit** | Entidades, helpers, repositories | 29 |
| **Integration Pre-Deploy** | Lambda handler, APIs externas | 8 |
| **Integration Post-Deploy** | API Gateway, infraestrutura | 1+ |
| **TOTAL** | - | **37+** |

---

**Última atualização:** Dezembro 2025  
**Testes passando:** ✅ 37/37
