# Research: Chef Batch Management

**Feature**: 004-chef-batch-management
**Date**: 2026-05-07

---

## Decision 1: How to expose the current user's role to the frontend

**Decision**: Add a `GET /api/v1/me` endpoint that returns the authenticated user's role from the Lambda authorizer context.

**Rationale**: The `id_token` is stored as an `HttpOnly` cookie, making it unreadable by JavaScript. The authorizer already decodes the JWT and propagates `role`, `userId`, and `email` in the Lambda context on every request. A lightweight `/me` endpoint is the cleanest pattern to expose this information — one round-trip on startup, then cached in the SPA. This is consistent with the existing `apiFetch` wrapper in `main.ts` and requires no new auth mechanism.

**Alternatives considered**:
- Parse the id_token in the frontend: Rejected — `HttpOnly` makes the cookie unreadable from JS; this is intentional for security.
- Use a non-HttpOnly cookie for role: Rejected — introduces a separate token storage mechanism; diverges from the existing auth design.
- Store role in localStorage after auth callback: Rejected — the auth callback response does not currently include role, and modifying it adds coupling between the auth flow and role-based UI logic.

---

## Decision 2: DynamoDB access pattern for listing all batches

**Decision**: Use a full table Scan on `coquito-batches-{environment}` to return all batches.

**Rationale**: The expected dataset is fewer than 20 batches (single chef, seasonal production). At this scale, a Scan reads a single DynamoDB page and incurs negligible cost and latency. Adding a GSI for a list-all pattern at this scale would be overengineering with no measurable user benefit.

**Alternatives considered**:
- Add a GSI on a synthetic `entityType` attribute: Rejected — unnecessary operational overhead for <20 items.
- Paginate with `LastEvaluatedKey`: Accepted as a defensive pattern in the handler, but a single page is expected in practice.

---

## Decision 3: Active-request count for the OPEN→CLOSED confirmation dialog

**Decision**: Include `activeRequestCount` in the `GET /api/v1/batches` list response. The `list_batches` handler performs one Scan of the `coquito-requests-{environment}` table and groups counts by `batchId`, filtering for status ≠ `CANCELLED`.

**Rationale**: The frontend shows this count before the chef confirms closing a batch. Fetching it eagerly in the list response means no additional API call is needed at confirmation time — the data is already in memory. A requests Scan is consistent with the existing pattern used by `create_request` for idempotency checks.

**Alternatives considered**:
- Separate `GET /api/v1/batches/{id}/request-count` endpoint: Rejected — extra round-trip with no benefit; adds a new endpoint solely for one number already available from a Scan.
- Derive count lazily at confirmation time in the frontend: Rejected — requires either storing request data in the frontend or an extra API call at a user-action moment, adding latency to the confirmation flow.

---

## Decision 4: Batch name uniqueness enforcement

**Decision**: The `create_batch` and `update_batch` handlers enforce uniqueness by scanning the batches table for an existing record with the same `batchName` (case-insensitive comparison). If a match is found, the handler returns `400 BATCH_NAME_CONFLICT`.

**Rationale**: DynamoDB's partition key is `batchId` (a generated UUID), so name uniqueness cannot be enforced natively. A Scan-based check is sufficient and correct at this scale. Case-insensitive comparison prevents near-duplicate names ("Holiday 2026" vs "holiday 2026") that would confuse the chef.

**Alternatives considered**:
- Enforce uniqueness only in the frontend: Rejected — API-level enforcement is required to handle any future multi-client scenarios and prevents bypass.
- Add a GSI on `batchName`: Accepted as a future optimization if scale grows; deferred for now.

---

## Decision 5: Auto-close mechanism for OPEN batches past their cutoff date

**Decision**: A new Lambda handler (`close_expired_batches`) is triggered by an EventBridge Scheduler rule running daily at 00:05 UTC. It scans all OPEN batches, identifies those whose `cutoffDate` < today, and transitions them to CLOSED via `update_item`.

**Rationale**: EventBridge Scheduler is already used by `send_reminder` for scheduled invocations, so the pattern is established in this codebase. A daily nightly check at 00:05 UTC ensures batches are closed within 24 hours of their cutoff date passing, which is well within user expectations for a single-chef seasonal application. The Lambda runs in isolation and has no impact on user-facing latency.

**Alternatives considered**:
- Check cutoff on every `list_batches` call (lazy auto-close): Rejected — write operations on read paths are unexpected and complicate testing. A dedicated worker is cleaner.
- Use a per-batch EventBridge Scheduler rule (one rule per batch): Rejected — more complex Terraform and IAM management; unnecessary for a small number of batches.

---

## Decision 6: Chef-only route protection strategy

**Decision**: Two-layer enforcement:
1. **API Gateway (authorizer)**: All new batch management routes use `authorization_type = "CUSTOM"` with the existing Lambda authorizer — same as all other protected routes.
2. **Handler level**: Each new chef-only handler reads `role` from `event["requestContext"]["authorizer"]["lambda"]["role"]` and returns `403 CHEF_ROLE_REQUIRED` if the value is not `"chef"`. This is extracted to a shared `_require_chef(event)` helper in each handler file.

**Rationale**: Defense in depth. The authorizer gate ensures only authenticated users with a recognized role (`chef` or `authorized-user`) reach the Lambda. The handler-level check ensures `authorized-user` accounts cannot access chef operations even if the API Gateway configuration is ever changed accidentally.

**Alternatives considered**:
- Authorizer-only enforcement: Rejected — the authorizer currently allows both `chef` and `authorized-user` through; handler-level checks are needed for chef-specific operations.
- Separate API Gateway authorizer for chef routes: Rejected — adds infra complexity for no additional security benefit given the handler-level check already exists.

---

## Decision 7: Frontend chef navigation item

**Decision**: After the auth callback (in `main.ts` startup), call `GET /api/v1/me` once. Cache the result in a module-level `currentUser` variable. The `renderLogoutButton` function is extended (or a new `renderChefNav` function added) to inject a "Manage Batches" nav link only when `currentUser.role === 'chef'`. The link navigates to `#/batches`.

**Rationale**: Reuses the existing startup flow (`handleAuthCallback().then(...)`) without adding a new abstraction. The cached `currentUser` is available synchronously to any subsequent route render functions that may need role gating.

**Alternatives considered**:
- Show the link to all users and redirect non-chefs on access: Rejected — the spec explicitly requires the link to be hidden from non-chefs; showing a link that silently redirects is a poor UX pattern.
- Dedicated `user.ts` service module: Accepted as a future refactor if more role-based UI decisions are added; deferred for now to keep scope minimal.
