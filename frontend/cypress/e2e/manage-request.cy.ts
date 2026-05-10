// US2: Manage an Existing Request — Cypress E2E tests
// Write FIRST (TDD) — must FAIL before implementation exists.

const REQUEST_ID = 'req-manage-001';

const MOCK_REQUEST_EDITABLE = {
  requestId: REQUEST_ID,
  status: 'CONFIRMED',
  requesterName: 'José Colón',
  variety: { varietyId: 'v-classic', name: 'Classic' },
  pickupDate: '2026-12-20',
  pickupTime: '14:00',
  exchangeLocation: '123 Palmas St',
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

const MOCK_REQUEST_LOCKED = {
  ...MOCK_REQUEST_EDITABLE,
  editable: false,
};

const MOCK_UPDATED_REQUEST = {
  ...MOCK_REQUEST_EDITABLE,
  variety: { varietyId: 'v-chocolate', name: 'Chocolate' },
  pickupTime: '16:00',
};

const MOCK_CANCELLED = {
  requestId: REQUEST_ID,
  status: 'CANCELLED',
  cancelledAt: '2026-03-29T12:00:00Z',
};

function stubGetRequest(response = MOCK_REQUEST_EDITABLE) {
  cy.intercept('GET', `**/requests/${REQUEST_ID}`, response).as('getRequest');
}

describe('US2 — Manage Request: View & Edit', () => {
  beforeEach(() => {
    stubGetRequest();
    cy.visit(`/#/manage/${REQUEST_ID}`);
    cy.wait('@getRequest');
  });

  it('loads and displays request details', () => {
    cy.get('[data-cy="request-summary"]').should('be.visible');
    cy.get('[data-cy="request-summary"]').should('contain', 'José Colón');
    cy.get('[data-cy="request-summary"]').should('contain', 'Classic');
    cy.get('[data-cy="request-summary"]').should('contain', '2026-12-20');
    cy.get('[data-cy="request-summary"]').should('contain', '123 Palmas St');
  });

  it('shows Edit and Cancel buttons when editable', () => {
    cy.get('[data-cy="edit-button"]').should('be.visible');
    cy.get('[data-cy="cancel-button"]').should('be.visible');
  });

  it('entering edit mode shows pre-filled form', () => {
    cy.get('[data-cy="edit-button"]').click();
    cy.get('[data-cy="edit-form"]').should('be.visible');
    cy.get('[data-cy="pickup-time"]').should('have.value', '14:00');
    cy.get('[data-cy="exchange-location"]').should('have.value', '123 Palmas St');
  });

  it('saving edit calls PUT and shows updated summary', () => {
    cy.intercept('PUT', `**/requests/${REQUEST_ID}`, MOCK_UPDATED_REQUEST).as('updateRequest');
    // After save, the page re-fetches via GET — stub it to return updated data
    cy.intercept('GET', `**/requests/${REQUEST_ID}`, MOCK_UPDATED_REQUEST).as('getUpdatedRequest');

    cy.get('[data-cy="edit-button"]').click();
    cy.get('[data-cy="pickup-time"]').clear().type('16:00');
    cy.get('[data-cy="save-button"]').click();
    cy.wait('@updateRequest');
    cy.wait('@getUpdatedRequest');

    cy.get('[data-cy="request-summary"]').should('contain', '16:00');
    cy.get('[data-cy="request-summary"]').should('contain', 'Chocolate');
  });
});

describe('US2 — Manage Request: Cancel', () => {
  beforeEach(() => {
    stubGetRequest();
    cy.visit(`/#/manage/${REQUEST_ID}`);
    cy.wait('@getRequest');
  });

  it('cancel button opens confirmation dialog', () => {
    cy.get('[data-cy="cancel-button"]').click();
    cy.get('[data-cy="cancel-dialog"]').should('be.visible');
  });

  it('confirming cancel calls DELETE and shows cancellation message', () => {
    cy.intercept('POST', `**/requests/${REQUEST_ID}/cancel`, MOCK_CANCELLED).as('cancelRequest');

    cy.get('[data-cy="cancel-button"]').click();
    cy.get('[data-cy="cancel-confirm"]').click();
    cy.wait('@cancelRequest');

    cy.get('[data-cy="cancelled-message"]').should('be.visible');
    cy.get('[data-cy="cancelled-message"]').should('contain', 'cancelled');
  });

  it('dismissing the dialog does not cancel the request', () => {
    cy.get('[data-cy="cancel-button"]').click();
    cy.get('[data-cy="cancel-dismiss"]').click();
    cy.get('[data-cy="cancel-dialog"]').should('not.be.visible');
    cy.get('[data-cy="request-summary"]').should('be.visible');
  });
});

describe('US2 — Manage Request: Locked after cut-off', () => {
  it('shows read-only view with friendly locked message when not editable', () => {
    cy.intercept('GET', `**/requests/${REQUEST_ID}`, MOCK_REQUEST_LOCKED).as('getRequestLocked');
    cy.visit(`/#/manage/${REQUEST_ID}`);
    cy.wait('@getRequestLocked');

    cy.get('[data-cy="locked-banner"]').should('be.visible');
    cy.get('[data-cy="edit-button"]').should('not.exist');
    cy.get('[data-cy="cancel-button"]').should('not.exist');
    cy.get('[data-cy="request-summary"]').should('contain', 'José Colón');
  });
});

describe('US2 — Manage Request: Not found', () => {
  it('shows friendly error when request ID is unknown', () => {
    cy.intercept('GET', `**/requests/${REQUEST_ID}`, {
      statusCode: 404,
      body: { code: 'REQUEST_NOT_FOUND', message: 'Not found' },
    }).as('getRequestNotFound');

    cy.visit(`/#/manage/${REQUEST_ID}`);
    cy.wait('@getRequestNotFound');
    cy.get('[data-cy="not-found-message"]').should('be.visible');
  });
});
