# Implementation Plan: AWS Deployment with Role-Based Authentication

**Branch**: `002-aws-deploy-auth` | **Date**: 2026-04-04 | **Spec**: `specs/002-aws-deploy-auth/spec.md`  
**Input**: Feature specification from `/specs/002-aws-deploy-auth/spec.md`

---

## Summary

Deploy the Coquito Please application to AWS using Terraform, with:
- **Frontend**: Private S3 bucket + CloudFront distribution + custom domain `coquito.gcardona.me`
- **Backend**: HTTP API Gateway v2 + existing Lambda handlers + custom domain `api.coquito.gcardona.me`
- **Auth**: Cognito User Pool with EMAIL_OTP passwordless login, `chef`/`authorized-user` groups, tokens stored in `httpOnly` cookies enforced by a Lambda authorizer
- **Data**: Existing DynamoDB tables unchanged
- **DNS**: Existing Route53 hosted zone for `coquito.gcardona.me`

All infrastructure managed by Terraform (hashicorp/aws v6.39.0). Deployment region: us-east-1.

---

## Spec Conflict: FR-003 — Password vs. Passwordless

> **ACTION REQUIRED before implementation**: FR-003 currently reads "email address and password combination." The user input and all design decisions in this plan use **Cognito EMAIL_OTP passwordless authentication**. FR-003 must be updated to: "Users MUST be able to log in using an email address with a one-time password (OTP) delivered via email via Amazon Cognito User Pools (EMAIL_OTP choice-based authentication)."
>
> This plan proceeds with the passwordless approach.

---

## Technical Context

**Language/Version**: Python 3.12 (backend Lambda), TypeScript 5.x (frontend)  
**Primary Dependencies**: boto3, AWS Lambda Powertools (backend); Vite 5.x, pnpm 9.x, Prettier 3.x (frontend); Terraform hashicorp/aws v6.39.0 (infra)  
**Storage**: DynamoDB (existing tables, unchanged); Cognito User Pool (new, user identity)  
**Testing**: pytest + coverage ≥80% (backend); Vitest (frontend); contract tests for all new auth endpoints  
**Target Platform**: AWS us-east-1 (Lambda, API Gateway HTTP API, CloudFront, S3, Cognito, DynamoDB, Route53)  
**Project Type**: Web application (SPA frontend + serverless backend)  
**Performance Goals**: API p95 < 200ms (Constitution IV); frontend TTI < 3s on median mobile (SC-001)  
**Constraints**: httpOnly Secure SameSite=Strict cookies only (FR-012); no self-registration (FR-007); 60-min inactivity timeout (FR-009); <$10/month at 500 MAU (SC-005)  
**Scale/Scope**: ≤500 MAU, well within free-tier limits for all services

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

### I. Code Quality ✅

- Each new Lambda function (`token-exchange`, `logout`, `authorizer`) has a single, clearly stated responsibility.
- No duplication: JWT validation logic lives exclusively in the authorizer; cookie-setting logic exclusively in the token-exchange Lambda.
- All functions will pass linting (ruff, mypy for Python; ESLint/tsc for TypeScript) with zero warnings.
- Inline documentation required for the authorizer's role-precedence logic (non-obvious).

### II. Testing Standards ✅

- Tests written before implementation code (Red-Green-Refactor).
- Integration tests for all auth user stories (US1–US3): login flow, role enforcement, session expiry, unauthorized access.
- Unit coverage ≥80% for all new source modules (backend already enforced via `pyproject.toml fail_under=80`).
- Contract tests for every new API endpoint defined in `contracts/auth-api.md`.
- Tests are deterministic: Cognito interactions mocked with `moto` + `pytest-mock`; JWT fixtures use a test RSA key pair.

### III. User Experience Consistency ✅

