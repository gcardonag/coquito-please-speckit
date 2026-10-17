// Feature 007 — responsive global shell: header (US5), top banner (US5) and 404 page (US6).
// Layout contract: specs/007-responsive-layout/contracts/ui-layout.md ("Global shell", "Flow 6").
// Written FIRST (TDD) — these MUST FAIL before the header, banner and 404 changes exist.

import { VIEWPORTS } from '../support/viewports';

const BATCH_ID = 'batch-001';

const MOCK_BATCH = {
  batchId: BATCH_ID,
  batchName: 'Christmas 2026',
  cutoffDate: '2026-12-01',
  maxBottleVolumeMl: 750,
  status: 'OPEN',
  availableVarieties: [
    {
      varietyId: 'variety-classic',
      name: 'Classic',
      description: 'The original Puerto Rican recipe',
      imageUrl: '/images/varieties/classic.jpg',
    },
  ],
};

const CHEF = { userId: 'u-chef', role: 'chef', email: 'chef@example.com' };
const CUSTOMER = { userId: 'u-cust', role: 'customer', email: 'customer@example.com' };

type ViewportName = keyof typeof VIEWPORTS;

/** Viewports where the header contract is asserted (mobile and desktop, per T023). */
const HEADER_VIEWPORTS: ViewportName[] = ['mobile', 'desktop'];

/** Shape of the banner module as loaded from the Vite dev server inside the app window. */
interface BannerModule {
  showBanner: (message: string, type?: 'warn' | 'error') => void;
}

/** Stub the signed-in user plus the APIs every page reached by these tests may call. */
function stubApis(user: typeof CHEF | typeof CUSTOMER): void {
  cy.intercept('GET', '**/me', user).as('getMe');
  cy.intercept('GET', '**/batches/**', MOCK_BATCH).as('getBatch');
  cy.intercept('GET', '**/batches', { batches: [] }).as('listBatches');
  cy.intercept('GET', '**/varieties*', { varieties: MOCK_BATCH.availableVarieties });
}

/** True when two DOMRects share any area. */
function overlaps(a: DOMRect, b: DOMRect): boolean {
  return a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
}

