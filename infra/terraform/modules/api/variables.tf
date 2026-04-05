variable "domain" {
  description = "Primary domain (e.g. coquito.gcardona.me)"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "certificate_arn" {
  description = "ACM certificate ARN for api.{domain} custom domain"
  type        = string
}

variable "cognito_user_pool_id" {
  description = "Cognito User Pool ID (passed to Lambda env vars)"
  type        = string
}

variable "cognito_user_pool_arn" {
  description = "Cognito User Pool ARN (for IAM policy)"
  type        = string
}

variable "cognito_client_id" {
  description = "Cognito App Client ID"
  type        = string
}

variable "cognito_client_secret_ssm_path" {
  description = "SSM parameter path for Cognito client secret"
  type        = string
}

variable "cognito_jwks_uri" {
  description = "Cognito JWKS URI for JWT validation"
  type        = string
}

variable "cognito_token_endpoint" {
  description = "Cognito token endpoint URL"
  type        = string
}

variable "lambda_zip_path" {
  description = "Local path to the packaged Lambda ZIP file"
  type        = string
  default     = "../../backend/lambda.zip"
}

variable "dynamodb_requests_table" {
  description = "DynamoDB requests table name"
  type        = string
}

variable "dynamodb_batches_table" {
  description = "DynamoDB batches table name"
  type        = string
}

variable "dynamodb_varieties_table" {
  description = "DynamoDB varieties table name"
  type        = string
}

variable "cloudfront_assets_base_url" {
  description = "CloudFront base URL for media assets (e.g., https://coquito.gcardona.me)"
  type        = string
}
