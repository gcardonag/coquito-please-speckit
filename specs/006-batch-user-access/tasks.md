# Tasks: Batch User Access Management

**Input**: Design documents from `/specs/006-batch-user-access/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/api.md ✅, quickstart.md ✅

**TDD Discipline**: Per constitution §II, contract tests MUST be written first and confirmed failing (RED) before each handler is implemented. Unit tests must be written first for new models.

**Organization**: Tasks grouped by user story — each phase is independently completable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks in the same phase)
- **[Story]**: Which user story this task belongs to (US1–US4)

---

## Phase 1: Setup (Terraform Infrastructure)

**Purpose**: Provision the new DynamoDB table and wire it through to the API module. No user story work can begin until Terraform changes are applied.

- [ ] T001 Add `aws_dynamodb_table.batch_access` resource (PAY_PER_REQUEST, composite key batchId+userId, SSE enabled, deletion protection) to `infra/terraform/modules/storage/main.tf`
- [ ] T002 Add `batch_access_table_name` output to `infra/terraform/modules/storage/outputs.tf`
- [ ] T003 Add `dynamodb_batch_access_table` input variable to `infra/terraform/modules/api/variables.tf`
- [ ] T004 Pass `module.storage.batch_access_table_name` into `module.api` as `dynamodb_batch_access_table` in `infra/terraform/main.tf`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core backend and frontend foundations that all user stories share. Must be complete before any user story phase begins.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T005 Extend `aws_iam_role_policy.lambda_cognito` in `infra/terraform/modules/api/main.tf` to add `cognito-idp:ListUsers` and `cognito-idp:AdminGetUser` permissions
- [ ] T006 Write unit test (RED) for `BatchAccessGrant.to_dict` and `BatchAccessGrant.from_dict` in `backend/tests/unit/test_batch_access_model.py`
- [ ] T007 Create `BatchAccessGrant` dataclass with `batch_id`, `user_id`, `email`, `first_name`, `last_name`, `granted_at` fields and `to_dict`/`from_dict` methods in `backend/src/models/batch_access.py` — make T006 pass (GREEN)
- [ ] T008 Add `UserSummary`, `BatchAccessUser`, `BatchAccessGrant`, `CreateUserPayload`, and `CreateUserResponse` TypeScript interfaces to `frontend/src/services/api.ts`

**Checkpoint**: Foundation ready — user story phases can now proceed.

---

## Phase 3: User Story 1 — Grant Existing User Batch Access (Priority: P1) 🎯 MVP

**Goal**: A chef can search for an existing user and grant them access to an open batch. The access list is visible in the Manage Access panel.

**Independent Test**: Log in as chef → open `#/batches` → select an OPEN batch → open "Manage Access" section → search for a known user → grant access → user appears in the access list.

### Tests for User Story 1 (RED — write before implementation)

- [ ] T009 [P] [US1] Write contract tests (RED) covering: email-prefix match returns results, given-name prefix match returns results, result present in both calls appears once (deduplication), empty results, non-chef (403), missing query param (400) for `GET /api/v1/chef/users` in `backend/tests/contract/test_chef_search_users.py`
- [ ] T010 [P] [US1] Write contract tests (RED) covering: success (201), non-chef (403), closed batch (403), user not found (404), batch not found (404), duplicate grant (409) for `PUT /api/v1/chef/batches/{id}/access/{userId}` in `backend/tests/contract/test_chef_grant_batch_access.py`
- [ ] T011 [P] [US1] Write contract tests (RED) covering: success with users, empty list, batch not found (404), non-chef (403) for `GET /api/v1/chef/batches/{id}/access` in `backend/tests/contract/test_chef_list_batch_access.py`

### Implementation for User Story 1

