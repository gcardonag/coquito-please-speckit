---
description: "Task list for 007-responsive-layout"
---

# Tasks: Responsive Layout Across All Flows

**Input**: Design documents from `/specs/007-responsive-layout/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ui-layout.md, quickstart.md

**Tests**: REQUIRED. Constitution II requires test-first, with an integration test per story. Each story's Cypress spec is written first and MUST fail before implementation.

**Organization**: Tasks are grouped by user story. All paths are relative to the repo root. Width ranges: M=375×660, T=768×1024, D=1280×800 (see contracts/ui-layout.md).

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [X] T001 Record baseline metrics on `main`. Run `pnpm build` in `frontend/` and record the total `dist/assets/*.css` bytes and the Lighthouse mobile TTI for `#/` (commands in specs/007-responsive-layout/quickstart.md). Write both numbers into specs/007-responsive-layout/quickstart.md under a new "Baseline" heading.
- [X] T002 Design review gate (constitution III). Confirm the token additions in specs/007-responsive-layout/data-model.md and the header and button appearance in specs/007-responsive-layout/contracts/ui-layout.md reuse only colours, radii and type from frontend/src/styles/tokens.css. Note "Design review: pass" with the date in specs/007-responsive-layout/plan.md.

---

## Phase 2: Foundational (blocks all stories)

- [X] T003 Update frontend/src/styles/tokens.css:
  - Add a commented "Breakpoints" block documenting the tablet `min-width: 40em` and desktop `min-width: 64em` breakpoints.
  - Add `--max-width-form: 60rem`, `--max-width-wide: 75rem` and `--gutter: var(--space-4)`.
  - Inside `@media (min-width: 40em)` set `--gutter: var(--space-6)`.
  - Remove `--max-width-cook`.
- [X] T004 Create frontend/src/styles/components.css with a header comment. Move these rules into it from frontend/src/pages/request-form/request-form.css, deleting them there:
  - text `input` base, `:focus` and `.input--error` rules
  - `.form-field`, `.field-error` and `.form-error`

  Then add:
  - `.field-pair`: a 1-column grid with `gap: var(--space-4)` and `align-items: start`; from 40em, `grid-template-columns: 1fr 1fr`.
  - `.btn`, `.btn--primary` and `.btn--secondary`, built from the existing tokens. Primary uses the coconut background with on-dark text. Secondary uses a surface background, a coconut border and coconut text. Both get `min-height: var(--touch-target-min)` plus hover, focus-visible and disabled states.
- [X] T005 Delete both `.date-time-row` definitions from frontend/src/pages/request-form/request-form.css and frontend/src/pages/manage-request/manage-request.css, and any other duplicated input or `.form-field` rules in manage-request.css.
- [X] T006 [P] Replace every `var(--touch-target)` with `var(--touch-target-min)` in frontend/src/pages/cook-view/cook-view.css and frontend/src/pages/manage-request/manage-request.css.
- [X] T007 Import `./styles/components.css` right after `global.css` in frontend/src/main.ts.
- [X] T008 [P] Update frontend/src/styles/global.css:
  - Make `h1` and `h2` fluid with `clamp()` so that h1 is 2.5rem at desktop and ≤ 2rem at 375px.
  - Set the `.page-wrapper` horizontal padding to `var(--gutter)`.
  - Add `.app-banner`, `.app-banner--warn`, `.app-banner--error` and `.app-banner__close` in normal flow, using the token colours for warning and error.
  - Add `.not-found` (centred card, `max-width: var(--max-width-content)`) and `.not-found__link` (`min-height: var(--touch-target-min)`, inline-flex, centred).
- [X] T009 [P] Add custom commands to frontend/cypress/support/commands.ts, typed via `declare global namespace Cypress`, each with a doc comment:
  - `assertNoHorizontalOverflow()`
  - `assertSideBySide(selA, selB)`: tops within 8px and A.right ≤ B.left
  - `assertStacked(selA, selB)`: B.top ≥ A.bottom
  - `assertMinTouchTarget(sel)`: each match has a height ≥ 44
  - `checkA11yAtViewport()`: `injectAxe` then `checkA11y` with the tags `wcag2a`, `wcag2aa`, `wcag21a` and `wcag21aa`

  Also export `const VIEWPORTS = { mobile: [375, 660], tablet: [768, 1024], desktop: [1280, 800] } as const`.

  _Done: `VIEWPORTS` is exported from frontend/cypress/support/viewports.ts, because commands.ts is a side-effect file loaded by support/e2e.ts. Specs import it with `import { VIEWPORTS } from '../support/viewports'`._
- [X] T010 Run `pnpm build && pnpm test && pnpm cypress:run` in frontend/. All existing specs MUST still pass after the CSS consolidation.

**Checkpoint**: The tokens, shared styles and test helpers are ready, so the stories below can proceed in parallel.

---

## Phase 3: User Story 1 — Chef list/detail on desktop (P1) 🎯 MVP

**Goal**: Batch and variety management show the list and detail side by side at D, and stacked with scroll-into-view at M and T.
**Independent Test**: The responsive-batch-management and responsive-variety-management specs pass.

### Tests (write first, must fail)

- [X] T011 [P] [US1] Create frontend/cypress/e2e/responsive-batch-management.cy.ts.
  - **Stubs**: `**/me` as a chef; `GET **/batches` with 6 batches (list endpoint is not under `/chef`; checklist varieties come from `GET **/varieties*`), the first OPEN; `GET **/chef/varieties` with 5 varieties; `GET **/chef/batches/*/access` returning an empty list. Use the same URL patterns as frontend/src/services/api.ts.
  - **At D**:
    - `assertSideBySide('[data-testid=batch-list]', '[data-testid=batch-detail]')` after clicking the first `[data-batch-id]`
    - the detail top is within the viewport
    - the variety checklist has ≥ 2 columns: the first two `.batch-form__variety-item` share a top
    - after expanding Manage Access, `#access-search-input` and its Search button are side by side
    - `[data-testid=edit-batch-form]` has the class `batch-form`
    - `.btn--primary` has a computed background other than `rgba(0, 0, 0, 0)` and other than the browser default
  - **At M and T**:
    - `assertStacked` on the list and detail
    - after a row click, the detail top is within the viewport
  - **Every viewport**: `assertNoHorizontalOverflow`, `assertMinTouchTarget('button')`, `checkA11yAtViewport`, and the Close Batch dialog fully inside the viewport.
- [X] T012 [P] [US1] Create frontend/cypress/e2e/responsive-variety-management.cy.ts.
  - **Stubs**: chef `/me`; `GET **/chef/varieties` with 6 varieties, one with 3 ingredients and one inactive.
  - **At D**: the list and detail are side by side after a row click. In the first `.variety-ingredient-row`, the name, qty, unit and category inputs and `.variety-ingredient-row__remove` share a top (±8px).
  - **At M**: the list and detail are stacked. The ingredient inputs are stacked and each is ≥ 120px wide. The remove button is ≥ 44×44.
  - **Every viewport**: no overflow, and a11y passes.

### Implementation

- [X] T013 [P] [US1] Update frontend/src/pages/batch-management/batch-management.css:
  - **Container**: `.batch-management` uses `max-width: var(--max-width-wide)` and padding `var(--gutter)`.
  - **From 64em**:
    - `display: grid; grid-template-columns: minmax(18rem, 2fr) 3fr; gap: var(--space-6)`
    - the header spans `1 / -1`
    - `[data-testid=batch-detail]` is sticky with `top: var(--space-4)`, a max-height of `calc(100dvh - 2 * var(--space-4))` and `overflow: auto`
    - `.batch-form__variety-list` is `display: grid; grid-template-columns: repeat(auto-fill, minmax(12rem, 1fr))`
    - `.access-search` lays out its input and button in a row with wrap
  - **Long text**: `.access-user-row` wraps long emails with `overflow-wrap: anywhere` instead of an ellipsis at D.
  - **Cleanup**: remove the unused `.batch-access-denied` rule.
- [X] T014 [P] [US1] Update frontend/src/pages/batch-management/index.ts:
  - Add the `batch-form` class to the edit form.
  - Wrap the access search input and Search button in `div.access-search__row`.
  - Add a small documented helper `revealDetail(detailEl)` that calls `scrollIntoView({ block: 'start' })` only when `!window.matchMedia('(min-width: 64em)').matches`. Call it after a row is selected and after "New Batch" is opened.
  - Keep every `data-testid` unchanged.
- [X] T015 [P] [US1] Update frontend/src/pages/variety-management/variety-management.css:
  - **Container**: the same container and 64em grid with a sticky detail panel as T013.
  - **`.variety-ingredient-row`**: 1 column at the base width. From 64em, `grid-template-columns: 2fr 1fr 1fr 1.5fr auto` with the name in the first column, not full width.
  - **Remove button**: `.variety-ingredient-row__remove` is at least `var(--touch-target-min)` square.
- [X] T016 [US1] Update frontend/src/pages/variety-management/index.ts to reveal the detail panel on row select and on "New Variety" using the same rule as T014.
  - Extract `revealDetail` into frontend/src/components/reveal-detail.ts with a doc comment, and import it from both pages so there is no duplication.
  - Depends on T014.
- [X] T017 [US1] Add a Vitest unit test in frontend/src/tests/components/reveal-detail.test.ts that stubs `matchMedia` to true and false and asserts whether `scrollIntoView` was called.
- [X] T018 [US1] Run T011 and T012 plus the existing frontend/src/tests/pages/*.test.ts; all MUST pass.

**Checkpoint**: The chef pages are responsive.

---

## Phase 4: User Story 2 — Request form (P1)

**Goal**: Field pairs sit side by side from T, and everything stacks on M.
**Independent Test**: responsive-request-form.cy.ts passes.

- [X] T019 [P] [US2] Create frontend/cypress/e2e/responsive-request-form.cy.ts.
  - **Stubs**: `GET **/batches/*/config` with an OPEN batch and 6 varieties, reusing the fixture shape from frontend/cypress/e2e/request-form.cy.ts.
  - **At D**:
    - `#requester-name` and `#requester-email` are side by side
    - `#pickup-date` and `#pickup-time` are side by side
    - the first 4 `.variety-card` share a top
    - the `.toggle-option`s within each fieldset share a top
    - the form container width is ≥ 896
  - **At T**: the field pairs are side by side.
  - **At M**: both pairs and the toggle options are stacked; `[data-cy=form-heading]` is ≤ 2 line-heights tall.
  - **Errors**: submit empty at D. Each error shows under its own field, and the paired fields' inputs keep the same top.
  - **Confirmation**: stub a successful POST at M and assert the confirmation card and `.manage-link-btn` are visible.
  - **Every viewport**: no overflow, and a11y passes.
- [X] T020 [US2] Update frontend/src/pages/request-form/index.ts:
  - Wrap the name and email fields in `div.field-pair`.
  - Change the date/time wrapper class from `date-time-row` to `field-pair`.
- [X] T021 [US2] Update frontend/src/pages/request-form/request-form.css:
  - **Container**: `.request-form-card` uses `max-width: var(--max-width-form)` and padding `var(--gutter)`.
  - **From 40em**:
    - `.toggle-group` options in a row with wrap and `gap: var(--space-4)`
    - `.variety-card__image` grows to 96px
  - **Cleanup**: remove the unused `.request-form-page` rule.
  - Depends on T020.
- [X] T022 [US2] Run T019 and frontend/cypress/e2e/request-form.cy.ts; both MUST pass.

---

## Phase 5: User Story 5 — Header and global controls (P1)

**Goal**: An in-flow header replaces the floating controls. There is no overlap, and content is never covered.
**Independent Test**: responsive-shell.cy.ts (header part) and app-header.test.ts pass.

- [X] T023 [P] [US5] Create frontend/cypress/e2e/responsive-shell.cy.ts, with the header tests covering two cases (chef and non-chef `/me`).
  - **At M and D**:
    - `header.app-header` exists before `#app`
    - `#logout-btn` and the `#chef-nav` links do not overlap (bounding rects disjoint)
    - the computed `position` of the header is not `fixed`
    - on `#/batches`, `a[href="#/batches"]` has `aria-current="page"`
    - the non-chef case has no `#chef-nav`
    - scroll to the bottom of `#/?batchId=…`: the submit button is fully in the viewport and clickable
  - **Banner**: trigger it by stubbing `**/health` with a 500 and setting `VITE_API_URL`; if that isn't feasible in dev, assert via `cy.window()` calling the exported banner function. Assert `[data-cy=form-heading]` top ≥ banner bottom.
  - **Every viewport**: a11y passes.
- [X] T024 [P] [US5] Create frontend/src/tests/components/app-header.test.ts (Vitest, jsdom) covering:
  - a chef renders 2 nav links and a non-chef renders none
  - `aria-current` follows `location.hash` on `hashchange`
  - clicking `#logout-btn` calls the injected logout callback
