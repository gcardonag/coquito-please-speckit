# Quickstart: Batch User Access Management (006)

## Prerequisites

- AWS credentials configured with access to the dev environment
- Cognito User Pool ID available in environment
- Existing dev environment deployed (see feature 002 quickstart)
- `uv` installed (Python package management)
- `pnpm` installed (frontend)

## Backend Development

```bash
# From repo root
cd backend

# Install dependencies
uv sync

# Run unit tests
uv run pytest tests/unit/ -v

# Run contract tests (uses moto for AWS mocks)
uv run pytest tests/contract/ -v

# Run a specific new test file
uv run pytest tests/contract/test_chef_batch_access.py -v
```

## Frontend Development

```bash
# From repo root
cd frontend

# Install dependencies
pnpm install

# Start dev server
pnpm dev
# App runs at http://localhost:5173

# Navigate to the batch management page
# http://localhost:5173/#/batches
# Log in as chef → select an OPEN batch → "Manage Access" section appears
```

## Testing the Feature Manually

1. Log in as a chef
2. Navigate to `#/batches` → click an OPEN batch
3. Click **Manage Access** button in the batch detail panel
4. **Search for existing user**: type an email prefix in the search field
5. **Grant access**: select a user from results → click "Grant Access"
6. **Create new user**: click "New User" → fill form → submit
7. **Revoke access**: in the access list, click "Remove" next to a user → confirm

## Environment Variables (new, per Lambda)

New handlers require `COGNITO_USER_POOL_ID` and `DYNAMODB_BATCH_ACCESS_TABLE`.

Add to `.env.test` for local contract tests:

```bash
COGNITO_USER_POOL_ID=us-east-1_TestPool
DYNAMODB_BATCH_ACCESS_TABLE=coquito-batch-access
DYNAMODB_BATCHES_TABLE=coquito-batches
```

## Terraform (infra changes)

```bash
cd infra/terraform

# Preview changes
terraform plan -var="environment=dev" -var="domain=dev.example.com"

# Apply
terraform apply -var="environment=dev" -var="domain=dev.example.com"
```

New resources created:
- `aws_dynamodb_table.batch_access`
- 4 `aws_lambda_function` resources
- 4 `aws_apigatewayv2_integration` + `aws_apigatewayv2_route` resources
- 4 `aws_cloudwatch_log_group` resources
- Updated `aws_iam_role_policy.lambda_cognito` (adds `ListUsers`, `AdminGetUser`)
