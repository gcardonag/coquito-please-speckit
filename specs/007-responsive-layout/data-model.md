# Data Model: Responsive Layout Across All Flows

This feature introduces **no persisted data, API changes, or backend changes**. Its only "model" is the set of shared design values every page uses. These go in `frontend/src/styles/tokens.css`.

## Width ranges (breakpoints)

| Name | Media condition | px equivalent | Used for |
|------|-----------------|---------------|----------|
| mobile (default) | none (mobile-first base styles) | < 640 | Single column; every field full width |
| tablet | `(min-width: 40em)` | ≥ 640 | Side-by-side field pairs, row-layout toggles |
| desktop | `(min-width: 64em)` | ≥ 1024 | List/detail grids, 2-column summary, multi-column variety checklist |

These values are recorded in a comment block in `tokens.css`, because custom properties cannot be used in media conditions (research R1).

## Layout width tokens

| Token | Value | Status | Used by |
|-------|-------|--------|---------|
| `--max-width-content` | 40rem (640px) | existing | Narrow centred cards: confirmation, 404, cancelled, not-found |
| `--max-width-form` | 60rem (960px) | **new** | Request form, manage-request page |
| `--max-width-wide` | 75rem (1200px) | **new** | Batch management, variety management, cook view, app header inner width |
| `--max-width-cook` | 30rem (480px) | **removed** | Only referenced by the chef pages, by mistake; replaced by `--max-width-wide` |
| `--touch-target-min` | 44px | existing | All `var(--touch-target)` references are corrected to this |
| `--gutter` | `var(--space-4)` at mobile, `var(--space-6)` from 40em | **new** | Horizontal page padding |

## State relevant to layout (unchanged, documented for preservation)

- **Chef pages**: the selected batch or variety and any unsaved form input live in the DOM. Changing viewport width MUST NOT re-render them (spec edge case: "narrows the window"). Layout changes come from CSS only, so this holds by construction.
- **Header active link**: derived from `location.hash` on each `hashchange`. No stored state.
