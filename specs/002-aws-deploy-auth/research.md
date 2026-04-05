# Research: AWS Deployment with Role-Based Authentication

**Branch**: `002-aws-deploy-auth` | **Phase**: 0 — Pre-design research

---

## 1. Passwordless Authentication via Cognito EMAIL_OTP

**Decision**: Use Cognito **choice-based authentication** with `ALLOW_USER_AUTH` flow and `EMAIL_OTP` as the passwordless factor.

**Rationale**:
- Cognito (Essentials plan or higher) natively supports `EMAIL_OTP` as a passwordless authentication method.
- The app client must set `ALLOW_USER_AUTH` in `explicit_auth_flows`.
- The UI uses Cognito Managed Login (hosted UI v2), which surfaces the email OTP flow automatically.
- No custom Lambda triggers are required for the basic OTP flow.
- Free tier covers 50,000 MAU/month (satisfies SC-005).

**Alternatives considered**:
- *Password-based (USER_SRP_AUTH)*: Simpler but requires password management and conflicts with the "passwordless" requirement in user input.
- *WebAuthn passkeys*: More modern but requires FIDO2-capable devices; narrower compatibility than email OTP.
- *Custom TOTP via Lambda trigger*: Possible but adds complexity without benefit when Cognito EMAIL_OTP is built-in.

**Spec Conflict — FR-003**:
> FR-003 currently reads: "Users MUST be able to log in using an email address and **password combination**."
> The user's plan input and feature intent are for **passwordless** EMAIL_OTP login.
> **Resolution**: FR-003 must be updated to read "via email OTP" before implementation begins.
> The plan proceeds with the passwordless (EMAIL_OTP) approach.

**Source**: [Cognito authentication flows](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-authentication-flow-methods.html)

---

## 2. httpOnly Cookie Token Storage + API Gateway Auth

**Decision**: Use **Cognito Managed Login OAuth2 flow** (authorization code) with a **token-exchange Lambda** that sets `httpOnly Secure SameSite=Strict` cookies. Protected API routes use a **Lambda authorizer** that reads the JWT from the cookie.