- [ ] T012 [P] [US1] Implement `chef_search_users` handler (`require_chef`, validate `query` param, issue two sequential `cognito.list_users` calls — `email ^= q` and `given_name ^= q` each with Limit=20 — merge by `sub`, deduplicate, cap at 20) in `backend/src/handlers/chef_search_users.py` — make T009 pass (GREEN)
- [ ] T013 [P] [US1] Implement `chef_grant_batch_access` handler (`require_chef`, read batch → validate OPEN, `admin_get_user` → verify exists, `put_item_if_not_exists` to batch-access table) in `backend/src/handlers/chef_grant_batch_access.py` — make T010 pass (GREEN)
- [ ] T014 [P] [US1] Implement `chef_list_batch_access` handler (`require_chef`, read batch → 404 if missing, query batch-access table by batchId) in `backend/src/handlers/chef_list_batch_access.py` — make T011 pass (GREEN)
- [ ] T015 [US1] Add `chef_search_users`, `chef_grant_batch_access`, and `chef_list_batch_access` Lambda functions, API Gateway integrations, routes (CUSTOM auth), and CloudWatch log groups (30-day retention) to `infra/terraform/modules/api/main.tf`; add all three to `local.protected_functions`; set env vars: `COGNITO_USER_POOL_ID` on search and grant; `DYNAMODB_BATCH_ACCESS_TABLE` on grant and list; `DYNAMODB_BATCHES_TABLE` on grant and list
- [ ] T016 [US1] Add `searchUsers`, `grantBatchAccess`, and `listBatchAccess` API functions to `frontend/src/services/api.ts`
- [ ] T017 [US1] Add "Manage Access" collapsible section to the batch detail panel in `frontend/src/pages/batch-management/index.ts`: show section only when `authContext.role === 'chef'` AND `batch.status === 'OPEN'` (read role from the decoded JWT / auth context, same source used by existing chef-only actions); render user search field, results list with "Grant Access" per row, and access list with loading and empty states
- [ ] T018 [US1] Add `.access-panel`, `.access-search`, `.access-results`, `.access-user-row`, and `.access-empty` CSS classes to `frontend/src/pages/batch-management/batch-management.css`
- [ ] T019 [US1] Write integration test covering: search for existing user, grant access, access appears in list (US1 acceptance scenarios) in `backend/tests/integration/test_batch_access_management.py`

**Checkpoint**: US1 fully functional — chef can search and grant access, and see the result in the access list.

---

## Phase 4: User Story 2 — Create a New User and Grant Batch Access (Priority: P2)

**Goal**: A chef can create a brand-new user (email + first name + optional last name) who is automatically granted access to the current batch upon creation.

**Independent Test**: Log in as chef → open `#/batches` → select an OPEN batch → open "Manage Access" section → click "New User" → fill form → submit → new user appears in the access list.

### Tests for User Story 2 (RED — write before implementation)

- [ ] T020 [US2] Update `backend/tests/contract/test_create_user.py` with RED test cases: `firstName` missing → 400, `firstName` present → 201 with Cognito `given_name` set, `lastName` optional → 201 without `family_name`, duplicate email → 409

### Implementation for User Story 2

- [ ] T021 [US2] Modify `backend/src/handlers/create_user.py` to parse `firstName` (required, non-empty) and `lastName` (optional) from request body; pass as Cognito `given_name` and `family_name` attributes on `admin_create_user` — make T020 pass (GREEN)
- [ ] T022 [US2] Add `createUser` API function to `frontend/src/services/api.ts`
- [ ] T023 [US2] Add "New User" inline form (email, first name, last name fields; submit creates user then calls `grantBatchAccess` with the returned `userId`; refreshes access list on success; on grant failure after successful creation, display an actionable error naming the created user with a "Grant access" button that retries only the grant step) to the Manage Access section in `frontend/src/pages/batch-management/index.ts`
- [ ] T024 [US2] Write integration test covering: create new user → auto-grant → user in access list; duplicate email → 409; firstName missing → 400 (US2 acceptance scenarios) in `backend/tests/integration/test_batch_access_management.py`

**Checkpoint**: US2 fully functional — chefs can onboard new users directly from the batch access panel.

---

## Phase 5: User Story 3 — View Users with Batch Access (Priority: P3)

