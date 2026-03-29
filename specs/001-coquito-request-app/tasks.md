---
description: "Task list for Coquito Request App implementation"
---

# Tasks: Coquito Request App

**Input**: Design documents from `/specs/001-coquito-request-app/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Test tasks are included per the Testing Standards principle (II) in the
constitution. Tests MUST be written before implementation code (TDD).

**Organization**: Tasks are grouped by user story to enable independent implementation
and testing of each story.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)
- Exact file paths included in every task description

## Path Conventions

- Frontend: `frontend/` at repository root
- Backend: `backend/` at repository root
- Specs: `specs/001-coquito-request-app/`

---

## Phase 1: Setup

**Purpose**: Initialize project scaffolding and tooling for both frontend and backend.

- [ ] T001 Initialize frontend project: run `pnpm create vite@latest frontend -- --template vanilla-ts` at repo root, producing `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/index.html`
- [ ] T002 [P] Configure Prettier in `frontend/.prettierrc` (single quotes, 2-space indent, 100-char print width) and add `"format": "prettier --write \"src/**/*.{ts,html,css}\""` and `"format:check": "prettier --check \"src/**/*.{ts,html,css}\""` scripts to `frontend/package.json`
- [ ] T003 [P] Install and configure Cypress: add `cypress` as dev dependency in `frontend/package.json`, create `frontend/cypress.config.ts` (baseUrl: http://localhost:5173), add `"cypress:open"` and `"cypress:run"` scripts to `frontend/package.json`
- [ ] T004 Initialize backend project: create `backend/` directory, `backend/requirements.txt` (boto3, aws-lambda-powertools), `backend/requirements-dev.txt` (pytest, pytest-cov, moto[dynamodb,ses,scheduler], python-dotenv)
- [ ] T005 [P] Configure pytest in `backend/pyproject.toml` with `[tool.pytest.ini_options]` setting testpaths to `tests`, and `[tool.coverage.run]` source to `src`; add `"test": "pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=80"` as a documented run command in `backend/README.md`
- [ ] T006 Create frontend source directory structure: `frontend/src/pages/request-form/`, `frontend/src/pages/manage-request/`, `frontend/src/pages/cook-view/`, `frontend/src/components/form/`, `frontend/src/components/ingredient-list/`, `frontend/src/services/`, `frontend/src/styles/`, `frontend/cypress/e2e/`, `frontend/cypress/support/`, `frontend/public/images/`
- [ ] T007 Create backend source directory structure: `backend/src/handlers/`, `backend/src/models/`, `backend/src/services/`, `backend/tests/unit/handlers/`, `backend/tests/integration/`; add `__init__.py` to each `src/` package directory
- [ ] T008 [P] Create environment variable template files: `frontend/.env.example` (VITE_API_BASE_URL, VITE_BATCH_ID) and `backend/.env.example` (DYNAMODB_REQUESTS_TABLE, DYNAMODB_BATCHES_TABLE, DYNAMODB_VARIETIES_TABLE, SES_FROM_ADDRESS, COOK_SECRET, AWS_REGION)

**Checkpoint**: Both `pnpm dev` (frontend) and `pytest --collect-only` (backend) run without errors.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared infrastructure that ALL user stories depend on. No story work can
begin until this phase is complete.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T009 Create design tokens in `frontend/src/styles/tokens.css`: CSS custom properties for colors (warm cream, deep coconut brown, tropical green accent, high-contrast text), typography (mobile-first base 18px, large heading), and spacing scale
- [ ] T010 Create global CSS in `frontend/src/styles/global.css`: CSS reset, body/html base styles, mobile-first responsive grid, imports `tokens.css`, sets font-family and base line-height for readability
- [ ] T011 Implement hash-based router in `frontend/src/main.ts`: reads `window.location.hash`, renders the matching page module into `#app`, handles routes `#/` (request-form), `#/manage/:id` (manage-request), `#/cook` (cook-view), and unknown routes (404 state)
- [ ] T012 Implement typed API client in `frontend/src/services/api.ts`: typed `fetch` wrappers for all contract endpoints (createRequest, getRequest, updateRequest, cancelRequest, listVarieties, getBatchConfig, getIngredientList, markIngredientAcquired), with error response parsing that surfaces `code` and `message` to callers
- [ ] T013 Create DynamoDB service helper in `backend/src/services/dynamodb.py`: thin wrappers around boto3 `get_item`, `put_item`, `update_item`, `query`, and `delete_item` that read table names from environment variables and raise typed exceptions on not-found and conflict errors
- [ ] T014 [P] Create Request model in `backend/src/models/request.py`: Python dataclass with all fields from data-model.md, `from_dict`/`to_dict` serialization, and static `validate` method enforcing email format, required fields, and `bottleVolumeMl` ≤ `maxBottleVolumeMl` when `bottleProvided = True`
- [ ] T015 [P] Create Batch model in `backend/src/models/batch.py`: Python dataclass with all fields from data-model.md, `from_dict`/`to_dict`, and `is_cutoff_passed(today: date) -> bool` helper
- [ ] T016 [P] Create Variety model in `backend/src/models/variety.py`: Python dataclass with all fields from data-model.md including nested `Ingredient` dataclass, `from_dict`/`to_dict`, and `active` filter helper
- [ ] T017 Create SES email service in `backend/src/services/ses.py`: `send_email(to, subject, body_html, body_text)` helper using boto3 SES; reads `SES_FROM_ADDRESS` from environment; raises `EmailDeliveryError` on failure
- [ ] T018 Create EventBridge Scheduler service in `backend/src/services/scheduler.py`: `create_one_time_schedule(name, schedule_at, target_arn, input_payload) -> str` returns ARN; `delete_schedule(name)` cancels schedule; reads scheduler role ARN from environment variable

