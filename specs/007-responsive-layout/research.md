# Research: Responsive Layout Across All Flows

All spec clarifications were resolved on 2026-10-16 (top header bar; style chef buttons). This document records the technical decisions made during planning.

## R1. Breakpoint mechanism

- **Decision**: Mobile-first CSS with `min-width` media queries at `40em` (640px, tablet) and `64em` (1024px, desktop). The values are documented once as a comment block in `tokens.css` next to the new layout width tokens.
- **Rationale**: CSS custom properties cannot be used inside `@media` conditions, and adding PostCSS `@custom-media` would mean a new build dependency for two values. Using `em` units makes the queries respond to browser zoom and text resizing, which WCAG 1.4.4 and 1.4.10 require.
- **Alternatives considered**:
  - `postcss-custom-media`: adds a dependency and configuration for little benefit.
  - Container queries: good for the cook-view sections but inconsistent with the page-level breakpoints elsewhere. `auto-fit` grids are used there instead.
  - JS `matchMedia`-driven classes: puts presentation logic in TS, which is worse on both the code-quality and performance principles.

## R2. Content width tokens

- **Decision**: Add `--max-width-form: 60rem` (960px) for the customer pages (request form, manage request) and `--max-width-wide: 75rem` (1200px) for the chef and cook pages. Keep `--max-width-content` (640px) for narrow centred cards (confirmation, dialogs, 404).
- **`--max-width-cook`**: it is referenced only by the chef pages, by mistake. Those references are replaced and the token is removed.
- **Rationale**:
  - Forms wider than about 960px give long, hard-to-read line lengths.
  - List/detail and multi-column cook layouts benefit from 1200px.
  - At 1280px both widths meet SC-001 (≥70% of the viewport): 960/1280 = 75%.
- **Alternatives considered**: one 1200px width for every page. Rejected because single-purpose customer forms become sparse at that width.

## R3. Shared form and button styles

- **Decision**: Create `src/styles/components.css`, imported eagerly from `main.ts` right after `global.css`. It holds:
  - text-input base, focus and error styles
  - `.form-field`, `.field-error`, `.form-error`
  - the single shared `.field-pair` two-up layout
  - `.btn`, `.btn--primary`, `.btn--secondary`

  The duplicated rules are removed from `request-form.css` and `manage-request.css`.
- **Rationale**: Fixes the defect where `#/manage/:id` opened directly renders unstyled inputs (FR-005). Removes the duplicate `.date-time-row` definitions (FR-013; constitution I: no duplication). Implements FR-028.
- **Alternatives considered**: keeping the rules in `global.css`. That file is base/reset level; component-level rules in their own file keep each file to one responsibility.

## R4. Global header (FR-029)

- **Decision**: A new component `src/components/app-header/app-header.ts` (with `app-header.css`) renders `<header class="app-header">` as the first child of `<body>`, before `#app`, so it is a banner landmark outside the main landmark.
  - **Contents**: the app name, which links to `#/`; `nav.app-header__nav` with the chef links, chefs only; and the Log out button.
  - **Placement**: in normal document flow, so it can never cover content. It is not fixed or sticky.
  - **Active link**: `aria-current="page"` is updated on `hashchange` (spec US5 scenario 4).
  - **Code removed**: it replaces `renderLogoutButton()` and `renderChefNav()` in `main.ts`, along with their inline styles.
  - **IDs**: the existing ids `logout-btn` and `chef-nav` are kept on the new elements for continuity.
- **Top banner**: `showBanner()` moves its inline styles to CSS classes (`.app-banner`, `.app-banner--error`/`--warn`). It is inserted in normal flow above the header instead of being `position:fixed`, so it no longer covers the page heading (US5 scenario 3).
- **Mobile**: the header uses flex-wrap. At under 40em, the nav links wrap onto a second row under the brand and Log out.
- **Alternatives considered**:
  - Sticky header: saves scrolling but costs vertical space on small phones, and with the banner present it can stack on top of content.
  - Hamburger menu: there are only 2 links, so it is not justified.

## R5. List/detail layout on chef pages (FR-020, FR-021)

- **Decision**: At 64em and wider, `.batch-management` and `.variety-management` become CSS grids: `grid-template-columns: minmax(18rem, 2fr) 3fr`.
  - The header spans both columns.
  - The list goes in column 1 and the `[data-testid=*-detail]` panel in column 2.
  - The detail panel is `position: sticky; top: var(--space-4)`, with `max-height: calc(100dvh - 2 * var(--space-4))` and `overflow:auto`.
  - Below 64em the page stays in a single stacked column.