- [X] T025 [US5] Create frontend/src/components/app-header/app-header.ts and frontend/src/components/app-header/app-header.css per contracts/ui-layout.md "Global shell".
  - **API**: `renderAppHeader({ isChef, onLogout }): HTMLElement`, which inserts the header before `#app`, is idempotent, and sets up `aria-current` syncing on `hashchange`.
  - **Header CSS**: an in-flow flex row with wrap; `.app-header__inner` has `max-width: var(--max-width-wide)` and padding `var(--gutter)`.
  - **Mobile**: below 40em the nav uses `order: 3; flex-basis: 100%`.
  - **Links**: use token colours, and the active link has an underline or bold weight.
  - **Doc comments**: on all exported functions.
- [X] T026 [US5] Update frontend/src/main.ts:
  - Delete `renderLogoutButton()` and `renderChefNav()` and replace them with `renderAppHeader`. The header is rendered once, after `getMe()` resolves, with `isChef` false on error.
  - Rewrite `showBanner()` to use the `.app-banner` classes, with no inline styles. It is inserted before the header in normal flow, and the close button is a real `<button class="app-banner__close" aria-label="Dismiss">` with an event listener rather than `onclick` HTML.
  - Depends on T025.
- [X] T027 [US5] Run T023 and T024; both MUST pass.

