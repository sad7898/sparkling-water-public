# Data source to get VPC information
data "aws_vpc" "selected" {
  count = var.vpc_id != null ? 1 : 0
  id    = var.vpc_id
}

data "aws_vpc" "default" {
  count   = var.vpc_id == null ? 1 : 0
  default = true
}

locals {
  vpc_id = var.vpc_id != null ? var.vpc_id : data.aws_vpc.default[0].id
}

# Data source to get all subnets in the VPC
data "aws_subnets" "selected" {
  filter {
    name   = "vpc-id"
    values = [local.vpc_id]
  }

  dynamic "filter" {
    for_each = var.availability_zones != null ? [1] : []
    content {
      name   = "availability-zone"
      values = var.availability_zones
    }
  }

  dynamic "filter" {
    for_each = var.subnet_type != null ? [1] : []
    content {
      name   = "tag:Type"
      values = [var.subnet_type]
    }
  }

  tags = var.subnet_tags
}

# Data source to get detailed information about each subnet
data "aws_subnet" "selected" {
  for_each = toset(data.aws_subnets.selected.ids)
  id       = each.value
}

data aws_security_group "selected" {
  vpc_id = local.vpc_id
  filter {
    name   = "group-name"
    values = ["default"]
  }
}