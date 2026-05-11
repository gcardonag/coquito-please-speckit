# Tasks: Chef Variety Management

**Input**: Design documents from `/specs/005-variety-management/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Included per constitution requirement — tests are written BEFORE implementation in each story phase. The Red-Green-Refactor cycle is enforced.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unresolved dependencies)
- **[Story]**: Which user story this task belongs to (US1=Browse, US2=Edit, US3=Ingredients, US4=Create)
- Exact file paths included in every description

---

## Phase 1: Setup (Shared Frontend Scaffolding)

**Purpose**: Create the new page files and wire up routing so the SPA can navigate to `#/varieties`. These are prerequisites for all frontend user stories.

- [X] T001 Create stub `frontend/src/pages/variety-management/index.ts` exporting `mountVarietyManagement(container: HTMLElement): Promise<void>` that renders a loading placeholder — makes routing work before any story is implemented
- [X] T002 [P] Create `frontend/src/pages/variety-management/variety-management.css` with base layout rules matching the batch-management page structure (`.variety-management`, `.variety-management__header`, `.variety-management__title`, `.variety-row`, `.variety-status`, `.variety-form`, `.variety-error`, `.variety-empty`)
- [X] T003 [P] Add `ChefVarietyDetail` and `IngredientItem` (chef variant with `ingredientId`) TypeScript interfaces, and `chefListVarieties()`, `chefCreateVariety()`, `chefUpdateVariety()` typed API functions to `frontend/src/services/api.ts` following the existing `request<T>()` helper pattern
- [X] T004 Add `renderVarietyManagement` async function and `{ pattern: /^#\/varieties$/, render: renderVarietyManagement }` route entry to `frontend/src/main.ts` (dynamic import of `./pages/variety-management/index`); depends on T001 and T003

**Checkpoint**: `pnpm dev` loads `#/varieties` without console errors; stub renders a loading placeholder

---

## Phase 2: Foundational (Backend Infrastructure)

**Purpose**: Terraform resources for all three new Lambda endpoints. Must be deployed before end-to-end integration tests can run against a real environment. Does not block unit tests.

**⚠️ CRITICAL**: This phase must be applied to each target environment before integration tests or manual testing can run against a deployed stack.

- [X] T005 Add to `infra/terraform/modules/api/main.tf`: three `aws_lambda_function` resources (`coquito-chef-list-varieties`, `coquito-chef-create-variety`, `coquito-chef-update-variety`) with `python3.12`/arm64 runtime, correct handler paths (`src.handlers.chef_list_varieties.handler` etc.), shared `lambda_zip`, deps layer, and env vars (`ENVIRONMENT`, `DYNAMODB_VARIETIES_TABLE`, `DYNAMODB_BATCHES_TABLE`, `DYNAMODB_REQUESTS_TABLE`); three `aws_apigatewayv2_integration` (AWS_PROXY, payload 2.0); three `aws_apigatewayv2_route` entries (`GET /api/v1/chef/varieties`, `POST /api/v1/chef/varieties`, `PUT /api/v1/chef/varieties/{id}`) with `authorization_type = "CUSTOM"` and existing `authorizer_id`; add all three to `protected_functions` locals map; three `aws_cloudwatch_log_group` resources (30-day retention)

**Checkpoint**: `terraform plan` shows 13 resources to add with no errors

---

## Phase 3: User Story 1 — Browse All Varieties (Priority: P1) 🎯 MVP

**Goal**: Chef navigates to `#/varieties` and sees all varieties (active + inactive) with name, status badge, description, and bottle yield. Non-chefs see an access-denied message.

**Independent Test**: Run `uv run pytest tests/unit/handlers/test_chef_list_varieties.py tests/contract/test_chef_varieties.py -v` and navigate to `#/varieties` as a chef — all seeded varieties appear including inactive ones.

> **⚠️ Write tests first. Run them. Confirm they FAIL. Then implement.**

### Tests — User Story 1

