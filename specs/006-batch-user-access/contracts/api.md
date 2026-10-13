# API Contracts: Batch User Access Management (006)

All endpoints are served at `api.{domain}/api/v1`. Authentication is via httpOnly cookie (JWT) validated by the existing Lambda authorizer. Chef role is enforced at the Lambda handler level via `require_chef()`.

---

## Modified: `POST /api/v1/users`

**Authorization**: Chef role required  
**Summary**: Create a new Cognito user and add them to the `authorized-user` group. Extended from the existing contract to require `firstName`.

### Request

```json
{
  "email": "jane.doe@example.com",
  "firstName": "Jane",
  "lastName": "Doe"
}
```

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `email` | string | Yes | Valid email format; must be unique in Cognito |
| `firstName` | string | Yes | Non-empty after trimming |
| `lastName` | string | No | Optional; stored as Cognito `family_name` |

### Responses

**201 Created**

```json
{
  "userId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "email": "jane.doe@example.com"
}
```

**400 Bad Request** — missing or invalid fields

```json
{ "code": "VALIDATION_ERROR", "message": "First name is required" }
```

**403 Forbidden** — caller is not a chef

```json
{ "code": "FORBIDDEN", "message": "Chef access required" }
```

**409 Conflict** — email already in use

```json
{ "code": "USER_EXISTS", "message": "A user with that email already exists" }
```

**503 Service Unavailable** — Cognito error

```json
{ "code": "COGNITO_ERROR", "message": "Failed to create user" }
```

---

## New: `GET /api/v1/chef/users`

**Authorization**: Chef role required  
**Summary**: Search Cognito users by email prefix. Used to find existing users before granting batch access.

### Query Parameters

| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| `query` | string | Yes | Prefix matched against `email`; minimum 1 character |

### Responses

**200 OK**

```json
{
  "users": [
    {
      "userId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "email": "jane.doe@example.com",
      "firstName": "Jane",
      "lastName": "Doe"
    }
  ]
}
```

Maximum 20 results returned. `lastName` may be absent if not set on the user.

**400 Bad Request** — missing `query` parameter

```json
{ "code": "VALIDATION_ERROR", "message": "query parameter is required" }
```

**403 Forbidden**

```json
{ "code": "FORBIDDEN", "message": "Chef access required" }
```

---

## New: `GET /api/v1/chef/batches/{id}/access`

**Authorization**: Chef role required  
**Summary**: List all users currently granted access to a batch.

### Path Parameters

| Parameter | Notes |
|-----------|-------|
| `id` | Batch ID |

### Responses

**200 OK**

```json
{
  "batchId": "batch-2026-001",
  "users": [
    {
      "userId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "email": "jane.doe@example.com",
      "firstName": "Jane",
      "lastName": "Doe",
      "grantedAt": "2026-05-23T18:00:00Z"
    }
  ]
}
```

`users` is an empty array when no access grants exist. `lastName` may be absent.

**403 Forbidden**

```json
{ "code": "FORBIDDEN", "message": "Chef access required" }
```

**404 Not Found** — batch does not exist

```json
{ "code": "NOT_FOUND", "message": "Batch not found" }
```

---

## New: `PUT /api/v1/chef/batches/{id}/access/{userId}`

**Authorization**: Chef role required  
**Summary**: Grant a Cognito user access to a batch. The batch must be OPEN.

### Path Parameters

| Parameter | Notes |
|-----------|-------|
| `id` | Batch ID |
| `userId` | Cognito `sub` UUID of the user to grant access to |

### Request Body

None required.

### Responses

**200 OK**

```json
{
  "batchId": "batch-2026-001",
  "userId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "grantedAt": "2026-05-23T18:00:00Z"
}
```

**403 Forbidden** — non-chef caller or batch is not OPEN

```json
{ "code": "FORBIDDEN", "message": "Access grants are only permitted on open batches" }
```

**404 Not Found** — batch or user does not exist

```json
{ "code": "NOT_FOUND", "message": "Batch not found" }
```

or

```json
{ "code": "NOT_FOUND", "message": "User not found" }
```

**409 Conflict** — user already has access to this batch

```json
{ "code": "ALREADY_GRANTED", "message": "This user already has access to the batch" }
```

---

## New: `DELETE /api/v1/chef/batches/{id}/access/{userId}`

**Authorization**: Chef role required  
**Summary**: Revoke a user's access from a batch. The batch must be OPEN.

### Path Parameters

| Parameter | Notes |
|-----------|-------|
| `id` | Batch ID |
| `userId` | Cognito `sub` UUID of the user to revoke |

### Responses

**204 No Content** — access successfully revoked

**403 Forbidden** — non-chef caller or batch is not OPEN

```json
{ "code": "FORBIDDEN", "message": "Access revocation is only permitted on open batches" }
```

**404 Not Found** — batch does not exist or user does not have access

```json
{ "code": "NOT_FOUND", "message": "Batch not found" }
```

or

```json
{ "code": "NOT_FOUND", "message": "Access grant not found" }
```
