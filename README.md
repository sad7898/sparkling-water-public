# Real-Time Crypto Sentiment Analysis

### CMPT 732 - Fall 2025

## Overview

Tracks Reddit discussions and crypto prices to analyze sentiment trends in real-time.

***This project is for CMPT732 final project cloned from SFU GitHub*** 

## Architecture

- Lambda for data extraction
- S3 as data lake
- EMR (Spark) for sentiment analysis
- Streamlit dashboard for visualization

## Setup Instructions

1. `conda env create -f environment.yml`
2. `python data_ingestion/coingecko_pipeline.py`
3. (optional) `aws configure` for S3 access

## Repo Structure

data_ingestion/ → scripts for Reddit & CoinGecko data  
sentiment_analysis/ → Spark + Hugging Face  
dashboard/ → Streamlit web app  
docs/ → report, diagrams, proposal


## Prerequisites

Before deploying, ensure you have:

1. **AWS CLI** installed and configured
   ```bash
   aws configure
   ```

2. **Terraform** installed (version >= 1.2)
   ```bash
   # macOS with Homebrew
   brew install terraform
   
   # Or download from https://terraform.io/downloads
   ```

3. **AWS Credentials** with appropriate permissions:
   - S3 full access
   - Lambda full access
   - IAM role creation
   - EventBridge/CloudWatch Events
   - CloudWatch Logs

4. **S3 Backend Bucket** (optional but recommended):
   ```bash
   aws s3 mb s3://your-terraform-state-bucket
   ```

## Local Deployment

### Step 1: Clone and Navigate
```bash
git clone <your-repo-url>
cd sparkling-water
```


### Step 2: Initialize Terraform
```bash
cd infrastructure/terraform
terraform init
```

### Step 3: Plan Deployment
Review what will be created:
```bash
terraform plan
```

Optional: Specify environment and customize variables:
```bash
terraform plan -var="environment=dev" -var="project_name=my-pipeline"
```

### Step 4: Deploy Infrastructure
```bash
terraform apply
```

Or with custom variables:
```bash
terraform apply -var="environment=prod" -var="data_extraction_schedule=rate(10 minutes)"
```

### Step 5: Verify Deployment
After successful deployment, you should see output similar to:
```
data_bucket_name = "sparkling-water-dev-data-bucket"
processed_data_bucket_name = "sparkling-water-dev-processed-data-bucket"
data_extractor_lambda_arn = "arn:aws:lambda:us-east-1:..."
```

## Configuration Options

You can customize the deployment by setting variables:

```bash
terraform apply \
  -var="environment=staging" \
  -var="project_name=my-data-pipeline" \
  -var="data_extraction_schedule=rate(2 minutes)" \
  -var="aws_region=us-west-2"
```

Available variables:
- `project_name`: Name prefix for resources (default: "sparkling-water")
- `environment`: Environment suffix (default: "dev")
- `aws_region`: AWS region (default: "us-east-1")
- `data_extraction_schedule`: Schedule expression (default: "rate(5 minutes)")


## Cleanup

To destroy all infrastructure:
```bash
terraform destroy
```
