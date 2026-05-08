# Tasks: Chef Batch Management

**Input**: Design documents from `/specs/004-chef-batch-management/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.
**Testing approach**: Test-first (Red-Green-Refactor) per constitution — test tasks precede implementation tasks in every phase.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other [P] tasks in the same phase (different files, no shared dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths included in all task descriptions

---

## Phase 1: Setup (Shared Prerequisites)

**Purpose**: Shared code used across multiple user stories: the `require_chef` authorization helper (used by all 5 chef-only handlers), the `Batch.name_exists` model extension (US2 + US3), and the `GET /api/v1/me` endpoint (prerequisite for frontend role detection in US1).

- [X] T001 Write unit tests (RED) for `Batch.name_exists` classmethod in `backend/tests/unit/test_batch_model.py` — cover: match (case-insensitive), no match, exclude-self case
- [X] T002 Extend `backend/src/models/batch.py` with `name_exists(batch_name, exclude_batch_id=None)` classmethod — use existing `scan_table` helper from `backend/src/services/dynamodb.py`, return True if a different batch has the same name (case-insensitive)
- [X] T003 [P] Create `backend/src/handlers/_auth.py` with a `require_chef(event)` function — reads `role` from `event["requestContext"]["authorizer"]["lambda"]["role"]`; returns a `{"statusCode": 403, "body": json.dumps({"code": "CHEF_ROLE_REQUIRED", "message": "..."})}` dict when role is not "chef", or None when authorized; all 5 chef-only handlers import and call this before any business logic
- [X] T004 [P] Write contract test (RED) for `GET /api/v1/me` in `backend/tests/contract/test_get_me.py` — verify 200 shape `{userId, role, email}`, 401 when unauthenticated
- [X] T005 [P] Write unit tests (RED) for `get_me` handler in `backend/tests/unit/handlers/test_get_me.py` — cover: chef role, authorized-user role, missing authorizer context
- [X] T006 Implement `backend/src/handlers/get_me.py` — call `_auth.require_chef` is NOT used here (this endpoint serves any authenticated role); read `userId`, `role`, `email` from `event["requestContext"]["authorizer"]["lambda"]`; return 200 with those fields; no DynamoDB access
- [X] T007 Add `get_me` Lambda function (`coquito-get-me`), permission, integration, `GET /api/v1/me` route (CUSTOM authorizer), and `/aws/lambda/coquito-get-me` CloudWatch log group in `infra/terraform/modules/api/main.tf`

**Checkpoint**: `GET /api/v1/me` deployed. `require_chef` helper tested. `Batch.name_exists` tested. All Phase 2 and Phase 3 work can begin.

---

## Phase 2: Foundational (Auto-Close Background Worker)

**Purpose**: EventBridge-triggered Lambda that auto-transitions OPEN batches to CLOSED when their cutoff date passes. Runs nightly at 00:05 UTC.

- [X] T008 Write unit tests (RED) for `close_expired_batches` in `backend/tests/unit/handlers/test_close_expired_batches.py` — cover: one expired batch transitions to CLOSED, non-expired batch unchanged, already-CLOSED batch unchanged, empty batches table
- [X] T009 Implement `backend/src/handlers/close_expired_batches.py` — use `scan_table` to fetch all OPEN batches; compare `cutoffDate` to today; call `update_item` for each expired batch to set status CLOSED; log each transition via Lambda Powertools Logger; no `_auth` check (invoked by EventBridge, not API Gateway)
- [X] T010 Add `close_expired_batches` Lambda function (`coquito-close-expired-batches`), IAM role permission for EventBridge Scheduler to invoke it, EventBridge Scheduler schedule (cron `cron(5 0 * * ? *)` UTC), and `/aws/lambda/coquito-close-expired-batches` CloudWatch log group in `infra/terraform/modules/api/main.tf`

**Checkpoint**: Auto-close Lambda runs nightly. OPEN batches past their cutoff date transition to CLOSED automatically.

---

## Phase 3: User Story 1 — View All Batches (Priority: P1) 🎯 MVP

**Goal**: Chef navigates to the batch management page and sees all batches in a scannable list with name, status badge, cutoff date, variety count, and active request count.

**Independent Test**: A chef can open `#/batches`, see all existing batches listed with correct status badges and counts, and be redirected with an access-denied message when accessing as a non-chef — without any create or edit functionality needing to exist.

