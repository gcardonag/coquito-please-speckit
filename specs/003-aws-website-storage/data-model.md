# Data Model: AWS Website Storage

**Feature**: 003-aws-website-storage  
**Date**: 2026-04-05

---

## DynamoDB Tables

All tables use PAY_PER_REQUEST billing, AWS owned key encryption at rest, and deletion protection.

---

### Table: `coquito-varieties-{environment}`

**Purpose**: Stores coquito flavor definitions, ingredients, and media asset keys  
**Partition key**: `varietyId` (String)  
**Sort key**: None

| Attribute | Type | Required | Description |
|---|---|---|---|
| `varietyId` | String | Yes (PK) | Unique identifier (e.g., `classic`, `rum-chata`) |
| `name` | String | Yes | Display name (e.g., "Classic Coquito") |
| `description` | String | Yes | Short flavor description |
| `imageKey` | String | Yes | S3 key for variety image (e.g., `assets/classic.jpg`) |
| `ingredients` | List | Yes | List of Ingredient maps (see below) |
| `bottleYieldMl` | Number | Yes | Yield per bottle in ml (default: 750) |
| `active` | Boolean | Yes | Whether this variety is currently orderable |

**Ingredient map** (embedded in `ingredients` list):

| Attribute | Type | Required | Description |
|---|---|---|---|
| `ingredientId` | String | Yes | Unique within the variety |
| `name` | String | Yes | Display name (e.g., "Coconut cream") |
| `quantityPerBottle` | Number | Yes | Quantity needed per bottle |
| `unit` | String | Yes | Unit of measure (e.g., `ml`, `g`, `cups`) |
| `category` | String | Yes | Grouping label (e.g., `dairy`, `spirit`, `sweetener`) |

**Access patterns**:
- Scan all active varieties (`scan_table` — acceptable at this scale; few records)
- Get single variety by `varietyId` (`get_item`)

---

### Table: `coquito-batches-{environment}`

**Purpose**: Stores production batch configurations that constrain what can be ordered  
**Partition key**: `batchId` (String)  
**Sort key**: None

| Attribute | Type | Required | Description |
|---|---|---|---|
| `batchId` | String | Yes (PK) | Unique identifier (e.g., `batch-2026-holiday`) |
| `batchName` | String | Yes | Human-readable name (e.g., "Holiday 2026") |
| `cutoffDate` | String | Yes | Order cutoff date (YYYY-MM-DD); orders must be after this |
| `maxBottleVolumeMl` | Number | Yes | Maximum allowed bottle size in ml |
| `availableVarietyIds` | List | Yes | List of `varietyId` strings available in this batch |
| `status` | String | Yes | `OPEN` \| `CLOSED` \| `COMPLETED` |
| `createdAt` | String | Yes | ISO 8601 creation timestamp |
| `acquiredIngredients` | Map | Yes | Map of `ingredientId` → Boolean (acquired flag) |

**Access patterns**:
- Get single batch by `batchId` (`get_item`)

---

### Table: `coquito-requests-{environment}`

**Purpose**: Stores individual coquito orders placed by authenticated users  
**Partition key**: `requestId` (String)  
**Sort key**: None

| Attribute | Type | Required | Description |
|---|---|---|---|
| `requestId` | String | Yes (PK) | UUID v4 |
| `requesterName` | String | Yes | Full name of the person ordering |
| `requesterEmail` | String | Yes | Email address (validated format) |
| `requesterId` | String | No | Cognito `sub` of the authenticated user |
| `batchId` | String | Yes | FK → batches table |
| `varietyId` | String | Yes | FK → varieties table |
| `pickupDate` | String | Yes | Requested pickup date (YYYY-MM-DD); must be after cutoffDate |
| `pickupTime` | String | Yes | Requested pickup time (HH:MM) |
| `exchangeLocation` | String | Yes | Physical pickup location description |
| `bottleProvided` | Boolean | Yes | Whether the requester provides their own bottle |
| `bottleVolumeMl` | Number | No | Required when `bottleProvided` is true |
| `costContribution` | Boolean | Yes | Whether the requester is contributing to ingredient cost |
| `status` | String | Yes | `PENDING` \| `CONFIRMED` \| `CANCELLED` |
| `reminders` | List | Yes | List of Reminder maps (see below) |
| `idempotencyKey` | String | Yes | Client-supplied deduplication key |
| `createdAt` | String | Yes | ISO 8601 creation timestamp |
| `updatedAt` | String | Yes | ISO 8601 last-updated timestamp |

