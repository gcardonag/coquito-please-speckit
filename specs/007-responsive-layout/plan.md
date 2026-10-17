# Implementation Plan: Responsive Layout Across All Flows

**Branch**: `007-responsive-layout` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/007-responsive-layout/spec.md`

## Summary

Make every frontend flow adapt to mobile (<640px), tablet (640–1023px) and desktop (≥1024px) widths. Mobile layout stays as it is.

**Technical approach.** Use mobile-first `em`-based media queries and add two new width tokens. Move the shared form and button styles into an eagerly loaded `components.css`.

**Header.** A new in-flow `app-header` component replaces the floating chef nav and Log out button. The top banner moves out of fixed positioning into normal page flow.

**Page changes.** Each page's CSS gains a grid-based desktop layout:
- **Chef pages:** list on one side, detail panel on the other.
- **Cook view:** variety sections in columns.
- **Order summary:** details in two columns.
- **Request form:** paired fields side by side.

**Behaviour change.** The only TS behaviour change is scrolling the chef detail panel into view on stacked layouts. Backend and API are unchanged.

## Technical Context

**Language/Version**: TypeScript 5.x, CSS (frontend only)
**Primary Dependencies**: Vite, pnpm 9.x, Prettier 3.x. No new dependencies.
**Storage**: N/A
**Testing**: Cypress 15 + cypress-axe (layout, integration, a11y at 3 viewports); Vitest + jsdom (app-header unit)
**Target Platform**: Evergreen browsers (Chrome, Safari iOS 16+, Firefox), served from CloudFront/S3
**Project Type**: Web application (frontend SPA + serverless backend); this feature touches the frontend only
**Performance Goals**: TTI ≤ 3s on median mobile; ≤10% regression vs `main`
**Constraints**:
- WCAG 2.1 AA, including 1.4.10 Reflow
- 44px touch targets
- Preserve all `data-cy`/`data-testid` attributes and the tested class names
- No flow behaviour changes

**Scale/Scope**: 5 routes plus 404, 6 page/component CSS files, 1 new component, 6 new Cypress specs

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Code Quality**: single responsibility, no duplication, zero linter warnings | ✅ Pass | Duplicate input/`.form-field`/`.date-time-row` rules consolidated into `components.css`. Header logic extracted from `main.ts` into its own component. Prettier is the configured linter; `format:check` must be clean. |
| **I. Code Quality**: no dead code; documented | ✅ Pass | Removed: the unused `--max-width-cook` token, the inline-style chef nav and Log out functions, and the duplicate rules. Unused CSS found during discovery is removed in touched files (`.access-denied-card`, `.batch-access-denied`, `.request-form-page`). Untouched unused files (`style.css`, `counter.ts`) stay out of scope, as recorded in the spec Assumptions. Each new CSS section gets a header comment stating its breakpoint purpose. |
| **II. Testing**: test-first; one integration test per story | ✅ Pass | Each user story has a `responsive-*.cy.ts` spec. Each spec is written first and must fail on `main` (red). The API is stubbed at the network boundary only. |
| **II. Testing**: ≥80% coverage; deterministic | ✅ Pass | New `app-header.ts` gets a Vitest unit test. Cypress uses fixed viewports and stubbed responses, with no timing waits. |
| **II. Testing**: contract tests for external interfaces | ✅ N/A | No API or interface changes. The UI layout contract (`contracts/ui-layout.md`) is enforced by the Cypress specs. |
| **III. UX Consistency**: consistent interactive elements; design review | ✅ Pass | The `.btn` variants are defined once and used on all pages. Header nav behaves identically on all routes. Visual changes reuse existing tokens only. The layout contract is reviewed against `tokens.css` and the design system before implementation (task gate). |
| **III. UX Consistency**: WCAG 2.1 AA; automated a11y check | ✅ Pass | Every responsive spec runs `checkA11y` at each viewport. Header is a banner landmark outside `main`. `aria-current` is set on the active link. |
| **III. UX Consistency**: actionable errors; style guide | ✅ Pass | No user-facing text changes, except the header brand "Coquito Please", which reuses the existing app name. |
| **IV. Performance**: TTI ≤ 3s; ≤10% regression | ✅ Pass | CSS-heavy change with roughly flat total bytes (duplicates removed). Measured before and after per quickstart. |

**Post-design re-check**: All principles satisfied. No Complexity Tracking entries.

**Design review: pass (2026-10-16, T002).** Reviewed `data-model.md` and `contracts/ui-layout.md` against `frontend/src/styles/tokens.css`:
- **New tokens** (`--max-width-form`, `--max-width-wide`, `--gutter`) are layout widths and spacing only. `--gutter` aliases the existing `--space-4`/`--space-6`. No new colours, radii or type sizes.
- **Buttons**: `.btn--primary` (`--color-coconut` background, `--color-text-on-dark` text) and `.btn--secondary` (`--color-surface` background, `--color-coconut` border and text) use existing colour tokens, `--radius-md`, `--border-width-thick` and `--touch-target-min`.
- **Header**: brand, nav links and Log out (`.btn--secondary`) use existing colour, type and spacing tokens. The active link is marked by weight or underline, not a new colour.
- **Banner**: `.app-banner--warn` / `--error` use the existing `--color-warning(-bg)` / `--color-error(-bg)` tokens. This replaces the current inline `#e67e22`, `#c0392b` and `#fff` literals.
- **Headings**: the fluid `h1`/`h2` `clamp()` ranges are bounded by the existing `--font-size-*` tokens (`h1`: `--font-size-xl` to `--font-size-2xl`).

