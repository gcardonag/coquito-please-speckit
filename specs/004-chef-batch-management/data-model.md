# Data Model: Chef Batch Management

**Feature**: 004-chef-batch-management
**Date**: 2026-05-07

---

## Summary

No DynamoDB schema changes are required. All new read and write operations use the existing
`coquito-batches-{environment}`, `coquito-requests-{environment}`, and
`coquito-varieties-{environment}` tables with their current attribute sets. The sections
below document the access patterns added by this feature and any new derived fields
surfaced in API responses.

---

## Existing Table: `coquito-batches-{environment}`

No attribute changes. Used by all new batch management handlers.

**Existing attributes** (unchanged):

| Attribute | Type | Description |
|---|---|---|
| `batchId` | String (PK) | UUID — system-generated on create |
| `batchName` | String | Human-readable name; enforced unique (case-insensitive) by handler |
| `cutoffDate` | String | Order cutoff date (YYYY-MM-DD) |
| `maxBottleVolumeMl` | Number | Maximum allowed bottle size in ml |
| `availableVarietyIds` | List\<String\> | Variety identifiers selectable in this batch |
| `status` | String | `OPEN` \| `CLOSED` \| `COMPLETED` |
| `createdAt` | String | ISO 8601 creation timestamp |
| `acquiredIngredients` | Map | `ingredientId` → Boolean (unchanged; managed by existing `mark_ingredient_acquired` handler) |

**New access patterns** (added by this feature):

| Pattern | Operation | Handler |
|---|---|---|
| List all batches | `scan_table` | `list_batches` |
| Create a batch | `put_item` | `create_batch` |
| Update batch properties | `update_item` (conditional: status ≠ COMPLETED) | `update_batch` |
| Transition batch status | `update_item` (conditional: forward-only) | `update_batch_status` |
| Close expired batches | `update_item` (status OPEN → CLOSED) | `close_expired_batches` |

**Validation rules** (enforced in handlers):

- `batchName`: required, non-empty string, unique across all batches (case-insensitive Scan check)
- `cutoffDate`: required, valid ISO 8601 date (YYYY-MM-DD), must be ≥ today on create; can be any future date on update while batch is OPEN
- `maxBottleVolumeMl`: required, positive integer (> 0)
- `availableVarietyIds`: required, non-empty list; each entry must match an `active = true` variety in `coquito-varieties-{environment}`
- `status` transitions: `OPEN → CLOSED` and `CLOSED → COMPLETED` only; all others rejected with `400 INVALID_STATUS_TRANSITION`

---

## Existing Table: `coquito-requests-{environment}`

Read-only from this feature's perspective. Used only to derive `activeRequestCount`.

**Access pattern added**:

| Pattern | Operation | Handler |
|---|---|---|
| Count non-cancelled requests per batch | `scan_table` (filter: `batchId = X AND status <> CANCELLED`) | `list_batches` |

**Derived field** — `activeRequestCount` (computed, not stored):

The `list_batches` handler performs a single Scan of the requests table, groups the results by `batchId`, and counts records where `status ≠ CANCELLED`. This count is embedded in each batch entry in the `GET /api/v1/batches` response. It is never persisted.

---

## Existing Table: `coquito-varieties-{environment}`

Read-only from this feature's perspective. Used to validate `availableVarietyIds` on create/update and to return variety summaries for the selection UI.

**Access pattern added**:

| Pattern | Operation | Handler |
|---|---|---|
| Fetch active varieties for selection | `scan_table` (filter: `active = true`) | `create_batch`, `update_batch` |

---

## New `GET /api/v1/me` Response Shape

The `get_me` handler reads from the Lambda authorizer context only — no DynamoDB access.

```json
{
  "userId": "<Cognito sub>",
  "role": "chef | authorized-user",
  "email": "<email address>"
}
```

---

## Batch Status Lifecycle

```
           ┌─────────────────────────────────┐
           │  OPEN  (new batches start here)  │
           └──────────────┬──────────────────┘
                          │  manual (chef action) OR
                          │  automatic (cutoff date passed)
                          ▼
           ┌─────────────────────────────────┐
           │            CLOSED               │
           └──────────────┬──────────────────┘
                          │  manual (chef action only)
                          ▼
           ┌─────────────────────────────────┐
           │          COMPLETED              │
           │       (read-only; final)        │
           └─────────────────────────────────┘
```

- OPEN → CLOSED (manual): requires confirmation dialog on frontend (shows `activeRequestCount`)
- OPEN → CLOSED (automatic): triggered nightly by `close_expired_batches` Lambda; no frontend interaction
- CLOSED → COMPLETED (manual): no confirmation dialog; batch becomes immutable
- All reverse transitions rejected: `400 INVALID_STATUS_TRANSITION`

---

## `Batch` Model Extension

The existing `Batch` dataclass (`backend/src/models/batch.py`) is extended with one new class method:

```python
@classmethod
def name_exists(cls, batch_name: str, exclude_batch_id: str | None = None) -> bool:
    """
    Return True if any batch in the table has the given name (case-insensitive),
    optionally excluding the batch being updated.
    Used for uniqueness validation on create and update.
    """
```

No changes to stored attributes or `to_dict` / `from_dict`.