**Checkpoint**: Foundation complete — all models importable, DynamoDB/SES/Scheduler services instantiate without error in test environment (moto fixtures).

---

## Phase 3: User Story 1 - Submit a Coquito Request (Priority: P1) 🎯 MVP

**Goal**: Requesters can open the app, fill out a culturally-themed form, and receive
a confirmation with their full order summary.

**Independent Test**: Open the app at `/#/`, complete all form fields, submit,
and see a confirmation card with a summary — no other feature required.

### Tests for User Story 1 ⚠️ Write these FIRST — verify they FAIL before implementing

- [ ] T019 [P] [US1] Write Cypress E2E test for happy-path form submission in `frontend/cypress/e2e/request-form.cy.ts`: stubs batch config and varieties API calls, fills all form fields, submits, asserts confirmation card appears with requester name, variety, pickup date/time, and location
- [ ] T020 [P] [US1] Write Cypress E2E validation tests in `frontend/cypress/e2e/request-form.cy.ts`: (a) empty required field shows friendly inline error; (b) bottle volume above max shows limit message; (c) pickup date past cut-off shows closed-batch message; verify form does NOT submit in each case
- [ ] T021 [P] [US1] Write pytest unit tests for `list_varieties` handler in `backend/tests/unit/handlers/test_list_varieties.py`: (a) returns only active varieties; (b) filters to batchId when provided; (c) returns 404 with BATCH_NOT_FOUND for unknown batchId
- [ ] T022 [P] [US1] Write pytest unit tests for `get_batch_config` handler in `backend/tests/unit/handlers/test_get_batch_config.py`: (a) returns batch with availableVarieties resolved; (b) returns 404 with BATCH_NOT_FOUND for unknown batchId
- [ ] T023 [P] [US1] Write pytest unit tests for `create_request` handler in `backend/tests/unit/handlers/test_create_request.py`: (a) happy path returns 201 with requestId; (b) idempotency — same idempotencyKey returns existing request; (c) BOTTLE_VOLUME_EXCEEDED for volume over max; (d) BATCH_CLOSED for pickup date after cutoff; (e) VALIDATION_ERROR for missing required field; (f) VARIETY_NOT_FOUND for inactive variety
- [ ] T024 [P] [US1] Write pytest integration test in `backend/tests/integration/test_request_creation.py`: seeds DynamoDB with a batch and varieties via moto, calls `create_request` handler, asserts item written to `coquito-requests` table with CONFIRMED status and two reminders scheduled

