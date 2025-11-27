# EMR Serverless Application - Cost Optimized for School Project
resource "aws_emrserverless_application" "sparkling_water_app" {
  name         = "${local.name_prefix}-emr-serverless"
  release_label = "emr-7.11.0"
  type         = "spark"
  initial_capacity {
    initial_capacity_type = "Driver"
    
    initial_capacity_config {
      worker_count = 1
      worker_configuration {
        cpu    = var.emr_serverless_min_capacity.cpu
        memory = var.emr_serverless_min_capacity.memory
        disk   = "20 GB"
      }
    }
  }

  initial_capacity {
    initial_capacity_type = "Executor"
    
    initial_capacity_config {
      worker_count = 2
      worker_configuration {
        cpu    = var.emr_serverless_min_capacity.cpu
        memory = var.emr_serverless_min_capacity.memory
        disk   = "20 GB"
      }
    }
  }
  monitoring_configuration {
    s3_monitoring_configuration {
      log_uri = "s3://${aws_s3_bucket.emr_logs_bucket.bucket}/emr-serverless-logs/"
    }
  }
  maximum_capacity {
    cpu    = var.emr_serverless_max_capacity.cpu
    memory = var.emr_serverless_max_capacity.memory
  }

  auto_stop_configuration {
    enabled              = true
    idle_timeout_minutes = var.emr_serverless_auto_stop_minutes
  }

  auto_start_configuration {
    enabled = true
  }

  tags = merge(local.common_tags, {
    Project = var.project_name
  })
}

# IAM Role for EMR Serverless
resource "aws_iam_role" "emr_serverless_execution_role" {
  name = "${local.name_prefix}-emr-serverless-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "emr-serverless.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = local.common_tags
}

# IAM Policy for EMR Serverless to access S3 data bucket
resource "aws_iam_policy" "emr_serverless_s3_policy" {
  name        = "${local.name_prefix}-emr-serverless-s3-policy"
  description = "Policy for EMR Serverless to access S3 data bucket"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${aws_s3_bucket.data_bucket.arn}",
          "${aws_s3_bucket.emr_logs_bucket.arn}",
          "${aws_s3_bucket.data_bucket.arn}/*",
          "${aws_s3_bucket.emr_logs_bucket.arn}/*"
        ]
      }
    ]
  })
}

# Attach the S3 policy
resource "aws_iam_role_policy_attachment" "emr_serverless_s3" {
  role       = aws_iam_role.emr_serverless_execution_role.name
  policy_arn = aws_iam_policy.emr_serverless_s3_policy.arn
}