# Route53 alias A record — coquito.gcardona.me → CloudFront
resource "aws_route53_record" "frontend" {
  zone_id = var.hosted_zone_id
  name    = var.domain
  type    = "A"

  alias {
    name                   = var.cloudfront_domain_name
    zone_id                = var.cloudfront_hosted_zone_id
    evaluate_target_health = false
  }
}

# Route53 alias A record — api.coquito.gcardona.me → API Gateway custom domain
resource "aws_route53_record" "api" {
  zone_id = var.hosted_zone_id
  name    = "api.${var.domain}"
  type    = "A"

  alias {
    name                   = var.api_target_domain_name
    zone_id                = var.api_hosted_zone_id
    evaluate_target_health = false
  }
}

# Route53 CNAME — auth.coquito.gcardona.me → Cognito custom domain alias
resource "aws_route53_record" "auth" {
  zone_id = var.hosted_zone_id
  name    = "auth.${var.domain}"
  type    = "CNAME"
  ttl     = 300
  records = [var.cognito_auth_domain_alias_target]
}