**Goal**: A chef can view the complete list of users with access to the current batch, including an empty state when no access grants exist.

**Independent Test**: Open `#/batches` → select a batch with pre-existing access grants → open "Manage Access" → access list shows all granted users with name and email. Also: select a batch with no grants → empty state message appears.

### Tests for User Story 3

- [ ] T025 [US3] Write integration test covering: list returns all granted users for a batch; list is empty for a batch with no grants; closed batch still returns list (GET-only, no state change) in `backend/tests/integration/test_batch_access_management.py`

### Implementation for User Story 3

- [ ] T026 [US3] Verify empty state message (`"No users have been granted access to this batch."`) renders correctly in the access list section of `frontend/src/pages/batch-management/index.ts`; confirm `data-testid="access-empty-state"` is present for e2e testability

**Checkpoint**: US3 fully functional — chefs have complete visibility into batch access, including empty state.

---

## Phase 6: User Story 4 — Revoke a User's Batch Access (Priority: P3)

**Goal**: A chef can remove a user from the batch access list with an explicit confirmation step. The batch must be OPEN.

**Independent Test**: Log in as chef → select an OPEN batch with at least one access grant → open "Manage Access" → click "Remove" for a user → confirmation dialog appears → confirm → user is removed from the list.

### Tests for User Story 4 (RED — write before implementation)

- [ ] T027 [US4] Write contract tests (RED) covering: success (204), non-chef (403), closed batch (403), batch not found (404), access grant not found (404) for `DELETE /api/v1/chef/batches/{id}/access/{userId}` in `backend/tests/contract/test_chef_revoke_batch_access.py`

### Implementation for User Story 4

- [ ] T028 [US4] Implement `chef_revoke_batch_access` handler (`require_chef`, read batch → validate OPEN, GetItem on batch-access table → 404 if not found, DeleteItem) in `backend/src/handlers/chef_revoke_batch_access.py` — make T027 pass (GREEN)
- [ ] T029 [US4] Add `chef_revoke_batch_access` Lambda function, API Gateway integration, route (`DELETE /api/v1/chef/batches/{id}/access/{userId}`, CUSTOM auth), and CloudWatch log group (30-day retention) to `infra/terraform/modules/api/main.tf`; add to `local.protected_functions`; set `DYNAMODB_BATCH_ACCESS_TABLE` and `DYNAMODB_BATCHES_TABLE` env vars
- [ ] T030 [US4] Add `revokeBatchAccess` API function to `frontend/src/services/api.ts`
- [ ] T031 [US4] Add "Remove" button per access row and revoke confirmation dialog (matching existing `batch-dialog-overlay` pattern) to the access panel in `frontend/src/pages/batch-management/index.ts`; refresh access list on confirmed revocation
- [ ] T032 [US4] Write integration test covering: revoke removes user from list; revoke on closed batch → 403; revoke non-existent grant → 404; cancel confirmation → no change (US4 acceptance scenarios) in `backend/tests/integration/test_batch_access_management.py`

**Checkpoint**: All four user stories are independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Accessibility, coverage validation, and error message consistency.

