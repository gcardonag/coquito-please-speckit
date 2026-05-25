output "requests_table_name" {
  value = aws_dynamodb_table.requests.name
}

output "batches_table_name" {
  value = aws_dynamodb_table.batches.name
}

output "varieties_table_name" {
  value = aws_dynamodb_table.varieties.name
}

output "cloudfront_assets_base_url" {
  description = "Base URL for CloudFront-served media assets"
  value       = "https://${var.domain}"
}

output "batch_access_table_name" {
  value = aws_dynamodb_table.batch_access.name
}
