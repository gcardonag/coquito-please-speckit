# Quickstart: Chef Batch Management

**Feature**: 004-chef-batch-management
**Date**: 2026-05-07

---

## Prerequisites

- All prerequisites from `specs/003-aws-website-storage/quickstart.md` satisfied
- `uv` installed (Python package management)
- `pnpm` 9.x installed (frontend)
- AWS credentials configured for the target environment
- Cognito user with `chef` group membership (for manual testing)

---

## Backend — Running New Handlers Locally

All new Lambda handlers can be unit-tested offline. No AWS credentials are required for unit tests.

```bash
cd backend

# Install dependencies (if not already done)
uv sync

# Run unit tests for the new handlers
uv run pytest tests/unit/handlers/test_list_batches.py -v
uv run pytest tests/unit/handlers/test_create_batch.py -v
uv run pytest tests/unit/handlers/test_update_batch.py -v
uv run pytest tests/unit/handlers/test_update_batch_status.py -v
uv run pytest tests/unit/handlers/test_get_me.py -v
uv run pytest tests/unit/handlers/test_close_expired_batches.py -v

# Run all backend tests
uv run pytest
```

---

## Backend — Contract Tests

Contract tests verify the handler response shapes match `contracts/api-contract.md`.
These run offline using `moto` to mock DynamoDB.

```bash
cd backend
uv run pytest tests/contract/test_list_batches.py -v
uv run pytest tests/contract/test_create_batch.py -v
uv run pytest tests/contract/test_update_batch.py -v
uv run pytest tests/contract/test_update_batch_status.py -v
uv run pytest tests/contract/test_get_me.py -v
```

---

## Backend — Integration Tests

Integration tests require a deployed environment or a local DynamoDB local instance with seed data.

```bash
cd backend

# Run the batch management integration test suite
uv run pytest tests/integration/test_batch_management.py -v
```

The integration test covers:
- Chef creates a batch → appears in list with OPEN status
- Chef updates batch properties → changes reflected in list
- Chef transitions OPEN → CLOSED → COMPLETED
- Non-chef receives 403 on all batch management endpoints
- Auto-close Lambda closes batches past their cutoff date

---

## Frontend — Running the Dev Server

```bash
cd frontend
pnpm install
pnpm dev
```

Navigate to `http://localhost:5173`. Log in with a Cognito account that has the `chef` group.
A "Manage Batches" link will appear in the navigation. Non-chef accounts will not see the link.

Hash route: `http://localhost:5173/#/batches`

---

## Frontend — Running Tests

```bash
cd frontend
pnpm test
```

New test file: `src/tests/pages/batch-management.test.ts`

Tests cover:
- Batch list renders with correct status badges
- Empty state renders when no batches exist
- Create form validates all required fields
- OPEN→CLOSED confirmation dialog shows active request count
- CLOSED→COMPLETED transitions without a dialog
- COMPLETED batches render as read-only
- Non-chef nav item is hidden

---

## Infrastructure — Applying Terraform Changes

```bash
cd infra/terraform

# Preview changes
terraform plan -var-file=environments/prod.tfvars

# Apply (requires AWS credentials)
terraform apply -var-file=environments/prod.tfvars
```

New resources added:
- `aws_lambda_function.get_me`
- `aws_lambda_function.list_batches`
- `aws_lambda_function.create_batch`
- `aws_lambda_function.update_batch`
- `aws_lambda_function.update_batch_status`
- `aws_lambda_function.close_expired_batches`
- `aws_apigatewayv2_route` for each of the five HTTP routes
- `aws_cloudwatch_log_group` for each new Lambda
- `aws_scheduler_schedule.close_expired_batches` (EventBridge Scheduler, daily 00:05 UTC)
- `aws_iam_role_policy` attachment for EventBridge Scheduler to invoke the close Lambda

---

## Manual Testing Checklist

After deployment, verify the following with a chef-role Cognito account:

- [ ] "Manage Batches" nav link is visible after login as chef
- [ ] "Manage Batches" nav link is absent after login as authorized-user
- [ ] Batch list loads and shows status, cutoff date, variety count
- [ ] Empty state displays with create prompt when no batches exist
- [ ] Create form rejects past cutoff dates with an actionable error
- [ ] Create form rejects duplicate batch names with an actionable error
- [ ] Create form rejects missing required fields
- [ ] Newly created batch appears in list immediately with OPEN status
- [ ] Editing an OPEN batch saves changes and updates the list
- [ ] OPEN→CLOSED shows confirmation dialog with active request count
- [ ] After CLOSED confirmation, batch status updates in the list
- [ ] CLOSED→COMPLETED transitions immediately with no dialog
- [ ] COMPLETED batch detail view is read-only
- [ ] Direct URL access to `#/batches` by non-chef redirects with access-denied message
