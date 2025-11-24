variable "api_name" {
  description = "Nome da API Gateway"
  type        = string
}

variable "api_description" {
  description = "Descrição da API Gateway"
  type        = string
  default     = ""
}

variable "stage_name" {
  description = "Nome do stage do API Gateway"
  type        = string
  default     = "dev"
}

variable "lambda_invoke_arn" {
  description = "ARN de invocação da função Lambda"
  type        = string
}

variable "lambda_function_name" {
  description = "Nome da função Lambda"
  type        = string
}

variable "authorization_type" {
  description = "Tipo de autorização para os métodos da API"
  type        = string
  default     = "NONE"
}

variable "authorizer_id" {
  description = "ID do autorizador (se usar autorização customizada)"
  type        = string
  default     = null
}

variable "enable_access_logs" {
  description = "Habilitar logs de acesso do API Gateway no CloudWatch"
  type        = bool
  default     = false
}

variable "enable_cors" {
  description = "Habilitar CORS para a API"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "Número de dias para retenção dos logs no CloudWatch"
  type        = number
  default     = 7
}

variable "tags" {
  description = "Tags para aplicar aos recursos"
  type        = map(string)
  default     = {}
}
