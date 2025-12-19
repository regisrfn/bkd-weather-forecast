# IAM Role para API Gateway acessar CloudWatch Logs
resource "aws_iam_role" "api_gateway_cloudwatch" {
  count = (var.enable_access_logs || var.enable_execution_logs) ? 1 : 0
  name  = "${var.api_name}-apigw-cloudwatch-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# Policy attachment para CloudWatch Logs
resource "aws_iam_role_policy_attachment" "api_gateway_cloudwatch" {
  count      = (var.enable_access_logs || var.enable_execution_logs) ? 1 : 0
  role       = aws_iam_role.api_gateway_cloudwatch[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}

# Configuração da conta API Gateway para CloudWatch Logs
resource "aws_api_gateway_account" "main" {
  count               = (var.enable_access_logs || var.enable_execution_logs) ? 1 : 0
  cloudwatch_role_arn = aws_iam_role.api_gateway_cloudwatch[0].arn

  depends_on = [aws_iam_role_policy_attachment.api_gateway_cloudwatch]
}

# API Gateway REST API
resource "aws_api_gateway_rest_api" "main" {
  name        = var.api_name
  description = var.api_description

  tags = var.tags
}

# ============================================================================
# RECURSOS E ROTAS ESPECÍFICAS
# ============================================================================

# /api
resource "aws_api_gateway_resource" "api" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "api"
}

# /api/health
resource "aws_api_gateway_resource" "health" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.api.id
  path_part   = "health"
}

# /api/weather
resource "aws_api_gateway_resource" "weather" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.api.id
  path_part   = "weather"
}

# /api/weather/city
resource "aws_api_gateway_resource" "weather_city" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.weather.id
  path_part   = "city"
}

# /api/weather/city/{cityId}
resource "aws_api_gateway_resource" "weather_city_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.weather_city.id
  path_part   = "{cityId}"
}

# /api/weather/city/{cityId}/detailed
resource "aws_api_gateway_resource" "weather_city_detailed" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.weather_city_id.id
  path_part   = "detailed"
}

# /api/weather/regional
resource "aws_api_gateway_resource" "weather_regional" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.weather.id
  path_part   = "regional"
}

# /api/cities
resource "aws_api_gateway_resource" "cities" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.api.id
  path_part   = "cities"
}

# /api/cities/neighbors
resource "aws_api_gateway_resource" "cities_neighbors" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.cities.id
  path_part   = "neighbors"
}

# /api/cities/neighbors/{cityId}
resource "aws_api_gateway_resource" "cities_neighbors_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.cities_neighbors.id
  path_part   = "{cityId}"
}

# /api/geo
resource "aws_api_gateway_resource" "geo" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.api.id
  path_part   = "geo"
}

# /api/geo/municipalities
resource "aws_api_gateway_resource" "geo_municipalities" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.geo.id
  path_part   = "municipalities"
}

# /api/geo/municipalities/{cityId}
resource "aws_api_gateway_resource" "geo_municipalities_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.geo_municipalities.id
  path_part   = "{cityId}"
}

# ============================================================================
# MÉTODOS E INTEGRAÇÕES
# ============================================================================

# GET /api/health
resource "aws_api_gateway_method" "health_get" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.health.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "health_get" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.health.id
  http_method             = aws_api_gateway_method.health_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.lambda_invoke_arn
}

# GET /api/weather/city/{cityId}
resource "aws_api_gateway_method" "weather_city_get" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.weather_city_id.id
  http_method   = "GET"
  authorization = "NONE"

  request_parameters = {
    "method.request.path.cityId" = true
  }
}

resource "aws_api_gateway_integration" "weather_city_get" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.weather_city_id.id
  http_method             = aws_api_gateway_method.weather_city_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.lambda_invoke_arn
}

# GET /api/weather/city/{cityId}/detailed
resource "aws_api_gateway_method" "weather_city_detailed_get" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.weather_city_detailed.id
  http_method   = "GET"
  authorization = "NONE"

  request_parameters = {
    "method.request.path.cityId" = true
  }
}

resource "aws_api_gateway_integration" "weather_city_detailed_get" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.weather_city_detailed.id
  http_method             = aws_api_gateway_method.weather_city_detailed_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.lambda_invoke_arn
}

# POST /api/weather/regional
resource "aws_api_gateway_method" "weather_regional_post" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.weather_regional.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "weather_regional_post" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.weather_regional.id
  http_method             = aws_api_gateway_method.weather_regional_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.lambda_invoke_arn
}

# GET /api/cities/neighbors/{cityId}
resource "aws_api_gateway_method" "cities_neighbors_get" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.cities_neighbors_id.id
  http_method   = "GET"
  authorization = "NONE"

  request_parameters = {
    "method.request.path.cityId" = true
  }
}