**Reminder map** (embedded in `reminders` list):

| Attribute | Type | Required | Description |
|---|---|---|---|
| `reminderId` | String | Yes | UUID v4 |
| `scheduledFor` | String | Yes | ISO 8601 datetime when reminder fires |
| `schedulerArn` | String | Yes | EventBridge Scheduler ARN (empty string on failure) |
| `status` | String | Yes | `SCHEDULED` \| `SENT` \| `CANCELLED` |

**Access patterns**:
- Get single request by `requestId` (`get_item`)
- Create new request (`put_item`)
- Update request status/fields (`update_item` with condition)
- Scan all requests for idempotency check (`scan_table` — acceptable at current scale)

---

## Static Assets (S3)

**Bucket**: `coquito-please-frontend-{environment}` (existing, managed by `modules/frontend`)  
**Encryption**: SSE-S3 (AES-256) — already applied by AWS default on this bucket  
**Access**: Private bucket, served exclusively through CloudFront OAC

### Key prefix conventions

| Prefix | Contents |
|---|---|
| `assets/` | Media files: variety images, icons (e.g., `assets/classic.jpg`) |
| `/` (root) | Frontend static build artifacts (HTML, CSS, JS bundles) |

### Asset URL construction

```
https://{domain}/assets/{imageKey}
```

Set via env var `CLOUDFRONT_ASSETS_BASE_URL = "https://{domain}"` on Lambda functions.  
`Variety.image_url(base)` constructs: `f"{base.rstrip('/')}/{self.image_key}"`  
Example: `https://coquito.gcardona.me/assets/classic.jpg`

---

## Seed Dataset (baseline for human test plan)

The seed script (`backend/scripts/seed_data.py`) writes the following records on first deployment:

### Seed Variety 1: Classic

```json
{
  "varietyId": "classic",
  "name": "Classic Coquito",
  "description": "Traditional Puerto Rican coquito with coconut cream and white rum.",
  "imageKey": "assets/classic.jpg",
  "bottleYieldMl": 750,
  "active": true,
  "ingredients": [
    {"ingredientId": "coconut-cream", "name": "Coconut cream", "quantityPerBottle": 400, "unit": "ml", "category": "dairy"},
    {"ingredientId": "condensed-milk", "name": "Condensed milk", "quantityPerBottle": 200, "unit": "ml", "category": "dairy"},
    {"ingredientId": "white-rum", "name": "White rum", "quantityPerBottle": 150, "unit": "ml", "category": "spirit"}
  ]
}
```

### Seed Variety 2: Chocolate

```json
{
  "varietyId": "chocolate",
  "name": "Chocolate Coquito",
  "description": "Decadent chocolate twist on the classic recipe.",
  "imageKey": "assets/chocolate.jpg",
  "bottleYieldMl": 750,
  "active": true,
  "ingredients": [
    {"ingredientId": "coconut-cream", "name": "Coconut cream", "quantityPerBottle": 400, "unit": "ml", "category": "dairy"},
    {"ingredientId": "condensed-milk", "name": "Condensed milk", "quantityPerBottle": 200, "unit": "ml", "category": "dairy"},
    {"ingredientId": "chocolate-syrup", "name": "Chocolate syrup", "quantityPerBottle": 50, "unit": "ml", "category": "flavoring"},
    {"ingredientId": "white-rum", "name": "White rum", "quantityPerBottle": 150, "unit": "ml", "category": "spirit"}
  ]
}
```

### Seed Batch 1: Test Batch

```json
{
  "batchId": "batch-test-2026",
  "batchName": "Test Batch 2026",
  "cutoffDate": "2026-01-01",
  "maxBottleVolumeMl": 1000,
  "availableVarietyIds": ["classic", "chocolate"],
  "status": "OPEN",
  "createdAt": "<ISO timestamp at seed time>",
  "acquiredIngredients": {}
}
```