- [X] T006 [P] [US1] Write unit tests in `backend/tests/unit/handlers/test_chef_list_varieties.py`: (a) chef role returns 200 with all varieties including inactive, each item has `varietyId`, `name`, `description`, `imageKey`, `bottleYieldMl`, `active`, and `ingredients` list; (b) non-chef role returns 403 `CHEF_ROLE_REQUIRED`; (c) empty varieties table returns 200 `{"varieties": []}`; (d) active-only filter is NOT applied (both active=true and active=false items appear)
- [X] T007 [P] [US1] Write GET /api/v1/chef/varieties contract test in `backend/tests/contract/test_chef_varieties.py`: verify response schema matches `ChefVarietyDetail` shape — all required fields present, `ingredients` is a list where each item has `ingredientId`, `name`, `quantityPerBottle`, `unit`, `category`
- [X] T008 [US1] Write integration test "chef views all varieties including inactive" in `backend/tests/integration/test_variety_management.py`: seed one active and one inactive variety, call handler as chef, assert both appear in response with correct `active` values

### Implementation — User Story 1

- [X] T009 [US1] Implement `backend/src/handlers/chef_list_varieties.py`: call `require_chef(event)` and return early on 403; `scan_table(varieties_table_name())` without active filter; for each item call `Variety.from_dict()` and serialize to ChefVarietyDetail including full `ingredients` list via `i.to_dict()` for each ingredient; return `{"varieties": [...]}` with status 200
- [X] T010 [US1] Implement variety list view in `frontend/src/pages/variety-management/index.ts`: call `chefListVarieties()` on mount; render an `<ul>` list where each `<li>` shows variety name, status badge (`active` / `inactive`), description, and bottle yield; render a placeholder element (e.g., `<span class="variety-img-placeholder">`) when `imageKey` is empty string; on 403 render inline "Access denied. Only chefs can manage varieties."; on empty list render empty-state message encouraging the chef to create the first variety; on other errors render retry message; follow the `el()` DOM-helper pattern and `data-testid` conventions from batch-management
- [X] T011 [US1] Write frontend unit tests for variety list rendering in `frontend/src/tests/pages/variety-management.test.ts`: mock `chefListVarieties` to return two varieties (one active, one inactive, one with empty imageKey); assert both appear in the DOM with correct names and status badges; assert inactive variety has visual distinction class; assert variety with empty imageKey renders a placeholder element; mock 403 and assert access-denied message renders; mock empty response and assert empty-state renders

**Checkpoint**: US1 fully functional — chef sees all varieties at `#/varieties`; non-chef sees access-denied message

---

## Phase 4: User Story 2 — Edit Variety Properties (Priority: P2)

**Goal**: Chef clicks a variety in the list to open an inline edit panel. Chef edits name, description, imageKey, bottleYieldMl, or active toggle and saves. Changes persist and are immediately reflected in the variety list. Validation errors and save failures show inline error messages; the form stays open with all edits intact.

**Independent Test**: Run `uv run pytest tests/unit/handlers/test_chef_update_variety.py -v`, then edit a seeded variety in the browser — changes appear in the list; toggling active=false removes the variety from the public customer listing.

> **⚠️ Write tests first. Run them. Confirm they FAIL. Then implement.**

### Tests — User Story 2

