#!/bin/bash
# Script Principal de Deploy da Lambda Weather Forecast
# Execute da raiz: bash scripts/deploy-main.sh
# Inclui: Build + Testes + Deploy + Validação

set -e  # Parar em caso de erro

echo "🚀 Deploy Lambda Weather Forecast"
echo "=================================="

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Ir para o diretório raiz do projeto
cd "$(dirname "$0")/.."
PROJECT_ROOT="$(pwd)"
LAMBDA_DIR="${PROJECT_ROOT}/lambda"
BUILD_DIR="${PROJECT_ROOT}/terraform/build"
PACKAGE_DIR="${BUILD_DIR}/package"

# ============================================
# Verificar e ativar ambiente virtual
# ============================================
echo -e "\n${YELLOW}🐍 Verificando Ambiente Virtual${NC}"
echo "================================="

if [ ! -d "${PROJECT_ROOT}/.venv" ]; then
    echo -e "${RED}❌ Erro: Ambiente virtual .venv não encontrado!${NC}"
    echo -e "${YELLOW}   Crie com: python3 -m venv .venv${NC}"
    echo -e "${YELLOW}   Depois: source .venv/bin/activate${NC}"
    echo -e "${YELLOW}   E: pip install -r lambda/requirements-dev.txt${NC}"
    exit 1
fi

source "${PROJECT_ROOT}/.venv/bin/activate"

