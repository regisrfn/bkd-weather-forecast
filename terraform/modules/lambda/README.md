# Módulo Lambda

Este módulo cria uma função AWS Lambda completa com todas as configurações necessárias.

## Recursos Criados

- Lambda Function
- IAM Role com assume role policy
- IAM Policy Attachments
- CloudWatch Log Group
- ZIP do código fonte

## Uso

```hcl
module "lambda" {
  source = "./modules/lambda"

  function_name         = "my-lambda-function"
  handler              = "lambda_function.lambda_handler"
  runtime              = "python3.13"
  timeout              = 30
  memory_size          = 256
  source_dir           = "${path.module}/../lambda"
  environment_variables = {
    ENVIRONMENT = "dev"
  }
  log_retention_days = 7
  
  tags = {
    Project = "my-project"
  }
}
```

## Variáveis

| Nome | Descrição | Tipo | Padrão | Obrigatório |
|------|-----------|------|--------|-------------|
| function_name | Nome da função Lambda | string | - | Sim |
| handler | Handler da função | string | lambda_function.lambda_handler | Não |
| runtime | Runtime da Lambda | string | python3.13 | Não |
| timeout | Timeout em segundos | number | 30 | Não |
| memory_size | Memória em MB | number | 256 | Não |
| source_dir | Diretório do código | string | - | Sim |
| environment_variables | Variáveis de ambiente | map(string) | {} | Não |
| log_retention_days | Dias de retenção logs | number | 7 | Não |
| additional_policy_arns | Políticas IAM adicionais | list(string) | [] | Não |
| vpc_config | Configuração VPC | object | null | Não |
| tags | Tags dos recursos | map(string) | {} | Não |

## Outputs

| Nome | Descrição |
|------|-----------|
| function_name | Nome da função Lambda |
| function_arn | ARN da função Lambda |
| invoke_arn | ARN de invocação |
| role_arn | ARN da IAM Role |
| role_name | Nome da IAM Role |
| log_group_name | Nome do Log Group |
| log_group_arn | ARN do Log Group |