**Rationale**:
- Storing tokens in `localStorage` is forbidden (FR-012). `httpOnly` cookies prevent XSS-based token theft.
- The standard pattern ([AWS Security Blog](https://aws.amazon.com/blogs/security/reduce-risk-by-implementing-httponly-cookie-authentication-in-amazon-api-gateway/)) is:
  1. Cognito Managed Login redirects back with `?code=` authorization code.
  2. A token-exchange Lambda (`POST /auth/callback`) exchanges the code for access + ID + refresh tokens via Cognito's `/oauth2/token` endpoint.
  3. Lambda sets three `httpOnly Secure SameSite=Strict` cookies: `id_token`, `access_token`, `refresh_token`.
  4. A Lambda authorizer on each protected route reads the `Cookie` header, extracts the `id_token` JWT, validates it against Cognito's JWKS endpoint, and returns an IAM allow/deny policy.
- HTTP API (v2) supports Lambda authorizers; 70% cheaper than REST API.

**Alternatives considered**:
- *Cognito JWT authorizer (HTTP API native)*: Reads only from `Authorization: Bearer` header — cannot read cookies. Ruled out.
- *REST API with Cognito authorizer*: Same limitation; also more expensive.
- *Lambda authorizer on REST API*: Works but 3× the cost of HTTP API. Ruled out.

**Session expiry (FR-009 — 60 min inactivity)**:
- Access token TTL is set to **60 minutes** in the Cognito app client.
- The frontend calls `POST /auth/refresh` (exchanges refresh token cookie for new tokens) only while the user is actively using the app.
- If ≥60 minutes pass without a refresh call, the access token expires → API Gateway returns 401 → frontend redirects to login.
- Refresh token TTL is set to 30 days (allows re-authentication with a single click rather than re-entering email if the tab is re-opened).

---

## 3. Frontend Hosting: CloudFront + S3 (OAC)

**Decision**: Private S3 bucket with **Origin Access Control (OAC)** + CloudFront distribution + ACM certificate + Route53 alias for `coquito.gcardona.me`.

**Rationale**:
- S3 direct website hosting requires a public bucket (security risk). OAC keeps the bucket private.
- CloudFront provides HTTPS enforcement (FR-001), global CDN, SPA 404→index.html redirect, and gzip compression.
- ACM certificate is free; must be provisioned in **us-east-1** (CloudFront requirement), even if other infrastructure is in a different region.
- CloudFront free tier: 1 TB data transfer + 10M requests/month for first 12 months; subsequently ~$0.01/GB → well under $10/month at 500 MAU.

**Alternatives considered**:
- *S3 public website hosting*: No HTTPS without CloudFront, public bucket — ruled out.
- *Amplify Hosting*: Simpler but adds a managed service abstraction that is harder to control via Terraform and costs more at scale.
- *EC2 / container hosting*: Standing cost, unnecessary for a SPA.

**SPA routing**: CloudFront custom error response — HTTP 403/404 from S3 → HTTP 200 with `/index.html`.

---

## 4. API Gateway: HTTP API v2

**Decision**: Use **HTTP API (v2)** with a custom domain `api.coquito.gcardona.me` and a **Lambda authorizer** for cookie-based JWT validation.

**Rationale**:
- HTTP API is ~70% cheaper than REST API ($1/million vs. $3.50/million requests).
- HTTP API supports Lambda authorizers, which can read any request property including the `Cookie` header.
- HTTP API supports Lambda proxy integrations and custom domain names.
- No features of REST API (usage plans, caching, WAF integration) are required for v1.

**Alternatives considered**:
- *REST API (v1)*: More expensive, no additional features needed here.
- *No custom domain for API*: Uses default `*.execute-api.*.amazonaws.com` URL; breaks SameSite cookie restrictions (different domain from CloudFront). Ruled out.

---

## 5. Cognito User Pool Configuration

**Decision**: Single User Pool with two groups (`chef`, `authorized-user`), Managed Login enabled, EMAIL_OTP only, no self-registration, Essentials plan.

| Setting | Value | Rationale |
|---------|-------|-----------|
| Auth flows | `ALLOW_USER_AUTH`, `ALLOW_REFRESH_TOKEN_AUTH` | Enables choice-based + refresh |
| MFA | None required (OTP *is* the factor) | Passwordless EMAIL_OTP = OTP as primary |
| Self-registration | Disabled | FR-007: Chef provisions accounts |
| Username attributes | Email | Users sign in with email address |
| Access token TTL | 60 minutes | FR-009 |
| Refresh token TTL | 30 days | Silent re-auth while active |
| App client type | Confidential (server-side token exchange) | Allows client secret for PKCE |
| User Pool domain | `auth.coquito.gcardona.me` | Custom domain via ACM |
| Deletion protection | Enabled | Prevents accidental user loss |

**Role precedence (dual-group accounts)**: The Lambda authorizer checks for `chef` group first. If present, role = `"chef"` regardless of other groups. Otherwise checks for `authorized-user`. If neither, returns `Deny`.

---

## 6. Terraform Infrastructure Layout

**Decision**: Custom Terraform modules (no community modules). Provider: `hashicorp/aws` v6.39.0.

**Rationale**:
- Community modules add unpredictable abstractions and upgrade churn; the infra is simple enough to write directly.
- Using `hashicorp/aws` at the latest stable version (6.39.0) ensures access to latest resource types (OAC, HTTP API custom domain).
- ACM cert for CloudFront **must** use a `provider` alias in `us-east-1` when the main region differs.

**Recommended deployment region**: `us-east-1`
- Simplifies ACM: certificate and CloudFront live in the same region; no provider alias needed.
- All AWS services used (Lambda, DynamoDB, Cognito, API Gateway, S3, CloudFront) are available in us-east-1.

**Module structure:**
```
infra/terraform/
├── providers.tf          # aws provider + optional us-east-1 alias
├── terraform.tf          # required_providers lock
├── main.tf               # module composition
├── variables.tf          # domain, region, tags
├── outputs.tf            # CloudFront URL, API GW URL, Cognito IDs
├── prod.tfvars           # environment values
└── modules/
    ├── acm/              # ACM cert (us-east-1), DNS validation records
    ├── frontend/         # S3 (private), CloudFront, OAC, error responses
    ├── auth/             # Cognito User Pool, app client, domain, groups
    ├── api/              # HTTP API, Lambda authorizer, integrations, custom domain
    └── dns/              # Route53 alias A records for CF + API GW
```

---

## 7. Cost Estimate (SC-005: <$10/month at 500 MAU)

| Service | Monthly cost @ 500 MAU | Notes |
|---------|----------------------|-------|
| Cognito | $0 | ≤50,000 MAU on Lite/Essentials |
| CloudFront | ~$0.01 | Minimal traffic; free tier first 12 months |
| S3 | ~$0.02 | Static assets <1 GB |
| API Gateway HTTP API | ~$0.10 | ~100K requests/month |
| Lambda | $0 | Well within 1M free-tier requests |
| DynamoDB | $0 | Within 25 RCU/WCU/25 GB free tier |
| ACM | $0 | Free |
| Route53 | $0.50 | Existing hosted zone |
| CloudWatch Logs | $0 | <5 GB/month free tier |
| **Total** | **~$0.63** | Well under $10 target |

---

## 8. DNS Structure (coquito.gcardona.me)

| Record | Type | Target |
|--------|------|--------|
| `coquito.gcardona.me` | A (alias) | CloudFront distribution |
| `api.coquito.gcardona.me` | A (alias) | API Gateway custom domain |
| `auth.coquito.gcardona.me` | CNAME | Cognito User Pool domain |
| `_acme-challenge.*` | CNAME | ACM DNS validation records |

---

## Actual Cost Baseline (T060 — verified 2026-04-05)

**Scenario**: 500 MAU, ~50 API calls/user/month = 25,000 Lambda invocations/month.

| Service | Usage @ 500 MAU | Free Tier | Monthly Cost |
|---------|----------------|-----------|--------------|
| Cognito | 500 MAU | 50,000 MAU free | $0.00 |
| Lambda | 25,000 invocations, ~160 GB-s | 1M req + 400K GB-s free | $0.00 |
| API Gateway HTTP | 25,000 calls | 1M calls/month (12 mo) | $0.00 |
| CloudFront | ~25,000 requests, <1 GB transfer | 1 TB + 10M req free | $0.00 |
| S3 | <10 MB stored, minimal GET | 5 GB + 20K GET free | $0.00 |
| Route53 | 1 hosted zone, low queries | — | $0.50 |
| ACM | 1 certificate, 3 domains | Free (AWS-issued) | $0.00 |
| DynamoDB | Existing tables, low traffic | 25 RCU/WCU + 25 GB free | $0.00 |
| **Total** | | | **~$0.50/month** |

**Verdict**: Well within SC-005 (<$10/month at 500 MAU). After all free-tier windows close, projected cost is ~$1–2/month at 500 MAU.

---

## Open Questions Resolved

| Was Unknown | Resolution |
|-------------|-----------|
| Passwordless mechanism | Cognito EMAIL_OTP via ALLOW_USER_AUTH |
| Token storage | httpOnly cookies set by token-exchange Lambda |
| API auth for cookies | Lambda authorizer reads Cookie header, validates JWT |
| ACM region constraint | Deploy everything in us-east-1; no provider alias needed |
| Session expiry mechanism | 60-min access token TTL; frontend refresh only when active |
| Custom domain for Cognito | `auth.coquito.gcardona.me` via Cognito domain + ACM |
