variable "domain" {
  description = "Primary domain (e.g. coquito.gcardona.me)"
  type        = string
}

variable "hosted_zone_id" {
  description = "Route53 hosted zone ID"
  type        = string
}

variable "cloudfront_domain_name" {
  description = "CloudFront distribution domain name (alias target for frontend)"
  type        = string
}

variable "cloudfront_hosted_zone_id" {
  description = "CloudFront hosted zone ID (Z2FDTNDATAQYW2 globally)"
  type        = string
}

variable "api_target_domain_name" {
  description = "API Gateway regional domain name (alias target for api.{domain})"
  type        = string
}

variable "api_hosted_zone_id" {
  description = "API Gateway hosted zone ID (for Route53 alias)"
  type        = string
}

variable "cognito_auth_domain_alias_target" {
  description = "CloudFront alias for the Cognito custom domain (CNAME target for auth.{domain})"
  type        = string
}
