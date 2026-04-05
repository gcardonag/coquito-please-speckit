resource "aws_dynamodb_table" "varieties" {
  name                        = "coquito-varieties-${var.environment}"
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = "varietyId"
  deletion_protection_enabled = true

  attribute {
    name = "varietyId"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }
}

resource "aws_dynamodb_table" "batches" {
  name                        = "coquito-batches-${var.environment}"
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = "batchId"
  deletion_protection_enabled = true

  attribute {
    name = "batchId"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }
}

resource "aws_dynamodb_table" "requests" {
  name                        = "coquito-requests-${var.environment}"
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = "requestId"
  deletion_protection_enabled = true

  attribute {
    name = "requestId"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }
}
