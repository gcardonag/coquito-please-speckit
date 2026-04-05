# Research: AWS Website Storage

**Feature**: 003-aws-website-storage  
**Date**: 2026-04-05  
**Status**: Complete — all NEEDS CLARIFICATION items resolved

---

## Decision 1: DynamoDB Billing Mode

**Decision**: PAY_PER_REQUEST (on-demand billing) for all three tables  
**Rationale**: The application is low-traffic with bursty access patterns. On-demand billing has zero idle cost — charges only occur on actual reads/writes. This directly satisfies SC-003 (cost scales with usage). Provisioned capacity would require minimum reserved throughput even with zero traffic.  
**Alternatives considered**:  
- Provisioned capacity with auto-scaling — rejected: incurs baseline cost even at idle; adds operational overhead for capacity planning.  
- DynamoDB Accelerator (DAX) — rejected: adds significant cost ($0.269/node/hr) with no benefit at this scale.

---

## Decision 2: DynamoDB Encryption at Rest

**Decision**: AWS owned key (`server_side_encryption { enabled = true }` in Terraform, which defaults to AWS owned key)  
**Rationale**: DynamoDB encrypts all user data at rest by default using AWS owned keys at no additional charge. This satisfies FR-009 (encryption at rest required) and SC-003 (no unnecessary cost). AWS owned keys provide the same data-at-rest protection as AWS managed keys for this use case.  
**Alternatives considered**:  
- AWS managed KMS key — rejected: incurs KMS charges (~$1/key/month + API call charges); no meaningful security improvement for this threat model.  
- Customer managed KMS key — rejected: adds operational burden (key rotation, access policies) with no benefit for a single-team project.

---

## Decision 3: Media Asset Storage Location

**Decision**: Assets are stored in the existing frontend S3 bucket (under an `assets/` key prefix) and served through the existing CloudFront distribution  
**Rationale**: The existing `modules/frontend` already provisions an S3 bucket with OAC and a CloudFront distribution. Media files are admin-deployed (per clarification Q1) so there is no user upload concern. Reusing the existing distribution avoids a second CloudFront distribution (~$0.0085/10K HTTP requests minimum charge) and keeps the deployment surface minimal. `CLOUDFRONT_ASSETS_BASE_URL` is set to `https://{domain}` and `image_key` values are stored with an `assets/` prefix (e.g., `assets/coquito-classic.jpg`).  
**Alternatives considered**:  
- Separate S3 bucket + second CloudFront distribution — rejected: additional monthly cost, additional Terraform module complexity, no user-visible benefit since assets are admin-managed.  
- Separate S3 bucket as second origin on existing CloudFront (path-based routing) — rejected: requires modifying the existing frontend module which has no other reason to change; the single-bucket approach is simpler and already supported.

---

## Decision 4: DynamoDB Table Naming

**Decision**: `coquito-{requests|batches|varieties}-${var.environment}` (e.g., `coquito-requests-prod`)  
**Rationale**: The existing IAM policy in `modules/api/main.tf` already grants Lambda access to `arn:aws:dynamodb:*:*:table/coquito-*`. Table names must match this prefix. Environment-suffixing follows the established project convention (all existing resources use `var.environment` suffix).  
**Alternatives considered**:  
- Single-word names (`requests`, `batches`, `varieties`) — rejected: would not match the existing `coquito-*` IAM policy wildcard.

---

## Decision 5: DynamoDB Table Access Pattern

**Decision**: Single-table-per-entity with a hash key only (no range key, no GSIs in v1)  
**Rationale**: All existing Lambda handlers access records by primary key (get_item by requestId/batchId/varietyId) or perform full scans (list_varieties). The existing `dynamodb.py` service layer uses `scan_table` for varieties (explicitly noted as acceptable at this scale) and `get_item` / `put_item` / `update_item` by PK for requests and batches. No GSI-dependent queries exist in the current codebase. Adding GSIs without a demonstrated need would add cost.  
**Alternatives considered**:  
- GSI on `requesterId` for user-scoped request listing — deferred: no handler for listing all requests by user exists yet; can be added when needed.

---

## Decision 6: Terraform Provider Version

**Decision**: hashicorp/aws ~> 6.39 (current latest: 6.39.0)  
**Rationale**: Matches the existing `terraform.tf` constraint exactly. No version change required.

---

## Decision 7: DynamoDB Deletion Protection

**Decision**: `deletion_protection_enabled = true` on all three tables  
**Rationale**: Spec clarification Q2 established that records are permanent (no user-initiated deletion, no automatic expiry). Deletion protection prevents accidental table drops via Terraform destroy and aligns with SC-004 (zero data loss). This is a zero-cost guardrail.

---

## Decision 8: Seed Data Strategy

**Decision**: Python seed script (`backend/scripts/seed_data.py`) using boto3, run manually after first deployment  
**Rationale**: A human-executable seed script is the simplest approach for a one-time baseline dataset. It produces a known, verifiable state for the test plan. Terraform `local-exec` was considered but rejected because it couples infrastructure apply to data state — if the apply is re-run, the seed logic would need idempotency guards that are easier to implement in a standalone script.  
**Seed dataset**: 2 active Variety records + 1 open Batch record referencing both varieties.

---

## Decision 9: CLOUDFRONT_ASSETS_BASE_URL Wiring

**Decision**: Pass `cloudfront_assets_base_url` from the storage module output (which returns `https://${var.domain}`) to all Lambda functions via the api module  
**Rationale**: `list_varieties.py` already reads `os.environ.get("CLOUDFRONT_ASSETS_BASE_URL", "")` and constructs image URLs. The env var is currently unset, causing image URLs to be empty strings in production. Wiring this through the module chain (storage → main → api) resolves the issue without any handler code changes.