### Tests for User Story 1

- [X] T011 [P] [US1] Write contract test (RED) for `GET /api/v1/batches` in `backend/tests/contract/test_list_batches.py` — verify 200 response shape `{batches: [{batchId, batchName, cutoffDate, maxBottleVolumeMl, status, availableVarietyIds, activeRequestCount, createdAt}]}`, 403 for non-chef
- [X] T012 [P] [US1] Write unit tests (RED) for `list_batches` handler in `backend/tests/unit/handlers/test_list_batches.py` — cover: multiple batches returned sorted by `createdAt` desc, `activeRequestCount` counts only non-CANCELLED requests, empty table returns empty list, non-chef gets 403
- [X] T013 [P] [US1] Write frontend unit tests (RED) for batch list rendering in `frontend/src/tests/pages/batch-management.test.ts` — cover: list renders with status badges, empty state shows create prompt, non-chef nav item absent, chef nav item present

### Implementation for User Story 1

- [X] T014 [US1] Implement `backend/src/handlers/list_batches.py` — call `_auth.require_chef(event)` and return early if non-nil; use `scan_table` on batches table; use `scan_table` on requests table to count non-CANCELLED requests grouped by `batchId`; return all batches sorted by `createdAt` descending with `activeRequestCount` per batch
- [X] T015 [US1] Add `list_batches` Lambda function (`coquito-list-batches`), permission, integration, `GET /api/v1/batches` route (CUSTOM authorizer), and `/aws/lambda/coquito-list-batches` CloudWatch log group in `infra/terraform/modules/api/main.tf`
- [X] T016 [US1] Add `BatchSummary` interface and `listBatches()` function to `frontend/src/services/api.ts` — `BatchSummary` includes `batchId`, `batchName`, `cutoffDate`, `maxBottleVolumeMl`, `status: 'OPEN' | 'CLOSED' | 'COMPLETED'`, `availableVarietyIds`, `activeRequestCount`, `createdAt`
- [X] T017 [P] [US1] Create `frontend/src/pages/batch-management/batch-management.css` — styles for batch list container, batch row, status badge (distinct colors per status using existing design tokens), empty state, access-denied message; all interactive elements must meet `--touch-target-min: 44px`
- [X] T018 [US1] Create `frontend/src/pages/batch-management/index.ts` with `mountBatchManagement(container)` — renders loading state; calls `listBatches()`; on success renders batch list with status badges, cutoff date, variety count, active request count, and empty state when no batches; on error renders actionable error message
- [X] T019 [US1] Add `#/batches` route and `renderBatchManagement()` function to `frontend/src/main.ts` — follow existing pattern from `renderCookView`
- [X] T020 [US1] Call `GET /api/v1/me` on startup in `frontend/src/main.ts` inside `handleAuthCallback().then(...)`, cache result in a module-level `currentUser` variable, and inject a "Manage Batches" nav link pointing to `#/batches` only when `currentUser?.role === 'chef'`; if the `/me` call fails, skip the nav item silently and continue
- [X] T021 [US1] Add baseline WCAG 2.1 AA accessibility attributes to all US1 components in `frontend/src/pages/batch-management/index.ts` — `role="list"` and `role="listitem"` on batch list, `aria-label` on status badges, `aria-live="polite"` on the loading/empty state region; verify all text meets AA contrast ratio against existing design tokens
- [X] T022 [US1] Write US1 standalone integration test in `backend/tests/integration/test_batch_management.py` — with seed batches in DynamoDB, a chef authenticates, calls `GET /api/v1/batches`, and receives the correct batch list with `activeRequestCount` values; verify non-chef receives 403