- Auth error messages follow the spec's error code conventions (`INVALID_CODE`, `REFRESH_EXPIRED`, etc.) — actionable, not generic.
- Login, logout, and session-expiry flows redirect to consistent pages without silent failures.
- Cognito Managed Login UI is used for the OTP flow; no custom auth UI in v1 (reduces inconsistency risk).
- WCAG 2.1 AA: Cognito Managed Login is managed by AWS and meets accessibility requirements. New frontend components (login redirect button, session-expired banner) will pass automated a11y checks.

### IV. Performance Requirements ✅

- Lambda authorizer caches JWKS for 15 minutes and the API Gateway caches authorizer results for 5 minutes → effectively zero added latency for warm requests.
- CloudFront serves all static assets from edge caches → TTI < 3s on median mobile.
- DynamoDB unchanged; no performance regression.
- New auth Lambdas are lightweight (no DB calls in authorizer); p95 < 200ms is achievable.

### Quality Gates (pre-merge checklist)

- [ ] All automated tests pass (unit, integration, contract)
- [ ] Coverage ≥80% for all new modules
- [ ] Linter + static analysis zero warnings
- [ ] Automated accessibility check passes for any UI changes
- [ ] Performance benchmarks show no regression
- [ ] Peer code review with ≥1 approval
- [ ] Constitution Check confirmed (this document)

---

## Project Structure

### Documentation (this feature)

```text
specs/002-aws-deploy-auth/
├── plan.md              # This file
├── research.md          # Phase 0: auth, cookies, CloudFront, Terraform decisions
├── data-model.md        # Phase 1: Cognito entities, token lifecycle, DynamoDB (unchanged)
├── quickstart.md        # Phase 1: deployment and seeding guide
├── contracts/
│   ├── auth-api.md      # Phase 1: auth + protected endpoint contracts
│   └── terraform-outputs.md  # Phase 1: inter-module output contracts
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
infra/
└── terraform/
    ├── providers.tf          # hashicorp/aws ~> 6.39, region = us-east-1
    ├── terraform.tf          # required_providers version lock
    ├── main.tf               # Module composition
    ├── variables.tf          # domain, region, hosted_zone_id, tags
    ├── outputs.tf            # frontend_url, api_url, cognito IDs, CF distribution ID
    ├── prod.tfvars           # Production values (non-secret)
    ├── prod.tfvars.example   # Template for first-time setup
    └── modules/
        ├── acm/              # aws_acm_certificate + DNS validation records
        ├── frontend/         # aws_s3_bucket (private), OAC, CloudFront distribution
        ├── auth/             # Cognito User Pool, app client, domain, groups
        ├── api/              # HTTP API v2, Lambda authorizer, integrations, custom domain
        └── dns/              # Route53 A alias records (CloudFront + API GW)

backend/
└── src/
    ├── handlers/
    │   ├── auth/
    │   │   ├── token_exchange.py   # POST /auth/callback — exchanges code, sets cookies
    │   │   ├── logout.py           # POST /auth/logout — clears cookies, revokes refresh token
    │   │   └── authorizer.py       # Lambda authorizer — validates JWT from cookie
    │   └── [existing handlers — updated to read role from authorizer context]
    └── services/
        └── cognito.py              # Cognito token endpoint client (used by token_exchange)

backend/
└── tests/
    ├── contract/
    │   ├── test_auth_callback.py
    │   ├── test_auth_logout.py
    │   └── test_auth_refresh.py
    ├── integration/
    │   ├── test_chef_login_and_access.py
    │   ├── test_authorized_user_login_and_access.py
    │   └── test_site_accessible.py
    └── unit/
        ├── test_authorizer.py
        ├── test_token_exchange.py
        └── test_logout.py

frontend/
└── src/
    └── services/
        └── auth.ts              # Cognito Managed Login redirect, refresh, logout helpers
```

**Structure Decision**: Web application layout (Option 2) extended with a new `infra/terraform/` top-level directory. The existing `backend/` and `frontend/` directories are preserved and extended, not restructured.

---

## Architecture Diagram

