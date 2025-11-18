# Módulo API Gateway

Este módulo cria um API Gateway REST API completo integrado com Lambda via proxy.

## Recursos Criados

- API Gateway REST API
- API Gateway Resources (proxy e root)
- API Gateway Methods (ANY)
- API Gateway Integrations com Lambda
- API Gateway Deployment
- API Gateway Stage
- Lambda Permission
- CloudWatch Log Group (opcional)
- CORS Configuration (opcional)

## Uso

```hcl
module "api_gateway" {
  source = "./modules/api-gateway"

  api_name              = "my-api"
  api_description       = "My API Gateway"
  stage_name            = "dev"
  lambda_invoke_arn     = module.lambda.invoke_arn
  lambda_function_name  = module.lambda.function_name
  enable_access_logs    = true
  enable_xray_tracing   = false
  enable_cors           = true
  log_retention_days    = 7
  
  tags = {
    Project = "my-project"
  }
}
```

## Variáveis

| Nome | Descrição | Tipo | Padrão | Obrigatório |
|------|-----------|------|--------|-------------|
| api_name | Nome da API Gateway | string | - | Sim |
| api_description | Descrição da API | string | "" | Não |
| stage_name | Nome do stage | string | dev | Não |
| lambda_invoke_arn | ARN de invocação Lambda | string | - | Sim |
| lambda_function_name | Nome da função Lambda | string | - | Sim |
| authorization_type | Tipo de autorização | string | NONE | Não |
| authorizer_id | ID do autorizador | string | null | Não |
| enable_access_logs | Habilitar logs acesso | bool | true | Não |
| enable_xray_tracing | Habilitar X-Ray | bool | false | Não |
| enable_cors | Habilitar CORS | bool | true | Não |
| log_retention_days | Dias retenção logs | number | 7 | Não |
| tags | Tags dos recursos | map(string) | {} | Não |

## Outputs

| Nome | Descrição |
|------|-----------|
| api_id | ID da API Gateway |
| api_arn | ARN da API Gateway |
| api_execution_arn | ARN de execução |
| invoke_url | URL de invocação |
| stage_name | Nome do stage |
| deployment_id | ID do deployment |

## Features

### Proxy Integration
O módulo configura integração proxy completa, permitindo que a Lambda receba todas as requisições HTTP.

### CORS
Quando habilitado, adiciona cabeçalhos CORS e método OPTIONS automaticamente.

### Logs
Suporta logs de acesso detalhados no CloudWatch com formato JSON estruturado.

### X-Ray Tracing
Pode ser habilitado para rastreamento distribuído com AWS X-Ray.
