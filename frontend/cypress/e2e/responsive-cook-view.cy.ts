// 007 US4: Cook view responsive layout — Cypress E2E tests (contracts/ui-layout.md, Flow 3)

import { VIEWPORTS } from '../support/viewports';

const BATCH_ID = 'b-cook-resp-001';
const COOK_SECRET = 'test-secret';

/** Max difference (px) allowed between the preview banner edges and the content area edges. */
const EDGE_TOLERANCE_PX = 1;

/** Max difference (px) allowed between the totals section width and the content width. */
const WIDTH_TOLERANCE_PX = 2;

const SECTION = '[data-cy="variety-section"]';
const SECOND_SECTION = '[data-cy="variety-section"]:nth-child(2)';
const TOTALS = '[data-cy="totals-section"]';
const BANNER = '[data-cy="preview-banner"]';
const CONTENT = '.cook-main';

/** Unfinalized list (so the preview banner shows) with 3 varieties; same shape as cook-view.cy.ts. */
const MOCK_INGREDIENT_LIST = {
  batchId: BATCH_ID,
  batchName: 'Christmas 2026',
  isFinalized: false,
  totalConfirmedRequests: 5,
  byVariety: [
    {
      varietyId: 'v-classic',
      varietyName: 'Classic',
      confirmedCount: 2,
      ingredients: [
        {
          ingredientId: 'i-rum',
          name: 'Rum',
          totalQuantity: 2,
          unit: 'bottle',
          category: 'alcohol',
          acquired: false,
        },
        {
          ingredientId: 'i-coconut',
          name: 'Coconut cream',
          totalQuantity: 4,
          unit: 'can',
          category: 'dairy',
          acquired: true,
        },
      ],
    },
    {
      varietyId: 'v-choco',
      varietyName: 'Chocolate',
      confirmedCount: 2,
      ingredients: [
        {
          ingredientId: 'i-cacao',
          name: 'Cacao powder',
          totalQuantity: 0.5,
          unit: 'cup',
          category: 'baking',
          acquired: false,
        },
      ],
    },
    {
      varietyId: 'v-pistachio',
      varietyName: 'Pistachio',
      confirmedCount: 1,
      ingredients: [
        {
          ingredientId: 'i-pistachio',
          name: 'Pistachio paste',
          totalQuantity: 1,
          unit: 'jar',
          category: 'baking',
          acquired: false,
        },
      ],
    },
  ],
  totals: [
    { name: 'Rum', totalQuantity: 2, unit: 'bottle', category: 'alcohol' },
    { name: 'Coconut cream', totalQuantity: 4, unit: 'can', category: 'dairy' },
    { name: 'Cacao powder', totalQuantity: 0.5, unit: 'cup', category: 'baking' },
    { name: 'Pistachio paste', totalQuantity: 1, unit: 'jar', category: 'baking' },
  ],
};

/** Stub the ingredient list, open the cook view and wait for it to render. */
function visitCookView(): void {
  cy.intercept('GET', '**/batches/*/ingredients', {
    statusCode: 200,
    body: MOCK_INGREDIENT_LIST,
  }).as('getIngredients');
  cy.visit(`/#/cook?batchId=${BATCH_ID}&cookSecret=${COOK_SECRET}`);
  cy.wait('@getIngredients');
  cy.get(SECTION).should('have.length', 3);
}

/** Width of an element's content box (border box minus horizontal padding and borders). */
function contentWidth(el: HTMLElement): number {
  const style = getComputedStyle(el);
  const horizontalInsets = [
    style.paddingLeft,
    style.paddingRight,
    style.borderLeftWidth,
    style.borderRightWidth,
  ].reduce((sum, v) => sum + parseFloat(v), 0);
  return el.getBoundingClientRect().width - horizontalInsets;
}

describe('007 US4 — Cook view: desktop layout', () => {
  beforeEach(() => {
    cy.viewport(...VIEWPORTS.desktop);
    visitCookView();
  });

  it('shows the first two variety sections side by side', () => {
    cy.assertSideBySide(SECTION, SECOND_SECTION);
  });

  it('spans the totals section across the full content width', () => {
    cy.get(TOTALS).should(($totals) => {
      const content = Cypress.$(CONTENT).get(0) as HTMLElement;
      const expected = contentWidth(content);
      expect($totals[0].getBoundingClientRect().width, 'totals width').to.be.closeTo(
        expected,
        WIDTH_TOLERANCE_PX
      );
    });
  });

  it('aligns the preview banner edges with the content area', () => {
    cy.get(BANNER).should(($banner) => {
      const banner = $banner[0].getBoundingClientRect();
      const content = Cypress.$(CONTENT).get(0)!.getBoundingClientRect();
      expect(banner.left, 'banner left edge').to.be.closeTo(content.left, EDGE_TOLERANCE_PX);
      expect(banner.right, 'banner right edge').to.be.closeTo(content.right, EDGE_TOLERANCE_PX);
    });
  });
});

describe('007 US4 — Cook view: mobile layout', () => {
  beforeEach(() => {
    cy.viewport(...VIEWPORTS.mobile);
    visitCookView();
  });

  it('stacks the variety sections', () => {
    cy.assertStacked(SECTION, SECOND_SECTION);
  });

  it('does not scroll the page horizontally', () => {
    cy.get(TOTALS).should('exist');
    cy.assertNoHorizontalOverflow();
  });
});

describe('007 US4 — Cook view: narrow phone (320px)', () => {
  beforeEach(() => {
    cy.viewport(320, 640);
    visitCookView();
  });

  it('lets keyboard users reach the totals table when it scrolls sideways', () => {
    cy.get(`${TOTALS} [role="region"][tabindex="0"]`)
      .should('have.attr', 'aria-labelledby')
      .then((id) => cy.get(`#${id}`).should('have.text', 'Total Shopping List'));
    cy.assertNoHorizontalOverflow();
    cy.checkA11yAtViewport();
  });
});

describe('007 US4 — Cook view: every viewport', () => {
  (Object.keys(VIEWPORTS) as Array<keyof typeof VIEWPORTS>).forEach((name) => {
    context(`at ${name}`, () => {
      beforeEach(() => {
        cy.viewport(...VIEWPORTS[name]);
        visitCookView();
      });

      it('keeps every ingredient row at least 44px tall', () => {
        cy.assertMinTouchTarget('.ingredient-row');
      });

      it('passes the WCAG 2.1 AA accessibility check', () => {
        cy.checkA11yAtViewport();
      });
    });
  });
});
