terraform {
  required_version = ">= 1.13.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.20.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Locals para organizar valores comuns
locals {
  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Módulo Lambda
module "lambda" {
  source = "./modules/lambda"

  function_name         = var.lambda_function_name
  handler              = "datadog_lambda.handler.handler"
  runtime              = "python3.13"
  timeout              = var.lambda_timeout
  memory_size          = var.lambda_memory_size
  description          = "Lambda function for ${var.project_name}"
  source_dir           = "${path.module}/../lambda"
  environment_variables = var.lambda_environment_variables
  log_retention_days   = var.log_retention_days
  
  # Cache DynamoDB
  cache_table_name = var.cache_table_name
  aws_region       = var.aws_region
  
  # Datadog Configuration
  datadog_api_key_secret_arn = var.datadog_api_key_secret_arn
  datadog_layer_arn          = var.datadog_layer_arn
  datadog_extension_layer_arn = var.datadog_extension_layer_arn
  datadog_site               = var.datadog_site
  datadog_env                = var.datadog_env
  datadog_version            = var.datadog_version
  
  tags = local.tags
}

# Módulo API Gateway (condicional)
module "api_gateway" {
  count  = var.create_api_gateway ? 1 : 0
  source = "./modules/api-gateway"

  api_name              = "${var.project_name}-api"
  api_description       = "API Gateway para Lambda ${var.lambda_function_name}"
  stage_name            = var.environment
  lambda_invoke_arn     = module.lambda.invoke_arn
  lambda_function_name  = module.lambda.function_name
  enable_access_logs    = var.enable_api_gateway_logs
  enable_cors           = var.enable_cors
  log_retention_days    = var.log_retention_days
  
  tags = local.tags
}