**Checkpoint**: Chef sees all batches with status, cutoff date, and request counts. Non-chef has no nav item and receives access-denied on direct URL. Empty state guides new users to create a batch. US1 is independently testable and deployable.

---

## Phase 4: User Story 2 — Create a New Batch (Priority: P2)

**Goal**: Chef fills out a form to create a batch; the system validates all inputs, enforces name uniqueness, and the new batch appears in the list immediately with OPEN status.

**Independent Test**: A chef can open the new-batch form, fill in a valid name, future cutoff date, positive volume, and at least one active variety; save; and immediately see the new batch in the list with OPEN status and all correct properties.

### Tests for User Story 2

- [X] T023 [US2] Write contract test (RED) for `POST /api/v1/batches` in `backend/tests/contract/test_create_batch.py` — verify 201 response shape, 400 for `BATCH_NAME_CONFLICT`, 400 for `CUTOFF_DATE_IN_PAST`, 400 for `VARIETY_NOT_ACTIVE`, 400 for missing fields, 403 for non-chef
- [X] T024 [P] [US2] Write unit tests (RED) for `create_batch` handler in `backend/tests/unit/handlers/test_create_batch.py` — cover: valid create assigns UUID + OPEN status + createdAt timestamp, duplicate name rejected, past date rejected, inactive variety rejected, empty variety list rejected, negative volume rejected

### Implementation for User Story 2

- [X] T025 [US2] Implement `backend/src/handlers/create_batch.py` — call `_auth.require_chef(event)` and return early if non-nil; validate `batchName` (non-empty, unique via `Batch.name_exists`), `cutoffDate` (valid YYYY-MM-DD, ≥ today), `maxBottleVolumeMl` (positive integer), `availableVarietyIds` (non-empty, each must be an active variety); generate `batchId` (UUID v4), set `status = OPEN`, set `createdAt` (ISO 8601), write via `put_item`; return 201 with full batch object
- [X] T026 [US2] Add `create_batch` Lambda function (`coquito-create-batch`), permission, integration, `POST /api/v1/batches` route (CUSTOM authorizer), and `/aws/lambda/coquito-create-batch` CloudWatch log group in `infra/terraform/modules/api/main.tf`
- [X] T027 [US2] Add `CreateBatchPayload` interface and `createBatch(payload)` function to `frontend/src/services/api.ts`
- [X] T028 [US2] Fetch active varieties on form open by calling `listVarieties()` (no batchId arg) and display as a checkbox list inside the create form in `frontend/src/pages/batch-management/index.ts`
- [X] T029 [US2] Implement the batch creation form in `frontend/src/pages/batch-management/index.ts` — fields: batch name (text), cutoff date (date input), max bottle volume in ml (number), variety checkboxes; include a "Create Batch" button; form is shown when chef clicks a "New Batch" button on the list view
- [X] T030 [US2] Wire create form submission in `frontend/src/pages/batch-management/index.ts` — call `createBatch()`; on success, add new batch to the displayed list and close the form; on error, display field-specific messages for `BATCH_NAME_CONFLICT`, `CUTOFF_DATE_IN_PAST`, `VARIETY_NOT_ACTIVE`, and `VALIDATION_ERROR` without clearing the form
- [X] T031 [US2] Extend `frontend/src/tests/pages/batch-management.test.ts` with US2 tests — create form validation (missing fields, past date, duplicate name, inactive variety), successful create adds batch to list, error messages are field-specific
- [X] T032 [US2] Add baseline WCAG 2.1 AA accessibility attributes to all US2 create form components in `frontend/src/pages/batch-management/index.ts` — `aria-required="true"` on required inputs, `aria-describedby` linking each input to its error message element, `aria-invalid="true"` when validation fails, `role="group"` on the variety checkboxes fieldset
- [X] T033 [US2] Write US2 standalone integration test in `backend/tests/integration/test_batch_management.py` — a chef authenticates, calls `POST /api/v1/batches` with valid payload, and the new batch is returned with OPEN status and correct fields; verify duplicate name returns 400 `BATCH_NAME_CONFLICT`; verify non-chef returns 403

