# Deploy Scripts Guide

## Visão Geral

Scripts automatizados para build e deploy da aplicação Weather Forecast API na AWS Lambda.

**Localização:** `/scripts`

---

## Script Principal

### `deploy-main.sh` - Deploy Completo Automatizado

Deploy completo em um único comando com validações e testes integrados.

**Uso:**
```bash
bash scripts/deploy-main.sh
```

**Fases do deploy:**

#### 1. 🔍 Validações Iniciais
- Verifica arquivos necessários (terraform.tfvars, requirements.txt)
- Valida variáveis de ambiente
- Checa dependências instaladas

#### 2. 📦 Build do Pacote Lambda
- Limpa build anterior
- Instala dependências Python em `build/package/`
- Copia código da aplicação (detecção automática de arquivos)
- Remove arquivos desnecessários (tests, cache, etc)
- Cria ZIP otimizado (~15MB)

**Detecção automática de arquivos:**
```bash
# Detecta TODOS os arquivos Python recursivamente
find "${LAMBDA_DIR}" -name "*.py" -exec cp {} "${PACKAGE_DIR}/" \;

# Copia diretórios da aplicação
for dir in domain application infrastructure shared data; do
    cp -r "${LAMBDA_DIR}/${dir}" "${PACKAGE_DIR}/"
done
```

#### 3. 🔧 Terraform Deploy
- `terraform init` - Inicializa provider
- `terraform validate` - Valida configuração
- `terraform plan` - Mostra mudanças
- `terraform apply` - Aplica mudanças na AWS

#### 4. 📊 Validação e Output
- Extrai API Gateway URL
- Salva URL em `API_URL.txt`
- Mostra resumo do deploy

---

## Exemplo de Output

```bash
🚀 Deploy Lambda Weather Forecast
===================================

🔍 FASE 1: Validações Iniciais
✓ terraform.tfvars encontrado
✓ requirements.txt encontrado
✓ Variáveis de ambiente carregadas

📦 FASE 2: Build do Pacote Lambda
🧹 Limpando build anterior...
✓ Diretório limpo

📥 Instalando dependências Python...
✓ Dependências instaladas (730 arquivos)

📂 Copiando código da aplicação...
   ✓ domain/ (8 arquivos)
   ✓ application/ (6 arquivos)
   ✓ infrastructure/ (12 arquivos)
   ✓ shared/ (5 arquivos)
   ✓ data/ (2 arquivos)

📋 Total: 33 arquivos Python detectados

🔍 Verificando arquivos críticos no ZIP...
   ✓ lambda_function.py
   ✓ config.py
   ✓ domain/entities/city.py
   ✓ domain/entities/weather.py
   ✓ application/use_cases/async_get_city_weather.py
   ✓ infrastructure/adapters/async_openweather_repository.py
   ✓ data/municipalities_db.json

✅ Pacote Lambda validado!

📦 ZIP criado: 15.2M
   📍 Local: terraform/build/lambda_function.zip

🔧 FASE 3: Terraform Deploy
Inicializando Terraform...
✓ Provider configurado
✓ Módulos baixados

Validando configuração...
✓ Configuração válida

Planejando mudanças...
Plan: 3 to add, 1 to change, 0 to destroy

Aplicando mudanças...
✓ Lambda function updated
✓ API Gateway configured
✓ DynamoDB table ready

📊 FASE 4: Outputs
🌐 API URL: https://xxxxx.execute-api.sa-east-1.amazonaws.com/prod
   (Salvo em API_URL.txt)

═══════════════════════════════════════
🎉 Deploy Finalizado com Sucesso!
═══════════════════════════════════════
✓ Build do pacote Lambda (15.2M)
✓ Deploy AWS (Terraform)
✓ API Gateway URL disponível
```

---

## Scripts Auxiliares

### `load_env.sh` - Carrega Variáveis de Ambiente

Carrega variáveis do arquivo `.env` no shell atual.

**Uso:**
```bash
source scripts/load_env.sh
```

**Variáveis carregadas:**
- `OPENWEATHER_API_KEY`
- `DYNAMODB_CACHE_TABLE`
- `AWS_DEFAULT_REGION`
- `ENVIRONMENT`

### `run_tests.sh` - Executa Testes

Executa testes locais antes ou depois do deploy.

**Uso:**
```bash
# Todos os testes
bash scripts/run_tests.sh

# Apenas integration tests
bash scripts/run_tests.sh integration

# Apenas unit tests
bash scripts/run_tests.sh unit
```

---

## Estrutura do Build