describe('US5 — Global header', () => {
  HEADER_VIEWPORTS.forEach((name) => {
    describe(`at ${name} (${VIEWPORTS[name].join('×')})`, () => {
      beforeEach(() => {
        cy.viewport(...VIEWPORTS[name]);
      });

      it('chef: header sits before #app in normal flow and its controls do not overlap', () => {
        stubApis(CHEF);
        cy.visit('/#/does-not-exist');
        cy.wait('@getMe');

        cy.get('header.app-header').should('exist');
        cy.get('header.app-header + #app[role="main"]').should('exist');
        cy.get('header.app-header').should('not.have.css', 'position', 'fixed');
        cy.get('header.app-header').should('not.have.css', 'position', 'sticky');

        cy.get('#chef-nav a').should('have.length', 2);
        cy.get('#logout-btn').should('be.visible');
        cy.document().should((doc) => {
          const logout = doc.getElementById('logout-btn')!.getBoundingClientRect();
          doc.querySelectorAll('#chef-nav a').forEach((link) => {
            const rect = link.getBoundingClientRect();
            expect(overlaps(rect, logout), `"${link.textContent}" overlaps Log out`).to.be.false;
          });
        });

        cy.assertMinTouchTarget('#logout-btn');
        cy.assertMinTouchTarget('#chef-nav a');
        cy.assertNoHorizontalOverflow();
      });

      if (name === 'mobile') {
        it('chef: brand and Log out share row 1, the chef nav wraps to row 2', () => {
          stubApis(CHEF);
          cy.visit('/#/does-not-exist');
          cy.wait('@getMe');
          cy.assertSideBySide('.app-header__brand', '#logout-btn');
          cy.assertStacked('#logout-btn', '#chef-nav');
        });
      } else {
        it('chef: brand, chef nav and Log out sit on one row', () => {
          stubApis(CHEF);
          cy.visit('/#/does-not-exist');
          cy.wait('@getMe');
          cy.assertSideBySide('.app-header__brand', '#chef-nav');
          cy.assertSideBySide('#chef-nav', '#logout-btn');
        });
      }

      it('chef: the current page link has aria-current="page"', () => {
        stubApis(CHEF);
        cy.visit('/#/batches');
        cy.wait('@getMe');
        cy.get('a[href="#/batches"]').should('have.attr', 'aria-current', 'page');
        cy.get('a[href="#/varieties"]').should('not.have.attr', 'aria-current');
      });

      it('non-chef: header has Log out but no chef nav', () => {
        stubApis(CUSTOMER);
        cy.visit('/#/does-not-exist');
        cy.wait('@getMe');
        cy.get('header.app-header #logout-btn').should('be.visible');
        cy.get('#chef-nav').should('not.exist');
      });

      it('scrolled to the bottom of the request form, the submit button is fully visible and clickable', () => {
        stubApis(CHEF);
        cy.visit(`/#/?batchId=${BATCH_ID}`);
        cy.wait('@getBatch');
        cy.get('header.app-header').should('exist');
        cy.get('[data-cy="submit-button"]').should('be.visible');
        cy.scrollTo('bottom');
        cy.get('[data-cy="submit-button"]').should(($btn) => {
          const el = $btn.get(0);
          const rect = el.getBoundingClientRect();
          const win = el.ownerDocument.defaultView!;
          expect(rect.top, 'submit top').to.be.at.least(0);
          expect(rect.bottom, 'submit bottom').to.be.at.most(win.innerHeight);
          const hit = el.ownerDocument.elementFromPoint(
            rect.left + rect.width / 2,
            rect.top + rect.height / 2
          );
          expect(el.contains(hit), 'submit button is the topmost element at its centre').to.be.true;
        });
      });
    });
  });

  (Object.keys(VIEWPORTS) as ViewportName[]).forEach((name) => {
    it(`chef header passes the a11y check at ${name}`, () => {
      cy.viewport(...VIEWPORTS[name]);
      stubApis(CHEF);
      cy.visit('/#/does-not-exist');
      cy.wait('@getMe');
      cy.get('header.app-header').should('exist');
      cy.checkA11yAtViewport();
    });
  });
});

describe('US5 — Top banner', () => {
  HEADER_VIEWPORTS.forEach((name) => {
    it(`at ${name}: the banner is in flow above the header and does not cover the heading`, () => {
      cy.viewport(...VIEWPORTS[name]);
      stubApis(CHEF);
      cy.visit(`/#/?batchId=${BATCH_ID}`);
      cy.wait('@getBatch');
      cy.get('[data-cy="form-heading"]').should('be.visible');
      cy.get('header.app-header').should('exist');

      // The health-check trigger is disabled in dev (VITE_API_URL unset), so call the real
      // exported banner function: the dev server hands back the same module main.ts imports.
      cy.window()
        .then(
          (win) =>
            win.eval("import('/src/components/app-banner/app-banner.ts')") as Promise<BannerModule>
        )
        .then((mod) => mod.showBanner('API is unreachable. Some features may not work.', 'warn'));

      cy.get('body > #app-banner.app-banner.app-banner--warn[role="alert"]').should('be.visible');
      cy.get('#app-banner + header.app-header').should('exist');
      cy.get('#app-banner').should('not.have.css', 'position', 'fixed');
      cy.document().should((doc) => {
        const banner = doc.getElementById('app-banner')!.getBoundingClientRect();
        const heading = doc.querySelector('[data-cy="form-heading"]')!.getBoundingClientRect();
        expect(heading.top, 'heading top >= banner bottom').to.be.at.least(banner.bottom);
      });
      cy.assertMinTouchTarget('.app-banner__close');
      cy.assertNoHorizontalOverflow();

      cy.get('.app-banner__close').click();
      cy.get('#app-banner').should('not.exist');
    });
  });
});