### Implementation for User Story 1

- [ ] T025 [P] [US1] Implement `list_varieties` handler in `backend/src/handlers/list_varieties.py`: reads active varieties from `coquito-varieties` table, optionally filters by batchId via `coquito-batches.availableVarietyIds`, returns variety list with CloudFront image URLs
- [ ] T026 [P] [US1] Implement `get_batch_config` handler in `backend/src/handlers/get_batch_config.py`: fetches batch from `coquito-batches` table, resolves `availableVarietyIds` to variety objects, returns batch config including `maxBottleVolumeMl`, `cutoffDate`, and `status`
- [ ] T027 [US1] Implement `create_request` handler in `backend/src/handlers/create_request.py`: validates input via Request model, checks idempotency key, enforces cutoff and volume constraints, writes to `coquito-requests` with status CONFIRMED, calls `scheduler.create_one_time_schedule` for 7-day and 1-day reminders, returns 201 response
- [ ] T028 [P] [US1] Create reusable form field components in `frontend/src/components/form/`: `labeled-input.ts` (text/email/number input with label, error slot), `date-time-picker.ts` (date + time inputs with min-date constraint), `variety-selector.ts` (card-style radio group with images), `bottle-preference.ts` (toggle + conditional volume input showing max limit), `cost-toggle.ts` (accessible yes/no toggle)
- [ ] T029 [US1] Create request form page in `frontend/src/pages/request-form/index.ts`: on mount fetches batch config + varieties from API, renders form with components from T028, includes Puerto Rican coquito cultural copy (heading, tagline, helper text referencing the craft of coquito-making), handles API errors gracefully with user-friendly messages
- [ ] T030 [US1] Create request form HTML template in `frontend/src/pages/request-form/index.html` (inline template string in index.ts): semantic HTML5 with `<form>`, ARIA labels on all inputs, and a `role="status"` region for the confirmation card
- [ ] T031 [US1] Create request form CSS in `frontend/src/pages/request-form/request-form.css`: mobile-first layout, form card with warm cultural color palette from `tokens.css`, hero image section, WCAG AA contrast on all text and interactive elements
- [ ] T032 [US1] Implement form submission in `frontend/src/pages/request-form/index.ts`: on submit validates all fields client-side (inline errors for each failure), calls `api.createRequest`, on 201 renders confirmation card with full order summary (variety, pickup date/time, location, bottle info, manage-request link using returned requestId)

**Checkpoint**: User Story 1 independently functional. `pnpm cypress run --spec cypress/e2e/request-form.cy.ts` passes. `pytest tests/unit/handlers/test_create_request.py tests/integration/test_request_creation.py` passes.

---

## Phase 4: User Story 2 - Manage an Existing Request (Priority: P2)

**Goal**: Requesters can navigate to `/#/manage/:requestId`, view their order,
edit or cancel it before cut-off, and see a read-only locked view after cut-off.

**Independent Test**: Navigate directly to `/#/manage/{uuid}` — the request loads,
edit/cancel options appear (if pre-cutoff), and saving updates the confirmation.

### Tests for User Story 2 ⚠️ Write these FIRST — verify they FAIL before implementing