resource "aws_api_gateway_integration" "cities_neighbors_get" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.cities_neighbors_id.id
  http_method             = aws_api_gateway_method.cities_neighbors_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.lambda_invoke_arn
}

# GET /api/geo/municipalities/{cityId}
resource "aws_api_gateway_method" "geo_municipalities_get" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.geo_municipalities_id.id
  http_method   = "GET"
  authorization = "NONE"

  request_parameters = {
    "method.request.path.cityId" = true
  }
}

resource "aws_api_gateway_integration" "geo_municipalities_get" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.geo_municipalities_id.id
  http_method             = aws_api_gateway_method.geo_municipalities_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.lambda_invoke_arn
}

# ============================================================================
# CORS PARA ROTAS ESPECÍFICAS
# ============================================================================

# OPTIONS /api/health
resource "aws_api_gateway_method" "health_options" {
  count         = var.enable_cors ? 1 : 0
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.health.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "health_options" {
  count       = var.enable_cors ? 1 : 0
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.health.id
  http_method = aws_api_gateway_method.health_options[0].http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "health_options" {
  count       = var.enable_cors ? 1 : 0
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.health.id
  http_method = aws_api_gateway_method.health_options[0].http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
    "method.response.header.Access-Control-Max-Age"       = true
  }
}

resource "aws_api_gateway_integration_response" "health_options" {
  count       = var.enable_cors ? 1 : 0
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.health.id
  http_method = aws_api_gateway_method.health_options[0].http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'${var.cors_allowed_headers}'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
    "method.response.header.Access-Control-Max-Age"       = "'86400'"
  }

  depends_on = [aws_api_gateway_method_response.health_options]
}

# OPTIONS /api/weather/city/{cityId}
resource "aws_api_gateway_method" "weather_city_options" {
  count         = var.enable_cors ? 1 : 0
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.weather_city_id.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "weather_city_options" {
  count       = var.enable_cors ? 1 : 0
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.weather_city_id.id
  http_method = aws_api_gateway_method.weather_city_options[0].http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "weather_city_options" {
  count       = var.enable_cors ? 1 : 0
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.weather_city_id.id
  http_method = aws_api_gateway_method.weather_city_options[0].http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
    "method.response.header.Access-Control-Max-Age"       = true
  }
}

resource "aws_api_gateway_integration_response" "weather_city_options" {
  count       = var.enable_cors ? 1 : 0
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.weather_city_id.id
  http_method = aws_api_gateway_method.weather_city_options[0].http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'${var.cors_allowed_headers}'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
    "method.response.header.Access-Control-Max-Age"       = "'86400'"
  }

  depends_on = [aws_api_gateway_method_response.weather_city_options]
}

# OPTIONS /api/weather/city/{cityId}/detailed
resource "aws_api_gateway_method" "weather_city_detailed_options" {
  count         = var.enable_cors ? 1 : 0
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.weather_city_detailed.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "weather_city_detailed_options" {
  count       = var.enable_cors ? 1 : 0
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.weather_city_detailed.id
  http_method = aws_api_gateway_method.weather_city_detailed_options[0].http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "weather_city_detailed_options" {
  count       = var.enable_cors ? 1 : 0
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.weather_city_detailed.id
  http_method = aws_api_gateway_method.weather_city_detailed_options[0].http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
    "method.response.header.Access-Control-Max-Age"       = true
  }
}

resource "aws_api_gateway_integration_response" "weather_city_detailed_options" {
  count       = var.enable_cors ? 1 : 0
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.weather_city_detailed.id
  http_method = aws_api_gateway_method.weather_city_detailed_options[0].http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'${var.cors_allowed_headers}'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
    "method.response.header.Access-Control-Max-Age"       = "'86400'"
  }

  depends_on = [aws_api_gateway_method_response.weather_city_detailed_options]
}

# OPTIONS /api/weather/regional
resource "aws_api_gateway_method" "weather_regional_options" {
  count         = var.enable_cors ? 1 : 0
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.weather_regional.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "weather_regional_options" {
  count       = var.enable_cors ? 1 : 0
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.weather_regional.id
  http_method = aws_api_gateway_method.weather_regional_options[0].http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "weather_regional_options" {
  count       = var.enable_cors ? 1 : 0
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.weather_regional.id
  http_method = aws_api_gateway_method.weather_regional_options[0].http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
    "method.response.header.Access-Control-Max-Age"       = true
  }
}

resource "aws_api_gateway_integration_response" "weather_regional_options" {
  count       = var.enable_cors ? 1 : 0
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.weather_regional.id
  http_method = aws_api_gateway_method.weather_regional_options[0].http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'${var.cors_allowed_headers}'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
    "method.response.header.Access-Control-Max-Age"       = "'86400'"
  }

  depends_on = [aws_api_gateway_method_response.weather_regional_options]
}

