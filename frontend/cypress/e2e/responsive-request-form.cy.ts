// US2 (007-responsive-layout): request form layout at mobile, tablet and desktop widths.
// Written FIRST (TDD) — layout assertions MUST fail before T020/T021 are implemented.
import { VIEWPORTS } from '../support/viewports';

const BATCH_ID = 'batch-001';

/** OPEN batch with 6 varieties; same shape as the MOCK_BATCH fixture in request-form.cy.ts. */
const MOCK_BATCH = {
  batchId: BATCH_ID,
  batchName: 'Christmas 2026',
  cutoffDate: '2026-12-01',
  maxBottleVolumeMl: 750,
  status: 'OPEN',
  availableVarieties: ['classic', 'chocolate', 'pistachio', 'coffee', 'pumpkin', 'nutella'].map(
    (slug) => ({
      varietyId: `variety-${slug}`,
      name: slug.charAt(0).toUpperCase() + slug.slice(1),
      description: `A delicious ${slug} coquito`,
      imageUrl: `/images/varieties/${slug}.jpg`,
    })
  ),
};

const MOCK_REQUEST_RESPONSE = {
  requestId: 'req-001',
  status: 'CONFIRMED',
  requesterName: 'María Rivera',
  variety: { varietyId: 'variety-classic', name: 'Classic' },
  pickupDate: '2026-12-20',
  pickupTime: '14:00',
  exchangeLocation: '123 Palmas St',
  bottleProvided: false,
  bottleVolumeMl: null,
  costContribution: true,
  reminders: [{ scheduledFor: '2026-12-13T14:00:00Z', status: 'SCHEDULED' }],
  createdAt: '2026-03-29T00:00:00Z',
};

/** Selector pairs for the two side-by-side field pairs. */
const FIELD_PAIRS: Array<[string, string]> = [
  ['#requester-name', '#requester-email'],
  ['#pickup-date', '#pickup-time'],
];

/** Selector pairs for the options of each toggle fieldset (bottle preference, cost). */
const TOGGLE_PAIRS: Array<[string, string]> = [
  ['label[for="bottle-provided-no"]', 'label[for="bottle-provided-yes"]'],
  ['label[for="cost-true"]', 'label[for="cost-false"]'],
];

function visitForm(viewport: readonly [number, number]) {
  cy.viewport(...viewport);
  cy.intercept('GET', '**/batches/*/config', MOCK_BATCH).as('getBatch');
  cy.intercept('GET', '**/varieties*', { varieties: MOCK_BATCH.availableVarieties });
  cy.visit(`/#/?batchId=${BATCH_ID}`);
  cy.wait('@getBatch');
  cy.get('#coquito-request-form').should('be.visible');
}

describe('US2 — Responsive request form', () => {
  context('desktop', () => {
    beforeEach(() => visitForm(VIEWPORTS.desktop));

    it('places field pairs and toggle options side by side', () => {
      FIELD_PAIRS.forEach(([a, b]) => cy.assertSideBySide(a, b));
      TOGGLE_PAIRS.forEach(([a, b]) => cy.assertSideBySide(a, b));
    });

    it('shows at least 4 varieties per row', () => {
      [1, 2, 3].forEach((n) =>
        cy.assertSideBySide(`.variety-card:nth-child(${n})`, `.variety-card:nth-child(${n + 1})`)
      );
    });

    it('uses a wide form container capped at --max-width-form', () => {
      cy.get('.request-form-card').should(($card) => {
        const width = $card[0].getBoundingClientRect().width;
        expect(width, 'form container width').to.be.at.least(896);
        expect(width, 'form container width').to.be.at.most(960);
      });
    });

    it('shows each error under its own field without misaligning the pair', () => {
      cy.get('[data-cy="submit-button"]').click();
      ['requester-name', 'requester-email', 'pickup-date', 'pickup-time'].forEach((id) => {
        cy.get(`#error-${id}`).should('be.visible');
        cy.get(`#${id}`).then(($input) => {
          const input = $input[0].getBoundingClientRect();
          cy.get(`#error-${id}`).should(($err) => {
            const err = $err[0].getBoundingClientRect();
            expect(err.top, `#error-${id} below its input`).to.be.at.least(input.bottom);
            expect(err.left, `#error-${id} left edge`).to.be.closeTo(input.left, 1);
            expect(err.right, `#error-${id} within its field`).to.be.at.most(input.right + 1);
          });
        });
      });
      FIELD_PAIRS.forEach(([a, b]) => cy.assertSideBySide(a, b));
    });

    it('keeps the pair aligned when only one field has an error', () => {
      cy.get('#requester-name').type('María Rivera');
      cy.get('#pickup-time').type('14:00');
      cy.get('[data-cy="submit-button"]').click();
      cy.get('#error-requester-email').should('be.visible');
      cy.get('#error-pickup-date').should('be.visible');
      FIELD_PAIRS.forEach(([a, b]) => cy.assertSideBySide(a, b));
    });

    it('has no horizontal overflow and passes a11y', () => {
      cy.assertNoHorizontalOverflow();
      cy.checkA11yAtViewport();
    });
  });

  context('tablet', () => {
    beforeEach(() => visitForm(VIEWPORTS.tablet));

    it('places field pairs side by side', () => {
      FIELD_PAIRS.forEach(([a, b]) => cy.assertSideBySide(a, b));
    });

    it('has no horizontal overflow and passes a11y', () => {
      cy.assertNoHorizontalOverflow();
      cy.checkA11yAtViewport();
    });
  });

  context('mobile', () => {
    beforeEach(() => visitForm(VIEWPORTS.mobile));

    it('stacks field pairs and toggle options', () => {
      FIELD_PAIRS.forEach(([a, b]) => cy.assertStacked(a, b));
      TOGGLE_PAIRS.forEach(([a, b]) => cy.assertStacked(a, b));
    });

    it('keeps the hero heading to at most 2 lines', () => {
      cy.get('[data-cy="form-heading"]').should(($h) => {
        const style = getComputedStyle($h[0]);
        const lineHeight = parseFloat(style.lineHeight);
        expect(lineHeight, 'computed line-height in px').to.be.greaterThan(0);
        expect($h[0].getBoundingClientRect().height, 'heading height').to.be.at.most(
          lineHeight * 2 + 1
        );
      });
    });

    it('shows the confirmation card and manage link after submitting', () => {
      cy.intercept('POST', '**/requests', MOCK_REQUEST_RESPONSE).as('createRequest');
      cy.get('#requester-name').type('María Rivera');
      cy.get('#requester-email').type('maria@example.com');
      cy.get('label.variety-card').first().click();
      cy.get('#pickup-date').type('2026-12-20');
      cy.get('#pickup-time').type('14:00');
      cy.get('#exchange-location').type('123 Palmas St');
      cy.get('[data-cy="submit-button"]').click();
      cy.wait('@createRequest');
      cy.get('[data-cy="confirmation-card"]').should('be.visible');
      cy.get('.manage-link-btn').scrollIntoView().should('be.visible');
      cy.assertNoHorizontalOverflow();
    });

    it('has no horizontal overflow and passes a11y', () => {
      cy.assertNoHorizontalOverflow();
      cy.checkA11yAtViewport();
    });
  });
});
