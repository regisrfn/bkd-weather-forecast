variable "aws_region" {
  description = "Região AWS onde os recursos serão criados"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Nome do projeto"
  type        = string
  default     = "api-lambda-test"
}

variable "environment" {
  description = "Ambiente (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "lambda_function_name" {
  description = "Nome da função Lambda"
  type        = string
  default     = "api-lambda-test-function"
}

variable "lambda_timeout" {
  description = "Timeout da função Lambda em segundos"
  type        = number
  default     = 30
}

variable "lambda_memory_size" {
  description = "Memória alocada para a função Lambda em MB"
  type        = number
  default     = 256
}

variable "lambda_environment_variables" {
  description = "Variáveis de ambiente para a função Lambda"
  type        = map(string)
  default = {
    ENVIRONMENT = "dev"
  }
}

variable "log_retention_days" {
  description = "Número de dias para retenção dos logs no CloudWatch"
  type        = number
  default     = 7
}

variable "create_api_gateway" {
  description = "Se deve criar API Gateway para a Lambda"
  type        = bool
  default     = true
}

variable "enable_api_gateway_logs" {
  description = "Habilitar logs de acesso do API Gateway no CloudWatch"
  type        = bool
  default     = true
}

variable "enable_xray_tracing" {
  description = "Habilitar AWS X-Ray tracing no API Gateway"
  type        = bool
  default     = false
}

variable "enable_cors" {
  description = "Habilitar CORS no API Gateway"
  type        = bool
  default     = true
}

variable "cache_table_name" {
  description = "Nome da tabela DynamoDB para cache (opcional, se null cache é desabilitado)"
  type        = string
  default     = null
}
