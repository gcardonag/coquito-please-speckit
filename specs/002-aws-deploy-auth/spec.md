# Feature Specification: AWS Deployment with Role-Based Authentication

**Feature Branch**: `002-aws-deploy-auth`  
**Created**: 2026-04-04  
**Status**: Draft  
**Input**: User description: "Add the ability to access the site via AWS, including the ability to log in and access the APIs as a Chef and as an authorized user. The deployment should be as cost-effective as possible."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Site Accessible via AWS (Priority: P1)

Any visitor can reach the Coquito Please application through a public AWS-hosted URL. The frontend loads fully and the backend APIs are reachable. No login is required to view the site, but protected actions require authentication.

**Why this priority**: Nothing else is testable until the site is live. This is the foundation for all other stories.

**Independent Test**: Can be tested by navigating to the public URL in a browser and confirming the application loads and the health/status endpoint returns a success response.

**Acceptance Scenarios**:

1. **Given** a visitor with no account, **When** they navigate to the public AWS URL, **Then** the application loads within 3 seconds and the homepage is displayed.
2. **Given** the application is deployed, **When** the frontend requests the backend health endpoint, **Then** it receives a successful response confirming the API is reachable.
3. **Given** the application is deployed, **When** a visitor attempts to access a protected API without credentials, **Then** they receive an "unauthorized" response and are redirected to the login page.

---

### User Story 2 - Chef Login and API Access (Priority: P2)

A Chef (restaurant owner/operator) can log in with their credentials and gain access to Chef-only API operations such as managing varieties, managing batches, and reviewing or fulfilling requests.

**Why this priority**: The Chef role controls the core operational workflows of the application. Chef access must be working before customer-facing flows can be validated end-to-end.

**Independent Test**: Can be tested by logging in with a Chef credential, calling a Chef-restricted endpoint (e.g., create/update a batch), and confirming access is granted and the operation succeeds.

**Acceptance Scenarios**:

1. **Given** a Chef with valid credentials, **When** they submit their login, **Then** they receive an authenticated session and are shown the Chef dashboard.
2. **Given** an authenticated Chef session, **When** they call a Chef-only API endpoint (e.g., manage batches), **Then** the request succeeds and the correct data is returned.
3. **Given** an authenticated Chef, **When** their session expires, **Then** they are prompted to log in again before continuing.
4. **Given** a user with invalid Chef credentials, **When** they attempt to log in as Chef, **Then** they receive a clear error message and access is denied.

---

### User Story 3 - Authorized User Login and API Access (Priority: P3)

An authorized customer (invited/pre-approved user) can log in with their credentials and access customer-facing API operations, such as placing coquito requests and viewing their order status.

**Why this priority**: Customer access depends on authentication infrastructure already proven by the Chef story. It adds customer-specific role restrictions on top.

**Independent Test**: Can be tested by logging in with an authorized user credential, calling a customer endpoint (e.g., submit a request), and confirming the operation succeeds and is visible to the Chef.

**Acceptance Scenarios**:

1. **Given** an authorized user with valid credentials, **When** they submit their login, **Then** they receive an authenticated session and are shown the customer view.
2. **Given** an authenticated authorized user, **When** they call a customer-facing API endpoint (e.g., submit a request), **Then** the request succeeds.
3. **Given** an authenticated authorized user, **When** they attempt to call a Chef-only endpoint, **Then** the request is rejected with an "unauthorized" response.
4. **Given** a person without an account attempting to self-register, **When** they try to sign up independently, **Then** they are informed that accounts require invitation and no account is created.

---

### Edge Cases