- [ ] T033 [P] Run axe-core accessibility audit against the Manage Access panel; confirm zero WCAG 2.1 AA violations; append audit results (tool name, version, date, zero-violation confirmation) to `docs/accessibility-audit.md` (create file if it does not exist)
- [ ] T034 [P] Verify all error messages in new Lambda handlers and frontend access panel are actionable (state what went wrong, why, and what to do); fix any generic messages found in `backend/src/handlers/chef_*.py` and `frontend/src/pages/batch-management/index.ts`
- [ ] T035 Run `uv run pytest --cov=src --cov-report=term-missing` from `backend/` and confirm coverage ≥ 80% for all new modules (`src/models/batch_access.py`, `src/handlers/chef_search_users.py`, `src/handlers/chef_grant_batch_access.py`, `src/handlers/chef_list_batch_access.py`, `src/handlers/chef_revoke_batch_access.py`, modified `src/handlers/create_user.py`)
- [ ] T036 Verify `quickstart.md` steps in `specs/006-batch-user-access/quickstart.md` execute without error against the completed implementation; update any steps that changed during implementation
- [ ] T037 [P] Add pytest-benchmark fixtures for `chef_search_users` (assert wall-clock p95 ≤ 1 000 ms under moto) and `chef_grant_batch_access` (assert p95 ≤ 200 ms under moto) in `backend/tests/benchmarks/test_batch_access_benchmarks.py`; add a `pytest --benchmark-only` step to the CI pipeline that runs on every PR touching `backend/src/handlers/` (constitution §IV: performance benchmarks in CI on critical paths)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (Terraform must be applied or Terraform changes must exist for IAM/env var config)
- **US1 (Phase 3)**: Depends on Phase 2 completion — BLOCKS nothing else, but US1 checkpoint validates grant/list before proceeding
- **US2 (Phase 4)**: Depends on Phase 2; can start after Phase 3 if `grantBatchAccess` endpoint is available (US2 auto-grants after create)
- **US3 (Phase 5)**: Depends on Phase 2; access list backend exists from Phase 3 — tasks here are integration test + frontend empty-state confirmation
- **US4 (Phase 6)**: Depends on Phase 3 (access list needed to verify revocation); otherwise independent
- **Polish (Phase 7)**: Depends on all story phases complete

### User Story Dependencies

- **US1 (P1)**: Independent after Phase 2
- **US2 (P2)**: Independent after Phase 2; integrates with US1's `grantBatchAccess` call
- **US3 (P3)**: Independent after Phase 2; backend endpoint built in Phase 3
- **US4 (P3)**: Depends on US1 (access grants must exist to revoke)

### Within Each User Story

1. Contract tests (RED) — write and confirm FAILING
2. Handler implementation (GREEN) — make tests pass
3. Terraform wiring — add Lambda/route/log group
4. Frontend API function — add to `api.ts`
5. Frontend UI — add to page component
6. Integration test — end-to-end story validation

### Parallel Opportunities

- T009, T010, T011 (contract tests for US1 handlers) can run in parallel
- T012, T013, T014 (handler implementations) can run in parallel once their respective RED tests exist
- T005, T006, T008 (Phase 2 tasks) can run in parallel
- T033 and T034 (Phase 7 checks) can run in parallel

---

## Parallel Example: User Story 1 (Tests)

```bash
# All three contract test files can be authored simultaneously:
T009: backend/tests/contract/test_chef_search_users.py
T010: backend/tests/contract/test_chef_grant_batch_access.py
T011: backend/tests/contract/test_chef_list_batch_access.py

# Then all three handlers in parallel (after RED tests confirmed):
T012: backend/src/handlers/chef_search_users.py
T013: backend/src/handlers/chef_grant_batch_access.py
T014: backend/src/handlers/chef_list_batch_access.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Terraform infrastructure
2. Complete Phase 2: Foundational model + IAM + frontend types
3. Complete Phase 3: US1 (search + grant + list)
4. **STOP and VALIDATE**: Chef can search a user, grant access, and see them in the list
5. Demo if ready

### Incremental Delivery

1. Phase 1 + 2 → Infrastructure ready
2. Phase 3 → US1: grant existing user → validate → deploy (MVP)
3. Phase 4 → US2: create new user → validate → deploy
4. Phase 5 → US3: view list polish → validate
5. Phase 6 → US4: revoke access → validate → deploy (full feature)
6. Phase 7 → Polish → release

---

## Notes

- All RED tests must be confirmed FAILING with `uv run pytest <file> -v` before writing the implementation
- Commit after each phase checkpoint
- `infra/terraform/modules/api/main.tf` receives multiple additions across phases — T015 (3 Lambdas) and T029 (1 Lambda) modify the same file; keep them sequential within each phase
- The `createUser` frontend function (T022) replaces the implied pattern from the existing endpoint — ensure the existing `create_user` Terraform route is NOT duplicated
- `data-testid` attributes are required on all interactive elements per existing conventions