# OPTIONS /api/cities/neighbors/{cityId}
resource "aws_api_gateway_method" "cities_neighbors_options" {
  count         = var.enable_cors ? 1 : 0
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.cities_neighbors_id.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "cities_neighbors_options" {
  count       = var.enable_cors ? 1 : 0
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.cities_neighbors_id.id
  http_method = aws_api_gateway_method.cities_neighbors_options[0].http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "cities_neighbors_options" {
  count       = var.enable_cors ? 1 : 0
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.cities_neighbors_id.id
  http_method = aws_api_gateway_method.cities_neighbors_options[0].http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
    "method.response.header.Access-Control-Max-Age"       = true
  }
}

resource "aws_api_gateway_integration_response" "cities_neighbors_options" {
  count       = var.enable_cors ? 1 : 0
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.cities_neighbors_id.id
  http_method = aws_api_gateway_method.cities_neighbors_options[0].http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'${var.cors_allowed_headers}'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
    "method.response.header.Access-Control-Max-Age"       = "'86400'"
  }

  depends_on = [aws_api_gateway_method_response.cities_neighbors_options]
}

# OPTIONS /api/geo/municipalities/{cityId}
resource "aws_api_gateway_method" "geo_municipalities_options" {
  count         = var.enable_cors ? 1 : 0
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.geo_municipalities_id.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "geo_municipalities_options" {
  count       = var.enable_cors ? 1 : 0
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.geo_municipalities_id.id
  http_method = aws_api_gateway_method.geo_municipalities_options[0].http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "geo_municipalities_options" {
  count       = var.enable_cors ? 1 : 0
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.geo_municipalities_id.id
  http_method = aws_api_gateway_method.geo_municipalities_options[0].http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
    "method.response.header.Access-Control-Max-Age"       = true
  }
}

resource "aws_api_gateway_integration_response" "geo_municipalities_options" {
  count       = var.enable_cors ? 1 : 0
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.geo_municipalities_id.id
  http_method = aws_api_gateway_method.geo_municipalities_options[0].http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'${var.cors_allowed_headers}'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
    "method.response.header.Access-Control-Max-Age"       = "'86400'"
  }

  depends_on = [aws_api_gateway_method_response.geo_municipalities_options]
}

# ============================================================================
# RECURSO PROXY (FALLBACK PARA ROTAS NÃO MAPEADAS)
# ============================================================================

# Recurso proxy para capturar rotas não mapeadas (fallback)
resource "aws_api_gateway_resource" "proxy" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "{proxy+}"
}

# Método ANY para o recurso proxy
resource "aws_api_gateway_method" "proxy" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.proxy.id
  http_method   = "ANY"
  authorization = var.authorization_type
  authorizer_id = var.authorizer_id
}

# Integração com Lambda para o proxy
resource "aws_api_gateway_integration" "lambda_proxy" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.proxy.id
  http_method             = aws_api_gateway_method.proxy.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.lambda_invoke_arn
}

# Método ANY para o root path
resource "aws_api_gateway_method" "proxy_root" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_rest_api.main.root_resource_id
  http_method   = "ANY"
  authorization = var.authorization_type
  authorizer_id = var.authorizer_id
}

# Integração com Lambda para o root
resource "aws_api_gateway_integration" "lambda_root" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_rest_api.main.root_resource_id
  http_method             = aws_api_gateway_method.proxy_root.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.lambda_invoke_arn
}

