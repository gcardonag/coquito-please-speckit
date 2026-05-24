# Implementation Plan: Batch User Access Management

**Branch**: `006-batch-user-access` | **Date**: 2026-05-23 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/006-batch-user-access/spec.md`

## Summary

Chefs can grant and revoke access to an open batch from the batch management page. User creation and search are backed by the existing Cognito User Pool. Batch-specific access grants are stored in a new DynamoDB table (`coquito-batch-access-{env}`). Four new Lambda endpoints are added under the `GET /api/v1/chef/...` namespace. The existing `POST /api/v1/users` handler is extended to accept `firstName` and `lastName`. The Manage Access panel is rendered inline within the batch detail view on the `#/batches` page for OPEN batches.

## Technical Context

**Language/Version**: Python 3.12 (backend Lambda), TypeScript 5.x (frontend)  
**Primary Dependencies**: boto3, AWS Lambda Powertools (backend); Vite 5.x, pnpm 9.x (frontend); hashicorp/aws ~> 6.39 (infra)  
**Storage**: DynamoDB (new `coquito-batch-access-{env}` table); Cognito User Pool (user identity, existing)  
**Testing**: pytest + moto (backend unit/contract); Cypress (frontend e2e, existing config)  
**Target Platform**: AWS Lambda (arm64, Amazon Linux 2023) + API Gateway HTTP v2; CloudFront + S3 (frontend)  
**Project Type**: Web application (frontend SPA + serverless backend)  
**Performance Goals**: Search results within 1 second; access grant/revoke within 200ms p95 (constitution requirement)  
**Constraints**: <200ms p95 on API endpoints; WCAG 2.1 AA on new UI components; 80% unit test coverage floor  
**Scale/Scope**: Small user base (~10–50 users per batch); no pagination required for batch access list

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Code Quality** — single responsibility per handler, no duplication, linter clean | ✅ Pass | Each new Lambda handler has one responsibility. `require_chef()` reused; DynamoDB helpers from `services/dynamodb.py` reused. No cross-handler duplication. |
| **I. Code Quality** — dead code removed, public APIs documented | ✅ Pass | No dead code introduced. Handler docstrings follow existing convention. |
| **II. Testing Standards** — tests before implementation (TDD), integration tests for each user story | ✅ Pass | Tasks ordered: contract tests first (RED), then implementation (GREEN), then refactor. One integration test per user story. |
| **II. Testing Standards** — 80% coverage floor, deterministic tests | ✅ Pass | New modules are small and testable via moto. Coverage floor maintained. |
| **II. Testing Standards** — contract tests for every new endpoint | ✅ Pass | Five contract test files: one per new/modified endpoint. |
| **III. UX Consistency** — actionable errors, WCAG 2.1 AA, consistent interactive elements | ✅ Pass | Error messages follow existing `code + message` pattern. New UI uses existing `btn`, `el()`, `data-testid` conventions. WCAG axe check required before merge. |
| **IV. Performance** — API responses <200ms p95, Time-to-Interactive <3s | ✅ Pass | Cognito `list_users` call in search handler is the only potentially slow path; capped at 20 results to bound latency. Batch access list is a DynamoDB query (fast). |

**Post-design re-check**: All principles satisfied. No violations requiring Complexity Tracking entries.

## Project Structure

### Documentation (this feature)

```text
specs/006-batch-user-access/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── api.md           # Phase 1 output — all endpoint contracts
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code Changes

```text
backend/
├── src/
│   ├── handlers/
│   │   ├── create_user.py               # MODIFY: add firstName, lastName support
│   │   ├── chef_search_users.py         # NEW: GET /api/v1/chef/users?query=
│   │   ├── chef_list_batch_access.py    # NEW: GET /api/v1/chef/batches/{id}/access
│   │   ├── chef_grant_batch_access.py   # NEW: PUT /api/v1/chef/batches/{id}/access/{userId}
│   │   └── chef_revoke_batch_access.py  # NEW: DELETE /api/v1/chef/batches/{id}/access/{userId}
│   └── models/
│       └── batch_access.py              # NEW: BatchAccessGrant dataclass
└── tests/
    ├── contract/
    │   ├── test_create_user.py          # MODIFY: add firstName/lastName test cases
    │   ├── test_chef_search_users.py    # NEW
    │   ├── test_chef_list_batch_access.py  # NEW
    │   ├── test_chef_grant_batch_access.py # NEW
    │   └── test_chef_revoke_batch_access.py # NEW
    └── integration/
        └── test_batch_access_management.py  # NEW: end-to-end per user story

