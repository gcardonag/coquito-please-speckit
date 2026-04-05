variable "domain" {
  description = "Primary domain (e.g. coquito.gcardona.me)"
  type        = string
}

variable "environment" {
  description = "Deployment environment (e.g. prod)"
  type        = string
}

variable "certificate_arn" {
  description = "ACM certificate ARN for the auth.{domain} custom domain"
  type        = string
}
