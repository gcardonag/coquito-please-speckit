# Tasks: AWS Website Storage

**Input**: Design documents from `/specs/003-aws-website-storage/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete sibling tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- All file paths are absolute from repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new Terraform module directory structure before any implementation begins.

- [X] T001 Create `infra/terraform/modules/storage/` directory with three empty stub files: `main.tf`, `variables.tf`, `outputs.tf` (content will be filled in Phase 4)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Wire the module chain in Terraform so that once the storage module is implemented, it connects automatically to the API module. These three tasks must be complete before any `terraform apply` can succeed.

**⚠️ CRITICAL**: T002 must precede T003. Both must be complete before `terraform apply`.

- [X] T002 [P] Update `infra/terraform/modules/api/variables.tf` — add four new input variable declarations: `dynamodb_requests_table`, `dynamodb_batches_table`, `dynamodb_varieties_table`, `cloudfront_assets_base_url` (see plan.md Detailed Implementation Specification → Updated Module: modules/api/)
- [X] T003 Update `infra/terraform/main.tf` — add `module "storage"` block (passing `environment` and `domain`); update `module "api"` block to pass the four new storage outputs through (see plan.md → Updated Root: main.tf)
- [X] T004 Update `infra/terraform/outputs.tf` — add four new outputs: `dynamodb_requests_table`, `dynamodb_batches_table`, `dynamodb_varieties_table`, `cloudfront_assets_base_url` sourced from `module.storage` (see plan.md → Updated Root: outputs.tf)

**Checkpoint**: Terraform module wiring is complete. `terraform validate` should pass once storage module stubs are filled in.

---

## Phase 3: User Story 1 — Static Website Content Accessible to Visitors (Priority: P1) 🎯 MVP

**Goal**: Confirm the existing CloudFront-backed S3 static site satisfies US1. No new infrastructure is required — this story was delivered by feature 002. The only new task is a contract test that encodes the acceptance scenario.

**Independent Test**: `backend/tests/contract/test_static_content.py` passes. Site loads in browser at `https://{domain}`.

### Tests for User Story 1

- [X] T005 [US1] Write contract test for static site availability in `backend/tests/contract/test_static_content.py` — test makes an HTTP GET to `FRONTEND_URL` env var (skips with `pytest.skip` if env var not set), asserts HTTP 200 and `Content-Type: text/html`. Covers spec acceptance scenario 1 (page loads for visitor with valid URL).

**Checkpoint**: US1 is independently testable. `pytest backend/tests/contract/test_static_content.py` passes (or skips if `FRONTEND_URL` not set). Existing frontend module requires no changes.

---

## Phase 4: User Story 2 — Application Data Persisted and Retrieved (Priority: P2)

**Goal**: DynamoDB tables created in AWS, Lambda functions wired with the correct table name env vars, and write→read round-trip validated by tests.

**Independent Test**: `pytest backend/tests/contract/test_dynamodb_tables.py` passes against a real deployed environment. `POST /api/v1/requests` creates a record retrievable via `GET /api/v1/requests/{id}`.

### Tests for User Story 2 (write first — must FAIL before implementation)

- [X] T006 [US2] Write contract tests for DynamoDB table schema in `backend/tests/contract/test_dynamodb_tables.py` — using boto3 with real AWS credentials (skip with `pytest.skip` if `AWS_INTEGRATION` env var not set), verify: (a) `coquito-varieties-{ENVIRONMENT}` table exists with hash key `varietyId`; (b) `coquito-batches-{ENVIRONMENT}` table exists with hash key `batchId`; (c) `coquito-requests-{ENVIRONMENT}` table exists with hash key `requestId`; (d) all tables report `BillingModeSummary.BillingMode = "PAY_PER_REQUEST"`; (e) all tables report `SSEDescription.Status = "ENABLED"`. Read `ENVIRONMENT` from env var (default `prod`).

- [X] T006b [P] [US2] Write real-AWS integration test for varieties read path in `backend/tests/integration/test_storage_integration.py` — skip with `pytest.skip` if `AWS_INTEGRATION` env var not set; seed one Variety and one Batch into real DynamoDB (teardown after test), call `list_varieties.handler` with no query params, assert HTTP 200 and at least one variety returned with a non-empty `imageUrl`. This satisfies constitution §II for US2: "full path from input to output without mocking the core domain layer."
- [X] T006c [P] [US2] Write real-AWS integration test for requests write→read path in `backend/tests/integration/test_storage_integration.py` — skip if `AWS_INTEGRATION` not set; seed required Batch + Variety; call `create_request.handler` with valid payload, assert HTTP 201 with `requestId`; then call `get_request.handler` with that `requestId`, assert HTTP 200 and data matches submitted payload; teardown seeded records after test.