---

## Phase 6: User Story 3 — Manage request (P2)

**Goal**: A 2-column summary at D, wrapping actions and a dialog that fits at M, and shared input styles on direct visits.
**Independent Test**: responsive-manage-request.cy.ts passes.

- [X] T028 [P] [US3] Create frontend/cypress/e2e/responsive-manage-request.cy.ts.
  - **Stubs**: reuse the mock shapes from frontend/cypress/e2e/manage-request.cy.ts, with `exchangeLocation` set to a 45-character string. Visit `#/manage/:id` directly.
  - **At D**: the summary is ≥ 896 wide and the first two `.summary-row` share a top. Open edit: the date and time inputs are side by side, and `#pickup-date` has a computed border-width equal to the request form's input border-width (≥ 1px, not the browser default).
  - **At M**: in each `.summary-row`, the label is above the value. Every button in `[data-cy=edit-button]`'s parent row has `scrollWidth <= clientWidth`. Open the cancel dialog: its left edge ≥ 16 and its right edge ≤ viewport − 16.
  - **Locked state** (`editable: false`) at M and D: centred, with no overflow.
  - **Every viewport**: a11y passes.
- [X] T029 [US3] Update frontend/src/pages/manage-request/index.ts:
  - The edit form's date/time wrapper uses the class `field-pair`.
  - Move the inline error-card styles (`max-width:560px; margin:2rem auto`) to a CSS class `manage-error-card`.
