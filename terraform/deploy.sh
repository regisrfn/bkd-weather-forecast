#!/bin/bash
# Script de Deploy da Lambda Weather Forecast
# Execute: bash deploy.sh
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

# 1. Verificar se está no diretório correto
if [ ! -f "terraform.tfvars" ]; then
    echo -e "${RED}❌ Erro: Execute este script do diretório terraform/${NC}"
    exit 1
fi

# 2. Executar testes locais ANTES do build
echo -e "\n${YELLOW}🧪 FASE 1: Testes Locais (Pré-Deploy)${NC}"
echo "========================================"
echo -e "${BLUE}Executando testes unitários do Lambda...${NC}"

cd ../lambda

# Executar testes locais
if python test_lambda.py; then
    echo -e "${GREEN}✅ Todos os testes locais passaram!${NC}"
else
    echo -e "${RED}❌ Testes locais falharam! Deploy cancelado.${NC}"
    exit 1
fi

cd ../terraform

# 3. Build Lambda com dependências
echo -e "\n${YELLOW}📦 FASE 2: Build do Pacote Lambda${NC}"
echo "===================================="
echo -e "${BLUE}Criando pacote Lambda com dependências...${NC}"
bash build-lambda.sh

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

# 7. Perguntar confirmação
echo -e "\n${BLUE}Revisar o plano acima${NC}"
read -p "Deseja aplicar as mudanças? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo -e "${RED}❌ Deploy cancelado${NC}"
    rm -f tfplan
    exit 0
fi

# 8. Terraform Apply
echo -e "\n${YELLOW}🚀 FASE 4: Deploy na AWS${NC}"
echo "=========================="
echo -e "${BLUE}Aplicando mudanças...${NC}"
terraform apply tfplan

# 9. Limpar arquivo de plano
rm -f tfplan

# 10. Mostrar outputs
echo -e "\n${GREEN}✅ Deploy na AWS concluído!${NC}"
echo -e "\n${BLUE}📊 Outputs:${NC}"
terraform output

# 11. Salvar API URL
if terraform output -raw api_gateway_url 2>/dev/null; then
    API_URL=$(terraform output -raw api_gateway_url)
    echo -e "\n${GREEN}🌐 API URL: ${API_URL}${NC}"
    echo "$API_URL" > ../API_URL.txt
    echo -e "${GREEN}   (Salvo em API_URL.txt)${NC}"
    
    # 12. Executar testes de integração DEPOIS do deploy
    echo -e "\n${YELLOW}🧪 FASE 5: Testes de Integração (Pós-Deploy)${NC}"
    echo "=============================================="
    echo -e "${BLUE}Aguardando 5 segundos para API ficar disponível...${NC}"
    sleep 5
    
    echo -e "${BLUE}Executando testes de integração no API Gateway...${NC}"
    
    cd ../lambda
    
    # Exportar URL para o script de teste
    export API_GATEWAY_URL="$API_URL"
    
    if python test_api_gateway.py; then
        echo -e "${GREEN}✅ Todos os testes de integração passaram!${NC}"
    else
        echo -e "${RED}⚠️  Alguns testes de integração falharam.${NC}"
        echo -e "${YELLOW}   Deploy foi concluído, mas verifique os logs acima.${NC}"
    fi
    
    cd ../terraform
else
    echo -e "${YELLOW}⚠️  Não foi possível obter a URL da API${NC}"
fi

echo -e "\n${GREEN}🎉 Deploy finalizado com sucesso!${NC}"
echo -e "${GREEN}   Testes locais: ✅${NC}"
echo -e "${GREEN}   Deploy AWS: ✅${NC}"
echo -e "${GREEN}   Testes integração: Verifique logs acima${NC}"

