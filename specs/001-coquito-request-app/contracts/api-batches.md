# API Contract: Batches

**Base path**: `/api/v1/batches`

---

## GET /api/v1/batches/{batchId}

**Lambda**: `get_batch_config`
**Description**: Retrieve batch configuration for the request form (cut-off date,
available varieties, bottle volume limit). No authentication required — used by the
requester form on load.

### Response: 200 OK

```json
{
  "batchId": "string",
  "batchName": "string",
  "cutoffDate": "string (YYYY-MM-DD)",
  "maxBottleVolumeMl": "number",
  "status": "OPEN | CLOSED | COMPLETED",
  "availableVarieties": [
    {
      "varietyId": "string",
      "name": "string",
      "description": "string",
      "imageUrl": "string (CloudFront URL)"
    }
  ]
}
```

### Error Responses

| Status | Code | Description |
|--------|------|-------------|
| 404 | `BATCH_NOT_FOUND` | `batchId` does not exist |

---

## GET /api/v1/batches/{batchId}/ingredients

**Lambda**: `get_ingredient_list`
**Auth**: `X-Cook-Secret` header required
**Description**: Returns the consolidated ingredient shopping list for all confirmed
requests in the batch. Computes aggregated quantities at query time.
Available before cut-off (returns a preview labeled as unfinalized).

### Response: 200 OK

```json
{
  "batchId": "string",
  "batchName": "string",
  "isFinalized": "boolean (true if cutoffDate has passed)",
  "totalConfirmedRequests": "number",
  "byVariety": [
    {
      "varietyId": "string",
      "varietyName": "string",
      "confirmedCount": "number",
      "ingredients": [
        {
          "ingredientId": "string",
          "name": "string",
          "totalQuantity": "number",
          "unit": "string",
          "category": "string",
          "acquired": "boolean"
        }
      ]
    }
  ],
  "totals": [
    {
      "name": "string",
      "totalQuantity": "number",
      "unit": "string",
      "category": "string"
    }
  ]
}
```

### Error Responses

| Status | Code | Description |
|--------|------|-------------|
| 401 | `UNAUTHORIZED` | Missing or invalid `X-Cook-Secret` header |
| 404 | `BATCH_NOT_FOUND` | `batchId` does not exist |

---

## PATCH /api/v1/batches/{batchId}/ingredients/{ingredientId}/acquired

**Lambda**: `mark_ingredient_acquired`
**Auth**: `X-Cook-Secret` header required
**Description**: Toggle the `acquired` flag on an ingredient in the shopping list.
Idempotent — marking an already-acquired ingredient as acquired returns 200.
`acquired` state is stored per-batch (not per-variety), keyed by `ingredientId`.

### Request Body

```json
{
  "acquired": "boolean"
}
```

### Response: 200 OK

```json
{
  "ingredientId": "string",
  "acquired": "boolean",
  "updatedAt": "string (ISO 8601)"
}
```

### Error Responses

| Status | Code | Description |
|--------|------|-------------|
| 401 | `UNAUTHORIZED` | Missing or invalid `X-Cook-Secret` header |
| 404 | `BATCH_NOT_FOUND` | `batchId` does not exist |
| 404 | `INGREDIENT_NOT_FOUND` | `ingredientId` not found in batch varieties |
