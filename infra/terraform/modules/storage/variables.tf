variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "domain" {
  description = "Primary domain (for CLOUDFRONT_ASSETS_BASE_URL output)"
  type        = string
}
