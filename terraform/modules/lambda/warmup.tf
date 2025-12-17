locals {
  warmup_rule_name = "${var.function_name}-warmup"
}

resource "aws_cloudwatch_event_rule" "lambda_warmup" {
  count = var.warmup_enabled ? 1 : 0

  name                = local.warmup_rule_name
  description         = "Warm-up schedule for ${var.function_name}"
  schedule_expression = var.warmup_schedule
}

resource "aws_cloudwatch_event_target" "lambda_warmup" {
  count = var.warmup_enabled ? var.warmup_concurrency : 0

  rule      = aws_cloudwatch_event_rule.lambda_warmup[0].name
  target_id = "lambda-warmup-${count.index}"
  arn       = aws_lambda_function.main.arn

  input = jsonencode({
    warmup = true
    note   = "EventBridge warm-up ping"
    index  = count.index
  })
}

resource "aws_lambda_permission" "allow_eventbridge_warmup" {
  count = var.warmup_enabled ? 1 : 0

  statement_id  = "AllowEventBridgeWarmup"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.main.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.lambda_warmup[0].arn
}