- [X] T012 [P] [US2] Write unit tests for `backend/src/handlers/chef_update_variety.py` in `backend/tests/unit/handlers/test_chef_update_variety.py`: (a) chef updates name → 200 with updated name; (b) chef updates `active: false` → 200 with `active: false`; (c) chef updates `bottleYieldMl` → 200 with new value; (d) non-chef → 403; (e) variety not found → 404 `VARIETY_NOT_FOUND`; (f) blank name → 400 `VALIDATION_ERROR` on field `name`; (g) `bottleYieldMl: 0` → 400 `VALIDATION_ERROR` on field `bottleYieldMl`; (h) `bottleYieldMl: -5` → 400; (i) update with no `ingredients` key preserves existing ingredients unchanged
- [X] T013 [P] [US2] Add PUT /api/v1/chef/varieties/{id} contract test to `backend/tests/contract/test_chef_varieties.py`: verify 200 response schema is `{"variety": ChefVarietyDetail}`; verify 404 schema is `{"code": "VARIETY_NOT_FOUND", "message": "..."}`; verify 400 schema includes `field`
- [X] T014 [US2] Add integration test "chef edits variety, deactivating removes it from public listing" to `backend/tests/integration/test_variety_management.py`: (a) update active variety to `active=false`, call public `list_varieties` handler, assert variety absent; (b) update inactive variety to `active=true`, call public handler, assert variety present
- [X] T015 [P] [US2] Write frontend unit tests for the edit panel in `frontend/src/tests/pages/variety-management.test.ts`: mock `chefUpdateVariety` to succeed and assert variety list re-renders with updated values; mock `chefUpdateVariety` to fail with a network error and assert the inline error appears, the form remains open, and all field values are preserved (not reset); assert no delete button is present in the edit panel (FR-010)

### Implementation — User Story 2

- [X] T016 [US2] Implement `backend/src/handlers/chef_update_variety.py`: `require_chef` gate; extract `{id}` from `event["pathParameters"]`; `get_item(varieties_table_name(), {"varietyId": id})` — raise 404 on `ItemNotFoundError`; merge provided fields onto existing item (name, description, imageKey, bottleYieldMl, active); validate: name non-empty if provided, bottleYieldMl > 0 if provided; process `ingredients` list if provided (see US3 for ingredient handling — scaffold the key with existing ingredients pass-through for now); `put_item` overwrite; return `{"variety": updated_dict}` with 200
- [X] T017 [US2] Implement inline edit panel in `frontend/src/pages/variety-management/index.ts`: clicking a variety row opens a detail panel (`data-testid="variety-detail"`) with form fields for name, description, imageKey, bottleYieldMl, and an active checkbox; no delete button is present; submit calls `chefUpdateVariety(id, payload)`; on success update the in-memory variety list and re-render; on `ApiRequestError` show inline error (`data-testid="detail-error"`) and keep the form open with all field values intact (do not reset inputs); on 403 in error show access-denied message; follow the same error and submit pattern as batch-management edit form

**Checkpoint**: US2 functional — edits persist, active toggle affects customer listing, errors shown inline with edits intact, no delete action present

---

## Phase 5: User Story 3 — Manage Variety Ingredients (Priority: P3)

**Goal**: Within the edit panel, chef sees all ingredients listed with name, quantity, unit, and category. Chef can add new ingredients, edit existing fields, and remove ingredients. The full updated ingredient list is saved atomically with the variety.

**Independent Test**: Add a new ingredient to any variety via the edit panel, save, refresh — ingredient persists with a system-assigned `ingredientId`. Edit its quantity, save, refresh — quantity updated. Remove it, save — ingredient gone.

> **⚠️ Write tests first. Run them. Confirm they FAIL. Then implement.**

### Tests — User Story 3

- [X] T018 [P] [US3] Add ingredient-specific unit tests to `backend/tests/unit/handlers/test_chef_update_variety.py`: (a) ingredient without `ingredientId` in request gets a new UUID assigned in response; (b) ingredient with existing `ingredientId` preserves that ID; (c) sending empty `ingredients: []` replaces the list with empty; (d) ingredient missing `name` → 400 `VALIDATION_ERROR` field `ingredients[0].name`; (e) ingredient `quantityPerBottle: 0` → 400; (f) ingredient missing `unit` → 400; (g) ingredient missing `category` → 400
- [X] T019 [US3] Add integration test "chef manages ingredients, batch ingredient calculations reflect changes" to `backend/tests/integration/test_variety_management.py`: (a) add ingredient to variety, assert it appears with a stable UUID in subsequent GET; (b) update ingredient quantity, assert updated value returned; (c) remove ingredient by omitting it from the list, assert it no longer appears
- [X] T020 [P] [US3] Write frontend unit tests for ingredient management in `frontend/src/tests/pages/variety-management.test.ts`: mock `chefUpdateVariety` with an ingredient payload and assert ingredient rows render with pre-filled values; assert clicking "Add Ingredient" appends a new empty row; assert clicking remove on an ingredient row removes it from the DOM; assert submit with an empty ingredient `name` field shows a per-field validation error and does not call `chefUpdateVariety`

