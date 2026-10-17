# UI Layout Contract: Responsive Layout Across All Flows

This contract defines the observable layout at each width range, plus the DOM hooks that must remain stable. The Cypress specs in `frontend/cypress/e2e/responsive-*.cy.ts` assert against it.

Viewports: **M** = 375×660, **T** = 768×1024, **D** = 1280×800.

## Every route, at every viewport (M, T, D, plus 320 and 1920 spot checks)

- `document.documentElement.scrollWidth <= clientWidth`, meaning there is no horizontal page scroll.
- `cy.checkA11y` passes with the `wcag2a`, `wcag2aa`, `wcag21a` and `wcag21aa` tags.
- Every visible `button`, `a.btn`, `input[type=checkbox|radio]` hit area and nav link is at least 44px tall.

## Preserved hooks (MUST NOT change)

- All `data-cy` and `data-testid` attributes.
- `[data-status]`, `[data-batch-id]`, `[data-variety-id]`, `[role=dialog]`, and `[aria-live=polite]` on the batch list.
- Class names asserted by Vitest:
  - `.variety-status--active` and `.variety-status--inactive`
  - `.variety-row--inactive`
  - `.variety-ingredient-row`
- Ids: `#logout-btn` and `#chef-nav` (now inside the header). `#app` keeps `role="main"`.

## Global shell

DOM, in body order: `div.app-banner.app-banner--{warn|error}[role=alert]?`, then `header.app-header`, then `div#app[role=main]`.

```
header.app-header
└── div.app-header__inner
    ├── a.app-header__brand[href="#/"]               "Coquito Please"
    ├── nav#chef-nav.app-header__nav[aria-label="Chef"]   (chefs only)
    │   ├── a.app-header__link[href="#/batches"]     "Manage Batches"   [aria-current=page when active]
    │   └── a.app-header__link[href="#/varieties"]   "Manage Varieties"
    └── button#logout-btn.btn.btn--secondary          "Log out"
```

| Viewport | Expectation |
|----------|-------------|
| M | Brand and Log out share row 1. Chef nav wraps to row 2. No two controls overlap. |
| T, D | Everything sits on one row. The inner width is capped at `--max-width-wide` and centred. |
| All | Header and banner are in normal flow, never `position: fixed`. The last element of `#app` is fully visible when scrolled to the bottom. |

## Flow 1: Request form (`#/`)

| Viewport | Expectation |
|----------|-------------|
| M | `#requester-name` and `#requester-email` are stacked. `#pickup-date` and `#pickup-time` are stacked. Toggle options are stacked. The variety grid has at least 2 columns. The hero h1 is at most 2 lines. |
| T | Name/email are side by side. Date/time are side by side. Toggle options sit in a row. |
| D | Same as T. The form container width is at least 896px, capped at `--max-width-form`. The variety grid has at least 4 columns. |

New markup: `div.field-pair` wraps the name and email fields. The date/time wrapper's class is `field-pair` (replacing `date-time-row`).

## Flow 2: Manage request (`#/manage/:id`)

| Viewport | Expectation |
|----------|-------------|
| M | Summary rows put the label above the value. `manage-actions`, `edit-actions` and `cancel-dialog__actions` wrap, and no button text is clipped. The cancel dialog has at least 16px viewport margin on each side. |
| D | `[data-cy=request-summary]` is at least 896px wide, capped at `--max-width-form`. Summary rows form 2 columns: the 1st and 2nd rows share a top. The edit form's date and time are side by side. |
| All | Edit form inputs have the shared input styling even on a direct visit, i.e. a computed border width and padding that match the request form. |

## Flow 3: Cook view (`#/cook?batchId=`)

| Viewport | Expectation |
|----------|-------------|
| M | `[data-cy=variety-section]` elements are stacked. The totals table may scroll inside its section, but the page does not. |
| D | With 3 or more varieties, the first two `[data-cy=variety-section]` elements are side by side. `[data-cy=totals-section]` spans the full content width. `[data-cy=preview-banner]` has the same left and right edges (±1px) as `main.cook-main`. |

## Flow 4: Batch management (`#/batches`)

| Viewport | Expectation |
|----------|-------------|
| M, T | `[data-testid=batch-list]` sits above `[data-testid=batch-detail]`. Selecting a row scrolls the detail panel into view (its top is within the viewport). |
| D | List and detail are side by side. After a row is selected, the detail panel's top is within the viewport with no scrolling (up to 10 rows). The variety checklist has at least 2 columns. `#access-search-input` and the Search button share a row. |
| All | The edit form has the `.batch-form` class. `.btn--primary` and `.btn--secondary` have a non-default background colour from the tokens. |

## Flow 5: Variety management (`#/varieties`)

| Viewport | Expectation |
|----------|-------------|
| M, T | List above detail. Selecting a row scrolls the detail into view. In each `.variety-ingredient-row`, the fields are stacked and each input is at least 120px wide. |
| D | List and detail are side by side. In each `.variety-ingredient-row`, the name, qty, unit and category inputs and the Remove button share a single row (equal-ish top). |

## Flow 6: 404

| Viewport | Expectation |
|----------|-------------|
| All | The card is centred, capped at `--max-width-content`, and its link is at least 44px tall. Inline styles move into CSS classes `.not-found` and `.not-found__link`. |
