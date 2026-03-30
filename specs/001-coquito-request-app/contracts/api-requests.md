# API Contract: Requests

**Base path**: `/api/v1/requests`
**Auth**: Request-specific UUID in URL path (no auth header required for read/update).
Cook endpoints require `X-Cook-Secret` header matching the configured secret.

---

## POST /api/v1/requests

**Lambda**: `create_request`
**Description**: Create a new coquito request. Idempotent when called with the same
`idempotencyKey`; returns the existing request without creating a duplicate.

### Request Body

```json
{
  "idempotencyKey": "string (UUID v4, client-generated)",
  "requesterName": "string",
  "requesterEmail": "string (valid email)",
  "batchId": "string (UUID v4)",
  "varietyId": "string (UUID v4)",
  "pickupDate": "string (YYYY-MM-DD)",
  "pickupTime": "string (HH:MM, 24h)",
  "exchangeLocation": "string",
  "bottleProvided": "boolean",
  "bottleVolumeMl": "number | null (required if bottleProvided=true)",
  "costContribution": "boolean"
}
```

### Response: 201 Created

```json
{
  "requestId": "string (UUID v4)",
  "status": "CONFIRMED",
  "requesterName": "string",
  "variety": { "varietyId": "string", "name": "string" },
  "pickupDate": "string",
  "pickupTime": "string",
  "exchangeLocation": "string",
  "bottleProvided": "boolean",
  "bottleVolumeMl": "number | null",
  "costContribution": "boolean",
  "reminders": [{ "scheduledFor": "string", "status": "SCHEDULED" }],
  "createdAt": "string (ISO 8601)"
}
```

### Error Responses

| Status | Code | Description |
|--------|------|-------------|
| 400 | `VALIDATION_ERROR` | Missing required field or field fails validation |
| 400 | `BOTTLE_VOLUME_EXCEEDED` | `bottleVolumeMl` exceeds batch maximum |
| 400 | `BATCH_CLOSED` | Pickup date is past the batch cut-off |
| 404 | `BATCH_NOT_FOUND` | `batchId` does not exist |
| 404 | `VARIETY_NOT_FOUND` | `varietyId` does not exist or is inactive |
| 409 | `DUPLICATE_REQUEST` | Idempotency key already used for a different request body |

---

## GET /api/v1/requests/{requestId}

**Lambda**: `get_request`
**Description**: Retrieve a request by its UUID. No authentication — the UUID is the
access credential.

### Response: 200 OK

Same shape as POST 201 response above, plus:

```json
{
  "...": "...",
  "updatedAt": "string (ISO 8601)",
  "batch": {
    "batchId": "string",
    "batchName": "string",
    "cutoffDate": "string (YYYY-MM-DD)",
    "maxBottleVolumeMl": "number"
  },
  "editable": "boolean (false if cutoffDate has passed)"
}
```

### Error Responses

| Status | Code | Description |
|--------|------|-------------|
| 404 | `REQUEST_NOT_FOUND` | `requestId` does not exist |

---

## PUT /api/v1/requests/{requestId}

**Lambda**: `update_request`
**Description**: Update a request. Rejected if the batch cut-off date has passed.
Idempotent — sending the same payload twice returns the same result.

### Request Body

Same fields as POST, minus `idempotencyKey` and `batchId` (batch cannot change).

### Response: 200 OK

Same shape as GET 200 response.

### Error Responses

| Status | Code | Description |
|--------|------|-------------|
| 400 | `VALIDATION_ERROR` | Field fails validation |
| 400 | `BOTTLE_VOLUME_EXCEEDED` | `bottleVolumeMl` exceeds batch maximum |
| 403 | `CUTOFF_PASSED` | Batch cut-off date has passed; request is locked |
| 404 | `REQUEST_NOT_FOUND` | `requestId` does not exist |
| 409 | `REQUEST_CANCELLED` | Cannot update a cancelled request |

---

## DELETE /api/v1/requests/{requestId}

**Lambda**: `cancel_request`
**Description**: Cancel a request. Sets status to `CANCELLED` and cancels all scheduled
reminders. Rejected if the batch cut-off date has passed. Idempotent — cancelling an
already-cancelled request returns 200.

### Response: 200 OK

```json
{
  "requestId": "string",
  "status": "CANCELLED",
  "cancelledAt": "string (ISO 8601)"
}
```

### Error Responses

| Status | Code | Description |
|--------|------|-------------|
| 403 | `CUTOFF_PASSED` | Batch cut-off date has passed; cancellation not permitted |
| 404 | `REQUEST_NOT_FOUND` | `requestId` does not exist |