### Implementation — User Story 3

- [X] T021 [US3] Extend `backend/src/handlers/chef_update_variety.py` ingredient processing: when `ingredients` key is present in request body, validate each item (name non-empty, quantityPerBottle > 0, unit non-empty, category non-empty — return 400 on first failure with field path); for each ingredient with an `ingredientId` preserve it; for each without assign `str(uuid.uuid4()).replace("-", "")`; replace variety's ingredient list with the processed list; (this extends the scaffold from T016)
- [X] T022 [US3] Implement ingredient management section in `frontend/src/pages/variety-management/index.ts` within the edit panel: render each existing ingredient as an editable row (name input, quantityPerBottle number input, unit input, category input, remove button); render an "Add Ingredient" row at the bottom with empty inputs and an "Add" button that appends a new ingredient row; on remove button click, show a confirm prompt then remove the row from DOM; on form submit, collect all ingredient rows (existing with their `ingredientId`, new without) and include in the `chefUpdateVariety` payload; inline validation: block submit if any ingredient row has empty name/unit/category or non-positive quantity with per-field error message

**Checkpoint**: US3 functional — full ingredient CRUD works end-to-end; stable ingredient IDs preserved across edits

---

## Phase 6: User Story 4 — Create a New Variety (Priority: P4)

**Goal**: Chef clicks "New Variety" to open a create form with all variety fields plus an ingredient management section. Submitting creates the variety with system-assigned IDs. The new variety appears at the top of the list.

**Independent Test**: Run `uv run pytest tests/unit/handlers/test_chef_create_variety.py tests/contract/test_chef_varieties.py -v`; create a variety in the browser — it appears in the list with all fields correct and a system-assigned `varietyId`.

> **⚠️ Write tests first. Run them. Confirm they FAIL. Then implement.**

### Tests — User Story 4

- [X] T023 [P] [US4] Write unit tests for `backend/src/handlers/chef_create_variety.py` in `backend/tests/unit/handlers/test_chef_create_variety.py`: (a) valid request returns 201 with a non-empty UUID `varietyId` and each ingredient gets a UUID `ingredientId`; (b) non-chef → 403; (c) blank name → 400 field `name`; (d) missing name key → 400; (e) `bottleYieldMl: 0` → 400 field `bottleYieldMl`; (f) `active` defaults to `true` when omitted; (g) `ingredients` defaults to `[]` when omitted; (h) ingredient with missing `name` → 400; (i) ingredient `quantityPerBottle: -1` → 400
- [X] T024 [P] [US4] Add POST /api/v1/chef/varieties contract test to `backend/tests/contract/test_chef_varieties.py`: verify 201 response schema `{"variety": ChefVarietyDetail}` with system-assigned `varietyId`; verify 400 schema includes `field`; verify 403 schema is `CHEF_ROLE_REQUIRED`
- [X] T025 [US4] Add integration test "chef creates new variety, appears in chef list" to `backend/tests/integration/test_variety_management.py`: call create handler as chef with valid payload including one ingredient; assert 201; assert `varietyId` is a non-empty string; call chef_list_varieties and assert the new variety appears with correct fields and ingredient with a stable UUID
- [X] T026 [P] [US4] Write frontend unit tests for the create form in `frontend/src/tests/pages/variety-management.test.ts`: mock `chefCreateVariety` to succeed and assert the new variety is prepended to the rendered list; mock `chefCreateVariety` to fail with a network error and assert inline error appears, form stays open, and all field values are preserved (not reset); assert that submitting with no ingredients shows a non-blocking warning but still calls `chefCreateVariety`; assert the Cancel button clears the detail panel

### Implementation — User Story 4