- [X] T030 [US3] Update frontend/src/pages/manage-request/manage-request.css:
  - **Cards**: `.summary-card`, `.edit-form-card`, `.locked-banner`, `.cancelled-card` and `.not-found-card` use `max-width: var(--max-width-form)`.
  - **Below 40em**: `.summary-row` uses `flex-direction: column` with the value left-aligned.
  - **From 64em**: `.summary-card` is a 2-column grid. `.summary-card__title` and `.manage-actions` span `1 / -1`.
  - **Action rows**: `.manage-actions`, `.edit-actions` and `.cancel-dialog__actions` get `flex-wrap: wrap`, with buttons at `flex: 1 1 auto; white-space: nowrap`.
  - **Dialog**: `.cancel-dialog` has `width: min(25rem, calc(100vw - 2 * var(--space-4)))`.
  - **Colours**: replace the hard-coded hex colours in the rules touched here with tokens.
  - Depends on T029.
- [X] T031 [US3] Run T028 and frontend/cypress/e2e/manage-request.cy.ts; both MUST pass.

---

## Phase 7: User Story 4 — Cook view (P2)

**Goal**: Variety sections in columns at D, the preview banner aligned with the content, and no page overflow at M.
**Independent Test**: responsive-cook-view.cy.ts passes.

- [X] T032 [P] [US4] Create frontend/cypress/e2e/responsive-cook-view.cy.ts.
  - **Stubs**: `GET **/batches/*/ingredients` with 3 varieties, unfinalized so the preview banner shows, reusing the shape from frontend/cypress/e2e/cook-view.cy.ts.
  - **At D**:
    - the first two `[data-cy=variety-section]` are side by side
    - the `[data-cy=totals-section]` width ≈ the `main.cook-main` content width (±2px)
    - the `[data-cy=preview-banner]` left and right edges match `main.cook-main` (±1px)
  - **At M**: the sections are stacked and there is no page overflow.
  - **Every viewport**: each `.ingredient-row` height ≥ 44, and a11y passes.
