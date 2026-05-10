# Data Model: Chef Variety Management

**Branch**: `005-variety-management` | **Date**: 2026-05-09

No schema changes to DynamoDB. The `coquito-varieties-{environment}` table already stores all fields required by this feature. The `Variety` and `Ingredient` Python dataclasses in `src/models/variety.py` are reused unchanged.

---

## Entities

### Variety

**Table**: `coquito-varieties-{environment}`  
**Partition key**: `varietyId` (string)  
**Sort key**: none

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `varietyId` | string | required, unique, system-assigned | `uuid4().hex` for chef-created; semantic slug for seed data |
| `name` | string | required, non-empty | Not unique — two varieties may share a name |
| `description` | string | required | May be empty string |
| `imageKey` | string | optional | S3 object key; empty string when not set |
| `bottleYieldMl` | number (int) | required, > 0 | Default 750 |
| `active` | boolean | required | `true` = visible to customers; `false` = hidden from public listing |
| `ingredients` | list\<Ingredient\> | required | May be empty list |

**State transitions**:

```
active=true  ──deactivate──►  active=false
active=false ──reactivate──►  active=true
```

No terminal state. No delete operation.

---

### Ingredient (embedded in Variety)

Stored as a list attribute within the Variety document — not a separate table.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `ingredientId` | string | required, unique within variety, system-assigned | `uuid4().hex`; stable across variety updates |
| `name` | string | required, non-empty | Display name; renaming does not change `ingredientId` |
| `quantityPerBottle` | number (float) | required, > 0 | Quantity of this ingredient per bottle of the variety |
| `unit` | string | required, non-empty | e.g., `"ml"`, `"g"`, `"oz"` |
| `category` | string | required, non-empty | e.g., `"dairy"`, `"spirit"`, `"flavoring"` |

**Ingredient identity rule**: On a `PUT /api/v1/chef/varieties/{id}` call, the caller sends the full replacement ingredient list. Any ingredient that includes an `ingredientId` retains that ID (update/retain). Any ingredient missing an `ingredientId` is treated as newly added and receives a new `uuid4().hex`.

---

## Validation Rules

Enforced at the handler layer (backend) before any DynamoDB write:

| Rule | Applied to |
|------|-----------|
| `name` must be a non-empty string after stripping whitespace | Variety (create + update) |
| `bottleYieldMl` must be an integer > 0 | Variety (create + update) |
| Each ingredient `name` must be non-empty | Ingredient (create + update) |
| Each ingredient `quantityPerBottle` must be a positive number | Ingredient (create + update) |
| Each ingredient `unit` must be non-empty | Ingredient (create + update) |
| Each ingredient `category` must be non-empty | Ingredient (create + update) |

Validation failure → HTTP 400 `{"code": "VALIDATION_ERROR", "message": "<field> <reason>", "field": "<fieldName>"}`.

---

## Relationship to Other Entities

- **Batch** (`coquito-batches-{env}`): stores `availableVarietyIds` — a list of `varietyId` strings. Deactivating a variety does **not** modify any batch; existing references remain. This is intentional (see spec Assumption: no retroactive batch update).
- **Request** (`coquito-requests-{env}`): stores `varietyId`. Same rule — deactivation does not affect existing requests.
- The `coquito-varieties-{env}` table is **read** by: `list_varieties`, `create_request`, `update_request`, `get_batch_config`, `get_ingredient_list`. None of those handlers are modified by this feature.