- [X] T027 [US4] Implement `backend/src/handlers/chef_create_variety.py`: `require_chef` gate; parse JSON body; validate name non-empty and bottleYieldMl > 0; validate each ingredient item (name, quantityPerBottle > 0, unit, category); assign `str(uuid.uuid4()).replace("-", "")` as `varietyId`; assign UUID per ingredient; set `active` default `True`, `description` default `""`, `imageKey` default `""`; `put_item(varieties_table_name(), item)`; return 201 `{"variety": item}`
- [X] T028 [US4] Implement "New Variety" create form in `frontend/src/pages/variety-management/index.ts`: add "New Variety" button (`data-testid="new-variety-btn"`) to the existing `.variety-management__header` element created in T010 — do not re-render the header; clicking opens the detail panel with empty create form containing name, description, imageKey, bottleYieldMl, active checkbox, and ingredient management section (same ingredient row pattern as T022/US3 — implement US3 first); submit calls `chefCreateVariety(payload)`; on success prepend new variety to in-memory list and re-render; show a non-blocking empty-ingredient-list warning if no ingredients are added; on save failure show inline error and keep form open with all field values intact (do not reset inputs); add Cancel button that clears the detail panel

**Checkpoint**: US4 functional — chef creates a variety with or without ingredients; variety appears in list immediately; form retains values on failure

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Accessibility audit, performance compliance, linter verification, coverage confirmation, and test completeness.

- [X] T029 [P] Audit WCAG 2.1 AA compliance in `frontend/src/pages/variety-management/index.ts`: confirm every `<input>` has an associated `<label>` or `aria-label`; every status badge has `aria-label`; error message containers have `role="alert"`; list regions have `aria-label` and `aria-live="polite"`; all buttons have descriptive text; keyboard navigation works (Enter/Space on variety rows, focus management on form open)
- [X] T030 [P] Run linter and type-checker: `uv run ruff check backend/src/handlers/chef_list_varieties.py backend/src/handlers/chef_create_variety.py backend/src/handlers/chef_update_variety.py` — fix any warnings to zero; run `pnpm tsc --noEmit` in `frontend/` — fix any type errors in `api.ts`, `main.ts`, `variety-management/index.ts`
- [X] T031 [P] Verify backend test coverage: run `uv run pytest tests/unit/handlers/test_chef_list_varieties.py tests/unit/handlers/test_chef_create_variety.py tests/unit/handlers/test_chef_update_variety.py --cov=src/handlers/chef_list_varieties --cov=src/handlers/chef_create_variety --cov=src/handlers/chef_update_variety --cov-fail-under=80` in `backend/` — coverage must be ≥ 80% for each new handler module
- [X] T032 [P] Verify performance compliance per constitution Principle IV: (a) in `backend/tests/unit/handlers/test_chef_list_varieties.py` add a benchmark case that calls the handler with a mocked DynamoDB response of 20 varieties (each with 5 ingredients), measures wall-clock time with `time.perf_counter()`, and asserts completion in ≤ 200 ms; (b) check `.github/workflows/` (or equivalent CI config) for an existing performance benchmark step — if one exists, confirm it covers the new handler; if none exists, add a step that runs `uv run pytest -k benchmark` and document the gap as a follow-up in `specs/005-variety-management/plan.md` under a new "Performance Benchmark Gap" note; (c) manually verify page TTI ≤ 3 s by opening `#/varieties` in browser DevTools Performance tab with network throttled to Fast 3G
- [X] T033 Validate the full quickstart.md flow per `specs/005-variety-management/quickstart.md`: run backend unit + contract tests (`uv run pytest tests/unit tests/contract -v`); run frontend unit tests (`pnpm test` in `frontend/`); confirm all pass with no failures; verify `#/varieties` route works end-to-end in the dev browser at the scenarios described in the quickstart

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — T001, T002, T003 can start simultaneously; T004 depends on T001 and T003
- **Foundational (Phase 2)**: Can start alongside Phase 1; BLOCKS end-to-end integration but not unit tests
- **User Stories (Phase 3–6)**: All depend on Phase 1 completion; Phase 2 (infra) needed only for integration tests and deployed environments
  - Stories proceed in priority order (US1 → US2 → US3 → US4) by a solo implementer
  - Or in parallel by a team once Phase 1 and 2 are done
