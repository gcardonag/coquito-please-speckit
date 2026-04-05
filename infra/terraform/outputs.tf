output "frontend_url" {
  description = "HTTPS URL of the frontend application"
  value       = "https://${var.domain}"
}

output "api_url" {
  description = "HTTPS URL of the API"
  value       = "https://api.${var.domain}"
}

output "auth_url" {
  description = "HTTPS URL of the Cognito Managed Login"
  value       = "https://auth.${var.domain}"
}

output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = module.auth.user_pool_id
}

output "cognito_client_id" {
  description = "Cognito App Client ID"
  value       = module.auth.client_id
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID (for cache invalidation)"
  value       = module.frontend.cloudfront_distribution_id
}

output "s3_bucket_name" {
  description = "S3 bucket name for frontend assets"
  value       = module.frontend.bucket_name
}
