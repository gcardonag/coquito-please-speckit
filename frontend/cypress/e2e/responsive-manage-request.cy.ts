// 007 US3: Manage request — responsive layout (contracts/ui-layout.md, Flow 2).
// Written first (TDD): must fail before the manage-request layout changes exist.
import { VIEWPORTS } from '../support/viewports';

const REQUEST_ID = 'req-responsive-001';

/** Pickup location longer than 30 characters, to prove long values wrap on mobile. */
const LONG_LOCATION = 'Calle Fortaleza 123, Viejo San Juan, PR 00901';

const MOCK_REQUEST_EDITABLE = {
  requestId: REQUEST_ID,
  status: 'CONFIRMED',
  requesterName: 'José Colón',
  variety: { varietyId: 'v-classic', name: 'Classic' },
  pickupDate: '2026-12-20',
  pickupTime: '14:00',
  exchangeLocation: LONG_LOCATION,
  bottleProvided: false,
  bottleVolumeMl: null,
  costContribution: true,
  reminders: [{ scheduledFor: '2026-12-13T14:00:00Z', status: 'SCHEDULED' }],
  createdAt: '2026-03-29T00:00:00Z',
  updatedAt: '2026-03-29T00:00:00Z',
  batch: {
    batchId: 'b-001',
    batchName: 'Christmas 2026',
    cutoffDate: '2026-12-01',
    maxBottleVolumeMl: 750,
  },
  editable: true,
};

const MOCK_REQUEST_LOCKED = { ...MOCK_REQUEST_EDITABLE, editable: false };

/** Minimum gap (px) between the cancel dialog and each viewport edge on mobile. */
const DIALOG_MIN_MARGIN_PX = 16;

/** Minimum summary card width (px) at desktop, per Flow 2. */
const DESKTOP_SUMMARY_MIN_WIDTH_PX = 896;

function visitManage(response: typeof MOCK_REQUEST_EDITABLE): void {
  cy.intercept('GET', `**/requests/${REQUEST_ID}`, response).as('getRequest');
  cy.visit(`/#/manage/${REQUEST_ID}`);
  cy.wait('@getRequest');
  cy.get('[data-cy="request-summary"]').should('be.visible');
}

/** Asserts an element is horizontally centred in the viewport (equal left/right space ±1px). */
function assertCentred(sel: string): void {
  cy.get(sel).should(($el) => {
    const rect = $el[0].getBoundingClientRect();
    const right = $el[0].ownerDocument.documentElement.clientWidth - rect.right;
    expect(Math.abs(rect.left - right), `"${sel}" left/right space difference`).to.be.at.most(1);
  });
}

describe('007 US3 — Manage request at desktop', () => {
  beforeEach(() => {
    cy.viewport(...VIEWPORTS.desktop);
    visitManage(MOCK_REQUEST_EDITABLE);
  });

  it('shows a wide summary with details in two columns', () => {
    expect(LONG_LOCATION.length).to.equal(45);
    cy.get('[data-cy="request-summary"]').should(($card) => {
      expect($card[0].getBoundingClientRect().width).to.be.at.least(DESKTOP_SUMMARY_MIN_WIDTH_PX);
    });
    cy.assertSideBySide('.summary-row:nth-of-type(1)', '.summary-row:nth-of-type(2)');
    cy.assertNoHorizontalOverflow();
  });

  it('puts date and time side by side with the shared input styling', () => {
    cy.get('[data-cy="edit-button"]').click();
    cy.get('[data-cy="edit-form"]').should('be.visible');
    cy.get('[data-cy="edit-form"] .date-time-row').should('not.exist');
    cy.assertSideBySide('[data-cy="pickup-date"]', '[data-cy="pickup-time"]');

    // The request form's inputs use the shared rule in components.css, whose border is
    // --border-width-thick; the edit form must match it even on a direct visit.
    cy.document().then((doc) => {
      const expected = getComputedStyle(doc.documentElement)
        .getPropertyValue('--border-width-thick')
        .trim();
      cy.get('[data-cy="pickup-date"]').should(($input) => {
        const style = getComputedStyle($input[0]);
        expect(parseFloat(style.borderTopWidth)).to.be.at.least(1);
        expect(style.borderTopWidth).to.equal(expected);
      });
    });
    cy.assertNoHorizontalOverflow();
  });
});

describe('007 US3 — Manage request at mobile', () => {
  beforeEach(() => {
    cy.viewport(...VIEWPORTS.mobile);
    visitManage(MOCK_REQUEST_EDITABLE);
  });

  it('puts each summary label above its value', () => {
    cy.get('.summary-row').each(($row) => {
      const label = $row.find('.summary-row__label')[0].getBoundingClientRect();
      const value = $row.find('.summary-row__value')[0].getBoundingClientRect();
      expect(value.top, 'value top >= label bottom').to.be.at.least(label.bottom);
    });
    cy.assertNoHorizontalOverflow();
  });

  it('shows every action button label without clipping', () => {
    cy.get('[data-cy="edit-button"]')
      .parent()
      .find('button')
      .each(($btn) => {
        expect($btn[0].scrollWidth, $btn.text()).to.be.at.most($btn[0].clientWidth);
      });
    cy.get('[data-cy="edit-button"]').click();
    cy.get('.edit-actions button').each(($btn) => {
      expect($btn[0].scrollWidth, $btn.text()).to.be.at.most($btn[0].clientWidth);
    });
  });

  it('fits the cancel dialog within the screen with a 16px margin', () => {
    cy.get('[data-cy="cancel-button"]').click();
    cy.get('[data-cy="cancel-dialog"]').should('be.visible');
    cy.get('[data-cy="cancel-dialog"]').should(($dialog) => {
      const rect = $dialog[0].getBoundingClientRect();
      const viewportWidth = $dialog[0].ownerDocument.documentElement.clientWidth;
      expect(rect.left).to.be.at.least(DIALOG_MIN_MARGIN_PX);
      expect(rect.right).to.be.at.most(viewportWidth - DIALOG_MIN_MARGIN_PX);
    });
    cy.get('.cancel-dialog__actions button').each(($btn) => {
      expect($btn[0].scrollWidth, $btn.text()).to.be.at.most($btn[0].clientWidth);
    });
  });
});

describe('007 US3 — Locked state', () => {
  (['mobile', 'desktop'] as const).forEach((name) => {
    it(`is centred with no overflow at ${name}`, () => {
      cy.viewport(...VIEWPORTS[name]);
      visitManage(MOCK_REQUEST_LOCKED);
      cy.get('[data-cy="locked-banner"]').should('be.visible');
      assertCentred('[data-cy="locked-banner"]');
      assertCentred('[data-cy="request-summary"]');
      cy.assertNoHorizontalOverflow();
    });
  });
});

describe('007 US3 — Accessibility', () => {
  (Object.keys(VIEWPORTS) as (keyof typeof VIEWPORTS)[]).forEach((name) => {
    it(`passes WCAG 2.1 AA at ${name}`, () => {
      cy.viewport(...VIEWPORTS[name]);
      visitManage(MOCK_REQUEST_EDITABLE);
      cy.checkA11yAtViewport();
    });
  });
});
