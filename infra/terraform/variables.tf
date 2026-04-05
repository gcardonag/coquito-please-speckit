variable "domain" {
  description = "Primary domain for the application"
  type        = string
  default     = "coquito.gcardona.me"
}

variable "region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "hosted_zone_id" {
  description = "Route53 hosted zone ID for coquito.gcardona.me"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"
}

variable "chef_seed_email" {
  description = "Email address for the first Chef account (seeded on first deploy)"
  type        = string
}
