# Implementation Plan: Coquito Request App

**Branch**: `001-coquito-request-app` | **Date**: 2026-03-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-coquito-request-app/spec.md`

## Summary

A mobile-first web application for requesting, managing, and fulfilling coquito orders.
Requesters submit orders via a culturally-themed form; the cook receives a consolidated
ingredient shopping list after a configurable cut-off date. The system is built on a
serverless AWS stack: a vanilla TypeScript/Vite frontend served from S3 via CloudFront,
single-purpose Python Lambda functions behind API Gateway + CloudFront, DynamoDB for
transactional data, and AWS SES for reminder emails.

## Technical Context

**Language/Version**: TypeScript 5.x (frontend), Python 3.12 (backend Lambda)
**Primary Dependencies**: Vite 5.x, pnpm 9.x, Prettier 3.x (frontend); boto3, AWS Lambda Powertools (backend)
**Storage**: DynamoDB (requests, batches, varieties); S3 (static assets — images, icons)
**Testing**: Cypress 13.x (frontend E2E flows); pytest 8.x (backend unit + integration)
**Target Platform**: Mobile-first web (modern browsers); AWS Lambda (Python 3.12 runtime)
**Project Type**: Web application (frontend SPA + serverless API)
**Performance Goals**: API responses ≤200ms p95; TTI ≤3s on median mobile device
**Constraints**: CloudFront CDN for static assets; Lambda cold-start mitigation via
provisioned concurrency on high-traffic paths; WCAG 2.1 AA accessibility minimum
**Scale/Scope**: Small-scale personal use (tens of requesters per batch); no multi-tenancy

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Gate | Status |
|-----------|------|--------|
| I. Code Quality | Each Lambda function has a single responsibility; Prettier enforced on all frontend files; no dead code permitted | ✅ PASS — architecture uses one Lambda per operation; Prettier configured in CI |
| II. Testing Standards | Cypress E2E tests for all frontend flows; pytest for all Lambda handlers; ≥80% backend coverage; contract tests for all API endpoints | ✅ PASS — Cypress covers requester and cook flows; pytest with coverage gate in CI |
| III. UX Consistency | Puerto Rican coquito cultural theming throughout; WCAG 2.1 AA; actionable error messages; cook view optimized for readability | ✅ PASS — design requirements encoded in spec; accessibility automated check in Cypress |
| IV. Performance Requirements | CloudFront CDN for all static assets; API Gateway + Lambda for backend; CI benchmarks on form submission and ingredient list load | ✅ PASS — CDN eliminates static asset latency; Lambda benchmarks in CI pipeline |

No violations. No Complexity Tracking entries required.

## Project Structure

### Documentation (this feature)

```text
specs/001-coquito-request-app/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── api-requests.md
│   ├── api-batches.md
│   └── api-varieties.md
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── pages/
│   │   ├── request-form/      # requester order form (P1)
│   │   ├── manage-request/    # view/edit/cancel request (P2)
│   │   └── cook-view/         # ingredient shopping list (P4)
│   ├── components/
│   │   ├── form/              # reusable form fields
│   │   ├── reminder-banner/   # reminder notification UI
│   │   └── ingredient-list/   # cook's checklist component
│   ├── services/
│   │   └── api.ts             # typed API client (fetch wrappers)
│   ├── styles/
│   │   ├── global.css
│   │   └── tokens.css         # design tokens (colors, typography)
│   └── main.ts
├── cypress/
│   ├── e2e/
│   │   ├── request-form.cy.ts
│   │   ├── manage-request.cy.ts
│   │   └── cook-view.cy.ts
│   └── support/
├── public/
│   └── images/                # coquito cultural imagery (served from S3 in production)
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
├── pnpm-lock.yaml
└── .prettierrc

backend/
├── src/
│   ├── handlers/
│   │   ├── create_request.py
│   │   ├── get_request.py
│   │   ├── update_request.py
│   │   ├── cancel_request.py
│   │   ├── list_varieties.py
│   │   ├── get_batch_config.py
│   │   ├── get_ingredient_list.py
│   │   ├── mark_ingredient_acquired.py
│   │   └── send_reminder.py
│   ├── models/
│   │   ├── request.py
│   │   ├── batch.py
│   │   └── variety.py
│   └── services/
│       ├── dynamodb.py        # DynamoDB access helpers
│       ├── ses.py             # email/reminder sending
│       └── scheduler.py      # EventBridge Scheduler helpers
├── tests/
│   ├── unit/
│   │   └── handlers/
│   └── integration/
├── requirements.txt
└── pyproject.toml
```

**Structure Decision**: Web application layout (frontend + backend). Frontend is a
vanilla TypeScript SPA built with Vite, deployed to S3 and served via CloudFront.
Backend is a collection of single-purpose Python Lambda handlers, each in its own file,
exposed via API Gateway and fronted by CloudFront.
