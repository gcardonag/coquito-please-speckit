# Research: Chef Variety Management

**Branch**: `005-variety-management` | **Date**: 2026-05-09

No external unknowns existed for this feature — the entire stack was fully legible from the codebase. Research consolidated findings from reading existing source files.

---

## Decision 1: API endpoint namespace

**Decision**: New chef variety endpoints live at `/api/v1/chef/varieties` (GET, POST) and `/api/v1/chef/varieties/{id}` (PUT).

**Rationale**: Keeps chef write operations clearly separated from the public `GET /api/v1/varieties` endpoint (which stays unchanged, returns active-only summary data without ingredients). A `/chef/` path segment makes the authorization intent self-documenting in API Gateway logs and IAM policies. All routes still sit behind the Lambda authorizer; chef role is enforced at the handler level via the existing `require_chef` helper in `src/handlers/_auth.py`.

**Alternatives considered**:
- Extend existing `GET /api/v1/varieties` with a `?includeInactive=true` query param — rejected because it couples a chef-only capability to a public endpoint, complicating the authorizer and handler.
- Use `PUT /api/v1/varieties/{id}` (no `/chef/` prefix) — rejected because it blurs the line between the public listing endpoint and chef management endpoints.

---

## Decision 2: Variety ID generation for new varieties

**Decision**: Use `uuid.uuid4().hex` (a 32-character hex string) as the `varietyId` for chef-created varieties.

**Rationale**: The existing seed data uses semantic slugs (`"classic"`, `"chocolate"`) but those are human-authored. Chef-created varieties must have guaranteed-unique IDs without manual slug entry. `uuid4().hex` matches the pattern already used for `requestId` and `batchId` in this codebase and avoids collisions.

**Alternatives considered**:
- Slugify the variety name — rejected because the spec explicitly allows duplicate names, making slug uniqueness unenforceable.
- Sequential integer IDs — rejected because the DynamoDB schema uses string partition keys and there is no auto-increment mechanism.

---

## Decision 3: Ingredient ID generation and update strategy

**Decision**: On variety creation and on variety update (for any ingredient that arrives without an `ingredientId`), assign a new `uuid.uuid4().hex`. On update, ingredients that supply an existing `ingredientId` retain it; ingredients without one are treated as newly added.

**Rationale**: The clarification session confirmed ingredient identity is system-assigned and not visible to the chef. UUID-per-ingredient preserves stable references if future features ever cross-reference ingredient IDs (e.g., acquired-ingredient tracking in batches). On the update path, the caller sends the full ingredient list; the handler assigns IDs to any element missing one.

**Alternatives considered**:
- Always regenerate all ingredient IDs on update — rejected because it would break any external reference that uses `ingredientId` as a stable key.

---

## Decision 4: DynamoDB write strategy for updates

**Decision**: `put_item` (unconditional overwrite of the full variety item) for the update handler.

**Rationale**: The spec specifies last-write-wins with no optimistic locking. Ingredients are embedded in the variety document, so a partial `update_item` expression would require complex SET/REMOVE expressions for the ingredient list. A full `put_item` is simpler, correct, and consistent with the spec's stated concurrency model. The `varieties_table_name()` helper already used by `list_varieties` supplies the table name.

**Alternatives considered**:
- `update_item` with attribute-level expressions — rejected because the ingredient list is a variable-length embedded list; managing it atomically with DynamoDB expressions is error-prone without meaningful benefit here.
- Conditional write with a version counter — rejected; the spec explicitly states no locking is required for v1.

---

## Decision 5: Chef variety list response shape

**Decision**: `GET /api/v1/chef/varieties` returns ALL varieties (active and inactive) with the full ingredient list per variety — contrast with the public `GET /api/v1/varieties` which returns only active varieties with no ingredients and an `imageUrl` (resolved CloudFront URL) instead of `imageKey`.

**Rationale**: Chefs need to see inactive varieties to manage them, and need ingredients to verify recipe correctness. The public endpoint intentionally omits this data for customers. Returning `imageKey` (the raw S3 key) rather than `imageUrl` in the chef endpoint allows the chef to read and edit the stored value; the CloudFront URL derivation is a display concern.

**Alternatives considered**:
- Reuse existing `list_varieties` with a chef flag — rejected (see Decision 1).
- Return `imageUrl` instead of `imageKey` in the chef endpoint — rejected because chefs need the raw key to display and edit it; URL construction from key can happen in the frontend if needed.

---

## Decision 6: Frontend page mount and routing

**Decision**: New page at `frontend/src/pages/variety-management/index.ts` exporting `mountVarietyManagement(container)`. Route `#/varieties` added to the router array in `main.ts`. Chef-only access check follows the existing pattern: catch a 403 from the first API call and display an inline "Access denied" message.

**Rationale**: Identical to the batch-management page pattern — the router does not enforce chef role; the API does. This keeps routing logic thin and consistent.

**Alternatives considered**:
- Route-level chef check before mounting (read `currentUser.role`) — rejected because `currentUser` is set asynchronously and the page is already mounted before the API call resolves; the existing pattern is simpler and correct.
