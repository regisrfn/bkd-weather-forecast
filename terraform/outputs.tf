# Lambda Outputs
output "lambda_function_name" {
  description = "Nome da função Lambda"
  value       = module.lambda.function_name
}

output "lambda_function_arn" {
  description = "ARN da função Lambda"
  value       = module.lambda.function_arn
}

output "lambda_function_invoke_arn" {
  description = "ARN de invocação da função Lambda"
  value       = module.lambda.invoke_arn
}

output "lambda_role_arn" {
  description = "ARN da IAM Role da Lambda"
  value       = module.lambda.role_arn
}

output "cloudwatch_log_group_name" {
  description = "Nome do CloudWatch Log Group da Lambda"
  value       = module.lambda.log_group_name
}

# API Gateway Outputs
output "api_gateway_url" {
  description = "URL do API Gateway"
  value       = var.create_api_gateway ? module.api_gateway[0].invoke_url : "API Gateway não criado"
}

output "api_gateway_id" {
  description = "ID do API Gateway"
  value       = var.create_api_gateway ? module.api_gateway[0].api_id : "API Gateway não criado"
}

output "api_gateway_execution_arn" {
  description = "ARN de execução do API Gateway"
  value       = var.create_api_gateway ? module.api_gateway[0].api_execution_arn : "API Gateway não criado"
}