**Checkpoint**: Chef can create a new batch and see it appear in the list immediately with OPEN status. All invalid inputs surface specific, actionable messages. US2 is independently testable and deployable.

---

## Phase 5: User Story 3 — Edit an Existing Batch (Priority: P3)

**Goal**: Chef edits OPEN or CLOSED batch properties; transitions OPEN→CLOSED with a confirmation dialog showing active request count; transitions CLOSED→COMPLETED without a dialog; COMPLETED batches are read-only; removing a variety with confirmed requests is blocked.

**Independent Test**: A chef can click an OPEN batch, edit its name and cutoff date, save, and see updated values in both the detail view and the list — without status transition controls needing to work yet.

### Tests for User Story 3

- [X] T034 [US3] Write contract test (RED) for `PUT /api/v1/batches/{id}` in `backend/tests/contract/test_update_batch.py` — verify 200 updated batch, 404 for unknown batch, 409 for COMPLETED batch, 400 for duplicate name, 400 for invalid inputs, 400 `VARIETY_HAS_REQUESTS` when removing a variety with confirmed requests, 403 for non-chef
- [X] T035 [P] [US3] Write contract test (RED) for `PUT /api/v1/batches/{id}/status` in `backend/tests/contract/test_update_batch_status.py` — verify OPEN→CLOSED 200, CLOSED→COMPLETED 200, invalid transitions 400 `INVALID_STATUS_TRANSITION`, 404, 403
- [X] T036 [P] [US3] Write unit tests (RED) for `update_batch` handler in `backend/tests/unit/handlers/test_update_batch.py` — cover: partial update (only provided fields change), COMPLETED batch rejected with 409, name uniqueness excluding self, missing batch returns 404, removing variety with confirmed requests returns 400 `VARIETY_HAS_REQUESTS`
- [X] T037 [P] [US3] Write unit tests (RED) for `update_batch_status` handler in `backend/tests/unit/handlers/test_update_batch_status.py` — cover: OPEN→CLOSED succeeds, CLOSED→COMPLETED succeeds, COMPLETED→any fails, OPEN→COMPLETED fails, CLOSED→OPEN fails

### Implementation for User Story 3

- [X] T038 [US3] Implement `backend/src/handlers/update_batch.py` — call `_auth.require_chef(event)` and return early if non-nil; fetch batch (404 if missing); reject COMPLETED with `409 BATCH_COMPLETED`; validate only provided fields (partial update); for `batchName` changes run `Batch.name_exists` excluding current `batchId`; for `availableVarietyIds` changes, scan requests table and block removal of any variety that has ≥1 non-CANCELLED request in this batch (return `400 VARIETY_HAS_REQUESTS` naming the blocked variety); validate remaining varieties are active; write via conditional `update_item` (condition: status ≠ COMPLETED); return 200 with full updated batch object
- [X] T039 [US3] Implement `backend/src/handlers/update_batch_status.py` — call `_auth.require_chef(event)` and return early if non-nil; fetch batch (404 if missing); validate transition is exactly `OPEN→CLOSED` or `CLOSED→COMPLETED`, reject all others with `400 INVALID_STATUS_TRANSITION`; write via conditional `update_item` (condition: current status matches expected source); return 200 with updated batch object
- [X] T040 [US3] Add `update_batch` (`coquito-update-batch`) and `update_batch_status` (`coquito-update-batch-status`) Lambda functions, permissions, integrations, `PUT /api/v1/batches/{id}` and `PUT /api/v1/batches/{id}/status` routes (CUSTOM authorizer), and CloudWatch log groups in `infra/terraform/modules/api/main.tf`
- [X] T041 [US3] Add `UpdateBatchPayload`, `UpdateBatchStatusPayload` interfaces and `updateBatch(id, payload)`, `updateBatchStatus(id, status)` functions to `frontend/src/services/api.ts`
- [X] T042 [US3] Implement batch detail/edit view in `frontend/src/pages/batch-management/index.ts` — clicking a batch row opens an edit panel with pre-filled fields (name, cutoff date, max volume, variety checkboxes); OPEN and CLOSED batches show editable fields and a save button; COMPLETED batches render all fields as read-only with a "Finalized" label and no save button
- [X] T043 [US3] Implement OPEN→CLOSED status control in `frontend/src/pages/batch-management/index.ts` — render a "Close Batch" button on OPEN batch detail; on click, show a confirmation dialog (`role="dialog"` `aria-modal="true"`) displaying the `activeRequestCount` from stored batch data; on confirm, call `updateBatchStatus(id, 'CLOSED')`; update the batch entry in list and detail view; on dismiss, do nothing
- [X] T044 [US3] Implement CLOSED→COMPLETED status control in `frontend/src/pages/batch-management/index.ts` — render a "Mark Complete" button on CLOSED batch detail; on click, immediately call `updateBatchStatus(id, 'COMPLETED')` with no dialog; update the batch entry in list and detail view to read-only; on error, surface actionable message
- [X] T045 [US3] Extend `frontend/src/tests/pages/batch-management.test.ts` with US3 tests — OPEN batch renders editable fields, COMPLETED batch renders read-only, OPEN→CLOSED shows confirmation dialog with correct request count, CLOSED→COMPLETED transitions without dialog, saved edits update the list, `VARIETY_HAS_REQUESTS` error surfaces with specific message