# Deploy do API Gateway
resource "aws_api_gateway_deployment" "main" {
  rest_api_id = aws_api_gateway_rest_api.main.id

  depends_on = [
    # Rotas específicas
    aws_api_gateway_integration.health_get,
    aws_api_gateway_integration.weather_city_get,
    aws_api_gateway_integration.weather_city_detailed_get,
    aws_api_gateway_integration.weather_regional_post,
    aws_api_gateway_integration.cities_neighbors_get,
    aws_api_gateway_integration.geo_municipalities_get,
    # CORS integrations
    aws_api_gateway_integration_response.health_options,
    aws_api_gateway_integration_response.weather_city_options,
    aws_api_gateway_integration_response.weather_city_detailed_options,
    aws_api_gateway_integration_response.weather_regional_options,
    aws_api_gateway_integration_response.cities_neighbors_options,
    aws_api_gateway_integration_response.geo_municipalities_options,
    # Proxy fallback
    aws_api_gateway_integration.lambda_proxy,
    aws_api_gateway_integration.lambda_root
  ]

  lifecycle {
    create_before_destroy = true
  }

  triggers = {
    redeployment = sha1(jsonencode([
      # Rotas específicas
      aws_api_gateway_resource.health.id,
      aws_api_gateway_method.health_get.id,
      aws_api_gateway_integration.health_get.id,
      aws_api_gateway_resource.weather_city_id.id,
      aws_api_gateway_method.weather_city_get.id,
      aws_api_gateway_integration.weather_city_get.id,
      aws_api_gateway_resource.weather_city_detailed.id,
      aws_api_gateway_method.weather_city_detailed_get.id,
      aws_api_gateway_integration.weather_city_detailed_get.id,
      aws_api_gateway_resource.weather_regional.id,
      aws_api_gateway_method.weather_regional_post.id,
      aws_api_gateway_integration.weather_regional_post.id,
      aws_api_gateway_resource.cities_neighbors_id.id,
      aws_api_gateway_method.cities_neighbors_get.id,
      aws_api_gateway_integration.cities_neighbors_get.id,
      aws_api_gateway_resource.geo_municipalities_id.id,
      aws_api_gateway_method.geo_municipalities_get.id,
      aws_api_gateway_integration.geo_municipalities_get.id,
      # CORS integration responses (para forçar redeploy quando headers mudarem)
      var.enable_cors ? aws_api_gateway_integration_response.health_options[0].id : "",
      var.enable_cors ? aws_api_gateway_integration_response.weather_city_options[0].id : "",
      var.enable_cors ? aws_api_gateway_integration_response.weather_city_detailed_options[0].id : "",
      var.enable_cors ? aws_api_gateway_integration_response.weather_regional_options[0].id : "",
      var.enable_cors ? aws_api_gateway_integration_response.cities_neighbors_options[0].id : "",
      var.enable_cors ? aws_api_gateway_integration_response.geo_municipalities_options[0].id : "",
      # Proxy fallback
      aws_api_gateway_resource.proxy.id,
      aws_api_gateway_method.proxy.id,
      aws_api_gateway_integration.lambda_proxy.id,
      aws_api_gateway_method.proxy_root.id,
      aws_api_gateway_integration.lambda_root.id,
      # CORS configuration hash
      var.enable_cors,
      var.cors_allowed_headers,
    ]))
  }
}

# Stage do API Gateway
resource "aws_api_gateway_stage" "main" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = var.stage_name

  dynamic "access_log_settings" {
    for_each = var.enable_access_logs ? [1] : []
    content {
      destination_arn = aws_cloudwatch_log_group.api_gateway[0].arn
      format = jsonencode({
        requestId      = "$context.requestId"
        ip             = "$context.identity.sourceIp"
        caller         = "$context.identity.caller"
        user           = "$context.identity.user"
        requestTime    = "$context.requestTime"
        httpMethod     = "$context.httpMethod"
        resourcePath   = "$context.resourcePath"
        status         = "$context.status"
        integrationError = "$context.integrationErrorMessage"
        protocol       = "$context.protocol"
        responseLength = "$context.responseLength"
      })
    }
  }

  tags = var.tags

  depends_on = [aws_api_gateway_account.main]
}

# Execution logs (stage-wide settings)
resource "aws_api_gateway_method_settings" "all" {
  count = var.enable_execution_logs ? 1 : 0

  rest_api_id = aws_api_gateway_rest_api.main.id
  stage_name  = aws_api_gateway_stage.main.stage_name
  method_path = "*/*"

  settings {
    logging_level      = "ERROR"
    data_trace_enabled = false
    metrics_enabled    = false
  }

  depends_on = [aws_api_gateway_stage.main]
}

# Gateway Responses para incluir CORS em respostas 4XX/5XX (timeouts/erros)
resource "aws_api_gateway_gateway_response" "default_4xx" {
  count         = var.enable_cors ? 1 : 0
  rest_api_id   = aws_api_gateway_rest_api.main.id
  response_type = "DEFAULT_4XX"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "'*'"
    "gatewayresponse.header.Access-Control-Allow-Headers" = "'${var.cors_allowed_headers}'"
    "gatewayresponse.header.Access-Control-Allow-Methods" = "'GET,POST,OPTIONS'"
  }
}

resource "aws_api_gateway_gateway_response" "default_5xx" {
  count         = var.enable_cors ? 1 : 0
  rest_api_id   = aws_api_gateway_rest_api.main.id
  response_type = "DEFAULT_5XX"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "'*'"
    "gatewayresponse.header.Access-Control-Allow-Headers" = "'${var.cors_allowed_headers}'"
    "gatewayresponse.header.Access-Control-Allow-Methods" = "'GET,POST,OPTIONS'"
  }
}

# CloudWatch Log Group para API Gateway (opcional)
resource "aws_cloudwatch_log_group" "api_gateway" {
  count             = var.enable_access_logs ? 1 : 0
  name              = "/aws/apigateway/${var.api_name}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# Permissão para API Gateway invocar Lambda
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}
