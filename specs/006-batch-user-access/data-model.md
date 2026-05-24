# Data Model: Batch User Access Management (006)

## New: DynamoDB Table — `coquito-batch-access-{env}`

**Key schema**:

| Attribute | Type | Role |
|-----------|------|------|
| `batchId` | String | Partition Key |
| `userId` | String | Sort Key (Cognito `sub` UUID) |

**Item attributes**:

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `batchId` | String | Yes | FK → `coquito-batches-{env}.batchId` |
| `userId` | String | Yes | Cognito `sub` (UUID); stable user identifier |
| `email` | String | Yes | Denormalized from Cognito for display without N+1 calls |
| `firstName` | String | Yes | Denormalized from Cognito `given_name` |
| `lastName` | String | No | Denormalized from Cognito `family_name`; may be empty string |
| `grantedAt` | String | Yes | ISO 8601 UTC timestamp of when access was granted |

**Access patterns**:

| Operation | Pattern |
|-----------|---------|
| List all users for a batch | Query: `batchId = :batchId` |
| Check if a specific user has access | GetItem: `batchId = :id, userId = :uid` |
| Grant access | PutItem with condition `attribute_not_exists(userId)` |
| Revoke access | DeleteItem: `batchId = :id, userId = :uid` |

**Configuration**:
- Billing mode: PAY_PER_REQUEST (consistent with other project tables)
- Server-side encryption: AWS-managed key (consistent with other project tables)
- Deletion protection: enabled

---

## Modified: Cognito User Attributes

The existing `admin_create_user` call is extended to include standard Cognito attributes:

| Attribute | Cognito Name | Required | Notes |
|-----------|-------------|----------|-------|
| Email | `email` | Yes | Also the Cognito Username; unique |
| Email verified | `email_verified` | Yes | Always `"true"` (no verification email sent) |
| First name | `given_name` | Yes | New — required in this feature |
| Last name | `family_name` | No | New — optional |

---

## Frontend Types (new additions to `api.ts`)

```typescript
// A user returned from the user search or batch access list
export interface UserSummary {
  userId: string;      // Cognito sub (UUID)
  email: string;
  firstName: string;
  lastName?: string;
}

// A user in a batch access list, with grant metadata
export interface BatchAccessUser {
  userId: string;
  email: string;
  firstName: string;
  lastName?: string;
  grantedAt: string;
}

// Response when granting access
export interface BatchAccessGrant {
  batchId: string;
  userId: string;
  grantedAt: string;
}

// Payload for creating a new user
export interface CreateUserPayload {
  email: string;
  firstName: string;
  lastName?: string;
}

// Response from create user
export interface CreateUserResponse {
  userId: string;
  email: string;
}
```

---

## State Transitions

### Batch Access Grant Lifecycle

```
[No access]
     │  Chef calls PUT /chef/batches/{id}/access/{userId}
     ▼
[Access granted]  ← stored in coquito-batch-access-{env}
     │  Chef calls DELETE /chef/batches/{id}/access/{userId}
     ▼
[No access]      ← item deleted from coquito-batch-access-{env}
```

**Constraint**: Grant and revoke are only permitted when `batch.status == "OPEN"`. Attempts on CLOSED or COMPLETED batches return 403.

---

## Terraform Storage Module Changes

New output `batch_access_table_name` added to `infra/terraform/modules/storage/outputs.tf`.

New variable `dynamodb_batch_access_table` passed from `infra/terraform/main.tf` → `infra/terraform/modules/api/variables.tf` → Lambda environment variables for the four new handlers.
