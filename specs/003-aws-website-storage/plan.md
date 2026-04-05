# Implementation Plan: AWS Website Storage

**Branch**: `003-aws-website-storage` | **Date**: 2026-04-05 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/003-aws-website-storage/spec.md`

---

## Summary

Provision the DynamoDB tables and wire the storage layer into the existing Terraform infrastructure so the already-deployed Lambda handlers can read and write application data. The frontend static site and CloudFront CDN are already operational (feature 002). This feature adds: three DynamoDB tables (varieties, batches, requests) with encryption at rest and on-demand billing; asset URL resolution for variety images via the existing CloudFront distribution; environment variable wiring into all Lambda functions; and a seed data script plus human test plan to validate the baseline dataset.

No Lambda handler code changes are required — all existing implementations are preserved as-is.

---

## Technical Context

**Language/Version**: Python 3.12 (backend Lambda), TypeScript 5.x (frontend), HCL (Terraform)  
**Primary Dependencies**: boto3 (DynamoDB access), AWS Lambda Powertools (logging), hashicorp/aws ~> 6.39  
**Storage**: DynamoDB (PAY_PER_REQUEST, AWS owned key SSE), S3 (existing frontend bucket for media assets)  
**Testing**: pytest (backend unit/integration), manual human test plan (see quickstart.md)  
**Target Platform**: AWS (us-east-1), Lambda + API Gateway v2 HTTP + DynamoDB + S3 + CloudFront  
**Project Type**: Serverless web application (SPA frontend + Lambda API backend)  
**Performance Goals**: API responses < 200ms p95 (constitution), page load < 3s (SC-001), data retrieval < 1s (SC-002)  
**Constraints**: 99.5% monthly availability (SC-000), cost scales with usage (SC-003), no provisioned DynamoDB capacity  
**Scale/Scope**: Low traffic; thousands to low millions of records; on-demand billing appropriate

---

## Constitution Check

*GATE: Evaluated before implementation. All principles satisfied.*

### I. Code Quality ✅
- No new Lambda handler code is introduced. Existing handlers are unchanged.
- New Terraform module `storage` follows the established single-responsibility pattern (one module per concern).
- The seed script has one clearly stated responsibility: write baseline test data.
- No dead code, commented-out blocks, or unused variables introduced.

### II. Testing Standards ✅
- Each Lambda handler that touches DynamoDB already has an associated contract (see `contracts/api-contract.md`).
- Integration tests for all handler paths that interact with real DynamoDB tables are required per the task plan (Red-Green-Refactor enforced).
- Unit test coverage must remain at or above 80% for `backend/src/` modules.
- The seed script is covered by a smoke test in the integration test suite.

### III. User Experience Consistency ✅
- Error messages from all handlers follow the established `{ "code": "...", "message": "..." }` format — actionable per the constitution.
- No UI changes introduced by this feature.

### IV. Performance Requirements ✅
- DynamoDB on-demand with no provisioned WCU/RCU — no artificial throttling introduced.
- All Lambda functions already use Keep-Alive via the boto3 resource pattern (connection reuse).
- CloudFront CDN for static content already in place (feature 002); assets served from same distribution.
- Performance benchmarks (API response time, page load) must be run as part of CI for any future changes to data-fetching paths.

### Complexity Tracking

No constitution violations. No deviations to justify.

---

## Architecture

### What Already Exists (no changes)

| Component | Resource | Status |
|---|---|---|
| Frontend static site | S3 bucket + CloudFront OAC distribution | ✅ Existing (`modules/frontend`) |
| API Gateway | HTTP API v2 (`coquito-api-{env}`) | ✅ Existing (`modules/api`) |
| Lambda functions | 14 handlers (auth, varieties, requests, batches) | ✅ Existing (`modules/api`) |
| Lambda IAM | Role with DynamoDB `coquito-*` policy + Cognito + SSM | ✅ Existing (`modules/api`) |
| Cognito | User Pool + Managed UI | ✅ Existing (`modules/auth`) |
| ACM certificate | Wildcard cert for domain | ✅ Existing (`modules/acm`) |
| DNS | Route 53 aliases for frontend, API, auth | ✅ Existing (`modules/dns`) |

### What This Feature Adds

| Component | Resource | Module |
|---|---|---|
| DynamoDB: varieties | `coquito-varieties-{env}` | New `modules/storage` |
| DynamoDB: batches | `coquito-batches-{env}` | New `modules/storage` |
| DynamoDB: requests | `coquito-requests-{env}` | New `modules/storage` |
| Lambda env vars | `DYNAMODB_*` + `CLOUDFRONT_ASSETS_BASE_URL` | Update `modules/api` |
| Seed data script | `backend/scripts/seed_data.py` | New script |

### Key Architecture Decision: Media Assets

Media assets (variety images) are served from the **existing** frontend CloudFront distribution and S3 bucket under the `assets/` key prefix. No additional CloudFront distribution is needed. `CLOUDFRONT_ASSETS_BASE_URL` is set to `https://{domain}` and `image_key` values in DynamoDB are stored as `assets/{filename}.jpg`.

