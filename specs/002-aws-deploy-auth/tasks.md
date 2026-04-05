# Tasks: AWS Deployment with Role-Based Authentication

**Input**: Design documents from `/specs/002-aws-deploy-auth/`  
**Branch**: `002-aws-deploy-auth`  
**Stack**: Python 3.12 (Lambda) · TypeScript 5.x (frontend) · Terraform hashicorp/aws v6.39.0  
**Tests**: Included — Constitution §II mandates test-first (Red-Green-Refactor)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable (different files, no shared dependency)
- **[US#]**: User story the task directly serves
- Exact file paths in all descriptions

---

## Phase 1: Setup (Project Structure)

**Purpose**: Create all directories and skeleton files needed before any implementation begins.

- [X] T001 Create Terraform directory tree: `infra/terraform/`, `infra/terraform/modules/acm/`, `infra/terraform/modules/frontend/`, `infra/terraform/modules/auth/`, `infra/terraform/modules/api/`, `infra/terraform/modules/dns/` (empty `main.tf` + `variables.tf` + `outputs.tf` in each)
- [X] T002 Create backend auth handler directory: `backend/src/handlers/auth/__init__.py` and stub files `authorizer.py`, `token_exchange.py`, `logout.py`
- [X] T003 [P] Create backend service stub: `backend/src/services/cognito.py`
- [X] T004 [P] Create frontend auth service stub: `frontend/src/services/auth.ts`
- [X] T005 [P] Create test directories and `__init__.py` files: `backend/tests/contract/`, `backend/tests/integration/`, `backend/tests/unit/auth/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: All Terraform modules, the Lambda authorizer, and Cognito infrastructure that MUST be complete before any user story can be tested end-to-end.

**⚠️ CRITICAL**: No user story acceptance criteria can be verified until this phase is complete.

- [X] T006 Implement `infra/terraform/providers.tf`: `hashicorp/aws ~> 6.39`, `region = "us-east-1"`, `default_tags` block with `Project = "coquito"` and `Environment = var.environment`
- [X] T007 Implement `infra/terraform/terraform.tf`: `required_version >= 1.6.0`, `required_providers` with `source = "hashicorp/aws"` and `version = "~> 6.39"`
- [X] T008 [P] Implement `infra/terraform/variables.tf`: `domain` (default `"coquito.gcardona.me"`), `region` (default `"us-east-1"`), `hosted_zone_id`, `environment` (default `"prod"`), `chef_seed_email`
- [X] T009 [P] Implement `infra/terraform/modules/acm/main.tf`: `aws_acm_certificate` (DNS validation, `domain_name = var.domain`, SANs for `api.coquito.gcardona.me` and `auth.coquito.gcardona.me`), `aws_route53_record` for each validation CNAME, `aws_acm_certificate_validation` resource
- [X] T010 [P] Implement `infra/terraform/modules/acm/variables.tf` + `outputs.tf`: input `domain`, `hosted_zone_id`; output `certificate_arn`
- [X] T011 [P] Implement `infra/terraform/modules/frontend/main.tf`: `aws_s3_bucket` (private, versioning enabled), `aws_s3_bucket_public_access_block` (all true), `aws_cloudfront_origin_access_control`, `aws_cloudfront_distribution` (HTTPS-only, default root `index.html`, custom error responses 403→`/index.html` + 404→`/index.html` with 200, alternate domain `var.domain`, viewer certificate from ACM)
- [X] T012 [P] Implement `infra/terraform/modules/frontend/variables.tf` + `outputs.tf`: inputs `domain`, `certificate_arn`; outputs `bucket_name`, `cloudfront_distribution_id`, `cloudfront_domain_name`
- [X] T013 [P] Implement `infra/terraform/modules/auth/main.tf`: `aws_cognito_user_pool` (email sign-in, no self-registration, `allow_user_auth` flow, deletion protection enabled, Managed Login), `aws_cognito_user_pool_client` (confidential, `ALLOW_USER_AUTH` + `ALLOW_REFRESH_TOKEN_AUTH`, access token 60 min, refresh token 30 days, callback URL `https://coquito.gcardona.me/auth/callback`, PKCE), `aws_cognito_user_group` for `chef` and `authorized-user`, `aws_cognito_user_pool_domain` for `auth.coquito.gcardona.me`
- [X] T014 [P] Implement `infra/terraform/modules/auth/variables.tf` + `outputs.tf`: outputs `user_pool_id`, `user_pool_arn`, `client_id`, `client_secret_ssm_path`, `jwks_uri`, `token_endpoint`, `domain`; store `client_secret` as `aws_ssm_parameter` SecureString at `/coquito/${var.environment}/cognito/client_secret`
- [X] T015 [P] Implement `infra/terraform/modules/api/main.tf`: `aws_apigatewayv2_api` (HTTP, CORS: origin `https://coquito.gcardona.me`, credentials `true`, headers `Content-Type`), `aws_apigatewayv2_authorizer` (Lambda, simple response, `$request.header.Cookie` identity source, 300s cache), `aws_apigatewayv2_domain_name` for `api.coquito.gcardona.me`, `aws_apigatewayv2_api_mapping`, `aws_lambda_permission` for authorizer
- [X] T016 [P] Implement `infra/terraform/modules/api/variables.tf` + `outputs.tf`: outputs `api_id`, `api_endpoint`, `custom_domain_name`, `target_domain_name`, `hosted_zone_id`
- [X] T017 [P] Implement `infra/terraform/modules/dns/main.tf`: `aws_route53_record` alias A for CloudFront (`coquito.gcardona.me`) and API Gateway (`api.coquito.gcardona.me`)
- [X] T018 Implement `infra/terraform/main.tf`: compose all five modules (`acm`, `frontend`, `auth`, `api`, `dns`), wire outputs between modules (ACM cert_arn → frontend + api; auth outputs → api Lambda env vars)
- [X] T019 [P] Implement `infra/terraform/outputs.tf`: `frontend_url`, `api_url`, `auth_url`, `cognito_user_pool_id`, `cognito_client_id`, `cloudfront_distribution_id`, `s3_bucket_name`
- [X] T020 [P] Implement `infra/terraform/prod.tfvars` and `prod.tfvars.example` with all required variable values (real hosted_zone_id in prod.tfvars; placeholders in example)
- [X] T021 Write unit tests for Lambda authorizer in `backend/tests/unit/auth/test_authorizer.py`: (a) valid `id_token` cookie → `isAuthorized=true`, correct `userId`/`role` context; (b) missing cookie → `isAuthorized=false`; (c) expired JWT → `isAuthorized=false`; (d) valid JWT, `chef` group → role=`"chef"`; (e) valid JWT, `authorized-user` group → role=`"authorized-user"`; (f) valid JWT, both groups → role=`"chef"` (precedence); (g) tampered signature → `isAuthorized=false`. Use a test RSA key pair fixture; mock JWKS fetch.
- [X] T022 Implement `backend/src/handlers/auth/authorizer.py`: parse `Cookie` header to extract `id_token`, fetch and cache Cognito JWKS (15-min in-memory cache), validate JWT (signature, expiry, `aud` = client_id), extract `cognito:groups`, apply chef-first precedence, return `{"isAuthorized": bool, "context": {"userId": sub, "role": role, "email": email}}`. Log WARN via Lambda Powertools on any validation failure (no PII). Verify T021 tests pass.
- [X] T023 [P] Write unit tests for `cognito.py` service in `backend/tests/unit/auth/test_cognito.py`: (a) `exchange_code` → returns token dict on success; (b) `exchange_code` → raises on Cognito error; (c) `revoke_token` → calls correct Cognito endpoint. Mock `httpx` or `urllib.request`.
- [X] T024 [P] Implement `backend/src/services/cognito.py` with three public functions: (1) `exchange_code(code: str, redirect_uri: str, code_verifier: str) -> dict` — calls Cognito `/oauth2/token` with `grant_type=authorization_code`; (2) `refresh_tokens(refresh_token: str) -> dict` — calls Cognito `/oauth2/token` with `grant_type=refresh_token`; (3) `revoke_token(refresh_token: str) -> None` — calls `/oauth2/revoke`. All three share an internal `_call_token_endpoint(params: dict) -> dict` to avoid duplication. Reads `client_id`, `client_secret`, `token_endpoint` from SSM at cold-start (cached). Verify T023 tests pass. *(Fixes H3: single-responsibility — exchange_code and refresh_tokens are distinct operations with distinct parameters)*

**Checkpoint**: Terraform modules are complete, Lambda authorizer passes all unit tests, Cognito service passes unit tests. Infrastructure is ready to deploy.

---

## Phase 3: User Story 1 — Site Accessible via AWS (Priority: P1) 🎯 MVP

**Goal**: The site is live at `https://coquito.gcardona.me`, the health endpoint is reachable, and unprotected access to protected APIs returns 401.

**Independent Test**: Navigate to `https://coquito.gcardona.me` in a browser — the page loads. `curl https://api.coquito.gcardona.me/health` returns `{"status":"ok"}`. `curl https://api.coquito.gcardona.me/api/v1/varieties` returns 401.

### Tests for User Story 1 ⚠️ Write first — verify FAIL before implementation

- [X] T025 [P] [US1] Contract test for health endpoint in `backend/tests/contract/test_health.py`: GET `/health` → 200 `{"status":"ok","service":"coquito-api"}`. Use `httpx` against a locally-invoked Lambda handler (no network required).
- [X] T026 [P] [US1] Integration test: unauthenticated GET `/api/v1/varieties` → 401 in `backend/tests/integration/test_site_accessible.py`. Mock the Lambda authorizer returning `isAuthorized=false` and verify the route returns 401.

### Implementation for User Story 1

- [X] T027 [US1] Implement `backend/src/handlers/health.py`: `handler(event, context) -> dict` — returns `{"statusCode": 200, "body": {"status": "ok", "service": "coquito-api"}}`. Use Lambda Powertools Logger for structured logging.
- [X] T028 [US1] Add `aws_lambda_function` for `coquito-health`, `aws_lambda_permission` (API GW invoke), and `aws_apigatewayv2_route` for `GET /health` (no authorizer) + `aws_apigatewayv2_integration` in `infra/terraform/modules/api/main.tf`. Add Lambda function resources for all existing handlers (`list_varieties`, `create_request`, `get_request`, `update_request`, `cancel_request`, `get_batch_config`, `get_ingredient_list`, `mark_ingredient_acquired`, `send_reminder`) with the Lambda authorizer attached.
- [X] T029 [US1] Add `aws_apigatewayv2_route` entries for all existing handler endpoints in `infra/terraform/modules/api/main.tf`: `GET /api/v1/varieties`, `POST /api/v1/requests`, `GET /api/v1/requests/{id}`, `PUT /api/v1/requests/{id}`, `POST /api/v1/requests/{id}/cancel`, `GET /api/v1/batches/{id}/config`, `GET /api/v1/batches/{id}/ingredients`, `PUT /api/v1/batches/{id}/ingredients/{ingredId}/acquired`, `POST /api/v1/requests/{id}/reminder` — all with `authorizer_id = aws_apigatewayv2_authorizer.main.id`
- [X] T030 [US1] Build frontend placeholder: update `frontend/src/main.ts` to render a "Coquito Please — Coming Soon" page that makes a fetch to `import.meta.env.VITE_API_URL + "/health"` and displays the status. Run `pnpm build` to verify the build succeeds.
- [X] T031 [US1] Run `terraform init && terraform apply -var-file=prod.tfvars` from `infra/terraform/`. Confirm: ACM certificate validated, S3 bucket created, CloudFront distribution deployed, Cognito user pool created, HTTP API created, Route53 records propagated.
- [X] T032 [US1] Deploy frontend to S3: `aws s3 sync frontend/dist/ s3://<bucket> --delete --cache-control "max-age=31536000,public" --exclude "index.html"` and upload `index.html` with `no-cache` headers. Invalidate CloudFront: `aws cloudfront create-invalidation --distribution-id <id> --paths "/*"`.
- [X] T033 [US1] Package and deploy all Lambda functions (health + existing handlers + authorizer): `pip install -r backend/requirements.txt -t backend/dist/ && cp -r backend/src backend/dist/ && cd backend/dist && zip -r ../lambda.zip . && aws lambda update-function-code --function-name <name> --zip-file fileb://backend/lambda.zip` for each function.
- [X] T034 [US1] Verify US1 acceptance criteria: (1) `curl -s -o /dev/null -w "%{http_code}" https://coquito.gcardona.me/` returns 200; (2) `curl https://api.coquito.gcardona.me/health` returns `{"status":"ok"}`; (3) `curl -s -o /dev/null -w "%{http_code}" https://api.coquito.gcardona.me/api/v1/varieties` returns 401. Run T025–T026 contract/integration tests against deployed endpoints.

**Checkpoint**: US1 fully functional. Site is live, health check passes, unauthenticated access returns 401.

---

## Phase 4: User Story 2 — Chef Login and API Access (Priority: P2)

**Goal**: A Chef can complete EMAIL_OTP login, receive an httpOnly session cookie, call Chef-only endpoints successfully, and get rejected after session expiry.

**Independent Test**: Log in as the seeded Chef account via `https://auth.coquito.gcardona.me`. Verify cookie is set. Call `GET /api/v1/batches/{id}/config` with the cookie — returns 200. Call same endpoint without cookie — returns 401. Call same endpoint with an `authorized-user` session — returns 403.

### Tests for User Story 2 ⚠️ Write first — verify FAIL before implementation

- [X] T035 [P] [US2] Contract test for `POST /auth/callback` in `backend/tests/contract/test_auth_callback.py`: (a) valid code → 302 redirect with three `Set-Cookie` headers (HttpOnly, Secure, SameSite=Strict); (b) missing code → 400 `INVALID_CODE`; (c) state mismatch → 400 `STATE_MISMATCH`. Mock `cognito.py` service.
- [X] T036 [P] [US2] Contract test for `POST /auth/logout` in `backend/tests/contract/test_auth_logout.py`: (a) valid session → 200, three cookies cleared (Max-Age=0); (b) no session → 200 (idempotent). Mock `cognito.py` revoke call.
- [X] T037 [P] [US2] Contract test for `POST /auth/refresh` in `backend/tests/contract/test_auth_refresh.py`: (a) valid refresh_token cookie → 200, new id_token + access_token cookies set; (b) missing/expired refresh_token → 401 `REFRESH_EXPIRED`.
- [X] T038 [P] [US2] Integration test for Chef login and access in `backend/tests/integration/test_chef_login_and_access.py`: (a) Chef session with `role="chef"` in authorizer context → Chef-only handler returns 200; (b) No session → 401; (c) `authorized-user` session on Chef endpoint → 403. Use test JWT fixtures and mock the authorizer context injection.

### Implementation for User Story 2

- [X] T039 [US2] Write unit tests for `token_exchange.py` in `backend/tests/unit/auth/test_token_exchange.py`: (a) valid code → sets three cookies, returns 302; (b) Cognito error → 503; (c) CSRF state validated. Verify tests FAIL, then implement.
- [X] T040 [US2] Implement `backend/src/handlers/auth/token_exchange.py`: parse `code`, `state`, and `code_verifier` from query params (code_verifier is echoed back from the SPA via a hidden field or query param alongside the auth code redirect). Call `cognito.exchange_code(code, redirect_uri, code_verifier)`. On success: set `id_token`, `access_token`, `refresh_token` cookies with correct flags (`HttpOnly; Secure; SameSite=Strict`), then redirect to `https://coquito.gcardona.me/?state=<echo_state>` so the SPA can verify the CSRF `state` against sessionStorage. Log WARN on errors (no PII). Verify T039 tests pass. *(Fixes H2: state echoed back to SPA for CSRF verification — no server-side state storage needed)*
- [X] T041 [US2] Write unit tests for `logout.py` in `backend/tests/unit/auth/test_logout.py`. Implement `backend/src/handlers/auth/logout.py`: clear all three cookies (Max-Age=0), call `cognito.revoke_token(refresh_token)` (best-effort, log WARN on failure), return 200 `{"ok": true}`. Verify tests pass.
- [X] T042 [US2] Write unit tests for `refresh.py` in `backend/tests/unit/auth/test_refresh.py`: (a) valid refresh_token cookie → calls `cognito.refresh_tokens()`, sets new cookies, returns 200; (b) missing/expired cookie → 401 `REFRESH_EXPIRED`. **Verify tests FAIL.** Implement `backend/src/handlers/auth/refresh.py`: read `refresh_token` cookie, call `cognito.refresh_tokens(refresh_token)`, set new `id_token` + `access_token` cookies, return 200. On failure return 401 `REFRESH_EXPIRED`. Verify tests pass. *(Fixes H2/H3: calls cognito.refresh_tokens — correct function name; explicit RED step added)*
- [X] T043 [US2] Add `aws_apigatewayv2_route` entries for auth endpoints in `infra/terraform/modules/api/main.tf`: `POST /auth/callback`, `POST /auth/logout`, `POST /auth/refresh` — all WITHOUT authorizer (public). Add `aws_lambda_function` resources for `coquito-auth-token-exchange`, `coquito-auth-logout`, `coquito-auth-refresh`.
- [X] T044 [US2] Add role enforcement to Chef-only handlers. Update `backend/src/handlers/get_batch_config.py`, `backend/src/handlers/get_ingredient_list.py`, `backend/src/handlers/mark_ingredient_acquired.py`, `backend/src/handlers/update_request.py`, `backend/src/handlers/send_reminder.py`: read `role = event["requestContext"]["authorizer"]["lambda"]["role"]`; if `role != "chef"` return 403 `{"code": "FORBIDDEN", "message": "Chef access required"}`.
- [X] T045 [US2] Implement `frontend/src/services/auth.ts`: `redirectToLogin()` — generates a random `state` UUID and PKCE `code_verifier`, stores both in sessionStorage under keys `auth_state` and `auth_code_verifier`, builds Cognito Managed Login URL with `code_challenge` (SHA-256 of code_verifier) and `state`, redirects browser. After callback returns to `/?state=<echo>`, call `verifyState(returnedState: string): boolean` — reads `auth_state` from sessionStorage and compares; clears sessionStorage keys after check. Also: `logout()` (calls `POST /auth/logout`), `refreshSession()` (calls `POST /auth/refresh`), `isSessionExpired(r: Response): boolean` (true on 401). Export all. *(Fixes H2: sessionStorage for code_verifier + state; state verified by SPA on return)*
- [X] T045a [P] [US2] Write Vitest unit tests for `frontend/src/services/auth.ts` in `frontend/src/tests/services/auth.test.ts`: (a) `redirectToLogin()` stores state + code_verifier in sessionStorage and builds a URL containing `state`, `code_challenge`, `client_id`, `redirect_uri`; (b) `verifyState('matching-value')` returns true and clears sessionStorage; (c) `verifyState('wrong-value')` returns false; (d) `isSessionExpired` returns true on a 401 Response, false on 200; (e) `logout()` calls `fetch('/auth/logout', { method: 'POST' })`. Run `pnpm test --coverage` and confirm ≥80% coverage on `auth.ts`. *(Fixes C1: frontend test coverage mandate)*
- [X] T046 [US2] Wire auth session handling in `frontend/src/main.ts`: on page load check for `?state=` query param and call `auth.verifyState()` (display error if mismatch). On API 401 response → call `auth.redirectToLogin()`. On API 503 response → display "Service temporarily unavailable — please try again" message (do NOT redirect). Add logout button. Rebuild and redeploy frontend. *(Also fixes M1: 503 handling)*
- [X] T047 [US2] Seed Chef account: `aws cognito-idp admin-create-user --user-pool-id <id> --username <chef_seed_email> --user-attributes Name=email,Value=<email> Name=email_verified,Value=true --message-action SUPPRESS && aws cognito-idp admin-add-user-to-group --user-pool-id <id> --username <chef_seed_email> --group-name chef`
- [X] T048 [US2] Redeploy Lambda functions (auth handlers + updated existing handlers). Verify US2 acceptance criteria: (1) Chef EMAIL_OTP login succeeds and `id_token` cookie is set; (2) Authenticated Chef call to `GET /api/v1/batches/{id}/config` returns 200; (3) After access_token expiry (or manual cookie deletion) → 401 and redirect to login; (4) Invalid credentials → Cognito error page with clear message.

**Checkpoint**: US1 and US2 both work. Chef can log in and access all Chef-only operations.

---

## Phase 5: User Story 3 — Authorized User Login and API Access (Priority: P3)

**Goal**: An invited customer can log in, submit requests, and view their own requests. They cannot self-register. They are rejected when calling Chef-only endpoints.

**Independent Test**: Log in as a seeded `authorized-user` account. Submit a `POST /api/v1/requests` — returns 201. Call `GET /api/v1/batches/{id}/config` (Chef-only) — returns 403. Attempt self-registration via Cognito — blocked. A different user's request ID → 403.

### Tests for User Story 3 ⚠️ Write first — verify FAIL before implementation

- [X] T049 [P] [US3] Integration test for authorized user access in `backend/tests/integration/test_authorized_user_access.py`: (a) `authorized-user` session → `POST /api/v1/requests` returns 201; (b) `authorized-user` session → `GET /api/v1/batches/{id}/config` returns 403; (c) No session → `POST /api/v1/requests` returns 401. Use JWT fixtures.
- [X] T050 [P] [US3] Integration test for user isolation in `backend/tests/integration/test_authorized_user_access.py`: `authorized-user` A attempts `GET /api/v1/requests/{id}` where request belongs to user B → 403.

### Implementation for User Story 3

- [X] T051 [US3] Add `userId` ownership check to `backend/src/handlers/get_request.py`: if `role == "authorized-user"` and `event["requestContext"]["authorizer"]["lambda"]["userId"] != request["requesterId"]`, return 403 `{"code": "FORBIDDEN", "message": "Access denied"}`. Chef bypass: skip check if `role == "chef"`.
- [X] T051a [US3] Add `userId` ownership check to `backend/src/handlers/cancel_request.py`: same pattern as T051 — if `role == "authorized-user"` and `userId != request["requesterId"]`, return 403. Chef bypass applies. Add test case to `backend/tests/integration/test_authorized_user_access.py`: authorized-user POSTing to cancel another user's request → 403; authorized-user cancelling own request → 200. *(Fixes H1: cancel_request gap in authorization boundary)*
- [X] T052 [US3] Add `userId` to request record on creation in `backend/src/handlers/create_request.py`: write `requesterId = event["requestContext"]["authorizer"]["lambda"]["userId"]` into the DynamoDB item so ownership can be checked by T051.
- [X] T053 [P] [US3] Implement `POST /api/v1/users` Chef-only endpoint in `backend/src/handlers/create_user.py`: reads `role` from authorizer context (403 if not chef), calls `boto3.client("cognito-idp").admin_create_user(...)` with provided email, calls `admin_add_user_to_group(group_name="authorized-user")`, returns 201 `{"userId": sub, "email": email}`. Log user creation at INFO level (no PII beyond the fact a user was created).
- [X] T054 [US3] Add `aws_lambda_function` for `coquito-create-user` and `aws_apigatewayv2_route` for `POST /api/v1/users` (with authorizer) in `infra/terraform/modules/api/main.tf`. Grant Lambda IAM permissions to call `cognito-idp:AdminCreateUser` and `cognito-idp:AdminAddUserToGroup`.
- [X] T055 [US3] Provision a test authorized-user account: `aws cognito-idp admin-create-user ... --group-name authorized-user`. Redeploy Lambda functions (updated handlers + new create_user). Verify US3 acceptance criteria: (1) authorized-user login succeeds; (2) `POST /api/v1/requests` succeeds; (3) `GET /api/v1/batches/{id}/config` returns 403; (4) self-registration blocked (Cognito `allow_admin_create_user_only = true` already set in T013).

**Checkpoint**: All three user stories functional. Chef and authorized-user flows verified end-to-end.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Observability, security hardening, cost verification, and final validation.

- [X] T056 [P] Add Lambda Powertools structured logging to all handlers that are missing it: `backend/src/handlers/list_varieties.py`, `cancel_request.py`, `get_request.py`. Ensure auth failure events (`INVALID_TOKEN`, `EXPIRED_SESSION`, `UNAUTHORIZED_ROLE`) are logged at WARN with `endpoint`, `timestamp`, `error` fields but no PII (no email, no userId in WARN logs). Verify logs appear in CloudWatch within 60 seconds (SC-007).
- [X] T057 [P] Add `aws_cloudwatch_log_group` resources for each Lambda function in `infra/terraform/modules/api/main.tf` with `retention_in_days = 30` to stay within the 5 GB/month free tier (SC-005).
- [ ] T058 [P] Security hardening — verify cookie flags end-to-end: use browser DevTools to confirm `id_token` cookie has `HttpOnly`, `Secure`, `SameSite=Strict` after login. Confirm `refresh_token` is scoped to `Path=/auth/refresh`. Confirm no tokens in `localStorage` or non-httpOnly cookies.
- [X] T058a [P] Automated accessibility check on new frontend UI: install `@axe-core/cli` (`pnpm add -D @axe-core/cli`) and run `axe https://coquito.gcardona.me/login https://coquito.gcardona.me/ --tags wcag2a,wcag2aa` against the login page and the session-expiry state. Fix any violations before merge. Document results in a comment in `frontend/src/pages/login/index.ts`. *(Fixes C2: Constitution §III Quality Gate — automated accessibility check for all UI changes)*
- [X] T059 [P] Run all tests and verify coverage ≥80% for new modules: `cd backend && python -m pytest --cov=src/handlers/auth --cov=src/services/cognito --cov-report=term-missing`. Fix any gaps.
- [X] T060 Validate cost estimate: review AWS Cost Explorer or use the pricing calculator. Confirm projected monthly cost <$10 at 500 MAU (SC-005). Document actual baseline cost in `specs/002-aws-deploy-auth/research.md` under a new "Actual Cost Baseline" section.
- [ ] T061 Run `quickstart.md` end-to-end validation: fresh clone → `terraform apply` → frontend deploy → Lambda deploy → seed Chef → verify all three acceptance scenarios from spec.md pass. Fix any steps that don't match the documented process.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 complete
- **US2 (Phase 4)**: Depends on Phase 2 complete; integrates with Phase 3 (live deployment)
- **US3 (Phase 5)**: Depends on Phase 4 complete (auth infrastructure required for role enforcement)
- **Polish (Phase 6)**: Depends on all user story phases complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational. No dependency on US2 or US3.
- **US2 (P2)**: Can start after Foundational. Requires live infrastructure from US1.
- **US3 (P3)**: Depends on US2 (auth Lambdas + authorizer context with `role` must be in place).

### Within Each User Story

- Tests MUST be written and FAIL before implementation starts
- For US1: Terraform before deploy; deploy before verification
- For US2: Unit tests → auth Lambda implementations → Terraform wiring → frontend → deploy → verify
- For US3: Tests → handler updates → Terraform → deploy → verify

---

## Parallel Opportunities

### Phase 2 (Foundational) — run these in parallel:

```
T009 + T010  modules/acm/
T011 + T012  modules/frontend/
T013 + T014  modules/auth/
T015 + T016  modules/api/
T017         modules/dns/
T021 → T022  authorizer (sequential: test then implement)
T023 → T024  cognito service (sequential: test then implement)
```

### Phase 4 (US2) — run these in parallel after T038:

```
T039 → T040  token_exchange (test → implement)
T041         logout (test + implement)
T042         refresh (test + implement)
T044         handler role enforcement (independent of auth Lambdas)
T045 → T045a frontend auth.ts implement then test (sequential)
T046         wire session/503 handling in main.ts (after T045a)
```

### Phase 6 (Polish) — all [P] tasks run in parallel:
```
T056   logging
T057   CloudWatch log groups
T058   security verification
T058a  accessibility check
T059   coverage check
```

---

## Implementation Strategy

### MVP First (US1 only — site is live)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (Terraform + authorizer)
3. Complete Phase 3: US1 (deploy, verify)
4. **STOP and VALIDATE**: Site loads, health check passes, unauthenticated → 401
5. Ship MVP

### Incremental Delivery

1. Phase 1 + 2 → Foundation ready
2. Phase 3: US1 → Site is live (demo-able)
3. Phase 4: US2 → Chef can log in and operate
4. Phase 5: US3 → Customers can be invited and submit requests
5. Phase 6: Polish → Production-hardened

### Parallel Team Strategy

With two developers after Phase 2 completes:
- Developer A: Phase 3 (US1 — deployment) + Phase 4 auth Lambdas
- Developer B: Phase 4 handler updates + frontend auth integration

---

## Notes

- [P] tasks operate on different files with no shared in-flight dependency
- Constitution §II mandates: write tests FIRST, verify they FAIL, then implement
- Each user story checkpoint must be independently verified before advancing
- Commit after each task or closely-related group (T009+T010, T011+T012, etc.)
- `terraform apply` is an explicit task (T031, T054) — do not apply speculatively
- Secrets (client_secret) are stored in SSM, never in code or env vars
- FR-003 spec conflict (password vs. passwordless) is resolved by this plan — update spec before running `/speckit.implement`
