# Implementation Plan: Chef Variety Management

**Branch**: `005-variety-management` | **Date**: 2026-05-09 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/005-variety-management/spec.md`

## Summary

Adds a chef-only Variety Management page that lets chefs list all varieties (active + inactive), edit top-level variety properties, manage ingredients within each variety, and create new varieties. Three new Lambda handlers enforce the chef role and expose a `/api/v1/chef/varieties` namespace. The frontend adds a `#/varieties` route following the same hash-based SPA pattern as the existing batch management page.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x (frontend), HCL Terraform (infra)  
**Primary Dependencies**: boto3, AWS Lambda Powertools (backend); Vite 5.x, pnpm 9.x (frontend); hashicorp/aws ~> 6.39 (infra)  
**Storage**: DynamoDB — `coquito-varieties-{environment}` (read + write, existing table, schema unchanged)  
**Testing**: pytest (backend — unit/integration/contract); Vitest (frontend unit); Cypress (E2E)  
**Target Platform**: AWS Lambda arm64 (backend), browser SPA (frontend)  
**Performance Goals**: Chef variety list response ≤ 200 ms p95; page Time-to-Interactive ≤ 3 s  
**Constraints**: Chef role enforced at handler level via existing `require_chef(_auth.py)`; last-write-wins (no optimistic locking); DynamoDB table schema is unchanged  
**Scale/Scope**: Small internal tool — handful of chefs, O(10) varieties; full table scan of varieties table is acceptable

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status | Notes |
|-----------|------|--------|-------|
| I. Code Quality | Each handler has a single responsibility; no copy-paste; zero linter warnings | ✅ PASS | Three separate handler files; `require_chef` reused from `_auth.py`; no duplication |
| I. Code Quality | All public APIs and non-obvious logic documented | ✅ PASS | Docstrings on every handler function per project convention |
| II. Testing Standards | Tests written before implementation (TDD) | ✅ PASS | Tasks file will order tests before implementation for each story |
| II. Testing Standards | ≥ 1 integration test per user story exercising the full path | ✅ PASS | `tests/integration/test_variety_management.py` covers all four stories |
| II. Testing Standards | Contract tests for every new API endpoint before it ships | ✅ PASS | `tests/contract/test_chef_varieties.py` covers all three endpoints |
| II. Testing Standards | Unit coverage ≥ 80% for modified modules | ✅ PASS | New handler modules must meet threshold |
| III. UX Consistency | Error messages are actionable (state what, why, what to do) | ✅ PASS | Backend returns `{code, message, field}` on 400; frontend shows inline errors |
| III. UX Consistency | WCAG 2.1 AA — labels, roles, aria attributes on all interactive elements | ✅ PASS | Follows batch-management page conventions with `aria-required`, `role`, `aria-label` |
| III. UX Consistency | Interactive elements behave identically to equivalent contexts | ✅ PASS | Reuses same `el()` helper, `btn btn--primary/secondary` classes, `data-testid` convention |
| IV. Performance | API endpoints ≤ 200 ms p95 | ✅ PASS | DynamoDB scan on small varieties table; ingredient data embedded (no joins) |
| IV. Performance | Page TTI ≤ 3 s | ✅ PASS | Code-split via dynamic import (same as batch management) |

**No violations.** Complexity Tracking section not required.

## Project Structure

### Documentation (this feature)

```text
specs/005-variety-management/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── chef-varieties-api.md
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code

```text
backend/
├── src/
│   ├── handlers/
│   │   ├── _auth.py                    # existing — reused, not modified
│   │   ├── chef_list_varieties.py      # NEW — GET /api/v1/chef/varieties
│   │   ├── chef_create_variety.py      # NEW — POST /api/v1/chef/varieties
│   │   └── chef_update_variety.py      # NEW — PUT /api/v1/chef/varieties/{id}
│   └── models/
│       └── variety.py                  # existing — reused, not modified
└── tests/
    ├── contract/
    │   └── test_chef_varieties.py      # NEW — contract tests for all 3 endpoints
    ├── integration/
    │   └── test_variety_management.py  # NEW — integration tests, one per user story
    └── unit/handlers/
        ├── test_chef_list_varieties.py # NEW
        ├── test_chef_create_variety.py # NEW
        └── test_chef_update_variety.py # NEW

frontend/
├── src/
│   ├── main.ts                         # existing — add #/varieties route
│   ├── pages/
│   │   └── variety-management/
│   │       ├── index.ts                # NEW — mountVarietyManagement()
│   │       └── variety-management.css  # NEW
│   ├── services/
│   │   └── api.ts                      # existing — add chef variety types + endpoints
│   └── tests/pages/
│       └── variety-management.test.ts  # NEW — unit tests for page logic

infra/terraform/modules/api/
└── main.tf                             # existing — add 3 Lambda functions, integrations,
                                        #            routes, and log groups
```

**Structure Decision**: Follows the existing Option 2 web-application layout exactly. All new backend handlers go in `src/handlers/` with the `chef_` prefix to distinguish chef-only operations. Frontend page in `src/pages/variety-management/` mirrors `src/pages/batch-management/`.