**Checkpoint**: All three user stories are independently functional. Chef can view, create, edit, and manage status transitions. Variety-removal guard prevents data inconsistency.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Combined flow coverage, final WCAG sweep, linting, performance spot-check, and deployment validation.

- [X] T046 Write combined integration test covering the full chef batch management flow in `backend/tests/integration/test_batch_management.py` — create batch → appears in list as OPEN → update properties → changes reflected → transition OPEN→CLOSED → transition CLOSED→COMPLETED → batch is read-only
- [X] T047 [P] Extend `backend/tests/integration/test_batch_management.py` with a test verifying `authorized-user` role receives `403 CHEF_ROLE_REQUIRED` on all five chef-only endpoints (`GET /api/v1/batches`, `POST /api/v1/batches`, `PUT /api/v1/batches/{id}`, `PUT /api/v1/batches/{id}/status`); verify `GET /api/v1/me` returns `authorized-user` role for that account
- [X] T048 [P] Final WCAG 2.1 AA sweep across all new frontend components in `frontend/src/pages/batch-management/index.ts` and `batch-management.css` — verify `aria-expanded` on any collapsible panels, focus management after dialog close, keyboard navigability of batch list rows, color-contrast of status badges; supplement per-story accessibility tasks T021 and T032
- [X] T049 [P] Run `pnpm prettier --write` on all new and modified frontend files (`frontend/src/pages/batch-management/index.ts`, `batch-management.css`, `frontend/src/services/api.ts`, `frontend/src/main.ts`, `frontend/src/tests/pages/batch-management.test.ts`) and commit any formatting changes
- [X] T050 [P] Run `uv run ruff check --fix` on all new backend handler files (`_auth.py`, `list_batches.py`, `create_batch.py`, `update_batch.py`, `update_batch_status.py`, `get_me.py`, `close_expired_batches.py`) and commit any lint fixes — added ruff>=0.4.0 to requirements-dev.txt; fixed 3 unused-import violations in update_batch.py and update_batch_status.py
- [ ] T051 Measure performance of the two critical new paths against constitution thresholds: (a) `GET /api/v1/batches` P95 latency < 200 ms under representative load; (b) `#/batches` page Time-to-Interactive ≤ 5 s on a median mobile device; document results in a brief note in `specs/004-chef-batch-management/quickstart.md`; if either threshold is exceeded, file a plan to address before merge
- [X] T052 Run full test suites (`uv run pytest --cov=src` + `pnpm test --coverage`) and confirm line coverage ≥ 80% for all new and modified modules; fix any gaps before marking done — 90% line coverage on all 8 new backend modules (80 backend + 20 frontend tests pass)
- [ ] T053 Verify all items in `specs/004-chef-batch-management/quickstart.md` manual testing checklist pass against the deployed environment

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: No dependency on Phase 1 — can run in parallel with Phase 1
- **US1 (Phase 3)**: Depends on Phase 1 complete (needs `_auth.py`, `GET /api/v1/me`, `Batch.name_exists`)
- **US2 (Phase 4)**: Depends on US1 Checkpoint (list page and `listBatches()` in api.ts must exist)
- **US3 (Phase 5)**: Backend tasks T034–T040 can start after Phases 1–2 complete (independent of US2 backend); frontend tasks T041–T045 depend on US2 frontend checkpoint (extend the list/detail view structure)
- **Polish (Phase 6)**: Depends on all user story phases complete

