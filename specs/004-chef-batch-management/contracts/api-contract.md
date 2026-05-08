# API Contract: Chef Batch Management

**Feature**: 004-chef-batch-management
**Date**: 2026-05-07
**Base URL**: `https://api.{domain}` (e.g., `https://api.coquito.gcardona.me`)
**Protocol**: HTTPS only (TLS 1.2 minimum)
**Auth**: Cookie-based JWT (same as all existing protected routes). Chef-only endpoints additionally return `403` when the authenticated user does not have the `chef` role.

> **Note**: This contract documents only the **new endpoints** added by this feature.
> Existing endpoints are unchanged and documented in `specs/003-aws-website-storage/contracts/api-contract.md`.

---

## Current User

### GET /api/v1/me

Return the identity and role of the currently authenticated user.
Reads from the Lambda authorizer context — no DynamoDB access.

**Auth**: Protected (any authenticated role)

**Response 200**:
```json
{
  "userId": "a1b2c3d4-...",
  "role": "chef",
  "email": "chef@example.com"
}
```

**Response 401**: Session expired or missing.

---

## Batches — Chef Operations

### GET /api/v1/batches

List all batches. Returns every batch regardless of status, sorted by `createdAt` descending.
Includes `activeRequestCount` (non-cancelled requests) per batch for use in the OPEN→CLOSED confirmation dialog.

**Auth**: Protected — chef role required

**Response 200**:
```json
{
  "batches": [
    {
      "batchId": "batch-2026-holiday",
      "batchName": "Holiday 2026",
      "cutoffDate": "2026-11-15",
      "maxBottleVolumeMl": 1000,
      "status": "OPEN",
      "availableVarietyIds": ["classic", "chocolate"],
      "activeRequestCount": 7,
      "createdAt": "2026-05-01T12:00:00Z"
    }
  ]
}
```

**Response 403**: `{ "code": "CHEF_ROLE_REQUIRED", "message": "This endpoint is restricted to chefs." }`

---

### POST /api/v1/batches

Create a new batch. The system assigns a `batchId` (UUID v4) and sets `status` to `OPEN`.

**Auth**: Protected — chef role required

**Request body**:
```json
{
  "batchName": "Holiday 2026",
  "cutoffDate": "2026-11-15",
  "maxBottleVolumeMl": 1000,
  "availableVarietyIds": ["classic", "chocolate"]
}
```

**Validation rules**:
- `batchName`: required; non-empty; must be unique (case-insensitive) across all existing batches
- `cutoffDate`: required; valid YYYY-MM-DD; must be ≥ today
- `maxBottleVolumeMl`: required; positive integer (> 0)
- `availableVarietyIds`: required; non-empty list; each ID must exist as an active variety

**Response 201**:
```json
{
  "batchId": "<uuid>",
  "batchName": "Holiday 2026",
  "cutoffDate": "2026-11-15",
  "maxBottleVolumeMl": 1000,
  "availableVarietyIds": ["classic", "chocolate"],
  "status": "OPEN",
  "activeRequestCount": 0,
  "createdAt": "2026-05-07T00:00:00Z"
}
```

**Response 400**:
```json
{ "code": "VALIDATION_ERROR", "message": "<specific field and reason>" }
```
```json
{ "code": "BATCH_NAME_CONFLICT", "message": "A batch named 'Holiday 2026' already exists." }
```
```json
{ "code": "CUTOFF_DATE_IN_PAST", "message": "cutoffDate must be today or a future date." }
```
```json
{ "code": "VARIETY_NOT_ACTIVE", "message": "Variety '{id}' is not active and cannot be added to a batch." }
```

**Response 403**: `{ "code": "CHEF_ROLE_REQUIRED", "message": "This endpoint is restricted to chefs." }`

---

### PUT /api/v1/batches/{id}

Update editable properties of an existing batch. Only allowed when `status` is `OPEN` or `CLOSED`.
COMPLETED batches return `409`. Status is not updated by this endpoint — use `PUT /api/v1/batches/{id}/status`.

**Auth**: Protected — chef role required

**Path parameter**: `id` — the `batchId`

**Request body** (all fields optional; omitted fields are unchanged):
```json
{
  "batchName": "Holiday 2026 Updated",
  "cutoffDate": "2026-11-20",
  "maxBottleVolumeMl": 750,
  "availableVarietyIds": ["classic"]
}
```

**Validation rules**: Same as `POST /api/v1/batches` for each provided field.
When updating `batchName`, uniqueness check excludes the batch being updated.

**Response 200**: Full batch object (same shape as POST 201 response).

**Response 400**: Same error codes as POST, plus:
```json
{ "code": "VALIDATION_ERROR", "message": "<specific field and reason>" }
```

**Response 403**: `{ "code": "CHEF_ROLE_REQUIRED", "message": "This endpoint is restricted to chefs." }`

**Response 404**: `{ "code": "BATCH_NOT_FOUND", "message": "Batch '{id}' not found." }`

**Response 409**: `{ "code": "BATCH_COMPLETED", "message": "Completed batches cannot be edited." }`

---

### PUT /api/v1/batches/{id}/status

Transition a batch status forward. Allowed transitions: `OPEN → CLOSED`, `CLOSED → COMPLETED`.
All other transitions return `400 INVALID_STATUS_TRANSITION`.

**Auth**: Protected — chef role required

**Path parameter**: `id` — the `batchId`

**Request body**:
```json
{ "status": "CLOSED" }
```

**Response 200**: Full batch object with updated status.

**Response 400**:
```json
{ "code": "INVALID_STATUS_TRANSITION", "message": "Cannot transition from COMPLETED to OPEN." }
```

**Response 403**: `{ "code": "CHEF_ROLE_REQUIRED", "message": "This endpoint is restricted to chefs." }`

**Response 404**: `{ "code": "BATCH_NOT_FOUND", "message": "Batch '{id}' not found." }`

---

## Error Response Format

All error responses use the existing project-wide format:
```json
{
  "code": "ERROR_CODE",
  "message": "Human-readable description of the error and what to do next."
}
```

## New HTTP Status Codes (additions to existing table)

| Code | Meaning |
|---|---|
| 403 | Authenticated but insufficient role (chef required) |
| 409 | Conflict — operation not permitted on resource in current state |

---

## Infrastructure Changes

Five new Lambda functions are added to `infra/terraform/modules/api/main.tf`, each following
the existing pattern (arm64, python3.12, `$default` stage, Lambda authorizer on all routes):

| Function name | Route | Method |
|---|---|---|
| `coquito-get-me` | `/api/v1/me` | GET |
| `coquito-list-batches` | `/api/v1/batches` | GET |
| `coquito-create-batch` | `/api/v1/batches` | POST |
| `coquito-update-batch` | `/api/v1/batches/{id}` | PUT |
| `coquito-update-batch-status` | `/api/v1/batches/{id}/status` | PUT |

One additional Lambda (`coquito-close-expired-batches`) is triggered by EventBridge Scheduler
(daily at 00:05 UTC) — no API Gateway route.
