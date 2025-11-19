# 🚀 Guia de Deploy - Lambda Weather Forecast

## 📋 Pré-requisitos

- ✅ AWS CLI configurado (`aws configure`)
- ✅ Terraform instalado (v1.13.5+)
- ✅ Credenciais AWS com permissões para:
  - Lambda
  - IAM
  - API Gateway
  - CloudWatch Logs

## 🔑 Verificar Credenciais AWS

```bash
# Verificar se AWS CLI está configurado
aws sts get-caller-identity

# Deve retornar:
# {
#   "UserId": "...",
#   "Account": "123456789012",
#   "Arn": "arn:aws:iam::123456789012:user/seu-usuario"
# }
```

## 📝 Configuração

### 1. Variáveis de Ambiente

O arquivo `terraform.tfvars` já está configurado com:

```terraform
aws_region           = "sa-east-1"  # São Paulo
project_name         = "weather-forecast"
environment          = "dev"
lambda_function_name = "api-lambda-weather-forecast"
lambda_timeout       = 300
lambda_memory_size   = 256

lambda_environment_variables = {
  ENVIRONMENT         = "production"
  OPENWEATHER_API_KEY = "7145a8ca3e346f00385a11181355eea7"
  CORS_ORIGIN         = "http://weather-forecast-production-7cbc1a12.s3-website-sa-east-1.amazonaws.com"
}
```

### 2. Estrutura que será criada

O Terraform criará:
- ✅ Lambda Function com Python 3.13
- ✅ IAM Role e Policies
- ✅ CloudWatch Log Group
- ✅ API Gateway REST API
- ✅ API Gateway Stage (dev)
- ✅ Permissões Lambda ↔ API Gateway

## 🚀 Deploy

### Opção 1: Script Automatizado (Recomendado)

```bash
cd /home/regis/GIT/bkd-weather-forecast/terraform
bash deploy.sh
```

O script irá:
1. Inicializar Terraform
2. Validar configuração
3. Mostrar plano de mudanças
4. Pedir confirmação
5. Aplicar mudanças
6. Mostrar outputs (API URL)

### Opção 2: Comandos Manuais

```bash
cd /home/regis/GIT/bkd-weather-forecast/terraform

# 1. Inicializar
terraform init

# 2. Validar
terraform validate

# 3. Ver plano
terraform plan

# 4. Aplicar
terraform apply

# 5. Ver outputs
terraform output
```

## 📊 Outputs Esperados

Após o deploy, você verá:

```
Outputs:

api_url = "https://xxxxxxxxxx.execute-api.sa-east-1.amazonaws.com/dev"
lambda_arn = "arn:aws:lambda:sa-east-1:123456789012:function:api-lambda-weather-forecast"
lambda_function_name = "api-lambda-weather-forecast"
```

## 🧪 Testar o Deploy

### 1. Teste via cURL

```bash
# Salvar API URL
API_URL=$(terraform output -raw api_url)

# Teste 1: Buscar cidades vizinhas
curl "${API_URL}/api/cities/neighbors/3550308?radius=50"

# Teste 2: Clima de uma cidade
curl "${API_URL}/api/weather/city/3550308"

# Teste 3: Clima regional
curl -X POST "${API_URL}/api/weather/regional" \
  -H "Content-Type: application/json" \
  -d '{"cityIds": ["3550308", "3304557", "5300108"]}'
```

### 2. Teste via Python

```python
import requests

API_URL = "https://xxxxxxxxxx.execute-api.sa-east-1.amazonaws.com/dev"

# Teste neighbors
response = requests.get(f"{API_URL}/api/cities/neighbors/3550308?radius=50")
print(response.json())

# Teste weather
response = requests.get(f"{API_URL}/api/weather/city/3550308")
print(response.json())
```

## 🔍 Monitoramento

### CloudWatch Logs

```bash
# Ver logs da Lambda
aws logs tail /aws/lambda/api-lambda-weather-forecast --follow

# Ver logs do API Gateway
aws logs tail /aws/apigateway/weather-forecast-api-dev --follow
```

### Métricas Lambda

```bash
# No Console AWS:
CloudWatch > Metrics > Lambda > By Function Name > api-lambda-weather-forecast
```

Métricas importantes:
- **Invocations** - Número de execuções
- **Duration** - Tempo de execução
- **Errors** - Erros
- **Throttles** - Limitações

## 🔄 Atualizar Deploy

Quando fizer mudanças no código:

```bash
cd /home/regis/GIT/bkd-weather-forecast/terraform

# Terraform detectará mudanças no código (via hash)
terraform plan

# Aplicar atualização
terraform apply
```

O Terraform irá:
1. Recriar o ZIP com novo código
2. Atualizar a Lambda Function
3. Manter a API Gateway (sem downtime)

## 🗑️ Destruir Infraestrutura

Para remover todos os recursos:

```bash
cd /home/regis/GIT/bkd-weather-forecast/terraform

terraform destroy

# Confirmar com: yes
```

⚠️ **Atenção:** Isso irá deletar:
- Lambda Function
- API Gateway
- IAM Role
- CloudWatch Logs

## 🐛 Troubleshooting

### Erro: "AccessDeniedException"

```
Error: creating Lambda Function: AccessDeniedException
```

**Solução:** Verificar permissões AWS
```bash
aws iam get-user
aws iam list-attached-user-policies --user-name SEU_USUARIO
```

### Erro: "InvalidZipFile"

```
Error: Error creating function: InvalidParameterValueException
```

**Solução:** Verificar se `lambda/` tem todos os arquivos necessários
```bash
ls -la ../lambda/
# Deve conter: lambda_function.py, domain/, application/, etc
```

### Lambda timeout

```
Task timed out after 30.00 seconds
```

**Solução:** Aumentar timeout no `terraform.tfvars`:
```terraform
lambda_timeout = 60  # ou mais
```

### CORS errors no frontend

```
Access-Control-Allow-Origin error
```

**Solução:** Verificar se `enable_cors = true` e atualizar CORS_ORIGIN:
```terraform
lambda_environment_variables = {
  CORS_ORIGIN = "https://seu-frontend.com"
}
```

## 📈 Custos Estimados

### Lambda
- **Free Tier:** 1M requisições/mês grátis
- **Após Free Tier:** $0.20 por 1M requisições
- **Compute:** $0.0000166667 por GB-segundo

### API Gateway
- **Free Tier:** 1M chamadas/mês grátis (12 meses)
- **Após Free Tier:** $3.50 por milhão de chamadas

### Estimativa mensal (10K requisições/dia):
- Lambda: **Grátis** (dentro do Free Tier)
- API Gateway: **Grátis** (dentro do Free Tier)
- CloudWatch Logs: **~$0.50**

**Total estimado:** $0.50/mês 💰

## 📞 Suporte

Se encontrar problemas:

1. Verificar logs do CloudWatch
2. Verificar permissões IAM
3. Testar Lambda localmente com `test_lambda.py`
4. Revisar documentação Terraform AWS

## 🎯 Próximos Passos

Após deploy bem-sucedido:

- [ ] Configurar domain customizado (Route 53)
- [ ] Adicionar autenticação (API Key, Cognito)
- [ ] Configurar alertas CloudWatch
- [ ] Adicionar CI/CD (GitHub Actions)
- [ ] Habilitar X-Ray tracing
- [ ] Configurar WAF para proteção
