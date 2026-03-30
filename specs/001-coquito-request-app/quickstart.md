# Quickstart: Coquito Request App

**Branch**: `001-coquito-request-app` | **Date**: 2026-03-28

## Prerequisites

- Node.js 20.x or later
- pnpm 9.x (`npm install -g pnpm`)
- Python 3.12
- AWS CLI configured with appropriate credentials
- Cypress system dependencies (see [Cypress docs](https://docs.cypress.io/guides/getting-started/installing-cypress#System-requirements))

## Frontend Setup

```bash
cd frontend
pnpm install
pnpm dev          # starts Vite dev server at http://localhost:5173
```

To check/fix formatting:

```bash
pnpm format:check   # check only (exits non-zero on violations)
pnpm format         # auto-fix all violations
```

## Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Run all backend tests:

```bash
pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=80
```

## Frontend E2E Tests (Cypress)

Requires the Vite dev server to be running (`pnpm dev` in `frontend/`).

```bash
cd frontend
pnpm cypress open       # interactive mode
pnpm cypress run        # headless (CI)
```

## Environment Variables

Copy `.env.example` to `.env.local` in both `frontend/` and `backend/` and fill in:

**frontend/.env.local**
```
VITE_API_BASE_URL=http://localhost:3000/api/v1
VITE_BATCH_ID=<test-batch-uuid>
```

**backend/.env.local**
```
DYNAMODB_REQUESTS_TABLE=coquito-requests
DYNAMODB_BATCHES_TABLE=coquito-batches
DYNAMODB_VARIETIES_TABLE=coquito-varieties
SES_FROM_ADDRESS=coquito@example.com
COOK_SECRET=<local-dev-secret>
AWS_REGION=us-east-1
```

## Cook View

The cook view requires two query params appended to the hash:

```
http://localhost:5173/#/cook?batchId=<batchId>&cookSecret=<secret>
```

The `cookSecret` value must match the `COOK_SECRET` environment variable set in `backend/.env.local`.

## Validation Checklist

Run this after any significant change to verify the setup is healthy:

- [ ] `pnpm dev` starts without errors and loads the request form
- [ ] `pnpm format:check` exits with code 0
- [ ] `pytest tests/ --cov=src --cov-fail-under=80` passes
- [ ] `pnpm cypress run` passes all E2E specs
- [ ] The request form loads batch config from the API on startup
- [ ] A test request can be submitted and a confirmation is displayed
- [ ] The cook view loads at `/#/cook?batchId=<id>&cookSecret=<secret>` and displays the ingredient list
- [ ] Navigating to `/#/cook` without `cookSecret` shows the access-denied message
