output "data_bucket_name" {
  description = "Name of the S3 bucket for raw data storage"
  value       = aws_s3_bucket.data_bucket.bucket
}

output "data_bucket_arn" {
  description = "ARN of the S3 bucket for raw data storage"
  value       = aws_s3_bucket.data_bucket.arn
}

output "data_extractor_lambda_arn" {
  description = "ARN of the data extractor Lambda function"
  value       = aws_lambda_function.data_extractor.arn
}

output "data_extraction_schedule_arn" {
  description = "ARN of the EventBridge rule for data extraction"
  value       = aws_cloudwatch_event_rule.data_extraction_schedule.arn
}

# EMR Serverless Outputs
output "emr_serverless_application_id" {
  description = "ID of the EMR Serverless application"
  value       = aws_emrserverless_application.sparkling_water_app.id
}

output "emr_serverless_application_arn" {
  description = "ARN of the EMR Serverless application"
  value       = aws_emrserverless_application.sparkling_water_app.arn
}

output "emr_serverless_execution_role_arn" {
  description = "ARN of the EMR Serverless execution role"
  value       = aws_iam_role.emr_serverless_execution_role.arn
}