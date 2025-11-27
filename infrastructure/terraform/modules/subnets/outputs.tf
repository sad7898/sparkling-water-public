output "subnet_ids" {
  description = "List of subnet IDs"
  value       = data.aws_subnets.selected.ids
}

output "subnet_details" {
  description = "Map of subnet details with subnet ID as key"
  value = {
    for subnet in data.aws_subnet.selected : subnet.id => {
      id                              = subnet.id
      arn                             = subnet.arn
      cidr_block                      = subnet.cidr_block
      availability_zone               = subnet.availability_zone
      vpc_id                          = subnet.vpc_id
      tags                            = subnet.tags
      map_public_ip_on_launch         = subnet.map_public_ip_on_launch
      assign_ipv6_address_on_creation = subnet.assign_ipv6_address_on_creation
      ipv6_cidr_block                 = subnet.ipv6_cidr_block
      state                           = subnet.state
    }
  }
}

output "public_subnet_ids" {
  description = "List of public subnet IDs (subnets that map public IPs on launch)"
  value = [
    for subnet in data.aws_subnet.selected : subnet.id
    if subnet.map_public_ip_on_launch
  ]
}

output "private_subnet_ids" {
  description = "List of private subnet IDs (subnets that don't map public IPs on launch)"
  value = [
    for subnet in data.aws_subnet.selected : subnet.id
    if !subnet.map_public_ip_on_launch
  ]
}

output "vpc_id" {
  description = "VPC ID of the retrieved subnets"
  value       = local.vpc_id
}

output "availability_zones" {
  description = "List of availability zones for the retrieved subnets"
  value       = distinct([for subnet in data.aws_subnet.selected : subnet.availability_zone])
}

output "default_security_group_id" {
  description = "ID of the default security group in the VPC"
  value       = data.aws_security_group.selected.id
}