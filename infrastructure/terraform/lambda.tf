# data extractor lambda
resource "null_resource" "data_extractor_dependencies" {
  triggers = {
    always_run = timestamp()
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      echo "Installing dependencies for data-extractor..."
      
      BUILD_DIR="/tmp/data-extractor-build"
      rm -rf $BUILD_DIR
      mkdir -p $BUILD_DIR
      
      cp -r ${path.root}/../../app/data-extractor/* $BUILD_DIR/
      
      cd $BUILD_DIR
      python3 -m pip install -r requirements.txt -t .
      
      find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
      find . -name "*.pyc" -delete
      find . -name "*.pyo" -delete
      find . -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true
      
      echo "Dependencies installed successfully for data-extractor"
    EOT
  }
}

data "archive_file" "data_extractor_zip" {
  depends_on = [null_resource.data_extractor_dependencies]
  
  type        = "zip"
  output_path = "/tmp/data_extractor.zip"
  source_dir  = "/tmp/data-extractor-build"
}

resource "aws_lambda_function" "data_extractor" {
  filename         = data.archive_file.data_extractor_zip.output_path
  function_name    = "${local.name_prefix}-data-extractor"
  role             = aws_iam_role.data_extractor_lambda_role.arn
  handler          = "lambda_handler.handle"
  runtime          = "python3.13"
  timeout          = 300
  source_code_hash = data.archive_file.data_extractor_zip.output_base64sha256

  environment {
    variables = {
      DATA_BUCKET_NAME = aws_s3_bucket.data_bucket.bucket
      REDDIT_CLIENT_ID = ""
      REDDIT_CLIENT_SECRET = ""
    }
  }
  lifecycle {
    ignore_changes = [
          environment, # This would prevent any environment variable changes
    ]
  }
  tags = local.common_tags
}

resource "aws_lambda_permission" "allow_eventbridge_invoke_extractor" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.data_extractor.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.data_extraction_schedule.arn
}

# task manager lambda
resource "null_resource" "task_manager_dependencies" {
  triggers = {
    always_run = timestamp()
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      echo "Installing dependencies for task-manager..."
      
      BUILD_DIR="/tmp/task-manager-build"
      rm -rf $BUILD_DIR
      mkdir -p $BUILD_DIR
      
      cp -r ${path.root}/../../app/task-manager/* $BUILD_DIR/
      
      cd $BUILD_DIR
      python3 -m pip install -r requirements.txt -t .
      
      find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
      find . -name "*.pyc" -delete
      find . -name "*.pyo" -delete
      find . -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true
      
      echo "Dependencies installed successfully for task-manager"
    EOT
  }
}

data "archive_file" "task_manager_zip" {
  depends_on = [null_resource.task_manager_dependencies]
  
  type        = "zip"
  output_path = "/tmp/task_manager.zip"
  source_dir  = "/tmp/task-manager-build"
}

resource "aws_lambda_function" "task_manager" {
  filename         = data.archive_file.task_manager_zip.output_path
  function_name    = "${local.name_prefix}-task-manager"
  role             = aws_iam_role.task_manager_lambda_role.arn
  handler          = "lambda_handler.handle"
  runtime          = "python3.13"
  timeout          = 60
  source_code_hash = data.archive_file.task_manager_zip.output_base64sha256

  environment {
    variables = {
      DATA_BUCKET_NAME = aws_s3_bucket.data_bucket.bucket
      EMR_APPLICATION_ID = aws_emrserverless_application.sparkling_water_app.id
      EMR_EXECUTION_ROLE_ARN = aws_iam_role.emr_serverless_execution_role.arn
      SQS_QUEUE_URL = aws_sqs_queue.s3_notifications_queue.url
      EMR_SCRIPT_PATH = "spark_jobs/sentiment_and_join.py"
    }
  }

  tags = local.common_tags
}

