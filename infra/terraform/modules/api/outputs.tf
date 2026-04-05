output "api_id" {
  description = "HTTP API ID"
  value       = aws_apigatewayv2_api.main.id
}

output "api_endpoint" {
  description = "Default HTTP API endpoint (before custom domain)"
  value       = aws_apigatewayv2_api.main.api_endpoint
}

output "custom_domain_name" {
  description = "Custom domain name (api.{domain})"
  value       = aws_apigatewayv2_domain_name.main.domain_name
}

output "target_domain_name" {
  description = "API Gateway regional domain name (for Route53 alias target)"
  value       = aws_apigatewayv2_domain_name.main.domain_name_configuration[0].target_domain_name
}

output "hosted_zone_id" {
  description = "Hosted zone ID for the API Gateway custom domain (for Route53 alias)"
  value       = aws_apigatewayv2_domain_name.main.domain_name_configuration[0].hosted_zone_id
}