### User Story Dependencies

- **Phase 1 + Phase 2**: Independent — run in parallel
- **US1 (P1)**: Unblocked after Phases 1 and 2 complete
- **US2 (P2)**: Unblocked after US1 Checkpoint
- **US3 backend (T034–T040)**: Unblocked after Phases 1–2 complete (can run alongside US2)
- **US3 frontend (T041–T045)**: Unblocked after US2 Checkpoint

### Within Each User Story

1. Contract tests and unit tests written first (must FAIL before implementation)
2. Backend handler implemented (imports `_auth.require_chef`)
3. Terraform resources added
4. Frontend types and API client functions added
5. Frontend page/component implemented
6. Accessibility attributes added (per-story)
7. Standalone integration test written and passing

### Parallel Opportunities

- T003, T004, T005 (Phase 1 setup tasks) can all run in parallel
- T011, T012, T013 (US1 tests) can all run in parallel
- T023, T024 (US2 tests) can run in parallel
- T034, T035, T036, T037 (US3 tests) can all run in parallel
- T046, T047, T048, T049, T050 (Polish) can all run in parallel

---

## Parallel Examples

### Phase 1 — Three setup tasks launch together

```
T003: backend/src/handlers/_auth.py
T004: backend/tests/contract/test_get_me.py
T005: backend/tests/unit/handlers/test_get_me.py
```

### Phase 3 (US1) — Tests launch together

```
T011: backend/tests/contract/test_list_batches.py
T012: backend/tests/unit/handlers/test_list_batches.py
T013: frontend/src/tests/pages/batch-management.test.ts
```

### Phase 5 (US3) — All four test files launch together

```
T034: backend/tests/contract/test_update_batch.py
T035: backend/tests/contract/test_update_batch_status.py
T036: backend/tests/unit/handlers/test_update_batch.py
T037: backend/tests/unit/handlers/test_update_batch_status.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T007)
2. Complete Phase 2: Foundational (T008–T010)
3. Complete Phase 3: User Story 1 (T011–T022)
4. **STOP and VALIDATE**: Chef can view all batches; non-chef is blocked; auto-close runs nightly; US1 integration test passes
5. Deploy and demo if ready

### Incremental Delivery

1. Setup + Foundational → Infrastructure ready (Phases 1–2)
2. User Story 1 → Batch list live; chef nav visible → Deploy/Demo (MVP)
3. User Story 2 → Create batch in-app → Deploy/Demo
4. User Story 3 → Full edit + status management → Deploy/Demo
5. Polish → Final WCAG, coverage, perf check, integration tests → Release

---

## Notes

- `[P]` tasks touch different files with no cross-dependencies — safe to execute simultaneously
- Every test task must produce **failing** tests before the corresponding implementation task begins
- `require_chef` is defined once in `backend/src/handlers/_auth.py` and imported by all chef-only handlers — never duplicated inline
- `scan_table` already exists in `backend/src/services/dynamodb.py` — no changes to that file needed
- `activeRequestCount` is computed at list-time from a requests table scan (never stored); it is always fresh
- The frontend caches `currentUser` from `GET /api/v1/me` for the duration of the session; no re-fetch needed on navigation
- US3 backend tasks (T034–T040) can start in parallel with US2 if team capacity allows; only the frontend tasks (T041–T045) depend on US2's list/detail page structure
- Commit after each phase checkpoint to preserve independently testable increments