- **Polish (Phase 7)**: Depends on all desired user stories complete

### User Story Dependencies

- **US1 (P1)**: Depends on Phase 1 setup only — no dependency on US2/US3/US4
- **US2 (P2)**: Depends on Phase 1; the edit panel renders within the list view from US1, so US1 should be complete first
- **US3 (P3)**: Extends the `chef_update_variety` handler scaffolded in US2; US2 must be complete
- **US4 (P4)**: Backend handler (T027) depends on Phase 1 only; frontend create form (T028) depends on US3 frontend (T022) for the ingredient row pattern — implement US3 first

### Within Each User Story

1. Write failing tests (all [P] test tasks can run concurrently)
2. Confirm tests FAIL (red)
3. Implement handler / page logic
4. Confirm tests PASS (green)
5. Refactor if needed

---

## Parallel Opportunities

### Phase 1 (Setup)

```
T001 + T002 + T003 run in parallel (different files, no dependencies)
T004 depends on T001 (page stub must exist to import) and T003 (API types needed)
```

### Phase 3 (US1)

```
Parallel: T006 (unit tests) + T007 (contract test)
Then: T008 (integration test)
Then: T009 (handler implementation)
Parallel: T010 (frontend) + T011 (frontend tests) — after T009
```

### Phase 4 (US2)

```
Parallel: T012 (backend unit tests) + T013 (contract test) + T015 (frontend unit tests)
Then: T014 (integration test)
Then: T016 (handler) → T017 (frontend)
```

### Phase 5 (US3)

```
Parallel: T018 (ingredient unit tests) + T020 (frontend unit tests)
Then: T019 (integration test)
Then: T021 (extend handler) → T022 (frontend)
```

### Phase 6 (US4)

```
Parallel: T023 (backend unit tests) + T024 (contract test) + T026 (frontend unit tests)
Then: T025 (integration test)
Parallel: T027 (backend handler) + T028 (frontend create form) — different files
```

### Phase 7 (Polish)

```
T029 + T030 + T031 + T032 run in parallel
T033 runs last (validates everything)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T004)
2. Complete Phase 3: US1 tests (T006–T008), then US1 implementation (T009–T011)
3. **STOP and VALIDATE**: navigate to `#/varieties` as chef — see all varieties
4. Deploy if ready

### Incremental Delivery

1. Phase 1 + Phase 3 → Chef can browse all varieties (MVP)
2. Phase 4 → Chef can edit variety properties (activate/deactivate)
3. Phase 5 → Chef can manage ingredient recipes
4. Phase 6 → Chef can create new varieties
5. Phase 7 → Polish, performance compliance, and harden

### Single-Developer Sequence

```
T001 → T002 → T003 → T004 (setup complete)
T005 (infra — apply to dev env)
T006 → T007 → T008 → T009 → T010 → T011 (US1 done ✓)
T012 → T013 → T014 → T015 → T016 → T017 (US2 done ✓)
T018 → T019 → T020 → T021 → T022 (US3 done ✓)
T023 → T024 → T025 → T026 → T027 → T028 (US4 done ✓)
T029 → T030 → T031 → T032 → T033 (polish done ✓)
```

---

## Notes

- `[P]` tasks touch different files — safe to run simultaneously
- `[Story]` label traces each task to the spec user story for review
- The constitution mandates ≥80% unit test coverage on all new handler modules — T031 enforces this
- The constitution mandates WCAG 2.1 AA — T029 enforces this
- The constitution mandates CI performance benchmarks on critical paths — T032 enforces this
- Ingredient handling in `chef_update_variety` is scaffolded in T016 (pass-through) and fully implemented in T021 — this is intentional so US2 can be independently validated before US3 is done
- US4 frontend (T028) reuses the ingredient row pattern from US3 (T022) — implement US3 before starting T028
- Commit after each checkpoint to keep the branch history clean and reviewable