- [X] T033 [US4] Update frontend/src/pages/cook-view/cook-view.css:
  - **Shared width**: `.cook-main` and `.preview-banner` both use `max-width: var(--max-width-wide); margin-inline: auto` and the same horizontal padding or margin model (`var(--gutter)`).
  - **Grid**: `.ingredient-list` is `display: grid; gap: var(--space-6); grid-template-columns: repeat(auto-fit, minmax(min(100%, 22rem), 1fr))`.
  - **Totals**: `.totals-section` spans `1 / -1` with `overflow-x: auto`.
  - **Cleanup**: remove the unused `.access-denied-card` rules.
- [X] T034 [US4] Run T032 and frontend/cypress/e2e/cook-view.cy.ts; both MUST pass.

---

## Phase 8: User Story 6 — 404 (P3)

- [X] T035 [P] [US6] Add a 404 block to frontend/cypress/e2e/responsive-shell.cy.ts. Visit `#/does-not-exist` at M and D and assert:
  - the card is horizontally centred (|left gap − right gap| ≤ 2)
  - the link height is ≥ 44
  - there is no overflow and a11y passes
- [X] T036 [US6] Update `renderNotFound()` in frontend/src/main.ts to use the `.not-found` and `.not-found__link` classes instead of inline styles. Depends on T026, which touches the same file.

---

## Phase 9: Polish & Cross-Cutting

