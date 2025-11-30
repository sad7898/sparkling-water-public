# DynamoDB Table for Processed Joined Data
resource "aws_dynamodb_table" "crypto_sentiment" {
  name           = "${local.name_prefix}-crypto-sentiment"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "coin"
  range_key      = "current_ts"

  attribute {
    name = "coin"
    type = "S"
  }

  attribute {
    name = "current_ts"
    type = "S"
  }

  tags = local.common_tags
}