This avoids an additional CloudFront distribution (cost saving) and leverages the existing OAC-protected bucket (security consistency). See `research.md` Decision 3 for full rationale.

---

## Project Structure

### Documentation (this feature)

```text
specs/003-aws-website-storage/
├── plan.md              ← This file
├── research.md          ← Phase 0: architecture decisions
├── data-model.md        ← Phase 1: DynamoDB schema + seed data spec
├── quickstart.md        ← Phase 1: deployment guide + human test plan
├── contracts/
│   └── api-contract.md  ← Phase 1: existing API route documentation
└── tasks.md             ← Phase 2 output (/speckit.tasks — not yet created)
```

### Source Code Changes

```text
infra/terraform/
├── main.tf                          ← ADD module "storage" call; pass outputs to module "api"
├── outputs.tf                       ← ADD DynamoDB table name outputs + assets URL output
├── modules/
│   ├── storage/                     ← NEW MODULE
│   │   ├── main.tf                  ← DynamoDB tables (3x) with SSE + deletion protection
│   │   ├── variables.tf             ← environment variable
│   │   └── outputs.tf               ← table names + cloudfront_assets_base_url
│   └── api/
│       ├── main.tf                  ← ADD env vars to all Lambda functions
│       └── variables.tf             ← ADD dynamodb_* + cloudfront_assets_base_url variables

backend/
├── scripts/
│   ├── __init__.py                  ← NEW: makes scripts/ a Python package (enables test imports)
│   └── seed_data.py                 ← NEW: seeds varieties + batch for human testing
└── tests/
    ├── contract/
    │   ├── test_static_content.py   ← NEW: US1 — real HTTP GET to CloudFront URL (AWS_INTEGRATION)
    │   └── test_dynamodb_tables.py  ← NEW: US2 — real DynamoDB schema contract test (AWS_INTEGRATION)
    ├── integration/
    │   └── test_storage_integration.py ← NEW: US2/US3 — full handler→DynamoDB path without mocking (AWS_INTEGRATION)
    └── unit/
        └── test_seed_data.py        ← NEW: US3 — seed script idempotency unit test (moto)
```

---

## Detailed Implementation Specification

### New Module: `infra/terraform/modules/storage/`

#### `main.tf`

Three DynamoDB tables with identical configuration pattern:

```hcl
resource "aws_dynamodb_table" "varieties" {
  name                        = "coquito-varieties-${var.environment}"
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = "varietyId"
  deletion_protection_enabled = true

  attribute {
    name = "varietyId"
    type = "S"
  }

  server_side_encryption {
    enabled = true   # AWS owned key — no KMS charges
  }
}

resource "aws_dynamodb_table" "batches" {
  name                        = "coquito-batches-${var.environment}"
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = "batchId"
  deletion_protection_enabled = true

  attribute {
    name = "batchId"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }
}

resource "aws_dynamodb_table" "requests" {
  name                        = "coquito-requests-${var.environment}"
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = "requestId"
  deletion_protection_enabled = true

  attribute {
    name = "requestId"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }
}
```

#### `variables.tf`

```hcl
variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "domain" {
  description = "Primary domain (for CLOUDFRONT_ASSETS_BASE_URL output)"
  type        = string
}
```

#### `outputs.tf`

```hcl
output "requests_table_name" {
  value = aws_dynamodb_table.requests.name
}

output "batches_table_name" {
  value = aws_dynamodb_table.batches.name
}

output "varieties_table_name" {
  value = aws_dynamodb_table.varieties.name
}

output "cloudfront_assets_base_url" {
  description = "Base URL for CloudFront-served media assets"
  value       = "https://${var.domain}"
}
```

---

### Updated Module: `infra/terraform/modules/api/`

#### `variables.tf` — add four new variables

```hcl
variable "dynamodb_requests_table" {
  description = "DynamoDB requests table name"
  type        = string
}

variable "dynamodb_batches_table" {
  description = "DynamoDB batches table name"
  type        = string
}

variable "dynamodb_varieties_table" {
  description = "DynamoDB varieties table name"
  type        = string
}

variable "cloudfront_assets_base_url" {
  description = "CloudFront base URL for media assets (e.g., https://coquito.gcardona.me)"
  type        = string
}
```

