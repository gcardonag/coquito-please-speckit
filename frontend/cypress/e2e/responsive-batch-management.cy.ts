// 007 US1 — Batch management list/detail layout at mobile, tablet and desktop widths.
// See specs/007-responsive-layout/contracts/ui-layout.md (Flow 4).
import { VIEWPORTS } from '../support/viewports';

const BATCHES = Array.from({ length: 6 }, (_, i) => ({
  batchId: `b-${i + 1}`,
  batchName: `Holiday Batch ${i + 1}`,
  cutoffDate: '2026-12-15',
  maxBottleVolumeMl: 750,
  status: i === 0 ? 'OPEN' : 'CLOSED',
  availableVarietyIds: ['v-1', 'v-2'],
  activeRequestCount: 3,
  createdAt: '2026-10-01T00:00:00Z',
}));

const VARIETIES = ['Classic', 'Chocolate', 'Pistachio', 'Nutella', 'Guava'].map((name, i) => ({
  varietyId: `v-${i + 1}`,
  name,
  description: `${name} coquito`,
  imageUrl: '',
}));

/** Browser default background for an unstyled <button> (Chromium "ButtonFace"). */
const DEFAULT_BUTTON_BG = 'rgb(239, 239, 239)';

function stubApi(): void {
  cy.intercept('GET', '**/me', {
    body: { userId: 'u-chef', role: 'chef', email: 'chef@example.com' },
  });
  cy.intercept('GET', '**/batches', { body: { batches: BATCHES } }).as('getBatches');
  cy.intercept('GET', '**/varieties*', { body: { varieties: VARIETIES } }).as('getVarieties');
  cy.intercept('GET', '**/chef/batches/*/access', { body: { users: [] } }).as('getAccess');
}

/** Open the first (OPEN) batch in the detail panel and wait for its form to render. */
function selectFirstBatch(): void {
  cy.get('[data-batch-id]').first().click();
  cy.wait('@getVarieties');
  cy.get('[data-testid=edit-batch-form]').should('be.visible');
}

/** scrollIntoView can settle a fraction of a pixel past the edge (e.g. -0.03125 on Linux). */
const SUBPIXEL_TOLERANCE_PX = 1;

/** Assert the top edge of the first match of `sel` lies inside the visible viewport. */
function assertTopInViewport(sel: string): void {
  cy.window().then((win) => {
    cy.get(sel).should(($el) => {
      const top = $el[0].getBoundingClientRect().top;
      expect(top, `${sel} top`).to.be.at.least(-SUBPIXEL_TOLERANCE_PX);
      expect(top, `${sel} top`).to.be.below(win.innerHeight);
    });
  });
}

/** Assert the first match of `sel` lies entirely inside the visible viewport. */
function assertFullyInViewport(sel: string): void {
  cy.window().then((win) => {
    cy.get(sel).should(($el) => {
      const r = $el[0].getBoundingClientRect();
      expect(r.top, `${sel} top`).to.be.at.least(-SUBPIXEL_TOLERANCE_PX);
      expect(r.left, `${sel} left`).to.be.at.least(-SUBPIXEL_TOLERANCE_PX);
      expect(r.bottom, `${sel} bottom`).to.be.at.most(win.innerHeight);
      expect(r.right, `${sel} right`).to.be.at.most(win.innerWidth);
    });
  });
}

describe('007 US1 — Responsive batch management', () => {
  (Object.keys(VIEWPORTS) as Array<keyof typeof VIEWPORTS>).forEach((name) => {
    describe(`at ${name}`, () => {
      beforeEach(() => {
        stubApi();
        cy.viewport(...VIEWPORTS[name]);
        cy.visit('/#/batches');
        cy.wait('@getBatches');
      });

      it('has no horizontal overflow, adequate touch targets and no a11y violations', () => {
        selectFirstBatch();
        cy.assertNoHorizontalOverflow();
        cy.assertMinTouchTarget('button');
        cy.checkA11yAtViewport();
      });

      it('shows the Close Batch dialog fully inside the viewport', () => {
        selectFirstBatch();
        cy.get('[data-testid=close-batch-btn]').click();
        assertFullyInViewport('.batch-dialog');
        cy.get('[data-testid=dialog-cancel-btn]').click();
      });

      if (name === 'desktop') {
        it('shows the list and detail side by side with the detail in view', () => {
          selectFirstBatch();
          cy.assertSideBySide('[data-testid=batch-list]', '[data-testid=batch-detail]');
          assertTopInViewport('[data-testid=batch-detail]');
        });

        it('lays the variety checklist out in at least two columns', () => {
          selectFirstBatch();
          cy.assertSideBySide(
            '.batch-form__variety-item:nth-child(1)',
            '.batch-form__variety-item:nth-child(2)'
          );
        });

        it('puts the access search input and Search button on one row', () => {
          selectFirstBatch();
          cy.get('[data-testid=manage-access-toggle]').click();
          cy.wait('@getAccess');
          // The sticky detail panel scrolls on its own; bring the access panel into its view.
          cy.get('#access-search-input').scrollIntoView();
          cy.assertSideBySide('#access-search-input', '[data-testid=access-search-btn]');
        });

        it('styles the edit form and primary buttons from the design tokens', () => {
          selectFirstBatch();
          cy.get('[data-testid=edit-batch-form]').should('have.class', 'batch-form');
          cy.get('.btn--primary')
            .first()
            .should(($btn) => {
              const bg = getComputedStyle($btn[0]).backgroundColor;
              expect(bg).not.to.equal('rgba(0, 0, 0, 0)');
              expect(bg).not.to.equal(DEFAULT_BUTTON_BG);
            });
        });
      } else {
        it('stacks the detail below the list and scrolls it into view on select', () => {
          selectFirstBatch();
          cy.assertStacked('[data-testid=batch-list]', '[data-testid=batch-detail]');
          assertTopInViewport('[data-testid=batch-detail]');
        });
      }
    });
  });
});