- [ ] T033 [P] [US2] Write Cypress E2E tests in `frontend/cypress/e2e/manage-request.cy.ts`: (a) loads request details from stubbed API; (b) edit mode shows pre-filled form; (c) save calls PUT and shows updated confirmation; (d) cancel button shows confirmation dialog, confirms calls DELETE and shows cancellation message; (e) post-cutoff: form is read-only with friendly locked-state message
- [ ] T034 [P] [US2] Write pytest unit tests for `get_request` handler in `backend/tests/unit/handlers/test_get_request.py`: (a) returns full request with `editable: true` before cutoff; (b) returns request with `editable: false` after cutoff; (c) 404 for unknown requestId
- [ ] T035 [P] [US2] Write pytest unit tests for `update_request` handler in `backend/tests/unit/handlers/test_update_request.py`: (a) updates variety/date/location and returns 200; (b) reschedules reminders when pickupDate changes; (c) 403 CUTOFF_PASSED after cutoff; (d) 409 REQUEST_CANCELLED for cancelled request; (e) BOTTLE_VOLUME_EXCEEDED
- [ ] T036 [P] [US2] Write pytest unit tests for `cancel_request` handler in `backend/tests/unit/handlers/test_cancel_request.py`: (a) sets status to CANCELLED and returns 200; (b) idempotent — already-cancelled returns 200; (c) 403 CUTOFF_PASSED after cutoff; (d) all reminders cancelled in EventBridge
- [ ] T037 [P] [US2] Write pytest integration test in `backend/tests/integration/test_request_management.py`: seeds a CONFIRMED request, calls update_request (changes pickup date), asserts DynamoDB item updated and old reminders cancelled + new ones scheduled; then calls cancel_request, asserts status CANCELLED and all reminders CANCELLED

### Implementation for User Story 2

- [ ] T038 [P] [US2] Implement `get_request` handler in `backend/src/handlers/get_request.py`: fetches request from `coquito-requests` by requestId, fetches associated batch to compute `editable` flag (cutoffDate not passed), resolves variety name, returns full response including `batch` object
- [ ] T039 [US2] Implement `update_request` handler in `backend/src/handlers/update_request.py`: validates cutoff not passed, validates fields via Request model, if pickupDate changed cancels existing EventBridge schedules and creates new ones, writes updated item to DynamoDB, returns 200 with full updated request
- [ ] T040 [P] [US2] Implement `cancel_request` handler in `backend/src/handlers/cancel_request.py`: validates cutoff not passed, sets request status to CANCELLED in DynamoDB, calls `scheduler.delete_schedule` for each SCHEDULED reminder, returns 200 with cancellation timestamp
- [ ] T041 [US2] Create manage-request page in `frontend/src/pages/manage-request/index.ts`: on mount extracts requestId from hash, calls `api.getRequest`, renders view mode (read-only summary) with Edit and Cancel buttons when `editable: true`, or locked-state message with friendly explanation when `editable: false`
- [ ] T042 [US2] Create manage-request HTML template in `frontend/src/pages/manage-request/index.ts` (inline template string): view-mode summary card, edit-mode form (reuses components from T028), cancel confirmation dialog (`<dialog>` element), locked-state banner
- [ ] T043 [US2] Create manage-request CSS in `frontend/src/pages/manage-request/manage-request.css`: locked-state banner styling (warm, non-alarming color), cancel dialog overlay, edit/view mode transition
- [ ] T044 [US2] Wire edit save to `api.updateRequest` and cancel to `api.cancelRequest` in `frontend/src/pages/manage-request/index.ts`: on successful PUT, switch back to view mode showing updated summary; on successful DELETE, show cancellation confirmation replacing the page content

**Checkpoint**: User Story 2 independently functional. `pnpm cypress run --spec cypress/e2e/manage-request.cy.ts` passes. `pytest tests/unit/handlers/test_get_request.py tests/unit/handlers/test_update_request.py tests/unit/handlers/test_cancel_request.py tests/integration/test_request_management.py` passes.

---

## Phase 5: User Story 3 - Receive Reminders (Priority: P3)

**Goal**: Confirmed requests automatically trigger two SES reminder emails (7-day
and 1-day before pickup) with a friendly, culturally warm tone and a manage-request link.
Reminders are cancelled when a request is cancelled; rescheduled when the date changes.

**Independent Test**: Seed a CONFIRMED request with a reminder scheduled 1 minute
ahead (test override), fire the EventBridge event manually, and assert the SES mock
received an email containing the order summary and a manage-request link.