### Diretório de Build

```
scripts/build/
├── package/              # Pacote Lambda temporário
│   ├── lambda_function.py
│   ├── config.py
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   ├── shared/
│   ├── data/
│   └── <730 dependências>
└── lambda_function.zip   # ZIP final (~15MB)
```

### Arquivos Críticos Validados

O script verifica presença de:
- ✅ `lambda_function.py` - Entry point
- ✅ `config.py` - Configurações
- ✅ `domain/entities/city.py` - Entidade City
- ✅ `domain/entities/weather.py` - Entidade Weather
- ✅ `application/use_cases/async_get_city_weather.py` - Use case principal
- ✅ `infrastructure/adapters/async_openweather_repository.py` - Repository
- ✅ `data/municipalities_db.json` - Base de 5.571 cidades

### Arquivos Removidos (otimização)

```bash
# Remove arquivos desnecessários para reduzir tamanho do ZIP
find "${PACKAGE_DIR}" -type d -name "__pycache__" -exec rm -rf {} +
find "${PACKAGE_DIR}" -type d -name "tests" -exec rm -rf {} +
find "${PACKAGE_DIR}" -type d -name ".pytest_cache" -exec rm -rf {} +
find "${PACKAGE_DIR}" -type f -name "*.pyc" -delete
find "${PACKAGE_DIR}" -type f -name "*.pyo" -delete
find "${PACKAGE_DIR}" -type f -name ".DS_Store" -delete
```

---

## Troubleshooting

### ❌ Erro: "terraform.tfvars not found"

**Solução:**
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars  # Configurar variáveis
```

### ❌ Erro: "Arquivo crítico faltando no ZIP"

O script para automaticamente se detectar arquivos faltando:

```bash
❌ Erro: Arquivos críticos faltando no ZIP!
   ✗ domain/entities/weather.py (FALTANDO!)
```

**Solução:**
1. Verificar se arquivo existe em `lambda/`
2. Verificar permissões do arquivo
3. Re-executar o script

### ❌ Erro: "AWS credentials not configured"

**Solução:**
```bash
aws configure
# Input: Access Key ID, Secret Access Key, Region
```

### ❌ ZIP muito grande (>50MB)

Lambda tem limite de 50MB (zipado) ou 250MB (descompactado).

**Otimizações aplicadas:**
- Remove `__pycache__/`, `tests/`, `.pytest_cache/`
- Remove `*.pyc`, `*.pyo`
- Usa apenas dependências necessárias

**Verificar tamanho:**
```bash
du -h terraform/build/lambda_function.zip
```

---

## Boas Práticas

### ✅ DO

1. **Sempre testar localmente antes do deploy**
   ```bash
   pytest lambda/tests/ -v
   ```

2. **Verificar terraform plan antes de apply**
   ```bash
   cd terraform
   terraform plan
   ```

3. **Fazer backup do estado do Terraform**
   ```bash
   cp terraform.tfstate terraform.tfstate.backup
   ```

4. **Validar API após deploy**
   ```bash
   API_URL=$(cat API_URL.txt)
   curl "$API_URL/api/cities/neighbors/3543204"
   ```

### ❌ DON'T

1. **❌ Não commitar secrets**
   ```bash
   # .gitignore
   terraform.tfvars
   .env
   *.tfstate
   ```

2. **❌ Não deployar sem testar**
   ```bash
   # Sempre rodar testes primeiro
   pytest && bash scripts/deploy-main.sh
   ```

3. **❌ Não ignorar warnings do Terraform**
   ```bash
   # Revisar warnings antes de apply
   ```

---

## Integração com CI/CD

### GitHub Actions Workflow

```yaml
name: Deploy to AWS

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.13'
    
    - name: Install dependencies
      run: |
        pip install -r lambda/requirements.txt
        pip install -r lambda/requirements-dev.txt
    
    - name: Run tests
      run: pytest lambda/tests/ -v
    
    - name: Configure AWS
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: sa-east-1
    
    - name: Deploy
      run: bash scripts/deploy-main.sh
```

---

## Referências

- **Terraform AWS Provider:** https://registry.terraform.io/providers/hashicorp/aws/
- **AWS Lambda Deployment:** https://docs.aws.amazon.com/lambda/latest/dg/lambda-deploy-functions.html
- **Lambda Layer Best Practices:** https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html

📖 **Ver também:**
- [Development Workflow](WORKFLOW.md) - Guia completo de desenvolvimento
- [Testing Guide](TESTING.md) - Como testar a aplicação