- **Scroll into view**: when an item is selected or "New" is chosen, the TS calls `detail.scrollIntoView({ block: 'start' })` only when `!matchMedia('(min-width: 64em)').matches`. This is the only behavioral TS change (spec FR-021, FR-026). It respects `prefers-reduced-motion` by not passing `behavior: 'smooth'`.
- **Edit form**: the batch edit form gets the `batch-form` class (FR-025).
- **Rationale**: Grid keeps the DOM order (list, then detail), so focus order matches visual order (FR-008).

## R6. Request form field pairs (FR-010)

- **Decision**:
  - Wrap the name and email `.form-field`s in `div.field-pair`, a small markup addition in `request-form/index.ts`.
  - The existing date/time wrapper gets the `field-pair` class and drops the `date-time-row` class. A repo grep shows no test depends on `date-time-row`.
  - `.field-pair` is one column below 40em and `1fr 1fr` from 40em, with `align-items: start` so an error message under one field doesn't misalign the other (spec US2 scenario 4).
  - `.toggle-group` becomes a row from 40em.
  - The variety grid keeps `auto-fill, minmax(140px, 1fr)`. At 960px that gives 6 columns, and at 343px it gives 2.

## R7. Cook view (FR-017–FR-019)

- **Decision**:
  - `.ingredient-list` becomes `display:grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 22rem), 1fr))`.
  - `.totals-section` gets `grid-column: 1 / -1`.
  - `.cook-main` and `.preview-banner` use the same `--max-width-wide` container, so their edges line up.
  - On mobile the totals table sits in a horizontally scrollable wrapper: `.totals-section { overflow-x: auto }`.
- **Rationale**: Gives 2 columns at desktop and 1 on mobile with no media query.

## R8. Manage request (FR-014–FR-016)

- **Decision**:
  - At 64em and wider, `.summary-card` lays out its `.summary-row`s as a 2-column grid. The title and actions span both columns.
  - Below 40em, `.summary-row` switches to a column (label above value).
  - Action rows get `flex-wrap: wrap`, with `flex: 1 1 auto` and `min-width: max-content` on buttons.
  - `.cancel-dialog` gets `width: min(25rem, calc(100vw - 2 * var(--space-4)))`.
- **Hard-coded colours** in `manage-request.css` that this feature touches are replaced with tokens (constitution I/III).

## R9. Testing strategy

- **Decision**: Layout is verified with Cypress at the viewports `[375, 660]`, `[768, 1024]` and `[1280, 800]`; jsdom has no layout engine.
  - **One spec per user story**, so the per-flow work stays independent and specs can be written in parallel:
    - `responsive-request-form.cy.ts`
    - `responsive-manage-request.cy.ts`
    - `responsive-cook-view.cy.ts`
    - `responsive-batch-management.cy.ts`
    - `responsive-variety-management.cy.ts`
    - `responsive-shell.cy.ts` (header, banner, 404)
  - **Shared custom commands** in `cypress/support/commands.ts`, so no assertion logic is duplicated:
    - `cy.assertNoHorizontalOverflow()`
    - `cy.assertSideBySide(selA, selB)`, which checks equal-ish top and A to the left of B
    - `cy.assertStacked(selA, selB)`, which checks that B is below A
    - `cy.assertMinTouchTarget(sel)`
    - `cy.checkA11yAtViewport()`, which calls `injectAxe` and `checkA11y` with WCAG 2.1 AA tags
  - **Unit tests**: the `app-header` component gets a Vitest unit test (jsdom) for:
    - chef vs non-chef rendering
    - `aria-current` updates
    - Log out wiring
  - **Existing tests**: all existing Vitest and Cypress specs must pass unchanged (SC-006).
- **Rationale**: Constitution II. Cypress specs are the per-story integration tests and are written first (red), with the API stubbed via `cy.intercept` only. No core domain logic is mocked.

## R10. Performance (constitution IV, SC-007)

- **Decision**:
  - This is a CSS-only change, plus the small header component.
  - Record the built CSS size and a Lighthouse mobile TTI for `#/` before and after (steps in quickstart.md).
  - The budget is TTI ≤ 3s, with no regression over 10%.
  - Expected CSS growth is a few KB gzipped. `components.css` loads eagerly, but the duplicate rules it replaces are removed from the lazy page CSS, so total bytes stay roughly flat.
