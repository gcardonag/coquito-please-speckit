resource "aws_cognito_user_pool" "main" {
  name = "coquito-user-pool-${var.environment}"

  # Email as username
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  # No self-registration — Chef provisions all accounts
  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  # EMAIL_OTP passwordless authentication
  sign_in_policy {
    allowed_first_auth_factors = ["EMAIL_OTP", "PASSWORD"]
  }

  # Managed Login (Essentials plan required for EMAIL_OTP)
  user_pool_tier = "ESSENTIALS"

  # Prevent accidental deletion
  deletion_protection = "ACTIVE"

  password_policy {
    minimum_length                   = 8
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = false
    require_uppercase                = true
    temporary_password_validity_days = 7
  }

  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }
}

resource "aws_cognito_user_pool_client" "main" {
  name         = "coquito-app-client"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret = true

  # Allow authorization code flow (PKCE) + refresh tokens
  explicit_auth_flows = [
    "ALLOW_USER_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]

  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  allowed_oauth_flows_user_pool_client = true

  supported_identity_providers = ["COGNITO"]

  callback_urls = ["https://${var.domain}/auth/callback"]
  logout_urls   = ["https://${var.domain}/"]

  # Token validity
  access_token_validity  = 60   # 60 minutes (FR-009)
  id_token_validity      = 60   # 60 minutes
  refresh_token_validity = 30   # 30 days

  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }

  prevent_user_existence_errors = "ENABLED"
}

resource "aws_cognito_user_group" "chef" {
  name         = "chef"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "Restaurant operators — full management access"
  precedence   = 0
}

resource "aws_cognito_user_group" "authorized_user" {
  name         = "authorized-user"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "Invited customers — limited access"
  precedence   = 1
}

resource "aws_cognito_user_pool_domain" "main" {
  domain                = "auth.${var.domain}"
  certificate_arn       = var.certificate_arn
  user_pool_id          = aws_cognito_user_pool.main.id
  managed_login_version = 2
}

resource "aws_cognito_managed_login_branding" "main" {
  user_pool_id                = aws_cognito_user_pool.main.id
  client_id                   = aws_cognito_user_pool_client.main.id
  use_cognito_provided_values = true
}

# Store client secret in SSM — never in code or env vars
resource "aws_ssm_parameter" "client_secret" {
  name  = "/coquito/${var.environment}/cognito/client_secret"
  type  = "SecureString"
  value = aws_cognito_user_pool_client.main.client_secret

  lifecycle {
    ignore_changes = [value]
  }
}