### Tests for User Story 3 ⚠️ Write these FIRST — verify they FAIL before implementing

- [ ] T045 [P] [US3] Write pytest unit tests for `send_reminder` handler in `backend/tests/unit/handlers/test_send_reminder.py`: (a) fetches request by requestId from event payload, sends SES email with correct subject, requester name, variety, pickup date/time, location, and manage link; (b) marks reminder status as SENT in DynamoDB; (c) logs warning and exits cleanly if request is CANCELLED
- [ ] T046 [P] [US3] Write pytest integration test in `backend/tests/integration/test_reminders.py`: seeds a CONFIRMED request with moto, invokes `send_reminder` handler with reminder payload, asserts moto SES received exactly one email to the requester address containing the manage-request URL and variety name; asserts reminder status updated to SENT in DynamoDB

### Implementation for User Story 3

- [ ] T047 [US3] Implement `send_reminder` handler in `backend/src/handlers/send_reminder.py`: invoked by EventBridge Scheduler with `{"requestId": "...", "reminderId": "..."}` payload; fetches request from DynamoDB; if status is CANCELLED, logs and returns; otherwise calls `ses.send_email` with reminder template, updates reminder status to SENT in DynamoDB
- [ ] T048 [US3] Add reminder email templates to `backend/src/services/ses.py`: `reminder_subject(days_until: int, variety_name: str) -> str` and `reminder_body_html(request, days_until, manage_url) -> str`; copy MUST include friendly, culturally warm Puerto Rican coquito references (e.g., references to el arte del coquito, holiday spirit); include full order summary and manage-request link
- [ ] T049 [US3] Update `create_request` handler in `backend/src/handlers/create_request.py` (from T027): after writing to DynamoDB, call `scheduler.create_one_time_schedule` twice — once for 7 days before `pickupDate` and once for 1 day before — with payload `{"requestId": id, "reminderId": uuid}` targeting the `send_reminder` Lambda ARN; store both `schedulerArn` values in the request's `reminders` list
- [ ] T050 [US3] Update `update_request` handler in `backend/src/handlers/update_request.py` (from T039): if `pickupDate` changed, cancel existing SCHEDULED reminders via `scheduler.delete_schedule` and create two new schedules; update `reminders` list in DynamoDB item with new ARNs and SCHEDULED status
- [ ] T051 [US3] Update `cancel_request` handler in `backend/src/handlers/cancel_request.py` (from T040): for each reminder with status SCHEDULED, call `scheduler.delete_schedule(schedulerArn)` and update reminder status to CANCELLED in DynamoDB

**Checkpoint**: User Story 3 independently functional. `pytest tests/unit/handlers/test_send_reminder.py tests/integration/test_reminders.py` passes.

---

## Phase 6: User Story 4 - Cook's Ingredient List (Priority: P4)

**Goal**: The cook opens `/#/cook` (authenticated by cook secret), sees a consolidated
ingredient list grouped by variety with totals, can mark items acquired, and can view
a preview before the cut-off or the finalized list after.

**Independent Test**: Open `/#/cook?secret=<cook-secret>` with mocked API — the
ingredient list renders grouped by variety with totals. Tapping an ingredient marks it
acquired and the checkbox state persists.

### Tests for User Story 4 ⚠️ Write these FIRST — verify they FAIL before implementing

