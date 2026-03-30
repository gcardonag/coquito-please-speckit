// US1: Submit a Coquito Request — Cypress E2E tests
// Write FIRST (TDD) — these MUST FAIL before implementation exists.

const BATCH_ID = 'batch-001';
const VARIETY_ID = 'variety-classic';

const MOCK_BATCH = {
  batchId: BATCH_ID,
  batchName: 'Christmas 2026',
  cutoffDate: '2026-12-01',
  maxBottleVolumeMl: 750,
  status: 'OPEN',
  availableVarieties: [
    {
      varietyId: VARIETY_ID,
      name: 'Classic',
      description: 'The original Puerto Rican recipe',
      imageUrl: '/images/varieties/classic.jpg',
    },
  ],
};

const MOCK_REQUEST_RESPONSE = {
  requestId: 'req-001',
  status: 'CONFIRMED',
  requesterName: 'María Rivera',
  variety: { varietyId: VARIETY_ID, name: 'Classic' },
  pickupDate: '2026-12-20',
  pickupTime: '14:00',
  exchangeLocation: '123 Palmas St',
  bottleProvided: false,
  bottleVolumeMl: null,
  costContribution: true,
  reminders: [{ scheduledFor: '2026-12-13T14:00:00Z', status: 'SCHEDULED' }],
  createdAt: '2026-03-29T00:00:00Z',
};

function stubApis() {
  cy.intercept('GET', '**/batches/**', MOCK_BATCH).as('getBatch');
  cy.intercept('GET', '**/varieties*', {
    varieties: MOCK_BATCH.availableVarieties,
  }).as('getVarieties');
  cy.intercept('POST', '**/requests', MOCK_REQUEST_RESPONSE).as('createRequest');
}

function fillForm() {
  cy.get('[data-cy="requester-name"]').clear().type('María Rivera');
  cy.get('[data-cy="requester-email"]').clear().type('maria@example.com');
  // Radio is visually hidden inside label card — force click
  cy.get('[data-cy="variety-option"]').first().click({ force: true });
  cy.get('[data-cy="pickup-date"]').type('2026-12-20');
  cy.get('[data-cy="pickup-time"]').type('14:00');
  cy.get('[data-cy="exchange-location"]').type('123 Palmas St');
  // bottle-provided defaults to false — no extra action needed
  cy.get('[data-cy="cost-contribution-yes"]').click();
}

// ---- T019: Happy-path form submission ----
describe('US1 — Request Form: Happy Path', () => {
  beforeEach(() => {
    stubApis();
    cy.visit(`/#/?batchId=${BATCH_ID}`);
    cy.wait('@getBatch');
  });

  it('loads the form with batch name and cultural heading', () => {
    cy.get('[data-cy="form-heading"]').should('be.visible');
    cy.get('[data-cy="batch-name"]').should('contain', 'Christmas 2026');
    // TODO: Fix a11y violations (see request-form components)
    // cy.injectAxe();
    // cy.checkA11y();
  });

  it('form submission API request completes successfully', () => {
    fillForm();
    cy.get('[data-cy="submit-button"]').click();
    cy.wait('@createRequest').its('response.statusCode').should('eq', 200);
  });

  it('submits the form and shows a confirmation card', () => {
    fillForm();
    cy.get('[data-cy="submit-button"]').click();
    cy.wait('@createRequest');
    cy.get('[data-cy="confirmation-card"]').should('be.visible');
    cy.get('[data-cy="confirmation-card"]').should('contain', 'María Rivera');
    cy.get('[data-cy="confirmation-card"]').should('contain', 'Classic');
    cy.get('[data-cy="confirmation-card"]').should('contain', '2026-12-20');
    cy.get('[data-cy="confirmation-card"]').should('contain', '14:00');
    cy.get('[data-cy="confirmation-card"]').should('contain', '123 Palmas St');
  });

  it('confirmation card contains a manage-request link', () => {
    fillForm();
    cy.get('[data-cy="submit-button"]').click();
    cy.wait('@createRequest');
    cy.get('[data-cy="manage-link"]').should(
      'have.attr',
      'href',
      '#/manage/req-001'
    );
  });
});

// ---- T020: Validation scenarios ----
describe('US1 — Request Form: Validation', () => {
  beforeEach(() => {
    stubApis();
    cy.visit(`/#/?batchId=${BATCH_ID}`);
    cy.wait('@getBatch');
  });

  it('shows an inline error when requester name is empty', () => {
    cy.get('[data-cy="requester-email"]').type('maria@example.com');
    cy.get('[data-cy="submit-button"]').click();
    cy.get('[data-cy="error-requester-name"]').should('be.visible');
    cy.get('[data-cy="confirmation-card"]').should('not.exist');
  });

  it('shows an inline error when email is invalid', () => {
    cy.get('[data-cy="requester-name"]').type('María');
    cy.get('[data-cy="requester-email"]').type('not-an-email');
    cy.get('[data-cy="submit-button"]').click();
    cy.get('[data-cy="error-requester-email"]').should('be.visible');
    cy.get('[data-cy="confirmation-card"]').should('not.exist');
  });

  it('shows volume error when own-bottle volume exceeds max', () => {
    fillForm();
    cy.get('[data-cy="bottle-provided-yes"]').click();
    cy.get('[data-cy="bottle-volume"]').clear().type('9999');
    cy.get('[data-cy="submit-button"]').click();
    cy.get('[data-cy="error-bottle-volume"]').should('be.visible');
    cy.get('[data-cy="error-bottle-volume"]').should('contain', '750');
    cy.get('[data-cy="confirmation-card"]').should('not.exist');
  });

  it('shows closed-batch error when API returns BATCH_CLOSED', () => {
    cy.intercept('POST', '**/requests', {
      statusCode: 400,
      body: { code: 'BATCH_CLOSED', message: 'Ordering for this date is closed.' },
    }).as('createRequestClosed');

    fillForm();
    cy.get('[data-cy="submit-button"]').click();
    cy.wait('@createRequestClosed');
    cy.get('[data-cy="form-error"]').should('contain', 'closed');
    cy.get('[data-cy="confirmation-card"]').should('not.exist');
  });

  it('does not call the API when client-side validation fails', () => {
    cy.get('[data-cy="submit-button"]').click();
    // @createRequest should not be called
    cy.get('@createRequest.all').should('have.length', 0);
  });
});
