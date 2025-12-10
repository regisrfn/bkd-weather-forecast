variable "rule_name_prefix" {
  description = "Prefixo para nomear a regra do EventBridge"
  type        = string
}

variable "schedule_expression" {
  description = "Expressão de agendamento (ex: rate(5 minutes))"
  type        = string
}

variable "warmup_path" {
  description = "Path/rota da Lambda a ser invocada para warmup"
  type        = string
  default     = "/api/warmup"
}

variable "function_arn" {
  description = "ARN da função Lambda alvo"
  type        = string
}

variable "function_name" {
  description = "Nome da função Lambda alvo"
  type        = string
}

variable "tags" {
  description = "Tags a aplicar nos recursos"
  type        = map(string)
  default     = {}
}
