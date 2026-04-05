variable "domain" {
  description = "Primary domain for the CloudFront distribution (e.g. coquito.gcardona.me)"
  type        = string
}

variable "certificate_arn" {
  description = "ARN of the ACM certificate (must be in us-east-1 for CloudFront)"
  type        = string
}