### Implementation for User Story 2

- [X] T007 [P] [US2] Implement `infra/terraform/modules/storage/variables.tf` — declare `environment` (string, required) and `domain` (string, required) variables per plan.md spec
- [X] T008 [P] [US2] Implement `infra/terraform/modules/storage/main.tf` — create three `aws_dynamodb_table` resources (`varieties`, `batches`, `requests`) each with: `billing_mode = "PAY_PER_REQUEST"`, `server_side_encryption { enabled = true }`, `deletion_protection_enabled = true`, and the correct hash key attribute per data-model.md. Table names: `coquito-{varieties|batches|requests}-${var.environment}`
- [X] T009 [P] [US2] Implement `infra/terraform/modules/storage/outputs.tf` — expose `requests_table_name`, `batches_table_name`, `varieties_table_name`, and `cloudfront_assets_base_url` (value: `"https://${var.domain}"`) per plan.md spec
- [X] T010 [US2] Update `infra/terraform/modules/api/main.tf` — add `DYNAMODB_REQUESTS_TABLE`, `DYNAMODB_BATCHES_TABLE`, `DYNAMODB_VARIETIES_TABLE` to the `environment.variables` block of all protected Lambda function resources: `health`, `list_varieties`, `create_request`, `get_request`, `update_request`, `cancel_request`, `get_batch_config`, `get_ingredient_list`, `mark_ingredient_acquired`, `send_reminder`, `create_user` (see plan.md → Updated Module: modules/api/ → main.tf). Auth functions `auth_token_exchange`, `auth_logout`, `auth_refresh` do NOT need DynamoDB env vars.

**Checkpoint**: Run `terraform apply`. Verify: (a) three DynamoDB tables appear in AWS console with correct names and billing mode; (b) `terraform output` shows all four new outputs; (c) `pytest backend/tests/contract/test_dynamodb_tables.py` passes with `AWS_INTEGRATION=1 ENVIRONMENT=prod`.

---

## Phase 5: User Story 3 — Media and Asset Files Stored and Served (Priority: P3)

**Goal**: `CLOUDFRONT_ASSETS_BASE_URL` is wired into the `list_varieties` Lambda so variety image URLs are non-empty in API responses; seed data (varieties + batch) is present so a human tester can verify the full end-to-end flow.

**Independent Test**: `GET /api/v1/varieties` (with seed data present) returns varieties with non-empty `imageUrl` values of the form `https://{domain}/assets/{key}`.

### Tests for User Story 3 (write first — must FAIL before implementation)

- [X] T011 [US3] Write unit test in `backend/tests/unit/test_seed_data.py` — import and call `seed_data.py` seed functions twice against moto-mocked DynamoDB; assert no `ConflictError` is raised on second call and exactly 2 variety records and 1 batch record exist. Covers seed script idempotency.

- [X] T011b [US3] Write real-AWS integration test for media asset URL resolution in `backend/tests/integration/test_storage_integration.py` — skip if `AWS_INTEGRATION` not set; seed one Variety with `imageKey = "assets/classic.jpg"` into real DynamoDB; call `list_varieties.handler` with `CLOUDFRONT_ASSETS_BASE_URL` set to a test domain value; assert the returned `imageUrl` equals `"{test_domain}/assets/classic.jpg"` (non-empty, correctly composed). This satisfies constitution §II for US3 without mocking DynamoDB.

### Implementation for User Story 3

- [X] T012 [US3] Update `infra/terraform/modules/api/main.tf` — add `CLOUDFRONT_ASSETS_BASE_URL = var.cloudfront_assets_base_url` to the `environment.variables` block of the `list_varieties` Lambda function resource (this is a separate edit from T010; the variable `var.cloudfront_assets_base_url` was added to api/variables.tf in T002)
- [X] T013a [US3] Create `backend/scripts/__init__.py` (empty file) to make `backend/scripts/` a Python package, enabling `from scripts.seed_data import ...` imports in `backend/tests/unit/test_seed_data.py`
- [X] T013 [US3] Create `backend/scripts/seed_data.py` — idempotent seed script using `put_item_if_not_exists` from `src.services.dynamodb`; reads table names from env vars `DYNAMODB_VARIETIES_TABLE` and `DYNAMODB_BATCHES_TABLE`; writes exactly the two Variety records and one Batch record defined in `data-model.md` (Seed Dataset section); prints progress to stdout; exits 0 on success. Requires `AWS_REGION`, `DYNAMODB_VARIETIES_TABLE`, `DYNAMODB_BATCHES_TABLE` env vars.

