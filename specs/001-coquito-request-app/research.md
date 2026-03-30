# Research: Coquito Request App

**Branch**: `001-coquito-request-app` | **Date**: 2026-03-28
**Phase**: 0 — Outline & Research

## Decision Log

### RD-001: Reminder Delivery Channel

**Decision**: AWS SES (Simple Email Service) for reminder delivery via email.

**Rationale**: The app is a browser-based web application with no native mobile shell,
so Web Push requires a service worker and opt-in permission flow that adds friction for
a casual family/friends audience. SMS via SNS requires phone number collection and
carrier trust setup. Email via SES is universally accessible, requires only an email
address (already collected at request time for confirmation), and integrates directly
with Lambda using boto3 with no third-party dependency.

**Alternatives considered**:
- Web Push API: Requires service worker + permission prompt; high drop-off rate on
  first visit; no fallback if user declines.
- AWS SNS (SMS): Requires phone number; carrier surcharges; SNS sandbox limits in
  non-production accounts.
- Third-party email (SendGrid, Mailgun): Unnecessary external dependency when SES
  covers the use case and is already on-stack.

---

### RD-002: Reminder Scheduling Mechanism

**Decision**: AWS EventBridge Scheduler for per-request reminder scheduling.

**Rationale**: Each request needs two reminders fired at specific absolute times (7 days
and 1 day before pickup). EventBridge Scheduler supports one-time schedules with an
arbitrary target (Lambda function), is serverless with no infrastructure to maintain,
and integrates natively with Lambda via IAM roles.

**Alternatives considered**:
- DynamoDB TTL + DynamoDB Streams: TTL deletion is not precise (up to 48h delay),
  making it unsuitable for time-sensitive reminders.
- Cron Lambda polling DynamoDB: Requires a perpetually-running scheduled Lambda
  scanning for "upcoming" requests. Less precise, higher cost at scale, more complex.
- Third-party scheduler (Celery, BullMQ): Requires always-on worker infrastructure,
  incompatible with pure serverless deployment.

---

### RD-003: Requester Identity and Access

**Decision**: No authentication. Requesters are identified by a unique per-request
UUID link. The cook accesses the ingredient view via a separate path protected by a
static shared secret (passed as a query parameter or HTTP header, configured as an
environment variable in Lambda).

**Rationale**: The audience is friends and family; full auth (OAuth, Cognito) is
disproportionate overhead. A UUID-based deep link (e.g., `/request/{uuid}`) is
unforgeable in practice for this audience and matches how similar casual apps work
(e.g., Calendly, Doodle). The cook view requires only minimal protection since it
contains ingredient quantities, not personal payment data.

**Alternatives considered**:
- Amazon Cognito: Full auth infrastructure; significant complexity and cost for a
  personal-scale app.
- Magic link email auth: Adds a round-trip before access; acceptable but overkill
  when the request confirmation email already contains the UUID link.
- No protection on cook view: Acceptable for this audience but a UUID-based admin
  secret is negligible effort and prevents accidental access.

---

### RD-004: CloudFront + Backend Integration Pattern

**Decision**: Single CloudFront distribution with two origins:
1. S3 origin for `/*` (frontend static assets)
2. API Gateway origin for `/api/*` (backend Lambda functions)

**Rationale**: A single CloudFront distribution keeps the app on one domain (no CORS),
caches static assets at edge, and routes API calls to API Gateway. API Gateway provides
the Lambda integration, request validation, and CORS headers. This is the standard AWS
serverless web app pattern.

**Alternatives considered**:
- Lambda Function URLs directly behind CloudFront: Skips API Gateway; fewer features
  (no request validation, no usage plans). Simpler but loses built-in CORS and
  request/response mapping.
- Separate domains (CloudFront for frontend, API Gateway URL for backend): Requires
  CORS configuration on every Lambda handler; worse DX.

---

### RD-005: DynamoDB Table Design

**Decision**: Three separate tables (not single-table design).

**Rationale**: The access patterns are simple and well-separated: requests are looked up
by ID or by requester email; batches are looked up by ID; varieties are listed in full.
Single-table design adds complexity (compound key construction, filter expressions, item
type disambiguation) that is not justified at this scale. Separate tables are readable,
maintainable, and easier to reason about for a small personal app.

**Tables**:
- `coquito-requests` — one item per request
- `coquito-batches` — one item per batch (cut-off date, bottle limit, status)
- `coquito-varieties` — one item per variety (name, description, ingredient list)

**Alternatives considered**:
- Single-table design: More efficient at high scale; significantly more complex to
  reason about and query. Not justified for tens-of-users scale.
- Relational DB (RDS): Relational model adds no value for this data shape; higher cost
  and operational overhead vs DynamoDB.

---

### RD-006: Frontend Routing Strategy

**Decision**: Hash-based client-side routing (`/#/request`, `/#/manage/:id`,
`/#/cook`) using vanilla TypeScript, no router library.

**Rationale**: The app has three distinct views (requester form, manage request, cook
view). Hash routing requires zero server configuration (S3 + CloudFront serve `index.html`
for any path); it is trivially implementable in ~50 lines of vanilla TS; and adding a
router library (React Router, Vue Router) would violate the minimal-libraries constraint.

**Alternatives considered**:
- History API (pushState) routing: Requires CloudFront error page → index.html redirect
  configuration; slightly more complex. Not worth it for 3 views.
- Multi-page app (separate HTML files): Simpler per-page but harder to share state
  (e.g., request data between form steps) and manage the single CloudFront distribution.

---

### RD-007: Python Lambda Runtime and Tooling

**Decision**: Python 3.12 runtime. Dependencies managed with `pip` + `requirements.txt`.
AWS Lambda Powertools for structured logging, tracing (X-Ray), and input validation.

**Rationale**: Python 3.12 is the latest stable Lambda runtime. Lambda Powertools is
the AWS-recommended utility layer that provides idiomatic logging, tracing, and event
parsing without heavy frameworks. It keeps each handler lean and single-purpose.

**Alternatives considered**:
- FastAPI / Flask running on Lambda: Adds a full web framework to a collection of
  single-purpose functions; violates the single-responsibility intent.
- Poetry for dependency management: Valid alternative; `requirements.txt` chosen for
  simplicity since the dependency list is small.
