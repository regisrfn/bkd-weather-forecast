output "api_id" {
  description = "ID da API Gateway"
  value       = aws_api_gateway_rest_api.main.id
}

output "api_arn" {
  description = "ARN da API Gateway"
  value       = aws_api_gateway_rest_api.main.arn
}

output "api_execution_arn" {
  description = "ARN de execução da API Gateway"
  value       = aws_api_gateway_rest_api.main.execution_arn
}

output "invoke_url" {
  description = "URL de invocação da API Gateway"
  value       = aws_api_gateway_stage.main.invoke_url
}

output "stage_name" {
  description = "Nome do stage"
  value       = aws_api_gateway_stage.main.stage_name
}

output "deployment_id" {
  description = "ID do deployment"
  value       = aws_api_gateway_deployment.main.id
}
