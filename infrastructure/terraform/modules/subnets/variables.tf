variable "vpc_id" {
  description = "VPC ID to get subnets from. If not provided, the default VPC will be used."
  type        = string
  default     = null
}

variable "availability_zones" {
  description = "List of availability zones to filter subnets by"
  type        = list(string)
  default     = null
}

variable "subnet_type" {
  description = "Type of subnets to filter by (e.g., 'public', 'private'). Expects a 'Type' tag on subnets."
  type        = string
  default     = null
}

variable "subnet_tags" {
  description = "Map of tags to filter subnets by"
  type        = map(string)
  default     = {}
}