# Quickstart: Responsive Layout Across All Flows

## Run locally

```bash
cd frontend
pnpm install
pnpm dev            # http://localhost:5173 (leave VITE_AUTH_URL unset so pages open without login)
```

To see chef UI locally, the `/me` endpoint must return `role: "chef"`. The Cypress specs stub it with `cy.intercept('GET', '**/me', { userId: 'u1', role: 'chef', email: 'chef@example.com' })`.

## Verify

```bash
pnpm format:check
pnpm build              # tsc type-check + production build
pnpm test               # Vitest (includes app-header unit test)
pnpm test:coverage      # ≥ 80% for touched modules
pnpm cypress:run        # all e2e, including responsive-*.cy.ts
pnpm cypress:run --spec "cypress/e2e/responsive-*.cy.ts"   # only this feature
```

## Manual check

Open DevTools device toolbar and visit each route at 375, 768, 1280 and 1920px:

| Route | Look for |
|-------|----------|
| `#/?batchId=<id>` | Name/email and date/time pairs side by side from 640px; variety grid widens |
| `#/manage/<id>` | Two-column summary at 1024px+; buttons wrap on phone; dialog fits |
| `#/cook?batchId=<id>` | Variety sections in columns at 1024px+; banner aligned |
| `#/batches` | List left, detail right at 1024px+; selecting a row on phone scrolls to detail |
| `#/varieties` | Same as batches; ingredient rows single-line on desktop, stacked on phone |
| `#/nope` | Centred 404 card |

Also: zoom to 200% at 1280px (should follow tablet rules), and scroll to the bottom of each page to confirm nothing is covered.

## Performance check (before vs after)

```bash
pnpm build && ls -l dist/assets/*.css          # record total CSS bytes
pnpm preview &                                 # http://localhost:4173
npx lighthouse http://localhost:4173/#/ --preset=perf --form-factor=mobile --only-categories=performance --quiet --output=json | jq '.audits.interactive.numericValue'
```

TTI must stay ≤ 3000ms and must not regress more than 10% from `main`.

## Baseline

Measured on 2026-10-16 from `007-responsive-layout` before any source change (source identical to `main` @ `53f35de`). Node 20.16.0, Vite 8.0.3.

**CSS bytes** (`pnpm build`, `dist/assets/*.css`):

| File | Bytes |
|------|-------|
| `index-*.css` (global + tokens, eager) | 3,588 |
| `request-form-*.css` | 5,528 |
| `manage-request-*.css` | 5,007 |
| `cook-view-*.css` | 2,919 |
| `batch-management-*.css` | 6,491 |
| `variety-management-*.css` | 4,842 |
| **Total** | **28,375** (7,229 gzipped) |

**Lighthouse mobile TTI for `#/`**: **1,225 ms** (median of 5 runs, range 1,222–1,226 ms; LCP ≈ 2,975 ms, TBT 0 ms). Lighthouse 12.8.2, headless Chrome, `--preset=perf --form-factor=mobile`.

The production build cannot be measured as-is: `.env.production` sets `VITE_AUTH_URL`, so `#/` redirects to the Cognito login page and Lighthouse measures the wrong page. TTI was measured against a build with no auth variables. Re-measure (T039) the same way:

```bash
pnpm exec vite build --mode lhtest --outDir <tmp>/dist-lh      # no .env.lhtest → auth vars unset
pnpm exec vite preview --mode lhtest --outDir <tmp>/dist-lh --port 4173 --strictPort &
npx lighthouse@12 "http://localhost:4173/#/" --preset=perf --form-factor=mobile \
  --only-categories=performance --quiet --chrome-flags="--headless=new" --output=json \
  | jq '.audits.interactive.numericValue'
```

## After (T039)

Measured 2026-10-16 on `007-responsive-layout` with the same method as the baseline.

**CSS bytes**: 34,268 total (+5,893, +20.8%). The eager `index-*.css` grew from 3,588 to 8,639 bytes because it now holds the shared form, button, header and banner styles. The `request-form` CSS shrank from 5,528 to 4,140 bytes. Byte size is not a budgeted metric. The growth is the new responsive rules, and it does not affect TTI (below).

**Lighthouse mobile TTI for `#/`**: **1,234 ms** (median of 5 runs, range 1,229–1,244 ms). That is +0.7% against the 1,225 ms baseline, within the 10% budget. LCP is about 2,980 ms (baseline about 2,975 ms) and CLS is 0.

**Regression found and fixed during T039.** The first version rendered the header after `GET /me` resolved, which gave a TTI of about 1,825 ms (+49%). On `main`, the floating Log out button had painted before `/me` returned. The fix is to render the header immediately and add the chef links afterwards with `showChefNav()`, which restored first paint.
