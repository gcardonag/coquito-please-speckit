# Quickstart: Chef Variety Management

**Branch**: `005-variety-management`

## Prerequisites

Same as the existing development environment — no new tools required.

- Python 3.12 + `uv`
- Node.js + pnpm 9.x
- AWS credentials (for integration tests pointing at a dev DynamoDB instance)
- Existing `DYNAMODB_VARIETIES_TABLE`, `DYNAMODB_BATCHES_TABLE`, `DYNAMODB_REQUESTS_TABLE` env vars

## Run backend unit tests

```sh
cd backend
uv run pytest tests/unit/handlers/test_chef_list_varieties.py \
              tests/unit/handlers/test_chef_create_variety.py \
              tests/unit/handlers/test_chef_update_variety.py -v
```

## Run all backend tests (unit + contract)

```sh
cd backend
uv run pytest tests/unit tests/contract -v
```

## Run backend integration tests

Requires real AWS credentials and dev-environment DynamoDB tables.

```sh
cd backend
DYNAMODB_VARIETIES_TABLE=coquito-varieties-dev \
DYNAMODB_BATCHES_TABLE=coquito-batches-dev \
DYNAMODB_REQUESTS_TABLE=coquito-requests-dev \
AWS_REGION=us-east-1 \
uv run pytest tests/integration/test_variety_management.py -v
```

## Run frontend dev server

```sh
cd frontend
pnpm dev
```

Navigate to `http://localhost:5173/#/varieties` — you must be logged in as a chef. The page calls `GET /api/v1/chef/varieties` on mount; a 403 displays an inline access-denied message.

## Run frontend unit tests

```sh
cd frontend
pnpm test
```

The test file is at `src/tests/pages/variety-management.test.ts`.

## Key files changed / added

| File | Change |
|------|--------|
| `backend/src/handlers/chef_list_varieties.py` | NEW — GET /api/v1/chef/varieties |
| `backend/src/handlers/chef_create_variety.py` | NEW — POST /api/v1/chef/varieties |
| `backend/src/handlers/chef_update_variety.py` | NEW — PUT /api/v1/chef/varieties/{id} |
| `backend/tests/unit/handlers/test_chef_list_varieties.py` | NEW |
| `backend/tests/unit/handlers/test_chef_create_variety.py` | NEW |
| `backend/tests/unit/handlers/test_chef_update_variety.py` | NEW |
| `backend/tests/contract/test_chef_varieties.py` | NEW |
| `backend/tests/integration/test_variety_management.py` | NEW |
| `frontend/src/pages/variety-management/index.ts` | NEW |
| `frontend/src/pages/variety-management/variety-management.css` | NEW |
| `frontend/src/tests/pages/variety-management.test.ts` | NEW |
| `frontend/src/services/api.ts` | MODIFIED — add ChefVarietyDetail, IngredientDetail types + 3 API functions |
| `frontend/src/main.ts` | MODIFIED — add `#/varieties` route |
| `infra/terraform/modules/api/main.tf` | MODIFIED — add 3 Lambda functions, integrations, routes, log groups |

## No infrastructure changes to existing resources

The `coquito-varieties-{env}` DynamoDB table schema is unchanged. Existing Lambdas (`list_varieties`, etc.) are not modified. The new Lambdas reuse the same IAM role (`coquito-lambda-exec-{env}`) which already has `dynamodb:PutItem` and `dynamodb:Scan` on `coquito-*` tables.
