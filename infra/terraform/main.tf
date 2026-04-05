module "acm" {
  source = "./modules/acm"

  domain         = var.domain
  hosted_zone_id = var.hosted_zone_id
}

module "frontend" {
  source = "./modules/frontend"

  domain          = var.domain
  certificate_arn = module.acm.certificate_arn
}

module "auth" {
  source = "./modules/auth"

  domain          = var.domain
  environment     = var.environment
  certificate_arn = module.acm.certificate_arn
}

module "api" {
  source = "./modules/api"

  domain                         = var.domain
  environment                    = var.environment
  certificate_arn                = module.acm.certificate_arn
  cognito_user_pool_id           = module.auth.user_pool_id
  cognito_user_pool_arn          = module.auth.user_pool_arn
  cognito_client_id              = module.auth.client_id
  cognito_client_secret_ssm_path = module.auth.client_secret_ssm_path
  cognito_jwks_uri               = module.auth.jwks_uri
  cognito_token_endpoint         = module.auth.token_endpoint
}

module "dns" {
  source = "./modules/dns"

  domain                          = var.domain
  hosted_zone_id                  = var.hosted_zone_id
  cloudfront_domain_name          = module.frontend.cloudfront_domain_name
  cloudfront_hosted_zone_id       = module.frontend.cloudfront_hosted_zone_id
  api_target_domain_name          = module.api.target_domain_name
  api_hosted_zone_id              = module.api.hosted_zone_id
  cognito_auth_domain_alias_target = module.auth.auth_domain_alias_target
}
