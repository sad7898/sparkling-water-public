resource "aws_iam_role" "data_extractor_lambda_role" {
  name = "${local.name_prefix}-data-extractor-lambda-role"

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

  tags = local.common_tags
}

resource "aws_iam_policy" "data_extractor_s3_policy" {
  name        = "${local.name_prefix}-data-extractor-s3-policy"
  description = "Policy for data extractor Lambda to write to S3"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl",
          "s3:ListBucket",
          "s3:GetObject"
        ]
        Resource = "${aws_s3_bucket.data_bucket.arn}/*"
      }
    ]
  })
}

resource "aws_iam_role" "task_manager_lambda_role" {
  name = "${local.name_prefix}-task-manager-lambda-role"

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

  tags = local.common_tags
}

resource "aws_iam_policy" "task_manager_emr_policy" {
  name        = "${local.name_prefix}-task-manager-emr-policy"
  description = "Policy for task manager Lambda to submit EMR Serverless jobs"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "emr-serverless:StartJobRun",
          "emr-serverless:GetJobRun",
          "emr-serverless:ListJobRuns",
          "emr-serverless:CancelJobRun",
          "emr-serverless:GetApplication",
          "emr-serverless:ListApplications"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = aws_iam_role.emr_serverless_execution_role.arn
      }
    ]
  })
}

resource "aws_iam_policy" "task_manager_sqs_policy" {
  name        = "${local.name_prefix}-task-manager-sqs-policy"
  description = "Policy for task manager Lambda to consume SQS messages"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = [
          aws_sqs_queue.s3_notifications_queue.arn,
          aws_sqs_queue.s3_notifications_dlq.arn
        ]
      }
    ]
  })
}

resource "aws_iam_policy" "task_manager_s3_policy" {
  name        = "${local.name_prefix}-task-manager-s3-policy"
  description = "Policy for task manager Lambda to read from S3 data bucket"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket",
          "s3:GetObjectVersion"
        ]
        Resource = [
          "${aws_s3_bucket.data_bucket.arn}",
          "${aws_s3_bucket.data_bucket.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "data_extractor_basic_execution" {
  role       = aws_iam_role.data_extractor_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "data_extractor_s3_attachment" {
  role       = aws_iam_role.data_extractor_lambda_role.name
  policy_arn = aws_iam_policy.data_extractor_s3_policy.arn
}

resource "aws_iam_role_policy_attachment" "task_manager_basic_execution" {
  role       = aws_iam_role.task_manager_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "task_manager_emr_attachment" {
  role       = aws_iam_role.task_manager_lambda_role.name
  policy_arn = aws_iam_policy.task_manager_emr_policy.arn
}

resource "aws_iam_role_policy_attachment" "task_manager_s3_attachment" {
  role       = aws_iam_role.task_manager_lambda_role.name
  policy_arn = aws_iam_policy.task_manager_s3_policy.arn
}

resource "aws_iam_role_policy_attachment" "task_manager_sqs_attachment" {
  role       = aws_iam_role.task_manager_lambda_role.name
  policy_arn = aws_iam_policy.task_manager_sqs_policy.arn
}