# SQS Queue for S3 notifications
resource "aws_sqs_queue" "s3_notifications_queue" {
  name                      = "${local.name_prefix}-s3-notifications-queue"
  delay_seconds             = 0
  max_message_size          = 2048
  message_retention_seconds = 1209600 # 14 days
  receive_wait_time_seconds = 10
  visibility_timeout_seconds = 330
  
  # Configure redrive policy for failed messages
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.s3_notifications_dlq.arn
    maxReceiveCount     = 3
  })

  tags = local.common_tags
}

# Dead Letter Queue for failed messages
resource "aws_sqs_queue" "s3_notifications_dlq" {
  name                      = "${local.name_prefix}-s3-notifications-dlq"
  message_retention_seconds = 1209600 # 14 days

  tags = local.common_tags
}

# SQS Queue Policy to allow S3 to send messages
resource "aws_sqs_queue_policy" "s3_notifications_queue_policy" {
  queue_url = aws_sqs_queue.s3_notifications_queue.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action = "sqs:SendMessage"
        Resource = aws_sqs_queue.s3_notifications_queue.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_s3_bucket.data_bucket.arn
          }
        }
      }
    ]
  })
}

# Lambda Event Source Mapping for SQS
resource "aws_lambda_event_source_mapping" "sqs_to_task_manager" {
  event_source_arn = aws_sqs_queue.s3_notifications_queue.arn
  function_name    = aws_lambda_function.task_manager.arn
  
  # Batch settings for processing multiple messages together
  batch_size                         = 60
  maximum_batching_window_in_seconds = 90
  
  scaling_config {
    maximum_concurrency = 2
  }
  
  function_response_types = ["ReportBatchItemFailures"]
}