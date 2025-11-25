# Usar zip pré-construído com dependências
# Execute: bash ../build-lambda.sh antes do terraform apply
locals {
  lambda_zip_path = "${path.module}/../../build/lambda_function.zip"
}

# IAM Role para Lambda
resource "aws_iam_role" "lambda_role" {
  name = "${var.function_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# Policy para logs do CloudWatch
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Policy inline para DynamoDB (Cache)
resource "aws_iam_role_policy" "dynamodb_cache_policy" {
  count = var.cache_table_name != null ? 1 : 0
  
  name = "${var.function_name}-dynamodb-cache"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem"
        ]
        Resource = "arn:aws:dynamodb:${var.aws_region}:*:table/${var.cache_table_name}"
      }
    ]
  })
}

# Policy inline para Secrets Manager (Datadog API Key)
resource "aws_iam_role_policy" "secrets_manager_policy" {
  name = "${var.function_name}-secrets-manager"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = var.datadog_api_key_secret_arn
      }
    ]
  })
}

# Políticas adicionais (opcional)
resource "aws_iam_role_policy_attachment" "additional_policies" {
  for_each = toset(var.additional_policy_arns)
  
  role       = aws_iam_role.lambda_role.name
  policy_arn = each.value
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# Lambda Function
resource "aws_lambda_function" "main" {
  filename         = local.lambda_zip_path
  function_name    = var.function_name
  role            = aws_iam_role.lambda_role.arn
  handler         = var.handler
  source_code_hash = filebase64sha256(local.lambda_zip_path)
  runtime         = var.runtime
  timeout         = var.timeout
  memory_size     = var.memory_size
  description     = var.description
  
  # Datadog Lambda Layers (Python + Extension)
  layers = [
    var.datadog_layer_arn,
    var.datadog_extension_layer_arn
  ]

  environment {
    variables = merge(
      var.environment_variables,
      {
        # Datadog Configuration
        DD_API_KEY_SECRET_ARN = var.datadog_api_key_secret_arn
        DD_SITE               = var.datadog_site
        DD_SERVICE            = "weather-forecast"
        DD_ENV                = var.datadog_env
        DD_VERSION            = var.datadog_version
        DD_TRACE_ENABLED      = "true"
        DD_LOGS_INJECTION     = "true"
        DD_LAMBDA_HANDLER     = "infrastructure.adapters.input.lambda_handler.lambda_handler"
        DD_SERVICE_MAPPING    = "dynamodb:weather-cache"
        DD_FLUSH_TO_LOG       = "false"
        DD_SERVERLESS_LOGS_ENABLED = "true"
      }
    )
  }

  dynamic "vpc_config" {
    for_each = var.vpc_config != null ? [var.vpc_config] : []
    content {
      subnet_ids         = vpc_config.value.subnet_ids
      security_group_ids = vpc_config.value.security_group_ids
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda_logs,
    aws_iam_role_policy_attachment.lambda_logs
  ]

  tags = var.tags
}