describe('US6 — Not-found page', () => {
  HEADER_VIEWPORTS.forEach((name) => {
    it(`at ${name}: the 404 card is centred with a 44px link, no overflow and passes a11y`, () => {
      cy.viewport(...VIEWPORTS[name]);
      stubApis(CUSTOMER);
      cy.visit('/#/does-not-exist');
      cy.wait('@getMe');

      cy.get('.not-found').should('be.visible');
      cy.document().should((doc) => {
        const card = doc.querySelector('.not-found')!.getBoundingClientRect();
        const viewportWidth = doc.documentElement.clientWidth;
        const leftGap = card.left;
        const rightGap = viewportWidth - card.right;
        expect(Math.abs(leftGap - rightGap), '|left gap − right gap|').to.be.at.most(2);
      });
      cy.get('.not-found__link').should('have.attr', 'href', '#/');
      cy.assertMinTouchTarget('.not-found__link');
      cy.assertNoHorizontalOverflow();
      cy.checkA11yAtViewport();
    });
  });
});

// T037: every route at the extreme widths — 320px small phone and 1920px wide monitor.
describe('Polish — no horizontal overflow at extreme widths', () => {
  const EXTREME_VIEWPORTS: [number, number][] = [
    [320, 640],
    [1920, 1080],
  ];
  /** Each route paired with an element that only exists once its real content has rendered. */
  const ROUTES: [string, string][] = [
    [`/#/?batchId=${BATCH_ID}`, '[data-cy="form-heading"]'],
    ['/#/manage/req-spot-001', '[data-cy="request-summary"]'],
    [`/#/cook?batchId=${BATCH_ID}`, '[data-cy="variety-section"]'],
    ['/#/batches', '[data-testid="empty-state"]'],
    ['/#/varieties', '[data-testid="variety-list"]'],
    ['/#/does-not-exist', '.not-found'],
  ];

  beforeEach(() => {
    stubApis(CHEF);
    cy.intercept('GET', '**/batches/*/ingredients', {
      batchId: BATCH_ID,
      batchName: 'Christmas 2026',
      isFinalized: false,
      totalConfirmedRequests: 1,
      byVariety: [
        {
          varietyId: 'variety-classic',
          varietyName: 'Classic',
          confirmedCount: 1,
          ingredients: [
            {
              ingredientId: 'i-rum',
              name: 'Rum',
              totalQuantity: 2,
              unit: 'bottle',
              category: 'alcohol',
              acquired: false,
            },
          ],
        },
      ],
      totals: [{ name: 'Rum', totalQuantity: 2, unit: 'bottle', category: 'alcohol' }],
    });
    cy.intercept('GET', '**/requests/*', {
      requestId: 'req-spot-001',
      status: 'CONFIRMED',
      requesterName: 'José Colón',
      variety: { varietyId: 'variety-classic', name: 'Classic' },
      pickupDate: '2026-12-20',
      pickupTime: '14:00',
      exchangeLocation: 'Calle Loíza 1500, Santurce, San Juan',
      bottleProvided: false,
      bottleVolumeMl: null,
      costContribution: true,
      reminders: [],
      createdAt: '2026-03-29T00:00:00Z',
      updatedAt: '2026-03-29T00:00:00Z',
      batch: { batchId: BATCH_ID, batchName: 'Christmas 2026', cutoffDate: '2026-12-01' },
      editable: true,
    });
    cy.intercept('GET', '**/chef/varieties', { varieties: [] });
  });

  EXTREME_VIEWPORTS.forEach(([width, height]) => {
    ROUTES.forEach(([route, contentSel]) => {
      it(`${route} at ${width}×${height}`, () => {
        cy.viewport(width, height);
        cy.visit(route);
        cy.get('header.app-header').should('exist');
        cy.get(contentSel).should('be.visible');
        cy.assertNoHorizontalOverflow();
      });
    });
  });
});
