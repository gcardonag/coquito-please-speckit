# API Contract: Varieties

**Base path**: `/api/v1/varieties`

---

## GET /api/v1/varieties

**Lambda**: `list_varieties`
**Description**: List all active coquito varieties. Used to populate the request form
dropdown. No authentication required.

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `batchId` | string | No | If provided, filters to varieties available in that batch |

### Response: 200 OK

```json
{
  "varieties": [
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
| 404 | `BATCH_NOT_FOUND` | `batchId` provided but does not exist |