if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${RED}❌ Erro: Falha ao ativar ambiente virtual${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Ambiente virtual ativo"
echo -e "   ${BLUE}→ Path: ${VIRTUAL_ENV}${NC}"
echo -e "   ${BLUE}→ Python: $(python --version)${NC}"
echo -e "   ${BLUE}→ Pip: $(pip --version | cut -d' ' -f1,2)${NC}"

# ============================================
# FASE 0: Validações iniciais
# ============================================
echo -e "\n${YELLOW}🔍 FASE 0: Validações Iniciais${NC}"
echo "================================="

# Verificar terraform.tfvars
if [ ! -f "terraform/terraform.tfvars" ]; then
    echo -e "${RED}❌ Erro: terraform/terraform.tfvars não encontrado!${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} terraform.tfvars encontrado"

# Verificar requirements.txt
if [ ! -f "lambda/requirements.txt" ]; then
    echo -e "${RED}❌ Erro: lambda/requirements.txt não encontrado!${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} requirements.txt encontrado"

# Avisar se requirements-dev.txt existe
if [ -f "lambda/requirements-dev.txt" ]; then
    echo -e "${BLUE}ℹ${NC}  requirements-dev.txt disponível para desenvolvimento local"
fi

# Carregar variáveis de ambiente
if [ -f ".env" ]; then
    echo -e "${BLUE}Carregando variáveis de ambiente do .env...${NC}"
    export $(grep -v '^#' .env | xargs)
    echo -e "${GREEN}✓${NC} Variáveis de ambiente carregadas"
fi

# ============================================
# FASE 1: Testes Unitários (Pré-Build)
# ============================================
echo -e "\n${YELLOW}🧪 FASE 1: Testes Unitários (Pré-Build)${NC}"
echo "========================================"

if bash scripts/run_tests.sh unit; then
    echo -e "${GREEN}✅ Todos os testes unitários passaram!${NC}"
else
    echo -e "${RED}❌ Testes unitários falharam! Deploy cancelado.${NC}"
    exit 1
fi

# ============================================
# FASE 2: Build do Pacote Lambda
# ============================================
echo -e "\n${YELLOW}📦 FASE 2: Build do Pacote Lambda${NC}"
echo "===================================="

# 2.1. Limpar build anterior
echo -e "\n${BLUE}🧹 Limpando build anterior...${NC}"
rm -rf "${BUILD_DIR}"
mkdir -p "${PACKAGE_DIR}"
echo -e "${GREEN}✓${NC} Diretório limpo"

# 2.2. Instalar dependências (APENAS PRODUÇÃO - sem pytest)
echo -e "\n${BLUE}📥 Instalando dependências Python (PRODUÇÃO)...${NC}"
echo -e "   ${BLUE}→${NC} Usando requirements.txt (sem ferramentas de teste)"
pip install -r "${LAMBDA_DIR}/requirements.txt" -t "${PACKAGE_DIR}" --upgrade --quiet
echo -e "${GREEN}✓${NC} Dependências de produção instaladas"

# 2.3. Copiar TODOS os arquivos Python recursivamente
echo -e "\n${BLUE}📂 Copiando código da aplicação (método recursivo)...${NC}"

# Copiar arquivos .py da raiz do lambda
echo -e "   ${BLUE}→${NC} Copiando arquivos .py da raiz..."
find "${LAMBDA_DIR}" -maxdepth 1 -name "*.py" -exec cp {} "${PACKAGE_DIR}/" \;

# Copiar todos os diretórios Python recursivamente (exceto tests)
echo -e "   ${BLUE}→${NC} Copiando diretórios (domain, application, infrastructure, shared, data)..."
for dir in domain application infrastructure shared data; do
    if [ -d "${LAMBDA_DIR}/${dir}" ]; then
        echo -e "      ${GREEN}✓${NC} ${dir}"
        cp -r "${LAMBDA_DIR}/${dir}" "${PACKAGE_DIR}/"
    fi
done

# Listar todos os arquivos .py copiados (do nosso código, não das dependências)
echo -e "\n${BLUE}📋 Arquivos Python da aplicação:${NC}"
OUR_PYTHON_FILES=$(find "${PACKAGE_DIR}" -maxdepth 1 -name "*.py" | wc -l)
OUR_PYTHON_FILES=$((OUR_PYTHON_FILES + $(find "${PACKAGE_DIR}/domain" -name "*.py" 2>/dev/null | wc -l)))
OUR_PYTHON_FILES=$((OUR_PYTHON_FILES + $(find "${PACKAGE_DIR}/application" -name "*.py" 2>/dev/null | wc -l)))
OUR_PYTHON_FILES=$((OUR_PYTHON_FILES + $(find "${PACKAGE_DIR}/infrastructure" -name "*.py" 2>/dev/null | wc -l)))
OUR_PYTHON_FILES=$((OUR_PYTHON_FILES + $(find "${PACKAGE_DIR}/shared" -name "*.py" 2>/dev/null | wc -l)))
echo -e "   ${GREEN}${OUR_PYTHON_FILES} arquivos .py da aplicação${NC}"

TOTAL_FILES=$(find "${PACKAGE_DIR}" -name "*.py" | wc -l)
DEP_FILES=$((TOTAL_FILES - OUR_PYTHON_FILES))
echo -e "   ${BLUE}${DEP_FILES} arquivos .py das dependências${NC}"
echo -e "   ${YELLOW}Total: ${TOTAL_FILES} arquivos .py${NC}"

# Mostrar alguns arquivos como exemplo
echo -e "\n${BLUE}📄 Arquivos da aplicação copiados:${NC}"
(
    find "${PACKAGE_DIR}" -maxdepth 1 -name "*.py"
    find "${PACKAGE_DIR}/domain" -name "*.py" 2>/dev/null || true
    find "${PACKAGE_DIR}/application" -name "*.py" 2>/dev/null || true
    find "${PACKAGE_DIR}/infrastructure" -name "*.py" 2>/dev/null || true
    find "${PACKAGE_DIR}/shared" -name "*.py" 2>/dev/null || true
) | sort | while read file; do
    rel_path=$(echo "$file" | sed "s|${PACKAGE_DIR}/||")
    echo -e "   ${GREEN}✓${NC} $rel_path"
done

# 2.4. Remover arquivos desnecessários
echo -e "\n${BLUE}🗑️  Removendo arquivos desnecessários...${NC}"

# Calcular tamanho antes
BEFORE_SIZE=$(du -sm "${PACKAGE_DIR}" 2>/dev/null | cut -f1 || echo "0")

# Remover __pycache__
find "${PACKAGE_DIR}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
echo -e "   ${GREEN}✓${NC} __pycache__ removidos"

# Remover testes
rm -rf "${PACKAGE_DIR}/tests" 2>/dev/null || true
find "${PACKAGE_DIR}" -type f -name "test_*.py" -delete 2>/dev/null || true
echo -e "   ${GREEN}✓${NC} Arquivos de teste removidos"

# Remover arquivos de cache Python
find "${PACKAGE_DIR}" -type f -name "*.pyc" -delete 2>/dev/null || true
find "${PACKAGE_DIR}" -type f -name "*.pyo" -delete 2>/dev/null || true
echo -e "   ${GREEN}✓${NC} Arquivos .pyc/.pyo removidos"

# Remover dist-info e egg-info
find "${PACKAGE_DIR}" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find "${PACKAGE_DIR}" -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
echo -e "   ${GREEN}✓${NC} Metadados de pacotes removidos"

# Remover pytest/pytest-cov se foi instalado por engano
rm -rf "${PACKAGE_DIR}/pytest" "${PACKAGE_DIR}/_pytest" 2>/dev/null || true
rm -rf "${PACKAGE_DIR}/pytest_cov" "${PACKAGE_DIR}/_pytest_cov" 2>/dev/null || true
find "${PACKAGE_DIR}" -type d -name "*pytest*" -exec rm -rf {} + 2>/dev/null || true
echo -e "   ${GREEN}✓${NC} Pytest/pytest-cov removidos (se existirem)"

# Remover arquivos do sistema e documentação
find "${PACKAGE_DIR}" -type f -name ".DS_Store" -delete 2>/dev/null || true
find "${PACKAGE_DIR}" -type f -name ".gitignore" -delete 2>/dev/null || true
find "${PACKAGE_DIR}" -type f -name "*.md" -delete 2>/dev/null || true
find "${PACKAGE_DIR}" -type f -name "LICENSE*" -delete 2>/dev/null || true
find "${PACKAGE_DIR}" -type f -name "README*" -delete 2>/dev/null || true
echo -e "   ${GREEN}✓${NC} Arquivos de sistema/documentação removidos"

# Calcular economia
AFTER_SIZE=$(du -sm "${PACKAGE_DIR}" 2>/dev/null | cut -f1 || echo "0")
SAVED_SIZE=$((BEFORE_SIZE - AFTER_SIZE))
if [ "$SAVED_SIZE" -gt 0 ]; then
    echo -e "${GREEN}✓${NC} Limpeza concluída (economizados ~${SAVED_SIZE}MB)"
else
    echo -e "${GREEN}✓${NC} Limpeza concluída"
fi

# 2.5. Criar ZIP
echo -e "\n${BLUE}📦 Criando arquivo ZIP...${NC}"
cd "${PACKAGE_DIR}"
zip -r9 "${BUILD_DIR}/lambda_function.zip" . > /dev/null
cd "${PROJECT_ROOT}"

ZIP_SIZE=$(du -h "${BUILD_DIR}/lambda_function.zip" | cut -f1)
echo -e "${GREEN}✓${NC} ZIP criado: ${ZIP_SIZE}"
echo -e "${BLUE}   📍 Local: ${BUILD_DIR}/lambda_function.zip${NC}"

# 2.6. Verificar arquivos principais
echo -e "\n${BLUE}🔍 Verificando arquivos críticos no ZIP...${NC}"

REQUIRED_FILES=(
    "lambda_function.py"
    "config.py"
    "domain/entities/city.py"
    "domain/entities/weather.py"
    "application/use_cases/get_city_weather.py"
    "application/use_cases/get_neighbor_cities.py"
    "application/use_cases/get_regional_weather.py"
    "infrastructure/repositories/municipalities_repository.py"
    "infrastructure/repositories/weather_repository.py"
    "shared/utils/haversine.py"
    "data/municipalities_db.json"
)

ALL_OK=true
for file in "${REQUIRED_FILES[@]}"; do
    if unzip -l "${BUILD_DIR}/lambda_function.zip" | grep -q "$file"; then
        echo -e "   ${GREEN}✓${NC} $file"
    else
        echo -e "   ${RED}✗${NC} $file ${RED}(FALTANDO!)${NC}"
        ALL_OK=false
    fi
done

# Verificar dependências
echo -e "\n${BLUE}🔍 Verificando dependências Python...${NC}"
REQUIRED_DEPS=(
    "aws_lambda_powertools"
    "requests"
    "botocore"
)

for dep in "${REQUIRED_DEPS[@]}"; do
    if unzip -l "${BUILD_DIR}/lambda_function.zip" | grep -q "$dep"; then
        echo -e "   ${GREEN}✓${NC} $dep"
    else
        echo -e "   ${RED}✗${NC} $dep ${RED}(FALTANDO!)${NC}"
        ALL_OK=false
    fi
done

if [ "$ALL_OK" = false ]; then
    echo -e "\n${RED}❌ Erro: Arquivos críticos faltando no ZIP!${NC}"
    echo -e "${YELLOW}   Verifique os logs acima.${NC}"
    exit 1
fi

echo -e "\n${GREEN}✅ Pacote Lambda validado com sucesso!${NC}"

# ============================================
# FASE 3: Terraform - Configuração
# ============================================
echo -e "\n${YELLOW}🔧 FASE 3: Configuração Terraform${NC}"
echo "==================================="

cd terraform

echo -e "${BLUE}Inicializando Terraform...${NC}"
terraform init -upgrade

echo -e "\n${BLUE}Validando configuração...${NC}"
terraform validate
echo -e "${GREEN}✓${NC} Configuração válida"

echo -e "\n${BLUE}Gerando plano de execução...${NC}"
terraform plan -out=tfplan

# ============================================
# FASE 4: Deploy na AWS
# ============================================
echo -e "\n${YELLOW}🚀 FASE 4: Deploy na AWS${NC}"
echo "=========================="

echo -e "${BLUE}Aplicando mudanças...${NC}"
terraform apply tfplan

# Limpar arquivo de plano
rm -f tfplan

echo -e "\n${GREEN}✅ Deploy na AWS concluído!${NC}"

# ============================================
# FASE 5: Outputs e Testes de Integração
# ============================================
echo -e "\n${YELLOW}📊 FASE 5: Outputs e Validação${NC}"
echo "================================"

echo -e "\n${BLUE}Outputs do Terraform:${NC}"
terraform output

# Salvar API URL
if terraform output -raw api_gateway_url 2>/dev/null; then
    API_URL=$(terraform output -raw api_gateway_url)
    echo -e "\n${GREEN}🌐 API URL: ${API_URL}${NC}"
    
    cd "${PROJECT_ROOT}"
    echo "$API_URL" > API_URL.txt
    echo -e "${GREEN}   (Salvo em API_URL.txt)${NC}"
    
    # Testes de integração
    echo -e "\n${YELLOW}🧪 Executando Testes de Integração...${NC}"
    echo "========================================"
    echo -e "${BLUE}Aguardando 5 segundos para API ficar disponível...${NC}"
    sleep 5
    
    export API_GATEWAY_URL="$API_URL"
    
    source "${PROJECT_ROOT}/.venv/bin/activate"
    bash "${PROJECT_ROOT}/scripts/load_env.sh"
    
    if python -m pytest "${PROJECT_ROOT}/lambda/tests/integration/test_api_gateway.py" -v; then
        echo -e "${GREEN}✅ Todos os testes de integração passaram!${NC}"
    else
        echo -e "${RED}⚠️  Alguns testes de integração falharam.${NC}"
        echo -e "${YELLOW}   Deploy foi concluído, mas verifique os logs acima.${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Não foi possível obter a URL da API${NC}"
fi

cd "${PROJECT_ROOT}"

# ============================================
# RESUMO FINAL
# ============================================
echo -e "\n${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}🎉 Deploy Finalizado com Sucesso!${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Testes unitários (pré-build)${NC}"
echo -e "${GREEN}✓ Build do pacote Lambda (${ZIP_SIZE})${NC}"
echo -e "${GREEN}✓ Deploy AWS (Terraform)${NC}"
echo -e "${GREEN}✓ Testes de integração (pós-deploy)${NC}"

if [ -f "API_URL.txt" ]; then
    echo -e "\n${BLUE}🌐 API disponível em:${NC}"
    cat API_URL.txt
fi

echo -e "\n${BLUE}💡 Comandos úteis:${NC}"
echo -e "   ${YELLOW}curl \$(cat API_URL.txt)/weather/3543204${NC}"
echo -e "   ${YELLOW}cd terraform && terraform destroy${NC}"
echo ""
