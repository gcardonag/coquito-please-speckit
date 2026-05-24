# Research: Batch User Access Management (006)

## Decision Log

---

### User Storage

**Decision**: Store users in the existing Cognito User Pool  
**Rationale**: Explicitly required by the project input. Users created for batch access are provisioned via `admin_create_user` (same flow as the existing `POST /api/v1/users` handler), added to the `authorized-user` Cognito group, and retrieved via `admin_list_users`. This keeps user identity in a single authoritative store and avoids a parallel user table in DynamoDB.  
**Alternatives considered**:  
- Separate DynamoDB user table: rejected — adds a second source of truth for user identity, conflicts with existing Cognito-based auth flow.

---

### Batch Access Storage

**Decision**: New DynamoDB table `coquito-batch-access-{env}` with composite key `batchId` (PK) + `userId` (SK)  
**Rationale**: Batch access is batch-specific (not app-global like the `authorized-user` Cognito group). DynamoDB is the existing data store for all batch-related state. A dedicated table with a composite key enables efficient per-batch queries and O(1) grant/revoke operations. User display attributes (`email`, `firstName`, `lastName`) are denormalized into the access item to avoid N+1 Cognito calls when listing access for a batch.  
**Alternatives considered**:  
- Cognito group per batch (e.g. `batch-{batchId}`): rejected — requires dynamic group creation in Cognito (complex IAM), group names have character restrictions, and there is no clean deletion path.
- `authorizedUsers` list on the batch DynamoDB item: rejected — list attributes on DynamoDB items cannot be queried efficiently; large batches would bloat the batch record; no conditional write guarantees for concurrent grants.

---

### User Name Attributes

**Decision**: Store `given_name` and `family_name` as Cognito user attributes on `admin_create_user`; also denormalize into the batch-access DynamoDB item at grant time  
**Rationale**: Cognito standard attributes `given_name` and `family_name` align with the spec's first/last name requirement. Denormalization into DynamoDB means listing batch access users does not require a Cognito call per row.  
**Trade-off**: If a user's name changes in Cognito after a batch access grant is created, the DynamoDB copy is stale. This is an acceptable trade-off given name changes are rare and the impact (display name mismatch) is low-severity.

---

### User Search

**Decision**: Cognito `list_users` with a server-side filter on `email` attribute prefix; result cap of 20  
**Rationale**: Cognito supports prefix filters (`email ^= 'query'`) via `list_users`. A single email-prefix search covers the primary lookup path (chef knows the user's email). Limiting to 20 results is consistent with Cognito's 60-result default page and avoids UI overload.  
**Alternatives considered**:  
- Dual filter (email + given_name in parallel): Cognito does not support OR filters; two separate API calls would be needed and results merged client-side. Deferred to avoid complexity; email search is sufficient for MVP.
- Full DynamoDB user table with scan: rejected — violates "use existing Cognito User Pool" requirement.

---

### Feature Location (Frontend)

**Decision**: Manage Access panel lives in the **batch management page** (`#/batches`) detail view, not the variety management page (`#/varieties`)  
**Rationale**: Access grants are batch-specific. The batch management page is the only place in the existing UI that provides batch context (the selected batch ID). The variety management page is a global variety catalogue with no batch scope. Adding a batch selector to the variety page would duplicate batch-selection UI already present in batch management. The batch detail panel already hosts batch-specific controls (edit form, status changes) — the Manage Access section follows this pattern.  
**Alternatives considered**:  
- Add a batch picker to the variety management page: rejected — introduces redundant batch-selection state in a page that does not otherwise need it.

---

### Chef Role Enforcement

**Decision**: Reuse existing `require_chef()` helper from `backend/src/handlers/_auth.py` in all new Lambda handlers  
**Rationale**: The helper is the established pattern for chef-only endpoints (used in `create_user.py`, `create_batch.py`, etc.). No new mechanism needed.

---

### IAM Policy Extension

**Decision**: Add `cognito-idp:ListUsers` and `cognito-idp:AdminGetUser` to the existing `lambda_cognito` IAM policy  
**Rationale**: Search and grant-time user verification require these Cognito API calls. The existing policy already grants `AdminCreateUser` and `AdminAddUserToGroup`; extending it is additive and minimal.

---

### Existing `create_user` Handler

**Decision**: Modify `backend/src/handlers/create_user.py` to accept and persist `firstName` (required) and `lastName` (optional)  
**Rationale**: The existing handler only accepts `email`. The spec and input require users to have a first name. Modifying the existing handler preserves the route (`POST /api/v1/users`) and avoids a parallel endpoint.  
**Impact**: The existing contract test for `POST /api/v1/users` must be updated to include `firstName` in the request body.
