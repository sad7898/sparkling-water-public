resource "aws_cloudwatch_event_rule" "data_extraction_schedule" {
  name                = "${local.name_prefix}-data-extraction-schedule"
  description         = "Trigger data extraction Lambda every 5 minutes"
  schedule_expression = var.data_extraction_schedule
  tags                = local.common_tags
  state               = "DISABLED"
}

resource "aws_cloudwatch_event_target" "data_extraction_target" {
  rule      = aws_cloudwatch_event_rule.data_extraction_schedule.name
  target_id = aws_lambda_function.data_extractor.function_name
  arn       = aws_lambda_function.data_extractor.arn
}