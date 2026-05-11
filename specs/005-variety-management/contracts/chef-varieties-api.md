# API Contract: Chef Variety Management

**Branch**: `005-variety-management` | **Date**: 2026-05-09  
**Base path**: `/api/v1/chef`  
**Authorization**: All endpoints require a valid session cookie. Requests without a valid session return `401`. Requests with a valid session but a non-chef role return `403`.

---

## Shared Types

### ChefVarietyDetail

```json
{
  "varietyId": "a1b2c3d4e5f6...",
  "name": "Classic Coquito",
  "description": "Traditional Puerto Rican coquito with coconut cream and white rum.",
  "imageKey": "assets/classic.jpg",
  "bottleYieldMl": 750,
  "active": true,
  "ingredients": [
    {
      "ingredientId": "f1e2d3c4...",
      "name": "Coconut cream",
      "quantityPerBottle": 400.0,
      "unit": "ml",
      "category": "dairy"
    }
  ]
}
```

### ValidationError (400)

```json
{
  "code": "VALIDATION_ERROR",
  "message": "bottleYieldMl must be a positive integer",
  "field": "bottleYieldMl"
}
```

### ChefRoleRequired (403)

```json
{
  "code": "CHEF_ROLE_REQUIRED",
  "message": "This endpoint is restricted to chefs."
}
```

### VarietyNotFound (404)

```json
{
  "code": "VARIETY_NOT_FOUND",
  "message": "Variety 'abc123' not found."
}
```

---

## GET /api/v1/chef/varieties

List all varieties including inactive, with full ingredient lists.

**Handler**: `src.handlers.chef_list_varieties.handler`  
**Lambda**: `coquito-chef-list-varieties`

### Request

No body. No query parameters.

### Responses

**200 OK**

```json
{
  "varieties": [
    { /* ChefVarietyDetail */ },
    { /* ChefVarietyDetail */ }
  ]
}
```

**403 Forbidden** — caller is not a chef

```json
{ "code": "CHEF_ROLE_REQUIRED", "message": "This endpoint is restricted to chefs." }
```

---

## POST /api/v1/chef/varieties

Create a new variety. The system assigns `varietyId` and `ingredientId` values.

**Handler**: `src.handlers.chef_create_variety.handler`  
**Lambda**: `coquito-chef-create-variety`

### Request Body

```json
{
  "name": "Chocolate Coquito",
  "description": "Decadent chocolate twist on the classic recipe.",
  "imageKey": "assets/chocolate.jpg",
  "bottleYieldMl": 750,
  "active": true,
  "ingredients": [
    {
      "name": "Coconut cream",
      "quantityPerBottle": 400.0,
      "unit": "ml",
      "category": "dairy"
    }
  ]
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `name` | yes | Non-empty string |
| `description` | no | Defaults to `""` |
| `imageKey` | no | Defaults to `""` |
| `bottleYieldMl` | yes | Positive integer |
| `active` | no | Defaults to `true` |
| `ingredients` | no | Defaults to `[]`; each item must pass ingredient validation if provided |

Each ingredient in the array:

| Field | Required | Notes |
|-------|----------|-------|
| `name` | yes | Non-empty string |
| `quantityPerBottle` | yes | Positive number |
| `unit` | yes | Non-empty string |
| `category` | yes | Non-empty string |

### Responses

**201 Created**

```json
{
  "variety": { /* ChefVarietyDetail with system-assigned IDs */ }
}
```

**400 Bad Request** — validation failure

```json
{
  "code": "VALIDATION_ERROR",
  "message": "name is required",
  "field": "name"
}
```

**403 Forbidden**

```json
{ "code": "CHEF_ROLE_REQUIRED", "message": "This endpoint is restricted to chefs." }
```

---

## PUT /api/v1/chef/varieties/{id}

Update an existing variety. Replaces the full ingredient list. Any ingredient in the list that omits `ingredientId` is treated as newly added and receives a system-assigned ID.

**Handler**: `src.handlers.chef_update_variety.handler`  
**Lambda**: `coquito-chef-update-variety`  
**Path parameter**: `id` — the `varietyId` of the variety to update

### Request Body

All top-level fields are optional (only provided fields are updated). `ingredients`, if provided, replaces the entire ingredient list.

```json
{
  "name": "Classic Coquito (Updated)",
  "description": "Updated description.",
  "imageKey": "assets/classic-v2.jpg",
  "bottleYieldMl": 800,
  "active": false,
  "ingredients": [
    {
      "ingredientId": "f1e2d3c4...",
      "name": "Coconut cream",
      "quantityPerBottle": 420.0,
      "unit": "ml",
      "category": "dairy"
    },
    {
      "name": "Cinnamon stick",
      "quantityPerBottle": 1.0,
      "unit": "piece",
      "category": "spice"
    }
  ]
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `name` | no | If provided, must be non-empty |
| `description` | no | |
| `imageKey` | no | |
| `bottleYieldMl` | no | If provided, must be positive integer |
| `active` | no | |
| `ingredients` | no | If provided, replaces the full ingredient list; each item validated |

Each ingredient item follows the same validation rules as POST, with the addition of an optional `ingredientId` (string) that preserves identity for existing ingredients.

### Responses

**200 OK**

```json
{
  "variety": { /* ChefVarietyDetail reflecting the updated state */ }
}
```

**400 Bad Request** — validation failure

```json
{
  "code": "VALIDATION_ERROR",
  "message": "bottleYieldMl must be a positive integer",
  "field": "bottleYieldMl"
}
```

**403 Forbidden**

```json
{ "code": "CHEF_ROLE_REQUIRED", "message": "This endpoint is restricted to chefs." }
```

**404 Not Found** — no variety with the given `id`

```json
{
  "code": "VARIETY_NOT_FOUND",
  "message": "Variety 'abc123' not found."
}
```

---

## Terraform additions required

Each new Lambda function requires the following resources added to `infra/terraform/modules/api/main.tf`:

- `aws_lambda_function.chef_list_varieties` — handler `src.handlers.chef_list_varieties.handler`, env vars: same as `list_varieties`
- `aws_lambda_function.chef_create_variety` — handler `src.handlers.chef_create_variety.handler`
- `aws_lambda_function.chef_update_variety` — handler `src.handlers.chef_update_variety.handler`
- `aws_apigatewayv2_integration` for each (AWS_PROXY, payload format 2.0)
- `aws_apigatewayv2_route` for each with `authorization_type = "CUSTOM"` and the existing `authorizer_id`
- `aws_lambda_permission` for each (added to `protected_functions` locals)
- `aws_cloudwatch_log_group` for each (retention 30 days)

Routes:

| Method | Path | Lambda |
|--------|------|--------|
| GET | `/api/v1/chef/varieties` | `coquito-chef-list-varieties` |
| POST | `/api/v1/chef/varieties` | `coquito-chef-create-variety` |
| PUT | `/api/v1/chef/varieties/{id}` | `coquito-chef-update-variety` |