## Project Structure

### Documentation (this feature)

```text
specs/007-responsive-layout/
├── plan.md
├── research.md
├── data-model.md          # design tokens / breakpoints
├── quickstart.md
├── contracts/
│   └── ui-layout.md       # per-viewport layout contract + preserved hooks
├── checklists/requirements.md
└── tasks.md               # /speckit.tasks
```

### Source Code (frontend only)

```text
frontend/
├── src/
│   ├── main.ts                                   # MODIFY: import components.css; use app-header; banner classes; 404 classes
│   ├── styles/
│   │   ├── tokens.css                            # MODIFY: breakpoint doc block, --max-width-form/-wide, --gutter; drop --max-width-cook
│   │   ├── global.css                            # MODIFY: fluid h1/h2, .page-wrapper gutter, banner + 404 classes
│   │   └── components.css                        # NEW: inputs, .form-field, .field-error, .form-error, .field-pair, .btn variants
│   ├── components/
│   │   └── app-header/
│   │       ├── app-header.ts                     # NEW: header render + aria-current sync
│   │       └── app-header.css                    # NEW
│   ├── pages/
│   │   ├── request-form/{index.ts,request-form.css}           # MODIFY (US2)
│   │   ├── manage-request/{index.ts,manage-request.css}       # MODIFY (US3)
│   │   ├── cook-view/cook-view.css                            # MODIFY (US4)
│   │   ├── batch-management/{index.ts,batch-management.css}   # MODIFY (US1)
│   │   └── variety-management/{index.ts,variety-management.css} # MODIFY (US1)
│   ├── components/ingredient-list/ingredient-list.ts           # MODIFY only if a wrapper is needed (US4)
│   └── tests/components/app-header.test.ts                    # NEW
└── cypress/
    ├── support/commands.ts                       # MODIFY: layout + a11y custom commands
    └── e2e/
        ├── responsive-shell.cy.ts                # NEW (US5, US6)
        ├── responsive-request-form.cy.ts         # NEW (US2)
        ├── responsive-manage-request.cy.ts       # NEW (US3)
        ├── responsive-cook-view.cy.ts            # NEW (US4)
        ├── responsive-batch-management.cy.ts     # NEW (US1)
        └── responsive-variety-management.cy.ts   # NEW (US1)
```

**Structure Decision**: Existing web-app layout; frontend only.
- **Foundational work** must land before any flow: tokens, `components.css`, header, and Cypress commands.
- **After that, each flow's files are disjoint.** Per-flow work can then run in parallel, one agent per flow.

## Complexity Tracking

No violations.
