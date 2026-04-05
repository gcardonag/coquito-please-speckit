# Quickstart & Human Test Plan: AWS Website Storage

**Feature**: 003-aws-website-storage  
**Date**: 2026-04-05  
**Audience**: Developer deploying and validating the storage layer for the first time

---

## Prerequisites

- AWS credentials configured (`aws configure` or IAM role in environment)
- Terraform >= 1.6.0 installed
- Python 3.12 + `uv` installed
- `pnpm` installed (for frontend build)
- Domain and hosted zone already configured (from feature 002)

---

## Deployment Steps

### 1. Build the Lambda package

```bash
cd backend
uv pip install -r requirements.txt --target ./package
cd package && zip -r ../lambda.zip . && cd ..
zip -g lambda.zip -r src/
```

### 2. Build the frontend

```bash
cd frontend
pnpm install
pnpm build
```

### 3. Apply Terraform

```bash
cd infra/terraform
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

Expected outputs after apply:
- `frontend_url` — website URL
- `api_url` — API base URL
- `s3_bucket_name` — S3 bucket for frontend + assets
- `dynamodb_requests_table` — requests table name
- `dynamodb_batches_table` — batches table name
- `dynamodb_varieties_table` — varieties table name

### 4. Deploy frontend to S3

```bash
S3_BUCKET=$(terraform output -raw s3_bucket_name)
CF_DISTRIBUTION_ID=$(terraform output -raw cloudfront_distribution_id)

aws s3 sync ../frontend/dist/ s3://$S3_BUCKET/ --delete
aws cloudfront create-invalidation --distribution-id $CF_DISTRIBUTION_ID --paths "/*"
```

### 5. Run the seed script

```bash
cd backend
DYNAMODB_VARIETIES_TABLE=$(cd ../infra/terraform && terraform output -raw dynamodb_varieties_table) \
DYNAMODB_BATCHES_TABLE=$(cd ../infra/terraform && terraform output -raw dynamodb_batches_table) \
AWS_REGION=us-east-1 \
uv run python scripts/seed_data.py
```

Expected output:
```
Seeding varieties table: coquito-varieties-prod
  ✓ Seeded variety: classic
  ✓ Seeded variety: chocolate
Seeding batches table: coquito-batches-prod
  ✓ Seeded batch: batch-test-2026
Seed complete.
```

---

## Human Test Plan

Run these tests in order after deployment. Each step has a clear pass/fail criterion.

---

### Test 1: Website Loads (SC-001 — 3s load time)

1. Open `https://{domain}` in a browser (use an incognito window to avoid cache)
2. Open DevTools → Network tab → check "Disable cache"
3. Reload the page

**Pass**: Page fully loads within 3 seconds. All static assets (CSS, JS, images) return HTTP 200. No console errors.  
**Fail**: Page does not load, or load time exceeds 3 seconds, or console shows failed requests.

---

### Test 2: Unauthenticated Access Blocked

1. Open `https://{domain}/dashboard` (or any protected route) without being logged in

**Pass**: Redirected to the login/auth page. No application data is visible.  
**Fail**: Application data loads without authentication.

---

### Test 3: Authentication Works

1. Click "Login" and complete Cognito authentication
2. Confirm you are redirected back to the application after login

**Pass**: Logged-in state is established; user identity visible in the UI (or no redirect loop).  
**Fail**: Login fails, redirect loop, or error page shown.

---

### Test 4: Varieties Visible with Baseline Dataset (SC-004)

1. While authenticated, navigate to the varieties/order page
2. Confirm both seed varieties appear:
   - "Classic Coquito"
   - "Chocolate Coquito"

**Pass**: Both varieties are displayed. Each variety shows a name and description.  
**Fail**: No varieties listed, or fetch error displayed.

> **Note**: Variety images (`assets/classic.jpg`, `assets/chocolate.jpg`) will show as broken images until placeholder image files are uploaded to `s3://{bucket}/assets/`. This is expected — image upload is out of scope for this feature's automated deployment.

---

### Test 5: API Health Check

```bash
curl -s https://api.{domain}/health
```

**Pass**: Response is `{"status":"ok"}` with HTTP 200.  
**Fail**: Connection refused, 502, or error body.

---

### Test 6: Protected Endpoint Requires Auth

```bash
curl -s -o /dev/null -w "%{http_code}" https://api.{domain}/api/v1/varieties
```

**Pass**: Returns `401` or `403` (no valid session cookie provided).  
**Fail**: Returns `200` — protected data accessible without authentication.

---

### Test 7: Create a Request (end-to-end data persistence — SC-004)

1. While authenticated, select "Classic Coquito" from the varieties list
2. Fill in the request form:
   - Name: "Test User"
   - Email: "test@example.com"
   - Batch: "Test Batch 2026"
   - Pickup date: any date after 2026-01-01
   - Pickup time: "10:00"
   - Exchange location: "Test lobby"
   - Bottle provided: No
   - Cost contribution: Yes
3. Submit the request

**Pass**: A success confirmation is shown. A `requestId` is returned.  
**Fail**: Error message displayed, or no confirmation shown.

---

### Test 8: Request Persists Across Sessions (SC-004)

1. Note the `requestId` from Test 7
2. Log out
3. Log back in
4. Navigate to request history or retrieve the request

**Pass**: The same request is visible and its data matches what was submitted.  
**Fail**: Request not found after re-login.

---

### Test 9: Data Retrieval Within 1 Second (SC-002)

Using the `requestId` from Test 7:

```bash
# After obtaining a session cookie from the browser DevTools
curl -s -w "\nTime: %{time_total}s\n" \
  -H "Cookie: <your-session-cookie>" \
  "https://api.{domain}/api/v1/requests/{requestId}"
```

**Pass**: Response contains the request data and `Time:` is under 1.00s.  
**Fail**: Response time exceeds 1 second consistently across 3 attempts.

---

### Test 10: Infrastructure Reproducibility (SC-005)

Run from a clean Terraform state:

```bash
cd infra/terraform
time terraform apply -var-file="terraform.tfvars" -auto-approve
```

**Pass**: Apply completes successfully in under 15 minutes.  
**Fail**: Apply takes more than 15 minutes or fails with errors.

---

## Troubleshooting

| Symptom | Likely Cause | Action |
|---|---|---|
| Varieties endpoint returns empty list | Seed script not run | Run `seed_data.py` |
| API returns 500 on data endpoints | Lambda env vars not set | Check `DYNAMODB_*` env vars in Lambda console |
| Images broken | Asset files not uploaded to S3 | Upload placeholder images to `s3://{bucket}/assets/` |
| CloudFront serving stale content | Cache not invalidated | Run `aws cloudfront create-invalidation` |
| `ItemNotFoundError` in Lambda logs | Table name mismatch | Verify `DYNAMODB_*` env vars match actual table names |