**Checkpoint**: Run `uv run python backend/scripts/seed_data.py` (with real AWS creds + table names). Verify two varieties and one open batch appear in DynamoDB console. Call `GET /api/v1/varieties` (authenticated) and confirm `imageUrl` is `https://{domain}/assets/{key}` for each variety.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Formatting, validation, and end-to-end verification before marking the feature complete.

- [X] T014 [P] Run `terraform fmt -recursive infra/terraform/modules/storage/` and `terraform fmt infra/terraform/modules/api/main.tf infra/terraform/modules/api/variables.tf infra/terraform/main.tf infra/terraform/outputs.tf` — fix any formatting differences; commit if any files change
- [X] T015 [P] Run `terraform validate` from `infra/terraform/` — must report "Success! The configuration is valid." with zero warnings or errors
- [X] T016 Run full backend test suite `pytest backend/tests/ -v` from `backend/` directory — all tests must pass; confirm unit test coverage remains at or above 80% for `backend/src/` modules (constitution gate)
- [ ] T017 Execute the 10-step human test plan in `quickstart.md` against the deployed environment — mark each step pass/fail; all 10 steps must pass before feature branch is merged

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (T001 stub files must exist before variables.tf and main.tf are updated)
- **US1 (Phase 3)**: Depends on Phase 2 — independent of US2 and US3
- **US2 (Phase 4)**: Depends on Phase 2; T010 depends on T007–T009 (storage module must be implemented before api/main.tf references its outputs meaningfully)
- **US3 (Phase 5)**: Depends on Phase 4 (T012 edits same file as T010; T013 can start after T007)
- **Polish (Phase 6)**: Depends on all prior phases complete

### User Story Dependencies

- **US1 (P1)**: Depends only on existing infrastructure (feature 002); T005 can be written immediately
- **US2 (P2)**: Depends on Foundational phase complete; T006 (test) can be written in parallel with T007–T009 (storage module implementation)
- **US3 (P3)**: Depends on US2 complete (T010 must precede T012 since both edit `api/main.tf`)

### Within Each Phase

- T006 (US2 contract test) must be written and FAIL before T007–T010 are implemented (constitution: Red-Green-Refactor)
- T011 (US3 unit test) must be written and FAIL before T013 is implemented
- T007, T008, T009 can run in parallel (different files in same directory)
- T014 and T015 can run in parallel (formatting and validation are independent)

---

## Parallel Example: User Story 2

```bash
# After T006 test is written and confirmed failing:
# These three implementation tasks touch different files and can run in parallel:
Task T007: "Implement infra/terraform/modules/storage/variables.tf"
Task T008: "Implement infra/terraform/modules/storage/main.tf"
Task T009: "Implement infra/terraform/modules/storage/outputs.tf"

# T010 runs after T007–T009 are complete:
Task T010: "Update infra/terraform/modules/api/main.tf — add DYNAMODB_* env vars"
```

---

## Implementation Strategy

### MVP First (User Story 2 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002–T004)
3. Complete Phase 4: US2 (T006–T010)
4. **STOP and VALIDATE**: Run `terraform apply`, verify DynamoDB tables, run contract tests
5. Application data is now fully operational — deploy if ready

### Incremental Delivery

1. Complete Setup + Foundational → Terraform chain is wired
2. Add US2 → DynamoDB tables live, application can persist data → **Deploy/Validate (MVP!)**
3. Add US3 → Variety images resolve, seed data present → **Deploy/Validate**
4. Polish → All gates pass → **Ready to merge**

---

## Notes

- `[P]` tasks touch different files and have no dependency on incomplete sibling tasks
- `[Story]` label maps each task to the user story it delivers for traceability to spec.md
- Constitution requires: tests written before implementation (Red-Green-Refactor), 80% unit coverage, zero linter warnings
- No Lambda handler code changes in this feature — all tasks are Terraform infrastructure, env var wiring, scripts, and tests
- Existing moto-based unit and integration tests in `backend/tests/` cover handler behavior and do not need to be rewritten
- Asset image files (`assets/classic.jpg`, `assets/chocolate.jpg`) are out of scope for this feature — `imageUrl` values will return valid but broken image links until real images are uploaded; this is acceptable and documented in `quickstart.md` Test 4 notes
