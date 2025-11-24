variable "function_name" {
  description = "Nome da função Lambda"
  type        = string
}

variable "handler" {
  description = "Handler da função Lambda"
  type        = string
  default     = "lambda_function.lambda_handler"
}

variable "runtime" {
  description = "Runtime da função Lambda"
  type        = string
  default     = "python3.13"
}

variable "timeout" {
  description = "Timeout da função Lambda em segundos"
  type        = number
  default     = 30
}

variable "memory_size" {
  description = "Memória alocada para a função Lambda em MB"
  type        = number
  default     = 256
}

variable "description" {
  description = "Descrição da função Lambda"
  type        = string
  default     = ""
}

variable "source_dir" {
  description = "Diretório contendo o código da Lambda"
  type        = string
}

variable "environment_variables" {
  description = "Variáveis de ambiente para a função Lambda"
  type        = map(string)
  default     = {}
}

variable "log_retention_days" {
  description = "Número de dias para retenção dos logs no CloudWatch"
  type        = number
  default     = 7
}

variable "additional_policy_arns" {
  description = "Lista de ARNs de políticas IAM adicionais para anexar à role da Lambda"
  type        = list(string)
  default     = []
}

variable "vpc_config" {
  description = "Configuração VPC para a Lambda (opcional)"
  type = object({
    subnet_ids         = list(string)
    security_group_ids = list(string)
  })
  default = null
}

variable "tags" {
  description = "Tags para aplicar aos recursos"
  type        = map(string)
  default     = {}
}

variable "cache_table_name" {
  description = "Nome da tabela DynamoDB para cache (opcional)"
  type        = string
  default     = null
}

variable "aws_region" {
  description = "Região AWS para o recurso DynamoDB"
  type        = string
  default     = "sa-east-1"
}

# Datadog Configuration
variable "datadog_api_key_secret_arn" {
  description = "ARN do secret no Secrets Manager contendo a API key do Datadog"
  type        = string
}

variable "datadog_layer_arn" {
  description = "ARN do Lambda Layer do Datadog"
  type        = string
}

variable "datadog_extension_layer_arn" {
  description = "ARN do Datadog Lambda Extension Layer"
  type        = string
}

variable "datadog_site" {
  description = "Site do Datadog"
  type        = string
  default     = "datadoghq.com"
}

variable "datadog_env" {
  description = "Environment tag para Datadog"
  type        = string
}

variable "datadog_version" {
  description = "Version tag para Datadog"
  type        = string
}