```
Browser
  │  HTTPS GET coquito.gcardona.me
  ▼
Route53 ──alias──► CloudFront ──OAC──► S3 (private bucket)
                      │                  [index.html, JS, CSS]
                      │ 403/404 → index.html (SPA routing)

Browser
  │  HTTPS GET/POST api.coquito.gcardona.me
  ▼
Route53 ──alias──► API Gateway HTTP API v2
                      │
              [Lambda Authorizer]
              reads Cookie: id_token=<jwt>
              validates against Cognito JWKS
              returns { isAuthorized, context: {userId, role} }
                      │
              [Lambda Integrations]
              token_exchange, logout, refresh (public)
              existing handlers (protected, role-checked)
                      │
              DynamoDB (existing tables, unchanged)

Browser
  │  HTTPS → auth.coquito.gcardona.me (Cognito Managed Login)
  ▼
Cognito User Pool
  EMAIL_OTP passwordless
  Groups: chef, authorized-user
  App client → redirects to /auth/callback with code
```

---

## Complexity Tracking

> No Constitution violations. No complexity justification required.

---

## Implementation Phases (for `/speckit.tasks` to expand)

The following phases will be translated into ordered tasks by `/speckit.tasks`:

### Phase A — Terraform Foundation
1. Initialize Terraform project: `providers.tf`, `terraform.tf`, `variables.tf`, `outputs.tf`
2. `modules/acm`: ACM certificate with Route53 DNS validation
3. `modules/frontend`: S3 bucket (private, versioning, OAC) + CloudFront distribution (HTTPS-only, SPA error pages, custom domain)
4. `modules/dns`: Route53 alias for `coquito.gcardona.me` → CloudFront
5. Smoke test: deploy static placeholder page, verify HTTPS loads at `coquito.gcardona.me`

### Phase B — Auth Infrastructure
6. `modules/auth`: Cognito User Pool (EMAIL_OTP, no self-registration, Managed Login, custom domain `auth.coquito.gcardona.me`)
7. Cognito app client + groups (`chef`, `authorized-user`)
8. `modules/api`: HTTP API v2 with custom domain `api.coquito.gcardona.me`
9. `modules/dns`: Route53 alias for `api.coquito.gcardona.me` → API GW

### Phase C — Auth Lambda Functions (test-first)
10. Unit tests for `authorizer.py` (JWT validation, role precedence, missing/expired cookie)
11. Implement `authorizer.py` (reads cookie, validates JWT against Cognito JWKS, returns policy + context)
12. Unit tests for `token_exchange.py` (code exchange, cookie setting, error cases)
13. Implement `token_exchange.py` (calls Cognito `/oauth2/token`, sets httpOnly cookies, redirects)
14. Unit tests for `logout.py` (cookie clearing, refresh token revocation)
15. Implement `logout.py`
16. Unit tests for `cognito.py` service
17. Wire auth Lambdas into API Gateway routes (`/auth/callback`, `/auth/logout`, `/auth/refresh`) — public routes, no authorizer
18. Wire Lambda authorizer to all protected routes

### Phase D — Existing Handler Updates (test-first)
19. Integration tests: Chef login → Chef-only endpoints succeed
20. Integration tests: Authorized user login → protected endpoints succeed; Chef-only endpoints return 403
21. Integration tests: No session → all protected endpoints return 401
22. Update existing handlers to read `event['requestContext']['authorizer']['lambda']['role']` for role enforcement
23. Add CloudWatch structured logging (Lambda Powertools, WARN for auth failures) to all handlers

### Phase E — Frontend Auth Integration
24. Implement `auth.ts` service (Managed Login redirect, session check, refresh, logout)
25. Add session-expiry handling (401 → redirect to login)
26. Add "unauthorized" (403) error display

### Phase F — Validation & Hardening
27. Contract tests for all auth endpoints (auth-api.md)
28. End-to-end acceptance scenario validation (US1–US3 acceptance criteria)
29. Verify SC-005: cost estimate confirmed <$10/month
30. Verify SC-007: auth failure logs appear in CloudWatch within 60 seconds
