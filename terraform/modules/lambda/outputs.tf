output "function_name" {
  description = "Nome da função Lambda"
  value       = aws_lambda_function.main.function_name
}

output "function_arn" {
  description = "ARN da função Lambda"
  value       = aws_lambda_function.main.arn
}

output "invoke_arn" {
  description = "ARN de invocação da função Lambda"
  value       = aws_lambda_function.main.invoke_arn
}

output "role_arn" {
  description = "ARN da IAM Role da Lambda"
  value       = aws_iam_role.lambda_role.arn
}

output "role_name" {
  description = "Nome da IAM Role da Lambda"
  value       = aws_iam_role.lambda_role.name
}

output "log_group_name" {
  description = "Nome do CloudWatch Log Group"
  value       = aws_cloudwatch_log_group.lambda_logs.name
}

output "log_group_arn" {
  description = "ARN do CloudWatch Log Group"
  value       = aws_cloudwatch_log_group.lambda_logs.arn
}
