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
  handler              = "lambda_function.lambda_handler"
  runtime              = "python3.13"
  timeout              = var.lambda_timeout
  memory_size          = var.lambda_memory_size
  description          = "Lambda function for ${var.project_name}"
  source_dir           = "${path.module}/../lambda"
  environment_variables = var.lambda_environment_variables
  log_retention_days   = var.log_retention_days
  
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
  enable_xray_tracing   = var.enable_xray_tracing
  enable_cors           = var.enable_cors
  log_retention_days    = var.log_retention_days
  
  tags = local.tags
}
