# Real-Time Crypto Sentiment Analysis

### CMPT 732 - Fall 2025

## Overview

Tracks Reddit discussions and crypto prices to analyze sentiment trends in real-time.
***This project is for CMPT732 final project cloned from SFU GitHub*** 
## Architecture

<img width="877" height="477" alt="image" src="https://github.com/user-attachments/assets/6f6dd3ea-d1a3-444b-8ec8-de67edbc3488" />


## Setup Instructions

1. `conda env create -f environment.yml`
2. `python data_ingestion/coingecko_pipeline.py`
3. (optional) `aws configure` for S3 access

## Repo Structure

infrastructure/terraform => infrastructure configuration

infrastructure/terraform/spark_jobs => spark script for EMR

app/ ==> each directory contains source codes for each lambda function except frontend

app/frontend ==> streamlit frontend


## Running the UI
If you only want to run the UI

1. **AWS CLI** installed and configured
   ```bash
   aws configure
   ```
2. **AWS Credentials** with appropriate permissions:
   - DynamoDB Read access

3. Install python dependencies
   ```bash
   pip3 install -r /app/frontend/requirements.txt
   ```
4. Run streamlit
   ```bash
   streamlit run app/frontend/app.py
   ```

   
## Deployment Prerequisites

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
   - Dynamodb
   - EMR

4. **S3 Backend Bucket**: 
   Create an S3 bucket to store terraform state
   ```bash
   aws s3 mb s3://your-terraform-state-bucket
   ```
   or use AWS console

## Deployment

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
terraform plan
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
Go to AWS console to check resource configuration

### Step 6: Upload Spark Script
1. Go to AWS S3 console and upload spark script to bucket **sparkling-water-dev-data-bucket** (default script is **sentiment_and_join-3.py**)
2. If script is different from default, go to AWS Lambda console. Click on lambda function named **sparkling-water-dev-task-manager**
   Change environment variable **EMR_SCRIPT_PATH** to appropiate location

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
