variable "domain" {
  description = "Primary domain (e.g. coquito.gcardona.me)"
  type        = string
}

variable "hosted_zone_id" {
  description = "Route53 hosted zone ID"
  type        = string
}
