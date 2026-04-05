output "bucket_name" {
  description = "S3 bucket name for the frontend assets"
  value       = aws_s3_bucket.main.id
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.main.id
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name (for DNS alias target)"
  value       = aws_cloudfront_distribution.main.domain_name
}

output "cloudfront_hosted_zone_id" {
  description = "CloudFront hosted zone ID (for Route53 alias)"
  value       = aws_cloudfront_distribution.main.hosted_zone_id
}