frontend/
├── src/
│   ├── services/
│   │   └── api.ts                       # MODIFY: add 5 new API functions + types
│   └── pages/
│       └── batch-management/
│           ├── index.ts                 # MODIFY: add Manage Access section to batch detail
│           └── batch-management.css     # MODIFY: add access panel styles

infra/terraform/modules/
├── storage/
│   ├── main.tf                          # MODIFY: add coquito-batch-access-{env} table
│   └── outputs.tf                       # MODIFY: export batch_access_table_name
└── api/
    ├── main.tf                          # MODIFY: 4 new Lambdas, integrations, routes, log groups; updated IAM
    └── variables.tf                     # MODIFY: add dynamodb_batch_access_table variable

infra/terraform/
└── main.tf                              # MODIFY: pass batch_access_table_name to api module
```

**Structure Decision**: Web application with separated `backend/`, `frontend/`, `infra/` directories. No new top-level directories. All changes are additive or modifications to existing files following existing file-per-handler conventions.

## Implementation Phases

### Phase A: Backend — Data Layer & New Handlers

**Step A1 — New DynamoDB table (Terraform)**

Modify `infra/terraform/modules/storage/main.tf`:
```hcl
resource "aws_dynamodb_table" "batch_access" {
  name         = "coquito-batch-access-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "batchId"
  range_key    = "userId"
  deletion_protection_enabled = true

  attribute { name = "batchId" type = "S" }
  attribute { name = "userId"  type = "S" }

  server_side_encryption { enabled = true }
}
```

Add to `outputs.tf`:
```hcl
output "batch_access_table_name" {
  value = aws_dynamodb_table.batch_access.name
}
```

**Step A2 — BatchAccessGrant model**

`backend/src/models/batch_access.py`:
```python
@dataclass
class BatchAccessGrant:
    batch_id: str
    user_id: str       # Cognito sub
    email: str
    first_name: str
    last_name: str
    granted_at: str    # ISO 8601 UTC

    def to_dict(self) -> dict: ...

    @classmethod
    def from_dict(cls, data: dict) -> "BatchAccessGrant": ...
