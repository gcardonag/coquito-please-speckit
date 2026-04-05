# Contract: Terraform Module Outputs

**Branch**: `002-aws-deploy-auth`  
**Purpose**: Defines the outputs exposed by each Terraform module. These are the integration points between modules and the values needed by application code at deploy time.

---

## Root Module Outputs (`infra/terraform/outputs.tf`)

| Output | Description | Consumer |
|--------|-------------|----------|
| `frontend_url` | `https://coquito.gcardona.me` | Docs, CI |
| `api_url` | `https://api.coquito.gcardona.me` | Frontend config, CI |
| `auth_url` | `https://auth.coquito.gcardona.me` | Frontend config |
| `cognito_user_pool_id` | Cognito User Pool ID | App config, CI |
| `cognito_client_id` | App client ID | Frontend config |
| `cloudfront_distribution_id` | CloudFront ID | CI cache invalidation |
| `s3_bucket_name` | Frontend S3 bucket | CI deploy |

---

## Module: `acm`

| Output | Description |
|--------|-------------|
| `certificate_arn` | ARN of the ACM cert (us-east-1), used by CloudFront and API GW |

---

## Module: `frontend`

| Output | Description |
|--------|-------------|
| `bucket_name` | S3 bucket name for frontend assets |
| `cloudfront_distribution_id` | Distribution ID for cache invalidation |
| `cloudfront_domain_name` | CloudFront default domain (used internally by DNS module) |

---

## Module: `auth`

| Output | Description |
|--------|-------------|
| `user_pool_id` | Cognito User Pool ID |
| `user_pool_arn` | Cognito User Pool ARN (for Lambda permissions) |
| `client_id` | App client ID |
| `client_secret_ssm_path` | SSM Parameter path for the app client secret |
| `jwks_uri` | Cognito JWKS endpoint (used by Lambda authorizer) |
| `token_endpoint` | Cognito `/oauth2/token` endpoint (used by token-exchange Lambda) |
| `domain` | Cognito domain (`auth.coquito.gcardona.me`) |

---

## Module: `api`

| Output | Description |
|--------|-------------|
| `api_id` | HTTP API ID |
| `api_endpoint` | Default API endpoint URL |
| `custom_domain_name` | `api.coquito.gcardona.me` (used by DNS module) |
| `target_domain_name` | API GW regional domain name (for Route53 alias) |
| `hosted_zone_id` | API GW regional hosted zone ID (for Route53 alias) |

---

## Module: `dns`

No outputs (only creates Route53 records). DNS propagation is verified via CI health check.

---

## SSM Parameter Store Layout

Sensitive values are stored in SSM Parameter Store (SecureString) and injected into Lambdas via environment variables at deploy time:

| SSM Path | Value | Consumer |
|----------|-------|----------|
| `/coquito/prod/cognito/client_secret` | App client secret | Token exchange Lambda |
| `/coquito/prod/cognito/user_pool_id` | User Pool ID | Authorizer Lambda |
| `/coquito/prod/cognito/client_id` | Client ID | Token exchange Lambda |
| `/coquito/prod/cognito/jwks_uri` | JWKS URL | Authorizer Lambda |

Lambdas read these at **cold-start** via `boto3.client('ssm')` and cache them in the execution environment. No secrets are stored in environment variables or code.