- [ ] T052 [P] [US4] Write Cypress E2E tests in `frontend/cypress/e2e/cook-view.cy.ts`: (a) renders ingredient list grouped by variety with per-variety and total quantities; (b) shows "PREVIEW — subject to change" banner when `isFinalized: false`; (c) shows no banner when `isFinalized: true`; (d) tapping an ingredient calls PATCH acquired endpoint and toggles checkbox; (e) without cook secret query param, shows access-denied message
- [ ] T053 [P] [US4] Write pytest unit tests for `get_ingredient_list` handler in `backend/tests/unit/handlers/test_get_ingredient_list.py`: (a) aggregates ingredient quantities correctly for multiple confirmed requests across varieties; (b) ignores CANCELLED requests; (c) returns `isFinalized: true` after cutoff; (d) returns `isFinalized: false` before cutoff; (e) 401 UNAUTHORIZED for missing/wrong cook secret; (f) 404 for unknown batchId
- [ ] T054 [P] [US4] Write pytest unit tests for `mark_ingredient_acquired` handler in `backend/tests/unit/handlers/test_mark_ingredient_acquired.py`: (a) sets acquired to true and returns 200; (b) idempotent — already-acquired returns 200; (c) sets acquired to false (toggle off); (d) 401 UNAUTHORIZED; (e) 404 for unknown ingredient
- [ ] T055 [P] [US4] Write pytest integration test in `backend/tests/integration/test_ingredient_list.py`: seeds batch with 2 varieties and 3 CONFIRMED requests (2 classic, 1 chocolate) via moto, calls `get_ingredient_list`, asserts quantities are multiplied correctly per variety and totals column is correct; calls `mark_ingredient_acquired`, asserts acquired flag persisted

### Implementation for User Story 4

- [ ] T056 [P] [US4] Implement `get_ingredient_list` handler in `backend/src/handlers/get_ingredient_list.py`: validates `X-Cook-Secret` header, fetches batch, queries all CONFIRMED requests for the batch, resolves each request's variety ingredients, multiplies `quantityPerBottle` by confirmed count per variety, groups by variety then by category, computes totals, includes `acquired` state (stored as a sparse map in batch item), returns full response per `api-batches.md` contract
- [ ] T057 [P] [US4] Implement `mark_ingredient_acquired` handler in `backend/src/handlers/mark_ingredient_acquired.py`: validates `X-Cook-Secret` header, verifies ingredientId exists in any of the batch's variety ingredient lists, updates acquired map on the batch DynamoDB item using a conditional expression, returns 200 with current acquired state
- [ ] T058 [US4] Create ingredient-list component in `frontend/src/components/ingredient-list/ingredient-list.ts`: renders a grouped ingredient list — accepts the `byVariety` and `totals` arrays from API response; each variety has a collapsible section with ingredient rows showing `name`, `totalQuantity`, `unit`, and an acquired checkbox; totals section at bottom
- [ ] T059 [US4] Create cook-view page in `frontend/src/pages/cook-view/index.ts`: on mount reads `cookSecret` from URL query param; if missing renders access-denied message; otherwise fetches batch ingredient list, renders preview banner if `isFinalized: false`, renders ingredient-list component, handles PATCH calls on checkbox toggle
- [ ] T060 [US4] Create cook-view HTML template inline in `frontend/src/pages/cook-view/index.ts`: semantic structure with `<main>`, section headings per variety, totals table, preview banner (`role="alert"`)
- [ ] T061 [US4] Create cook-view CSS in `frontend/src/pages/cook-view/cook-view.css`: large base font (minimum 20px for ingredient names and quantities), high-contrast color scheme (dark text on light background; passes WCAG AA in bright and dim light), generous touch targets (≥44px) for acquired checkboxes, simple high-readability table layout for totals

**Checkpoint**: User Story 4 independently functional. `pnpm cypress run --spec cypress/e2e/cook-view.cy.ts` passes. `pytest tests/unit/handlers/test_get_ingredient_list.py tests/unit/handlers/test_mark_ingredient_acquired.py tests/integration/test_ingredient_list.py` passes.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Quality gates, CI, and cross-story consistency.