```

**Step A3 — Modify `create_user.py`**

Accept `firstName` (required) and `lastName` (optional) in request body. Pass as Cognito `given_name` and `family_name` attributes on `admin_create_user`.

**Step A4 — `chef_search_users.py`**

`GET /api/v1/chef/users?query={q}`
1. `require_chef()` guard
2. Validate `query` query-string parameter is present and non-empty
3. Issue two sequential Cognito `list_users` calls (Limit=20 each):
   - `Filter=f'email ^= "{q}"'`
   - `Filter=f'given_name ^= "{q}"'`
4. Merge results by Cognito `sub`; deduplicate (a user matching both filters appears once); cap merged list at 20
5. Map each user: extract `sub`, `email`, `given_name`, `family_name`
6. Return `{"users": [...]}`

**Step A5 — `chef_list_batch_access.py`**

`GET /api/v1/chef/batches/{id}/access`
1. `require_chef()` guard
2. Read batch from `coquito-batches` → 404 if not found
3. Query `coquito-batch-access` where `batchId = {id}`
4. Return `{"batchId": id, "users": [...]}`

**Step A6 — `chef_grant_batch_access.py`**

`PUT /api/v1/chef/batches/{id}/access/{userId}`
1. `require_chef()` guard
2. Read batch → 404 if not found; 403 if status ≠ OPEN
3. `cognito.admin_get_user(Username=userId_or_email)` → 404 if not found; extract attributes
4. `put_item_if_not_exists` to `coquito-batch-access` → 409 if already exists
5. Return grant record

**Step A7 — `chef_revoke_batch_access.py`**

`DELETE /api/v1/chef/batches/{id}/access/{userId}`
1. `require_chef()` guard
2. Read batch → 404 if not found; 403 if status ≠ OPEN
3. GetItem from `coquito-batch-access` → 404 if access grant not found
4. DeleteItem
5. Return 204

**Step A8 — Terraform: Lambda, IAM, routes**

In `infra/terraform/modules/api/main.tf`:
- Add 4 new `aws_lambda_function` resources (pattern identical to `chef_list_varieties`)
- Add `COGNITO_USER_POOL_ID` to search and grant; `DYNAMODB_BATCH_ACCESS_TABLE` to grant, list, and revoke; `DYNAMODB_BATCHES_TABLE` to grant, list, and revoke
- Extend `lambda_cognito` IAM policy to add `cognito-idp:ListUsers` and `cognito-idp:AdminGetUser`
- Add 4 `aws_apigatewayv2_integration` + `aws_apigatewayv2_route` resources (all CUSTOM auth)
- Add 4 `aws_cloudwatch_log_group` resources (30-day retention)

---

### Phase B: Backend Tests

Write contract tests (RED → GREEN cycle per handler):

- `test_create_user.py` — add cases for firstName/lastName validation and Cognito attribute storage
- `test_chef_search_users.py` — success (multiple results), empty results, missing query param, non-chef
- `test_chef_list_batch_access.py` — success with users, empty list, batch not found, non-chef
- `test_chef_grant_batch_access.py` — success, closed batch, user not found, duplicate grant, non-chef
- `test_chef_revoke_batch_access.py` — success (204), closed batch, grant not found, non-chef

Write integration test `test_batch_access_management.py` covering:
- US1: search + grant flow
- US2: create user + auto-grant flow
- US3: view access list
- US4: revoke flow

---

### Phase C: Frontend

**Step C1 — `api.ts` additions**

Add types (`UserSummary`, `BatchAccessUser`, `BatchAccessGrant`, `CreateUserPayload`, `CreateUserResponse`) and five new functions:
```typescript
searchUsers(query: string): Promise<{ users: UserSummary[] }>
listBatchAccess(batchId: string): Promise<{ batchId: string; users: BatchAccessUser[] }>
grantBatchAccess(batchId: string, userId: string): Promise<BatchAccessGrant>
revokeBatchAccess(batchId: string, userId: string): Promise<void>
createUser(payload: CreateUserPayload): Promise<CreateUserResponse>
```

**Step C2 — Manage Access section in `batch-management/index.ts`**

Added to the batch detail panel when `batch.status === 'OPEN'`:

```
[Manage Access ▼]          ← collapsible toggle button

  Search users:   [________] [Search]
  Results list    → [Grant Access] per row
  — or —
  [+ New User]    → inline create form

  ─── Users with access ───
  Jane Doe (jane@...) [Remove]
  ...
  (empty state if none)
```

Revoke triggers a confirmation dialog (matching existing `showCloseConfirmation` dialog pattern).

**Step C3 — CSS in `batch-management.css`**

New CSS classes following existing BEM conventions:
- `.access-panel`, `.access-panel__search`, `.access-panel__results`
- `.access-user-row`, `.access-user-row__name`, `.access-user-row__email`
- `.access-empty`, `.access-dialog-overlay`, `.access-dialog`

---

## Complexity Tracking

| Deviation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| Feature placed on batch management page (`#/batches`), not variety management page (`#/varieties`) as stated in spec | Batch context (batch ID) is required to grant/revoke access. The variety management page has no batch scope — adding a batch picker there would duplicate batch-selection UI that already exists on the batch management page. | Batch picker on variety management page adds redundant state management, two-step UX, and a second entry point for batch selection that diverges from the existing single-page-per-concern pattern. |

## Assumptions

- The `userId` path parameter in grant/revoke endpoints is the Cognito `sub` (UUID), not the email address. The search and access list endpoints return `userId` as the `sub`.
- The existing Lambda IAM role (`coquito-lambda-exec-{env}`) is shared across all Lambda functions; adding `ListUsers` and `AdminGetUser` to the role policy affects all functions but is additive and non-breaking.
- The `CLOUDFRONT_ASSETS_BASE_URL` environment variable is not needed by any of the four new Lambda handlers.
- Unit test coverage for new handlers will exceed 80% given their small size and straightforward branching logic.
