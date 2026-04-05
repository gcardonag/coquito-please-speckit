output "user_pool_id" {
  description = "Cognito User Pool ID"
  value       = aws_cognito_user_pool.main.id
}

output "user_pool_arn" {
  description = "Cognito User Pool ARN"
  value       = aws_cognito_user_pool.main.arn
}

output "client_id" {
  description = "Cognito App Client ID"
  value       = aws_cognito_user_pool_client.main.id
}

output "client_secret_ssm_path" {
  description = "SSM path where the app client secret is stored"
  value       = aws_ssm_parameter.client_secret.name
}

output "jwks_uri" {
  description = "JWKS endpoint for JWT validation"
  value       = "https://cognito-idp.${data.aws_region.current.name}.amazonaws.com/${aws_cognito_user_pool.main.id}/.well-known/jwks.json"
}

output "token_endpoint" {
  description = "Cognito OAuth2 token endpoint"
  value       = "https://auth.${var.domain}/oauth2/token"
}

output "domain" {
  description = "Cognito Managed Login domain"
  value       = aws_cognito_user_pool_domain.main.domain
}

output "auth_domain_alias_target" {
  description = "CloudFront alias target for the Cognito custom domain (for Route53 CNAME)"
  value       = aws_cognito_user_pool_domain.main.cloudfront_distribution
}

data "aws_region" "current" {}
