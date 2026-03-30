# Data Model: Coquito Request App

**Branch**: `001-coquito-request-app` | **Date**: 2026-03-28
**Phase**: 1 — Design

## DynamoDB Tables

### Table: `coquito-requests`

Stores one item per coquito order.

**Primary Key**
- Partition key: `requestId` (String) — UUID v4

**Global Secondary Index: `RequesterEmailIndex`**
- Partition key: `requesterEmail` (String)
- Sort key: `pickupDate` (String, ISO 8601 date)
- Projection: ALL
- Used to look up all requests for a given requester

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `requestId` | String | ✅ | UUID v4, primary key |
| `requesterName` | String | ✅ | Display name |
| `requesterEmail` | String | ✅ | Used for confirmations and reminders |
| `batchId` | String | ✅ | FK to `coquito-batches.batchId` |
| `varietyId` | String | ✅ | FK to `coquito-varieties.varietyId` |
| `pickupDate` | String | ✅ | ISO 8601 date (YYYY-MM-DD) |
| `pickupTime` | String | ✅ | HH:MM (24h) |
| `exchangeLocation` | String | ✅ | Free text, requester-provided |
| `bottleProvided` | Boolean | ✅ | `true` = requester brings own bottle |
| `bottleVolumeMl` | Number | Conditional | Required if `bottleProvided = true`; ≤ batch `maxBottleVolumeMl` |
| `costContribution` | Boolean | ✅ | `true` = willing to contribute to cost |
| `status` | String | ✅ | Enum: `PENDING` \| `CONFIRMED` \| `CANCELLED` |
| `reminders` | List | ✅ | List of reminder objects (see below) |
| `createdAt` | String | ✅ | ISO 8601 datetime |
| `updatedAt` | String | ✅ | ISO 8601 datetime |

**Reminder object** (embedded in `reminders` list):

| Attribute | Type | Description |
|-----------|------|-------------|
| `reminderId` | String | UUID v4 |
| `scheduledFor` | String | ISO 8601 datetime when reminder fires |
| `schedulerArn` | String | EventBridge Scheduler ARN (for cancellation) |
| `status` | String | Enum: `SCHEDULED` \| `SENT` \| `CANCELLED` |

**Validation rules**:
- `bottleVolumeMl` MUST be ≤ `batch.maxBottleVolumeMl` when `bottleProvided = true`
- `pickupDate` MUST be a date after `batch.cutoffDate`
- `status` transitions: `PENDING` → `CONFIRMED` → `CANCELLED`; or `PENDING` → `CANCELLED`
- `requesterEmail` MUST be a valid email format

---

### Table: `coquito-batches`

Stores configuration for a production batch (a single cook run for a given date window).

**Primary Key**
- Partition key: `batchId` (String) — UUID v4

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `batchId` | String | ✅ | UUID v4, primary key |
| `batchName` | String | ✅ | Human-readable label (e.g., "Christmas 2026") |
| `cutoffDate` | String | ✅ | ISO 8601 date — no modifications allowed after this |
| `maxBottleVolumeMl` | Number | ✅ | Global maximum for requester-provided bottles (e.g., 750) |
| `availableVarietyIds` | List | ✅ | List of `varietyId` strings available for this batch |
| `status` | String | ✅ | Enum: `OPEN` \| `CLOSED` \| `COMPLETED` |
| `createdAt` | String | ✅ | ISO 8601 datetime |

**Validation rules**:
- `cutoffDate` MUST be before the earliest `pickupDate` in associated requests
- `status` transitions: `OPEN` → `CLOSED` (at cutoff) → `COMPLETED`

---

### Table: `coquito-varieties`

Stores coquito variety definitions and ingredient recipes. Pre-configured by the cook;
not modifiable by requesters.

**Primary Key**
- Partition key: `varietyId` (String) — UUID v4

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `varietyId` | String | ✅ | UUID v4, primary key |
| `name` | String | ✅ | Display name (e.g., "Classic", "Chocolate", "Piña") |
| `description` | String | ✅ | Short description shown in the request form |
| `imageKey` | String | ✅ | S3 object key for variety image |
| `ingredients` | List | ✅ | List of ingredient objects (see below) |
| `bottleYieldMl` | Number | ✅ | Volume produced per batch unit (e.g., 750ml per bottle) |
| `active` | Boolean | ✅ | `false` = hidden from requester form |

**Ingredient object** (embedded in `ingredients` list):

| Attribute | Type | Description |
|-----------|------|-------------|
| `ingredientId` | String | UUID v4 |
| `name` | String | Ingredient name (e.g., "Cream of coconut") |
| `quantityPerBottle` | Number | Quantity needed per 750ml bottle |
| `unit` | String | Measurement unit (e.g., "ml", "g", "can", "tbsp") |
| `category` | String | Shopping category (e.g., "Dairy", "Spirits", "Spices") |

---

## Ingredient List Aggregation

The ingredient list shown to the cook is a **derived view** — it is computed at query
time from confirmed requests and variety ingredient data. It is NOT stored as a separate
DynamoDB item.

**Aggregation logic**:
1. Fetch all requests for a batch where `status = CONFIRMED`
2. For each request, look up the variety's `ingredients` list and multiply
   `quantityPerBottle` by the number of confirmed requests for that variety
3. Group by variety, then by `category` within each variety
4. Produce a "totals" section summing across all varieties per ingredient name/unit

This is computed by the `get_ingredient_list` Lambda handler on every call.

---

## S3 Bucket Structure

Bucket: `coquito-please-assets`

```text
images/
├── varieties/
│   ├── {varietyId}.jpg        # variety display images
│   └── ...
├── ui/
│   ├── hero.jpg               # cultural hero image for request form
│   └── ...
└── icons/
    └── ...
```

Static frontend assets (HTML, CSS, JS bundles) are stored in a **separate** S3 bucket:
`coquito-please-frontend` and served exclusively through CloudFront.
