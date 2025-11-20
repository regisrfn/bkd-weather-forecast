#!/bin/bash
# Script para criar pacote Lambda com dependências
# Execute: bash build-lambda.sh

set -e  # Parar em caso de erro

echo "📦 Criando pacote Lambda com dependências"
echo "=========================================="

# Diretórios
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAMBDA_DIR="${SCRIPT_DIR}/../lambda"
BUILD_DIR="${SCRIPT_DIR}/build"
PACKAGE_DIR="${BUILD_DIR}/package"

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. Limpar build anterior
echo -e "\n${BLUE}1️⃣  Limpando build anterior...${NC}"
rm -rf "${BUILD_DIR}"
mkdir -p "${PACKAGE_DIR}"

# 2. Instalar dependências
echo -e "\n${BLUE}2️⃣  Instalando dependências Python...${NC}"
pip install -r "${LAMBDA_DIR}/requirements.txt" -t "${PACKAGE_DIR}" --upgrade

# 3. Copiar código da aplicação
echo -e "\n${BLUE}3️⃣  Copiando código da aplicação...${NC}"
cp -r "${LAMBDA_DIR}"/*.py "${PACKAGE_DIR}/" 2>/dev/null || true
cp -r "${LAMBDA_DIR}"/domain "${PACKAGE_DIR}/" 2>/dev/null || true
cp -r "${LAMBDA_DIR}"/application "${PACKAGE_DIR}/" 2>/dev/null || true
cp -r "${LAMBDA_DIR}"/infrastructure "${PACKAGE_DIR}/" 2>/dev/null || true
cp -r "${LAMBDA_DIR}"/shared "${PACKAGE_DIR}/" 2>/dev/null || true
cp -r "${LAMBDA_DIR}"/data "${PACKAGE_DIR}/" 2>/dev/null || true

# 4. Remover arquivos desnecessários
echo -e "\n${BLUE}4️⃣  Removendo arquivos desnecessários...${NC}"
find "${PACKAGE_DIR}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${PACKAGE_DIR}" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find "${PACKAGE_DIR}" -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
find "${PACKAGE_DIR}" -type f -name "*.pyc" -delete 2>/dev/null || true
find "${PACKAGE_DIR}" -type f -name "*.pyo" -delete 2>/dev/null || true
find "${PACKAGE_DIR}" -type f -name ".DS_Store" -delete 2>/dev/null || true

# Remover arquivos de teste
rm -f "${PACKAGE_DIR}"/test_*.py 2>/dev/null || true
rm -f "${PACKAGE_DIR}"/load_env.py 2>/dev/null || true
rm -f "${PACKAGE_DIR}"/load_env.sh 2>/dev/null || true
rm -f "${PACKAGE_DIR}"/lambda_function_old.py 2>/dev/null || true

# 5. Criar ZIP
echo -e "\n${BLUE}5️⃣  Criando arquivo ZIP...${NC}"
cd "${PACKAGE_DIR}"
zip -r9 "${BUILD_DIR}/lambda_function.zip" . > /dev/null

# 6. Informações do pacote
echo -e "\n${GREEN}✅ Pacote criado com sucesso!${NC}"
ZIP_SIZE=$(du -h "${BUILD_DIR}/lambda_function.zip" | cut -f1)
echo -e "${BLUE}📦 Tamanho: ${ZIP_SIZE}${NC}"
echo -e "${BLUE}📍 Local: ${BUILD_DIR}/lambda_function.zip${NC}"

# 7. Listar conteúdo (primeiros arquivos)
echo -e "\n${BLUE}📄 Conteúdo do pacote (primeiros 20 arquivos):${NC}"
unzip -l "${BUILD_DIR}/lambda_function.zip" | head -25

# 8. Verificar arquivos principais
echo -e "\n${BLUE}🔍 Verificando arquivos principais...${NC}"
REQUIRED_FILES=(
    "lambda_function.py"
    "domain/entities/city.py"
    "domain/entities/weather.py"
    "application/use_cases/get_neighbor_cities.py"
    "infrastructure/repositories/municipalities_repository.py"
    "data/municipalities_db.json"
)

ALL_OK=true
for file in "${REQUIRED_FILES[@]}"; do
    if unzip -l "${BUILD_DIR}/lambda_function.zip" | grep -q "$file"; then
        echo -e "  ${GREEN}✓${NC} $file"
    else
        echo -e "  ${YELLOW}✗${NC} $file ${YELLOW}(não encontrado)${NC}"
        ALL_OK=false
    fi
done

# 9. Verificar dependências
echo -e "\n${BLUE}🔍 Verificando dependências...${NC}"
REQUIRED_DEPS=(
    "aws_lambda_powertools"
    "requests"
)

for dep in "${REQUIRED_DEPS[@]}"; do
    if unzip -l "${BUILD_DIR}/lambda_function.zip" | grep -q "$dep"; then
        echo -e "  ${GREEN}✓${NC} $dep"
    else
        echo -e "  ${YELLOW}✗${NC} $dep ${YELLOW}(não encontrado)${NC}"
        ALL_OK=false
    fi
done

if [ "$ALL_OK" = true ]; then
    echo -e "\n${GREEN}🎉 Pacote Lambda pronto para deploy!${NC}"
else
    echo -e "\n${YELLOW}⚠️  Alguns arquivos podem estar faltando${NC}"
fi

echo -e "\n${BLUE}💡 Próximos passos:${NC}"
echo -e "   1. cd terraform"
echo -e "   2. terraform apply"
