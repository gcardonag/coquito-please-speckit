# Implementation Plan: Chef Batch Management

**Branch**: `004-chef-batch-management` | **Date**: 2026-05-07 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-chef-batch-management/spec.md`

## Summary

Add a chef-only batch management page to the existing Vite/TypeScript frontend and back it with five new Python Lambda handlers behind the existing API Gateway + Lambda authorizer. The authorizer already propagates `role` in its context; new handlers enforce `role == "chef"` at the handler level. No schema changes are required — the `coquito-batches-{environment}` DynamoDB table already holds all needed attributes. A scheduled EventBridge rule runs the auto-close Lambda nightly to transition OPEN batches whose cutoff date has passed.

## Technical Context

**Language/Version**: TypeScript 5.x (frontend), Python 3.12 (backend Lambda), HCL (Terraform)
**Primary Dependencies**: Vite 5.x, pnpm 9.x, Prettier 3.x (frontend); boto3, AWS Lambda Powertools (backend); hashicorp/aws ~> 6.39 (infra)
**Storage**: DynamoDB — `coquito-batches-{environment}` (existing, unchanged schema); `coquito-requests-{environment}` (read-only, for active-request counts); `coquito-varieties-{environment}` (read-only, for variety selection)
**Testing**: pytest + moto (backend unit/contract); Vitest (frontend)
**Target Platform**: AWS Lambda arm64 + API Gateway HTTP API v2 (backend); CloudFront SPA (frontend)
**Project Type**: Web application (SPA + serverless API)
**Performance Goals**: List page loads within 5 s; save operations visible in list within 3 s (SC-001, SC-005)
**Constraints**: Chef-only access enforced at both API Gateway (Lambda authorizer) and handler level; batch Scan acceptable at expected scale (<20 batches); single-chef, no concurrent-edit handling required
**Scale/Scope**: Single chef account; expected <20 batches total; ~5 screens

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

### I. Code Quality ✅

- Each new Lambda handler (`list_batches`, `create_batch`, `update_batch`, `update_batch_status`, `get_me`, `close_expired_batches`) has a single, clearly stated responsibility.
- Role-enforcement logic is extracted to a **shared module** at `backend/src/handlers/_auth.py` exposing a `require_chef(event)` function; all chef-only handlers import and call it rather than duplicating the guard. This satisfies the constitution's prohibition on duplicated logic.
- No dead code introduced; existing handlers are untouched.

### II. Testing Standards ✅

- Tests written before implementation (Red-Green-Refactor enforced per constitution).
- Each user story has at least one integration test exercising the full path.
- Contract tests added for all five new HTTP endpoints.
- Frontend unit tests added for the batch management page and new API client functions.
- Coverage floor of 80% must be maintained after this feature.

### III. User Experience Consistency ✅

- New page uses existing design tokens (`tokens.css`) — no new color or spacing values introduced.
- Interactive elements (batch status buttons, confirmation dialog) follow patterns already established in `cook-view` and `request-form` pages.
- Error messages follow the `{ code, message }` API contract already established.
- WCAG 2.1 AA: all new interactive elements use `aria-*` attributes, minimum 44px touch targets (`--touch-target-min`), and sufficient contrast ratios per existing token values.

### IV. Performance Requirements ✅

- `list_batches` uses DynamoDB Scan (acceptable: expected <20 batches); no user-facing latency budget breached.
- Active-request count is derived in the same Scan pass via an in-handler count of the requests table — one additional Scan acceptable at this scale.
- Auto-close Lambda runs in an isolated EventBridge-triggered worker and does not touch user-facing request paths.
- CloudWatch metrics and structured logging (Lambda Powertools) are added to all new handlers, consistent with existing observability pattern.

**Constitution violations**: None. No Complexity Tracking entry required.

## Project Structure

### Documentation (this feature)

```text
specs/004-chef-batch-management/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── api-contract.md  # Phase 1 output — new endpoints only
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── handlers/
│   │   ├── _auth.py                 # NEW — shared require_chef(event) helper
│   │   ├── list_batches.py          # NEW — GET /api/v1/batches
│   │   ├── create_batch.py          # NEW — POST /api/v1/batches
│   │   ├── update_batch.py          # NEW — PUT /api/v1/batches/{id}
│   │   ├── update_batch_status.py   # NEW — PUT /api/v1/batches/{id}/status
│   │   ├── get_me.py                # NEW — GET /api/v1/me
│   │   ├── close_expired_batches.py # NEW — EventBridge nightly trigger
│   │   └── [existing handlers unchanged]
│   ├── models/
│   │   └── batch.py                 # EXTEND — add name_exists class method
│   └── services/
│       └── dynamodb.py              # scan_table helper already present — no changes needed
└── tests/
    ├── contract/
    │   ├── test_list_batches.py     # NEW
    │   ├── test_create_batch.py     # NEW
    │   ├── test_update_batch.py     # NEW
    │   ├── test_update_batch_status.py # NEW
    │   └── test_get_me.py           # NEW
    ├── integration/
    │   └── test_batch_management.py # NEW — full chef batch management flows
    └── unit/
        └── handlers/
            ├── test_list_batches.py     # NEW
            ├── test_create_batch.py     # NEW
            ├── test_update_batch.py     # NEW
            ├── test_update_batch_status.py # NEW
            ├── test_get_me.py           # NEW
            └── test_close_expired_batches.py # NEW

frontend/
├── src/
│   ├── pages/
│   │   └── batch-management/
│   │       ├── index.ts             # NEW — page mount function
│   │       └── batch-management.css # NEW — page styles
│   ├── services/
│   │   └── api.ts                   # EXTEND — new types + 5 new functions
│   └── main.ts                      # EXTEND — add #/batches route + chef nav item
└── src/tests/
    └── pages/
        └── batch-management.test.ts  # NEW

infra/terraform/modules/api/
└── main.tf                           # EXTEND — 6 Lambda functions, routes,
                                      #          integrations, log groups,
                                      #          EventBridge rule + IAM
```

**Structure Decision**: Web application layout (Option 2). All new files follow the established handler-per-endpoint pattern for the backend and the pages/{name}/index.ts pattern for the frontend.

## Complexity Tracking

> No constitution violations — section intentionally empty.