- [ ] T062 Run `pnpm format:check` on all frontend files; fix any Prettier violations in `frontend/src/**/*.{ts,html,css}`
- [ ] T063 [P] Run full Cypress suite (`pnpm cypress run`) and confirm all E2E tests in `frontend/cypress/e2e/` pass
- [ ] T064 [P] Run `pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=80` in `backend/`; add tests to reach 80% if any module is below threshold
- [ ] T065 [P] Add axe-core accessibility checks to Cypress support in `frontend/cypress/support/commands.ts`; add `cy.checkA11y()` calls to `request-form.cy.ts` and `cook-view.cy.ts`; fix any WCAG AA violations found
- [ ] T066 Create CI workflow in `.github/workflows/ci.yml`: jobs for (1) frontend — `pnpm install`, `pnpm format:check`, `pnpm cypress run`; (2) backend — `pip install -r requirements-dev.txt`, `pytest --cov=src --cov-fail-under=80`; both jobs run on push and pull_request
- [ ] T067 [P] Add performance benchmark assertions to Cypress: in `request-form.cy.ts` assert that form submission API response completes in under 2000ms; in `cook-view.cy.ts` assert that ingredient list API response completes in under 2000ms
- [ ] T068 Run quickstart.md validation checklist end-to-end: verify all checklist items pass and update `specs/001-coquito-request-app/quickstart.md` with any corrections discovered during validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Phase 2 — no dependency on US2/US3/US4
- **User Story 2 (Phase 4)**: Depends on Phase 2 — no dependency on US1 (but shares DynamoDB models)
- **User Story 3 (Phase 5)**: Depends on Phase 2 — integrates with US1 (`create_request`) and US2 (`update_request`, `cancel_request`); complete US1 + US2 first
- **User Story 4 (Phase 6)**: Depends on Phase 2 — no dependency on US1/US2/US3 for the cook view itself
- **Polish (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: No story dependencies — pure foundation + new code
- **US2 (P2)**: No story dependencies — shares models from foundation
- **US3 (P3)**: Integrates with US1 (`create_request` schedules reminders) and US2 (`update_request`, `cancel_request` manage reminders) — implement US1 and US2 first
- **US4 (P4)**: No story dependencies — cook view is independent of requester flows

### Within Each User Story

- Tests MUST be written FIRST and MUST FAIL before implementation begins (TDD)
- Backend models before services before handlers
- Frontend components before page assembly
- Complete story + passing tests before moving to next

### Parallel Opportunities

- T002, T003, T008 can run in parallel with T001 (after pnpm init)
- T004, T005 can run in parallel with frontend setup
- T014, T015, T016 (models) run in parallel within Phase 2
- All [P]-marked test tasks within a story can be written in parallel
- US1 and US2 backend work (T021–T029 vs T033–T040) can proceed in parallel once Phase 2 is done
- US4 backend and frontend are independent from US1/US2 backend

---

## Parallel Example: User Story 1 Backend Tests

```bash
# Write all backend tests for US1 in parallel (different files, no dependencies):
Task: "Write pytest unit tests for list_varieties in backend/tests/unit/handlers/test_list_varieties.py"        # T021
Task: "Write pytest unit tests for get_batch_config in backend/tests/unit/handlers/test_get_batch_config.py"  # T022
Task: "Write pytest unit tests for create_request in backend/tests/unit/handlers/test_create_request.py"       # T023
Task: "Write pytest integration test in backend/tests/integration/test_request_creation.py"                    # T024
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: `pnpm cypress run --spec cypress/e2e/request-form.cy.ts` passes; `pytest tests/unit/handlers/test_create_request.py` passes
5. Deploy/demo the request form if ready

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → requester can submit an order → **MVP demo**
3. US2 → requester can manage their order → **demo edit/cancel**
4. US3 → reminders fire automatically → **demo end-to-end notification flow**
5. US4 → cook has ingredient list → **full feature complete**

---

## Notes

- [P] tasks = different files or truly independent, safe to parallelize
- [Story] label maps every task to its user story for traceability
- TDD is mandatory (constitution Principle II): tests written first, confirmed failing, then implemented
- Run `pnpm format:check` before any frontend PR — Prettier violations block merge (constitution Principle I)
- pytest coverage must stay ≥80% — CI enforces this (constitution Principle II)
- Cook view CSS must pass WCAG AA at minimum — verified by axe-core in Cypress (constitution Principle III)
- Stop at each story checkpoint to validate independently before proceeding
