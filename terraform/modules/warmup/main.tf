resource "aws_cloudwatch_event_rule" "lambda_warmup" {
  name                = "${var.rule_name_prefix}-warmup"
  description         = "Warmup da Lambda para reduzir cold start"
  schedule_expression = var.schedule_expression

  tags = var.tags
}

resource "aws_cloudwatch_event_target" "lambda_warmup" {
  rule      = aws_cloudwatch_event_rule.lambda_warmup.name
  target_id = "lambda-warmup"
  arn       = var.function_arn

  input = jsonencode({
    resource                        = var.warmup_path,
    path                            = var.warmup_path,
    httpMethod                      = "GET",
    headers                         = { "Content-Type" = "application/json" },
    multiValueHeaders               = { "Content-Type" = ["application/json"] },
    queryStringParameters           = null,
    multiValueQueryStringParameters = null,
    pathParameters                  = null,
    stageVariables                  = null,
    requestContext = {
      resourcePath = var.warmup_path,
      httpMethod   = "GET",
      path         = var.warmup_path,
      identity     = {}
    },
    body            = null,
    isBase64Encoded = false
  })
}

resource "aws_lambda_permission" "allow_eventbridge_warmup" {
  statement_id  = "AllowEventBridgeWarmup"
  action        = "lambda:InvokeFunction"
  function_name = var.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.lambda_warmup.arn
}
