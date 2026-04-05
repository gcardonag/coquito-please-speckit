# Data Model: AWS Deployment with Role-Based Authentication

**Branch**: `002-aws-deploy-auth` | **Phase**: 1 — Design

---

## Overview

No new DynamoDB tables are introduced in this feature. The primary new data store is the **Amazon Cognito User Pool**, which holds user accounts and group memberships. The existing DynamoDB tables (requests, batches, varieties) are unchanged.

---

## Cognito User Pool (Identity Store)

### User Attributes

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `sub` | UUID (system-generated) | Yes | Primary identifier across all systems |
| `email` | String | Yes | Username; must be unique in the pool |
| `email_verified` | Boolean | System | Set true after OTP confirmation |
| `given_name` | String | No | Display name |
| `custom:role` | String | No | Informational only; enforcement is via group membership |

### User Groups

| Group Name | Purpose | Access Level |
|------------|---------|--------------|
| `chef` | Restaurant operator — full management access | Create/read/update varieties, batches, requests; provision users |
| `authorized-user` | Invited customer — limited access | Submit and view own requests |

**Role precedence rule**: If a user belongs to both `chef` and `authorized-user`, the Lambda authorizer grants `chef` access. Authorization checks `cognito:groups` claim and selects the highest-privilege role present.

### App Client Configuration

| Setting | Value |
|---------|-------|
| `name` | `coquito-app-client` |
| `explicit_auth_flows` | `ALLOW_USER_AUTH`, `ALLOW_REFRESH_TOKEN_AUTH` |
| `auth_session_validity` | 8 minutes (Managed Login default) |
| `access_token_validity` | 60 minutes (FR-009) |
| `refresh_token_validity` | 30 days |
| `token_validity_units` | minutes / days respectively |
| `generate_secret` | `true` (server-side token exchange) |
| `allowed_oauth_flows` | `code` (PKCE) |
| `allowed_oauth_scopes` | `openid`, `email`, `profile` |
| `callback_urls` | `https://coquito.gcardona.me/auth/callback` |
| `logout_urls` | `https://coquito.gcardona.me/` |
| `supported_identity_providers` | `COGNITO` |
| `prevent_user_existence_errors` | `ENABLED` |

---

## Session / Token Lifecycle

Tokens are **not stored in DynamoDB**. Lifecycle is managed entirely by Cognito and httpOnly cookies.

```
[Cognito EMAIL_OTP Login]
        │
        ▼
[Cognito Managed Login issues auth code]
        │
        ▼
[Token Exchange Lambda: POST /auth/callback?code=...]
        │  Calls Cognito /oauth2/token
        │  Sets httpOnly cookies:
        │    id_token     (60 min TTL)
        │    access_token (60 min TTL)
        │    refresh_token (30 day TTL)
        ▼
[Browser stores cookies; subsequent API calls include cookies automatically]
        │
        ▼
[Lambda Authorizer validates id_token from Cookie header]
        │  Fetches JWKS from Cognito (cached)
        │  Verifies signature, expiry, audience
        │  Extracts cognito:groups claim
        │  Returns IAM policy + context: { userId, role }
        ▼
[Lambda handler receives: event.requestContext.authorizer.lambda.userId/role]
```

### Cookie Specification

| Cookie | Flags | Max-Age | Path |
|--------|-------|---------|------|
| `id_token` | `HttpOnly; Secure; SameSite=Strict` | 3600s (60 min) | `/` |
| `access_token` | `HttpOnly; Secure; SameSite=Strict` | 3600s (60 min) | `/` |
| `refresh_token` | `HttpOnly; Secure; SameSite=Strict` | 2592000s (30 days) | `/auth/refresh` |

`refresh_token` path is scoped to `/auth/refresh` to prevent it from being sent with every API request.

### Session Inactivity (FR-009)

- `id_token` and `access_token` expire after 60 minutes.
- The frontend calls `POST /auth/refresh` (silently) before expiry if the user has been active within the last 60 minutes.
- If no refresh call is made within 60 minutes, the access token expires. The Lambda authorizer returns `Deny`, API Gateway returns 401, and the frontend redirects to login.
- There is no server-side session tracking; the TTL-based cookie is the sole enforcer.

---

## Lambda Authorizer Context

The Lambda authorizer enriches the request context, available to all downstream Lambdas as `event['requestContext']['authorizer']['lambda']`:

```json
{
  "userId": "<cognito-sub>",
  "role": "chef" | "authorized-user",
  "email": "<user-email>"
}
```

---

## Existing DynamoDB Tables (Unchanged)

| Table | Key | Description |
|-------|-----|-------------|
| `coquito-requests` | `requestId` (PK) | Customer requests |
| `coquito-batches` | `batchId` (PK) | Production batches |
| `coquito-varieties` | `varietyId` (PK) | Coquito varieties |

No schema changes are required to existing tables. Role-based access is enforced at the API layer, not the data layer.

---

## Infrastructure Entities (Terraform-managed, not DynamoDB)

These are AWS resource entities managed by Terraform, included here for completeness:

| Entity | AWS Resource | Identifier |
|--------|-------------|-----------|
| User Pool | `aws_cognito_user_pool` | Pool ID (output) |
| App Client | `aws_cognito_user_pool_client` | Client ID + Secret (SSM) |
| Chef Group | `aws_cognito_user_group` | `chef` |
| Authorized User Group | `aws_cognito_user_group` | `authorized-user` |
| Frontend Bucket | `aws_s3_bucket` | `coquito-please-frontend-prod` |
| CloudFront Distribution | `aws_cloudfront_distribution` | Distribution ID (output) |
| HTTP API | `aws_apigatewayv2_api` | API ID (output) |
| Token Exchange Lambda | `aws_lambda_function` | `coquito-auth-token-exchange` |
| Logout Lambda | `aws_lambda_function` | `coquito-auth-logout` |
| Authorizer Lambda | `aws_lambda_function` | `coquito-auth-authorizer` |
| ACM Certificate | `aws_acm_certificate` | ARN (output) |
