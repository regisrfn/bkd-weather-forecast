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

variable "lambda_reserved_concurrency" {
  description = "Concorrência reservada da Lambda (null para ilimitado)"
  type        = number
  default     = null
}

variable "lambda_warmup_enabled" {
  description = "Habilita warm-up via EventBridge (override de enable_warmup_cron)"
  type        = bool
  default     = null
}

variable "lambda_warmup_schedule" {
  description = "Agendamento do warm-up (cron ou rate) (override de warmup_schedule_expression)"
  type        = string
  default     = null
}

variable "lambda_warmup_concurrency" {
  description = "Invocações paralelas por execução do warm-up (override de warmup_concurrency)"
  type        = number
  default     = null
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

variable "enable_warmup_cron" {
  description = "Ativa/desativa warm-up (compatibilidade com tfvars existente)"
  type        = bool
  default     = true
}

variable "warmup_schedule_expression" {
  description = "Agenda do warm-up (compatibilidade com tfvars existente)"
  type        = string
  default     = "rate(5 minutes)"
}

variable "warmup_concurrency" {
  description = "Invocações paralelas por execução do warm-up (compatibilidade com tfvars existente)"
  type        = number
  default     = 1
}

# Datadog Configuration
variable "datadog_api_key_secret_arn" {
  description = "ARN do secret no Secrets Manager contendo a API key do Datadog"
  type        = string
}

variable "datadog_layer_arn" {
  description = "ARN do Lambda Layer do Datadog para Python 3.13"
  type        = string
}

variable "datadog_extension_layer_arn" {
  description = "ARN do Datadog Lambda Extension Layer"
  type        = string
}

variable "datadog_site" {
  description = "Site do Datadog (datadoghq.com, datadoghq.eu, etc)"
  type        = string
  default     = "datadoghq.com"
}

variable "datadog_env" {
  description = "Environment tag para Datadog (dev, staging, production)"
  type        = string
  default     = "production"
}

variable "datadog_version" {
  description = "Version tag para Datadog"
  type        = string
  default     = "1.0.0"
}