- What happens when a user's session token is tampered with or replayed from another device?
- How does the system handle simultaneous login attempts from the same account?
- What happens when the authentication service is temporarily unavailable — does the site degrade gracefully?
- **Dual-role accounts**: If a Chef is also added to the `authorized-user` Cognito group, the Chef role takes precedence. Authorization logic checks for the `chef` group first; if present, full Chef access is granted regardless of additional group membership. No context-switching UI is required.
- What happens when a deployment configuration is missing or misconfigured?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The frontend application MUST be hosted and publicly accessible via a global AWS-backed URL with HTTPS enforced.
- **FR-002**: The backend API MUST be accessible only via HTTPS; all unencrypted requests MUST be rejected.
- **FR-003**: Users MUST be able to log in using an email address with Email-based One-Time Password via Amazon Cognito User Pools.
- **FR-004**: The system MUST support two roles: **Chef** and **Authorized User**, implemented as Cognito User Pool Groups (`chef`, `authorized-user`), with distinct access permissions for each.
- **FR-005**: Chef-only API endpoints MUST reject requests from Authorized Users and unauthenticated callers. Authorization checks the `chef` Cognito group first; membership grants full access.
- **FR-006**: Authorized User API endpoints MUST reject requests from unauthenticated callers; Chef accounts MAY access these endpoints (Chef role takes precedence over any dual-group membership).
- **FR-007**: The system MUST allow a Chef to create and manage Authorized User accounts (no self-registration).
- **FR-008**: The system MUST invalidate sessions upon explicit logout.
- **FR-009**: Authenticated sessions MUST expire after **60 minutes of inactivity** and require re-authentication. Cognito refresh tokens handle silent renewal while the user is active; once the inactivity window elapses the user must log in again.
- **FR-010**: The infrastructure MUST use pay-per-use or free-tier services wherever possible to minimize standing costs.
- **FR-012**: Cognito tokens MUST be stored in `httpOnly`, `Secure`, `SameSite=Strict` cookies; storage in `localStorage` or non-`httpOnly` cookies is prohibited.
- **FR-013**: All Lambda functions MUST emit structured logs to CloudWatch Logs using AWS Lambda Powertools logger. Auth failures (invalid token, expired session, unauthorized role) MUST be logged at WARN level with request context (endpoint, timestamp, error reason — no PII).
- **FR-011**: The system MUST provide actionable error messages when login fails (invalid credentials, account not found, account disabled).

### Key Entities

- **Chef**: An operator account with full access to manage varieties, batches, and requests. Created and managed by the system administrator.
- **Authorized User**: A customer account with access to place and view their own requests. Accounts are provisioned by a Chef.
- **Session / Token**: A time-limited credential issued upon successful login that authorizes subsequent API calls.
- **Role**: A classification (Chef or Authorized User) attached to an account that determines which API operations are permitted.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The site loads and is fully interactive within 3 seconds for a visitor on a median mobile connection.
- **SC-002**: A Chef or Authorized User can complete the full login flow and reach their respective dashboard in under 60 seconds.
- **SC-003**: 100% of Chef-only endpoints reject requests from Authorized User sessions with an appropriate error.
- **SC-004**: 100% of protected endpoints reject unauthenticated requests.
- **SC-005**: Monthly AWS infrastructure cost remains under $10 USD at low-to-moderate traffic volumes (up to 500 monthly active users). CloudWatch Logs remain within the 5 GB/month free tier.
- **SC-007**: Auth failure events (invalid token, expired session, unauthorized role access) are observable in CloudWatch Logs within 60 seconds of occurrence.
- **SC-006**: Session tokens expire and require re-login after **60 minutes of inactivity**, with 100% enforcement across all protected routes.

## Assumptions

- User accounts are not self-service; only Chefs (or a designated admin) can create Authorized User accounts. There is no public sign-up flow.
- The initial set of Chef accounts will be created manually (e.g., seeded during deployment) and not through the UI.
- The existing backend Lambda functions and DynamoDB tables will be extended rather than replaced; this feature adds authentication and infrastructure around them.
- All AWS resources will be deployed in a single region to minimize complexity and cost.
- The frontend is a static single-page application suitable for CDN/object-storage hosting without a persistent server.
- "Cost-effective" means minimizing standing (always-on) costs; pay-per-use pricing models are preferred.
- Mobile support is within scope for the login and customer-facing views; the Chef dashboard may be desktop-first.
- Password reset and self-service account recovery are out of scope for v1 and will be handled manually by the Chef.
- Authentication is handled by **Amazon Cognito User Pools**; API Gateway uses Cognito authorizers to validate tokens on protected routes.

## Clarifications

### Session 2026-04-04

- Q: Which AWS authentication mechanism should be used? → A: Amazon Cognito User Pools
- Q: What should the session inactivity timeout be? → A: 60 minutes
- Q: What should happen when a Chef account is also in the authorized-user group (dual role)? → A: Chef takes precedence; dual-role accounts behave as Chef only
- Q: Where should the frontend store Cognito tokens after login? → A: httpOnly cookies (Secure, SameSite=Strict)
- Q: Should the deployment include observability instrumentation? → A: CloudWatch Logs + structured logging via Lambda Powertools

## Integration & External Dependencies

- **Authentication service**: Amazon Cognito User Pools (free tier covers 50,000 MAU; satisfies SC-005).
  - Chef and Authorized User accounts are stored in a single Cognito User Pool, differentiated by Cognito Groups (`chef`, `authorized-user`).
  - API Gateway routes use Cognito authorizers to enforce authentication and group membership.
  - Cognito issues access, ID, and refresh tokens; the frontend stores tokens in **`httpOnly` cookies** (`Secure`, `SameSite=Strict`), preventing XSS-based token theft and providing CSRF resistance.
  - Failure mode: if Cognito is temporarily unreachable, API Gateway authorizers will reject all protected requests with 503; the frontend must surface a clear "service unavailable" message rather than silently failing.
