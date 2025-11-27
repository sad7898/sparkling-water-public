resource "aws_s3_bucket" "data_bucket" {
  bucket = "${local.name_prefix}-data-bucket"
  tags   = local.common_tags
}

resource "aws_s3_bucket_versioning" "data_bucket_versioning" {
  bucket = aws_s3_bucket.data_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_bucket_encryption" {
  bucket = aws_s3_bucket.data_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "data_bucket_lifecycle" {
  bucket = aws_s3_bucket.data_bucket.id

  rule {
    id     = "expire_objects"
    status = "Enabled"
    filter {
      prefix = "raw/"
    }
    expiration {
      days = 7
    }
  }
}

resource "aws_s3_bucket_public_access_block" "data_bucket_pab" {
  bucket = aws_s3_bucket.data_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket Notification for SQS Queue
resource "aws_s3_bucket_notification" "data_bucket_notification" {
  bucket = aws_s3_bucket.data_bucket.id

  queue {
    queue_arn = aws_sqs_queue.s3_notifications_queue.arn
    events    = ["s3:ObjectCreated:*"]
    filter_prefix = "raw/reddit/"
  }

  depends_on = [aws_sqs_queue_policy.s3_notifications_queue_policy]
}

# Null resource to bundle Python dependencies for Spark jobs
resource "null_resource" "spark_dependencies_bundle" {
  # Trigger rebuilds when requirements.txt changes
  triggers = {
    requirements_hash = filemd5("${path.module}/spark_jobs/requirements.txt")
  }

  provisioner "local-exec" {
    command = <<-EOT
      docker build -t emr_deps:latest ${path.module}/spark_jobs
      container_id=$(docker create emr_deps:latest)
      docker cp $container_id:/output/pyspark_venv.tar.gz ${path.module}/spark_jobs/_spark_venv.tar.gz
      docker rm $container_id
    EOT
  }
}

# Upload the bundled dependencies to S3
resource "aws_s3_object" "spark_dependencies_zip" {
  bucket = aws_s3_bucket.data_bucket.bucket
  key    = "spark_jobs/dependencies/spark_venv.tar.gz"
  source = "${path.module}/spark_jobs/_spark_venv.tar.gz"
  
  tags = local.common_tags
  
  # Ensure the bundle is created first
  depends_on = [null_resource.spark_dependencies_bundle]
  lifecycle {
    replace_triggered_by = [ null_resource.spark_dependencies_bundle ]
  }
}

# S3 Bucket for EMR Serverless Logs
resource "aws_s3_bucket" "emr_logs_bucket" {
  bucket = "${local.name_prefix}-emr-logs-bucket"
  tags   = local.common_tags
}

resource "aws_s3_bucket_versioning" "emr_logs_bucket_versioning" {
  bucket = aws_s3_bucket.emr_logs_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "emr_logs_bucket_encryption" {
  bucket = aws_s3_bucket.emr_logs_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "emr_logs_bucket_pab" {
  bucket = aws_s3_bucket.emr_logs_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "emr_logs_lifecycle" {
  bucket = aws_s3_bucket.emr_logs_bucket.id

  rule {
    id     = "expire_objects"
    status = "Enabled"

    expiration {
      days = 7
    }
  }
}