- [X] T037 Add spot checks to frontend/cypress/e2e/responsive-shell.cy.ts: visit every route at 320×640 and 1920×1080 and run `assertNoHorizontalOverflow`.
- [X] T038 Run `pnpm format` then `pnpm format:check`, `pnpm build`, `pnpm test:coverage` (≥ 80% for touched TS modules) and `pnpm cypress:run` in frontend/. Everything MUST pass with zero warnings.
- [X] T039 Re-measure the CSS bytes and Lighthouse mobile TTI against the T001 baseline. Record them in specs/007-responsive-layout/quickstart.md. Any regression over 10% MUST be justified and mitigated.
- [X] T040 Grep frontend/src for leftovers and remove them: `--max-width-cook`, `var(--touch-target)` without `-min`, `date-time-row`, `position:fixed` in main.ts, and `max-width: 480px` / `640px` / `560px` literals in page CSS.

- [X] T041 [P] Bring frontend/src/pages/request-form/index.ts to ≥ 80% line coverage. Add Vitest (jsdom) tests in frontend/src/tests/pages/request-form.test.ts covering every state:
  - loading, config error and CLOSED batch
  - the form render, including the `.field-pair` wrappers
  - validation, the bottle-volume reveal, an API error and a successful submit showing the confirmation
- [X] T042 [P] Bring frontend/src/pages/manage-request/index.ts to ≥ 80% line coverage. Add tests in frontend/src/tests/pages/manage-request.test.ts covering:
  - load, not-found, load error, locked and editable states
  - edit save and discard, save errors
  - cancel dialog confirm, dismiss and error
- [X] T043 [P] Bring frontend/src/pages/batch-management/index.ts from 53% to ≥ 80% line coverage. Extend frontend/src/tests/pages/batch-management.test.ts to cover the paths that are still untested, especially the Manage Access panel (search, grant, new user, revoke) and the status transitions.
- [X] T044 [P] Bring frontend/src/main.ts to ≥ 80% line coverage. Add frontend/src/tests/main.test.ts covering:
  - routing for every route and the 404 page
  - the auth callback branches: code exchange success and failure, state mismatch, and redirect to login
  - the health banner branches
  - header rendering for chef and non-chef users
- [X] T045 Fix the CI-only failures seen on PR #22 (Linux reserves 15px for classic scrollbars):
  - **Cancel dialog:** sized with `100%` rather than `100vw` in frontend/src/pages/manage-request/manage-request.css, so it keeps its 16px margin when a scrollbar is present.
  - **Cook view totals table:** wrapped in a focusable, labelled `div.totals-scroll` region in frontend/src/components/ingredient-list/ingredient-list.ts (axe `scrollable-region-focusable`). Covered by a 320px Cypress test and a new frontend/src/tests/components/ingredient-list.test.ts.
  - **Cypress setup:**
    - Classic scrollbars are now forced in all Cypress runs (frontend/cypress/support/e2e.ts), so macOS runs match CI.
    - axe violations are printed to the terminal through a `log` task (frontend/cypress.config.ts).
    - Viewport assertions in frontend/cypress/e2e/responsive-batch-management.cy.ts allow sub-pixel differences.

---

## Dependencies & Execution Order

- **Phase 1 → Phase 2 → stories.** Phase 2 blocks all stories.
- **Stories are independent of each other** once Phase 2 is done. US1, US2, US3, US4 and US5 touch disjoint files, so they can run in parallel, one agent per story.
- **Shared-file exceptions:**
  - US6's T036 touches main.ts after US5's T026, so run US6 after US5.
  - T016 depends on T014 (the shared helper).
- **Within a story:** tests first (they must fail), then implementation, then the verification run.
- **Polish** runs after all stories.

## Parallel Example

After Phase 2, launch 5 agents at once:
- **US1:** T011, T012, then T013–T018
- **US2:** T019, then T020–T022
- **US5 then US6:** T023 and T024, then T025–T027, then T035 and T036
- **US3:** T028, then T029–T031
- **US4:** T032, then T033 and T034

## Implementation Strategy

- **MVP:** Phases 1–2 plus US1 (the chef list/detail), which delivers the biggest desktop gain.
- **Then:** US2 and US5 (both P1), followed by US3, US4 and US6.
- **Checkpoints:** each story is verified by its own Cypress spec before merge.
