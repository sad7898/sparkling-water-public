terraform {
  backend "s3" {
    bucket = "sparkling-water-terraform-state-use1"
    key    = "sparkling-water/infrastructure/terraform.tfstate"
    region = "us-east-1"
  }
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.20"
    }
  }
  required_version = ">= 1.2"
}

provider "aws" {
  region = var.aws_region
}

module "subnets" {
  source = "./modules/subnets"
}

