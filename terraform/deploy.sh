#!/bin/bash
# Script de Deploy da Lambda Weather Forecast
# Execute: bash deploy.sh

set -e  # Parar em caso de erro

echo "🚀 Deploy Lambda Weather Forecast"
echo "=================================="

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Verificar se está no diretório correto
if [ ! -f "terraform.tfvars" ]; then
    echo -e "${RED}❌ Erro: Execute este script do diretório terraform/${NC}"
    exit 1
fi

# 2. Build Lambda com dependências
echo -e "\n${BLUE}1️⃣  Criando pacote Lambda com dependências...${NC}"
bash build-lambda.sh

if [ ! -f "build/lambda_function.zip" ]; then
    echo -e "${RED}❌ Erro: Falha ao criar pacote Lambda${NC}"
    exit 1
fi

# 3. Terraform Init
echo -e "\n${BLUE}2️⃣  Inicializando Terraform...${NC}"
terraform init

# 4. Terraform Validate
echo -e "\n${BLUE}3️⃣  Validando configuração...${NC}"
terraform validate

# 5. Terraform Plan
echo -e "\n${BLUE}4️⃣  Gerando plano de execução...${NC}"
terraform plan -out=tfplan

# 6. Perguntar confirmação
echo -e "\n${BLUE}5️⃣  Revisar o plano acima${NC}"
read -p "Deseja aplicar as mudanças? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo -e "${RED}❌ Deploy cancelado${NC}"
    rm -f tfplan
    exit 0
fi

# 6. Terraform Apply
echo -e "\n${BLUE}5️⃣  Aplicando mudanças...${NC}"
terraform apply tfplan

# 7. Limpar arquivo de plano
rm -f tfplan

# 8. Mostrar outputs
echo -e "\n${GREEN}✅ Deploy concluído!${NC}"
echo -e "\n${BLUE}📊 Outputs:${NC}"
terraform output

# 9. Salvar API URL
if terraform output -raw api_url 2>/dev/null; then
    API_URL=$(terraform output -raw api_url)
    echo -e "\n${GREEN}🌐 API URL: ${API_URL}${NC}"
    echo "$API_URL" > ../API_URL.txt
    echo -e "${GREEN}   (Salvo em API_URL.txt)${NC}"
fi

echo -e "\n${GREEN}🎉 Deploy finalizado com sucesso!${NC}"