#### `main.tf` — add env vars to all Lambda functions

Add the following to the `environment.variables` block of **every** `aws_lambda_function` resource that accesses DynamoDB (all protected handlers plus the authorizer):

```hcl
environment {
  variables = {
    ENVIRONMENT               = var.environment
    DYNAMODB_REQUESTS_TABLE   = var.dynamodb_requests_table
    DYNAMODB_BATCHES_TABLE    = var.dynamodb_batches_table
    DYNAMODB_VARIETIES_TABLE  = var.dynamodb_varieties_table
    CLOUDFRONT_ASSETS_BASE_URL = var.cloudfront_assets_base_url
  }
}
```

Auth Lambda functions (`auth_token_exchange`, `auth_logout`, `auth_refresh`) retain their existing env vars and do not require DynamoDB env vars (they do not interact with DynamoDB).

---

### Updated Root: `infra/terraform/main.tf`

Add the storage module call and wire outputs to the api module:

```hcl
module "storage" {
  source = "./modules/storage"

  environment = var.environment
  domain      = var.domain
}

# Update module "api" to pass storage outputs:
module "api" {
  source = "./modules/api"

  # ... existing vars ...
  dynamodb_requests_table    = module.storage.requests_table_name
  dynamodb_batches_table     = module.storage.batches_table_name
  dynamodb_varieties_table   = module.storage.varieties_table_name
  cloudfront_assets_base_url = module.storage.cloudfront_assets_base_url
}
```

---

### Updated Root: `infra/terraform/outputs.tf`

Add DynamoDB table name outputs (needed by seed script and quickstart):

```hcl
output "dynamodb_requests_table" {
  description = "DynamoDB requests table name"
  value       = module.storage.requests_table_name
}

output "dynamodb_batches_table" {
  description = "DynamoDB batches table name"
  value       = module.storage.batches_table_name
}

output "dynamodb_varieties_table" {
  description = "DynamoDB varieties table name"
  value       = module.storage.varieties_table_name
}

output "cloudfront_assets_base_url" {
  description = "Base URL for CloudFront-served variety images"
  value       = module.storage.cloudfront_assets_base_url
}
```

---

### New Script: `backend/scripts/seed_data.py`

Idempotent seed script — uses `put_item_if_not_exists` to avoid overwriting existing records on re-runs. Reads table names from environment variables.

See `data-model.md` for the exact seed records to write (2 varieties + 1 batch).

Usage:
```bash
DYNAMODB_VARIETIES_TABLE=coquito-varieties-prod \
DYNAMODB_BATCHES_TABLE=coquito-batches-prod \
AWS_REGION=us-east-1 \
uv run python scripts/seed_data.py
```

---

## Test Plan

See `quickstart.md` for the full 10-step human test plan.

### Integration Tests (`tests/integration/test_storage_integration.py`)

Must cover:
- `GET /api/v1/varieties` with seed data present → 200 with both varieties
- `GET /api/v1/varieties?batchId=batch-test-2026` → 200 filtered to seed batch
- `GET /api/v1/varieties?batchId=nonexistent` → 404 BATCH_NOT_FOUND
- `POST /api/v1/requests` with valid payload → 201 with requestId
- `POST /api/v1/requests` with same idempotencyKey → 201 with same requestId (idempotency)
- `GET /api/v1/requests/{id}` → 200 with persisted data
- `POST /api/v1/requests` with expired batchId → 400 BATCH_CLOSED
- `GET /health` → 200

### Unit Tests (`tests/unit/test_seed_data.py`)

- Seed script is idempotent when run twice (no ConflictError raised on second run)
- Seed script writes exactly 2 varieties and 1 batch

---

## Dependency Order

1. `modules/storage` (no dependencies) — creates DynamoDB tables
2. `modules/api` update (depends on storage outputs) — wires env vars
3. `infra/terraform/main.tf` update (depends on 1 + 2) — wires module chain
4. `infra/terraform/outputs.tf` update (depends on 1) — exposes table names
5. `backend/scripts/seed_data.py` (depends on tables existing) — run post-apply
6. Tests (depend on tables + seed data)

---

## Post-Plan Constitution Check ✅

All four constitution principles remain satisfied after Phase 1 design:

- **Code Quality**: New storage module follows single-responsibility. Existing handlers unchanged. No duplication.
- **Testing Standards**: Integration tests required for every handler path touching DynamoDB. Unit tests for seed script.
- **UX Consistency**: No user-facing changes. Error response format unchanged.
- **Performance**: On-demand DynamoDB has no artificial throttling. CloudFront CDN unchanged.
