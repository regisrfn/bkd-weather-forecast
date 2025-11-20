#!/bin/bash
# Script de Deploy da Lambda Weather Forecast
# Execute da raiz: bash scripts/deploy.sh
# Inclui testes locais (pré-deploy) e testes de integração (pós-deploy)

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

# 1. Verificar se terraform.tfvars existe
if [ ! -f "terraform/terraform.tfvars" ]; then
    echo -e "${RED}❌ Erro: terraform/terraform.tfvars não encontrado!${NC}"
    exit 1
fi

# 2. Executar testes unitários ANTES do build
echo -e "\n${YELLOW}🧪 FASE 1: Testes Unitários (Pré-Build)${NC}"
echo "========================================"
echo -e "${BLUE}Executando testes unitários antes do build...${NC}"

# Carregar variáveis de ambiente do .env
if [ -f ".env" ]; then
    echo -e "${BLUE}Carregando variáveis de ambiente...${NC}"
    export $(grep -v '^#' .env | xargs)
fi

# Executar apenas testes unitários no pré-build
if bash scripts/run_tests.sh unit; then
    echo -e "${GREEN}✅ Todos os testes unitários passaram!${NC}"
else
    echo -e "${RED}❌ Testes unitários falharam! Deploy cancelado.${NC}"
    exit 1
fi

# 3. Build Lambda com dependências
echo -e "\n${YELLOW}📦 FASE 2: Build do Pacote Lambda${NC}"
echo "===================================="
echo -e "${BLUE}Criando pacote Lambda com dependências...${NC}"

cd terraform
bash ../scripts/build-lambda.sh

if [ ! -f "build/lambda_function.zip" ]; then
    echo -e "${RED}❌ Erro: Falha ao criar pacote Lambda${NC}"
    exit 1
fi

# 4. Terraform Init
echo -e "\n${YELLOW}🔧 FASE 3: Configuração Terraform${NC}"
echo "==================================="
echo -e "${BLUE}Inicializando Terraform...${NC}"
terraform init

# 5. Terraform Validate
echo -e "\n${BLUE}Validando configuração...${NC}"
terraform validate

# 6. Terraform Plan
echo -e "\n${BLUE}Gerando plano de execução...${NC}"
terraform plan -out=tfplan

# 7. Terraform Apply (sem confirmação manual para automação)
echo -e "\n${YELLOW}🚀 FASE 4: Deploy na AWS${NC}"
echo "=========================="
echo -e "${BLUE}Aplicando mudanças automaticamente...${NC}"
terraform apply tfplan

# 8. Limpar arquivo de plano
rm -f tfplan

# 9. Mostrar outputs
echo -e "\n${GREEN}✅ Deploy na AWS concluído!${NC}"
echo -e "\n${BLUE}📊 Outputs:${NC}"
terraform output

# 10. Salvar API URL
if terraform output -raw api_gateway_url 2>/dev/null; then
    API_URL=$(terraform output -raw api_gateway_url)
    echo -e "\n${GREEN}🌐 API URL: ${API_URL}${NC}"
    cd "$PROJECT_ROOT"
    echo "$API_URL" > API_URL.txt
    echo -e "${GREEN}   (Salvo em API_URL.txt)${NC}"
    
    # 11. Executar testes de integração DEPOIS do deploy
    echo -e "\n${YELLOW}🧪 FASE 5: Testes de Integração (Pós-Deploy)${NC}"
    echo "=============================================="
    echo -e "${BLUE}Aguardando 5 segundos para API ficar disponível...${NC}"
    sleep 5
    
    echo -e "${BLUE}Executando testes de integração no API Gateway...${NC}"
    
    # Exportar URL para o script de teste
    export API_GATEWAY_URL="$API_URL"
    
    # Ativar ambiente virtual e executar testes de integração
    source "$PROJECT_ROOT/.venv/bin/activate"
    bash "$PROJECT_ROOT/scripts/load_env.sh"
    
    if python -m pytest "$PROJECT_ROOT/lambda/tests/integration/test_api_gateway.py" -v; then
        echo -e "${GREEN}✅ Todos os testes de integração passaram!${NC}"
    else
        echo -e "${RED}⚠️  Alguns testes de integração falharam.${NC}"
        echo -e "${YELLOW}   Deploy foi concluído, mas verifique os logs acima.${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Não foi possível obter a URL da API${NC}"
fi

cd "$PROJECT_ROOT"

echo -e "\n${GREEN}🎉 Deploy finalizado com sucesso!${NC}"
echo -e "${GREEN}   Testes unitários (pré-build): ✅${NC}"
echo -e "${GREEN}   Deploy AWS: ✅${NC}"
echo -e "${GREEN}   Testes integração (pós-deploy): Verifique logs acima${NC}"

