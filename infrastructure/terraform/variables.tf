variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "sparkling-water"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "data_extraction_schedule" {
  description = "CloudWatch Events schedule expression for data extraction"
  type        = string
  default     = "rate(5 minutes)"
}

variable "ingestor_package_name" {
  description = "Name of the package to be used in Lambda functions"
  type        = string
  default     = "ingestor_lambda.zip"
}

variable "emr_serverless_min_capacity" {
  description = "Minimum capacity for EMR Serverless application (cost optimization)"
  type = object({
    cpu    = string
    memory = string
  })
  default = {
    cpu    = "1 vCPU"
    memory = "2 GB"
  }
}

variable "emr_serverless_max_capacity" {
  description = "Maximum capacity for EMR Serverless application"
  type = object({
    cpu    = string
    memory = string
  })
  default = {
    cpu    = "32 vCPU"
    memory = "80 GB"  
  }
}

variable "emr_serverless_auto_stop_minutes" {
  description = "Auto-stop configuration in minutes for cost optimization"
  type        = number
  default     = 15
}

variable "emr_serverless_pre_initialized_capacity" {
  description = "Pre-initialized capacity"
  type = object({
    cpu    = string
    memory = string
  })
  default = {
    cpu    = "0 vCPU"
    memory = "0 GB"
  }
}