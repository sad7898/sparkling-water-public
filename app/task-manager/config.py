import os

DATA_BUCKET_NAME = os.getenv("DATA_BUCKET_NAME", "sparkling-water-data-bucket")
EMR_SERVERLESS_APPLICATION_ID = os.getenv("EMR_APPLICATION_ID", "")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL", "")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
EMR_EXECUTION_ROLE_ARN = os.getenv("EMR_EXECUTION_ROLE_ARN", "")
EMR_SCRIPT_PATH = os.getenv("EMR_SCRIPT_PATH", "spark_jobs/sentiment_spark_job.py")