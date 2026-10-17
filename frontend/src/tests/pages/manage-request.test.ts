/**
 * T042: Unit tests for the manage-request page
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// ---------------------------------------------------------------------------
// Mock the api module
// ---------------------------------------------------------------------------
vi.mock('../../services/api', () => ({
  getRequest: vi.fn(),
  updateRequest: vi.fn(),
  cancelRequest: vi.fn(),
  ApiRequestError: class ApiRequestError extends Error {
    code: string;
    status: number;
    constructor({ code, message, status }: { code: string; message: string; status: number }) {
      super(message);
      this.code = code;
      this.status = status;
    }
  },
}));

import * as api from '../../services/api';
import { mountManageRequest } from '../../pages/manage-request/index';

const mockGetRequest = api.getRequest as ReturnType<typeof vi.fn>;
const mockUpdateRequest = api.updateRequest as ReturnType<typeof vi.fn>;
const mockCancelRequest = api.cancelRequest as ReturnType<typeof vi.fn>;

const REQUEST_ID = 'req-001';

function makeRequest(overrides: Partial<api.RequestResponse> = {}): api.RequestResponse {
  return {
    requestId: REQUEST_ID,
    status: 'PENDING',
    requesterName: 'María',
    variety: { varietyId: 'classic', name: 'Classic Coquito' },
    pickupDate: '2026-12-20',
    pickupTime: '14:30',
    exchangeLocation: '123 Palmas St',
    bottleProvided: false,
    bottleVolumeMl: null,
    costContribution: false,
    reminders: [],
    createdAt: '2026-10-01T00:00:00Z',
    batch: {
      batchId: 'b-001',
      batchName: 'Holiday 2026',
      cutoffDate: '2026-12-01',
      maxBottleVolumeMl: 1000,
    },
    editable: true,
    ...overrides,
  };
}

function apiError(code: string, message: string, status: number): Error {
  return new api.ApiRequestError({ code, message, status });
}

function q<T extends Element = HTMLElement>(container: HTMLElement, cy: string): T | null {
  return container.querySelector<T>(`[data-cy="${cy}"]`);
}

function summaryValues(container: HTMLElement): Record<string, string> {
  const out: Record<string, string> = {};
  container.querySelectorAll('[data-cy="request-summary"] .summary-row').forEach((row) => {
    const label = row.querySelector('.summary-row__label')!.textContent!.trim();
    out[label] = row.querySelector('.summary-row__value')!.textContent!.trim();
  });
  return out;
}

async function mountAndWait(container: HTMLElement, cy = 'request-summary'): Promise<void> {
  mountManageRequest(container, REQUEST_ID);
  await vi.waitFor(() => expect(q(container, cy)).not.toBeNull());
}

function setValue(container: HTMLElement, cy: string, value: string): void {
  q<HTMLInputElement>(container, cy)!.value = value;
}

function submitEditForm(container: HTMLElement): void {
  q<HTMLFormElement>(container, 'edit-form')!.dispatchEvent(
    new Event('submit', { bubbles: true, cancelable: true })
  );
}

// ---------------------------------------------------------------------------
// Shared setup: container + HTMLDialogElement stubs (jsdom lacks them)
// ---------------------------------------------------------------------------
let container: HTMLDivElement;
const originalShowModal = HTMLDialogElement.prototype.showModal;
const originalClose = HTMLDialogElement.prototype.close;

beforeEach(() => {
  vi.clearAllMocks();
  container = document.createElement('div');
  document.body.appendChild(container);
  HTMLDialogElement.prototype.showModal = function (this: HTMLDialogElement) {
    this.setAttribute('open', '');
  };
  HTMLDialogElement.prototype.close = function (this: HTMLDialogElement) {
    this.removeAttribute('open');
  };
});

afterEach(() => {
  container.remove();
  HTMLDialogElement.prototype.showModal = originalShowModal;
  HTMLDialogElement.prototype.close = originalClose;
});

// ---------------------------------------------------------------------------
// Loading / not-found / load error
// ---------------------------------------------------------------------------
describe('Initial load states', () => {
  it('shows a loading message while the request is being fetched', () => {
    mockGetRequest.mockReturnValue(new Promise(() => {}));

    mountManageRequest(container, REQUEST_ID);

    expect(mockGetRequest).toHaveBeenCalledWith(REQUEST_ID);
    expect(container.textContent).toMatch(/Loading your order details/);
  });

  it('shows the not-found card on a 404', async () => {
    mockGetRequest.mockRejectedValue(apiError('NOT_FOUND', 'nope', 404));

    await mountAndWait(container, 'not-found-message');

    const card = q(container, 'not-found-message')!;
    expect(card.textContent).toMatch(/Order not found/);
    expect(card.querySelector('a[href="#/"]')).not.toBeNull();
    expect(q(container, 'request-summary')).toBeNull();
  });

  it('shows a generic load error for non-404 API errors', async () => {
    mockGetRequest.mockRejectedValue(apiError('INTERNAL', 'boom', 500));

    mountManageRequest(container, REQUEST_ID);

    await vi.waitFor(() => expect(container.querySelector('[role="alert"]')).not.toBeNull());
    expect(container.textContent).toMatch(/couldn't load your order/);
    expect(q(container, 'not-found-message')).toBeNull();
  });

  it('shows a generic load error for non-API errors', async () => {
    mockGetRequest.mockRejectedValue(new TypeError('network down'));

    mountManageRequest(container, REQUEST_ID);

    await vi.waitFor(() => expect(container.querySelector('[role="alert"]')).not.toBeNull());
    expect(container.textContent).toMatch(/couldn't load your order/);
  });
});

// ---------------------------------------------------------------------------
// Summary card rendering
// ---------------------------------------------------------------------------
describe('Summary card', () => {
  it('renders every order detail row', async () => {
    mockGetRequest.mockResolvedValue(makeRequest());

    await mountAndWait(container);

    expect(container.querySelector('.manage-hero__heading')!.textContent).toBe('Your Request');
    expect(summaryValues(container)).toEqual({
      Name: 'María',
      Variety: 'Classic Coquito',
      'Pickup date': '2026-12-20',
      'Pickup time': '14:30',
      Location: '123 Palmas St',
      'Bottle provided': 'No',
      'Cost contribution': 'No',
    });
  });

  it('shows the bottle volume and cost contribution when provided', async () => {
    mockGetRequest.mockResolvedValue(
      makeRequest({ bottleProvided: true, bottleVolumeMl: 750, costContribution: true })
    );

    await mountAndWait(container);

    const values = summaryValues(container);
    expect(values['Bottle provided']).toBe('Yes (750ml)');
    expect(values['Cost contribution']).toBe('Yes, happy to contribute');
  });

  it('falls back to the variety id when the variety has no name', async () => {
    mockGetRequest.mockResolvedValue(
      makeRequest({ variety: { varietyId: 'chocolate' } as api.RequestResponse['variety'] })
    );

    await mountAndWait(container);

    expect(summaryValues(container).Variety).toBe('chocolate');
  });

  it('renders an empty variety when the variety is missing', async () => {
    mockGetRequest.mockResolvedValue(
      makeRequest({ variety: undefined as unknown as api.RequestResponse['variety'] })
    );

    await mountAndWait(container);

    expect(summaryValues(container).Variety).toBe('');
  });

  it('escapes HTML in user-supplied values', async () => {
    mockGetRequest.mockResolvedValue(
      makeRequest({ requesterName: `<img src=x onerror="alert('x')">&` })
    );

    await mountAndWait(container);

    const summary = q(container, 'request-summary')!;
    expect(summary.querySelector('img')).toBeNull();
    expect(summaryValues(container).Name).toBe(`<img src=x onerror="alert('x')">&`);
  });
});

// ---------------------------------------------------------------------------
// Locked state
// ---------------------------------------------------------------------------
describe('Locked (non-editable) request', () => {
  it('shows the locked banner with the cutoff date and no edit/cancel controls', async () => {
    mockGetRequest.mockResolvedValue(makeRequest({ editable: false }));

    await mountAndWait(container);

    const banner = q(container, 'locked-banner')!;
    expect(banner).not.toBeNull();
    expect(banner.textContent).toMatch(/Changes are no longer available/);
    expect(banner.textContent).toMatch(/\(2026-12-01\)/);
    expect(q(container, 'edit-button')).toBeNull();
    expect(q(container, 'cancel-button')).toBeNull();
    expect(q(container, 'edit-form')).toBeNull();
    expect(q(container, 'cancel-dialog')).toBeNull();
  });

  it('uses a generic cutoff phrase when the batch is missing', async () => {
    mockGetRequest.mockResolvedValue(makeRequest({ editable: false, batch: undefined }));

    await mountAndWait(container);

    expect(q(container, 'locked-banner')!.textContent).toMatch(/\(the cut-off date\)/);
  });
});

// ---------------------------------------------------------------------------
// Editable state + edit form
// ---------------------------------------------------------------------------
describe('Editable request — edit form', () => {
  beforeEach(() => {
    mockGetRequest.mockResolvedValue(makeRequest());
  });

  it('shows edit and cancel buttons inside the summary with the form hidden', async () => {
    await mountAndWait(container);

    const summary = q(container, 'request-summary')!;
    expect(summary.querySelector('[data-cy="edit-button"]')!.textContent).toMatch(/Edit Order/);
    expect(summary.querySelector('[data-cy="cancel-button"]')!.textContent).toBe('Cancel Order');
    expect(q(container, 'locked-banner')).toBeNull();
    expect(q(container, 'edit-form')!.closest('.edit-form-card')!.hasAttribute('hidden')).toBe(
      true
    );
  });

  it('opens the edit form pre-filled with the current values', async () => {
    await mountAndWait(container);

    q(container, 'edit-button')!.click();

    const card = q(container, 'edit-form')!.closest<HTMLElement>('.edit-form-card')!;
    expect(card.hidden).toBe(false);
    expect(q(container, 'request-summary')!.hidden).toBe(true);
    expect(card.querySelector('.edit-form-card__title')!.textContent).toBe('Edit Your Order');

    const date = q<HTMLInputElement>(container, 'pickup-date')!;
    expect(date.value).toBe('2026-12-20');
    expect(date.type).toBe('date');
    expect(date.min).toBe('2026-12-01');
    expect(q<HTMLInputElement>(container, 'pickup-time')!.value).toBe('14:30');
    expect(q<HTMLInputElement>(container, 'exchange-location')!.value).toBe('123 Palmas St');
  });

  it('places date and time side by side in a field-pair, location outside it', async () => {
    await mountAndWait(container);

    const pair = q(container, 'edit-form')!.querySelector('.field-pair')!;
    const fields = pair.querySelectorAll(':scope > .form-field');
    expect(fields).toHaveLength(2);
    expect(fields[0].querySelector('input')!.id).toBe('edit-pickup-date');
    expect(fields[1].querySelector('input')!.id).toBe('edit-pickup-time');
    expect(pair.querySelector('#edit-exchange-location')).toBeNull();
    expect(q(container, 'edit-form')!.querySelector('#edit-exchange-location')).not.toBeNull();
  });

  it('does not set a min date when the batch has no cutoff', async () => {
    mockGetRequest.mockResolvedValue(makeRequest({ batch: undefined }));

    await mountAndWait(container);

    expect(q<HTMLInputElement>(container, 'pickup-date')!.min).toBe('');
  });

  it('discard hides the form and shows the summary again without saving', async () => {
    await mountAndWait(container);
    q(container, 'edit-button')!.click();

    const discard = container.querySelector<HTMLButtonElement>('.btn-discard')!;
    expect(discard.textContent).toBe('Discard');
    discard.click();

    expect(q(container, 'request-summary')!.hidden).toBe(false);
    expect(q(container, 'edit-form')!.closest<HTMLElement>('.edit-form-card')!.hidden).toBe(true);
    expect(mockUpdateRequest).not.toHaveBeenCalled();
  });

  it('shows field errors for every empty required field and does not save', async () => {
    await mountAndWait(container);
    q(container, 'edit-button')!.click();

    setValue(container, 'pickup-date', '');
    setValue(container, 'pickup-time', '');
    setValue(container, 'exchange-location', '   ');
    submitEditForm(container);

    expect(q(container, 'error-edit-pickup-date')!.textContent).toMatch(/pick up your coquito/);
    expect(q(container, 'error-edit-pickup-time')!.textContent).toBe('What time works for you?');
    expect(q(container, 'error-edit-exchange-location')!.textContent).toBe('Where should we meet?');
    expect(q(container, 'pickup-date')!.getAttribute('aria-invalid')).toBe('true');
    expect(mockUpdateRequest).not.toHaveBeenCalled();
  });

  it('clears previous field errors on a subsequent valid submit', async () => {
    mockUpdateRequest.mockReturnValue(new Promise(() => {}));
    await mountAndWait(container);
    q(container, 'edit-button')!.click();

    setValue(container, 'pickup-time', '');
    submitEditForm(container);
    expect(q(container, 'error-edit-pickup-time')!.hidden).toBe(false);

    setValue(container, 'pickup-time', '15:00');
    submitEditForm(container);

    expect(q(container, 'error-edit-pickup-time')!.hidden).toBe(true);
    expect(q(container, 'pickup-time')!.hasAttribute('aria-invalid')).toBe(false);
  });

  it('sends only the changed fields and disables the save button while saving', async () => {
    mockUpdateRequest.mockReturnValue(new Promise(() => {}));
    await mountAndWait(container);
    q(container, 'edit-button')!.click();

    setValue(container, 'pickup-time', '16:00');
    setValue(container, 'exchange-location', '  456 Luna St  ');
    submitEditForm(container);

    expect(mockUpdateRequest).toHaveBeenCalledWith(REQUEST_ID, {
      pickupTime: '16:00',
      exchangeLocation: '456 Luna St',
    });
    const save = q<HTMLButtonElement>(container, 'save-button')!;
    expect(save.disabled).toBe(true);
    expect(save.textContent).toBe('Saving...');
  });

  it('sends an empty payload when nothing changed', async () => {
    mockUpdateRequest.mockReturnValue(new Promise(() => {}));
    await mountAndWait(container);

    submitEditForm(container);

    expect(mockUpdateRequest).toHaveBeenCalledWith(REQUEST_ID, {});
  });

  it('re-fetches and re-renders the summary with updated values after a successful save', async () => {
    mockUpdateRequest.mockResolvedValue(undefined);
    mockGetRequest
      .mockResolvedValueOnce(makeRequest())
      .mockResolvedValueOnce(makeRequest({ pickupDate: '2026-12-24' }));
    await mountAndWait(container);
    q(container, 'edit-button')!.click();

    setValue(container, 'pickup-date', '2026-12-24');
    submitEditForm(container);

    expect(mockUpdateRequest).toHaveBeenCalledWith(REQUEST_ID, { pickupDate: '2026-12-24' });
    await vi.waitFor(() => expect(summaryValues(container)['Pickup date']).toBe('2026-12-24'));
    expect(mockGetRequest).toHaveBeenCalledTimes(2);
    expect(q(container, 'request-summary')!.hidden).toBe(false);
    expect(container.querySelectorAll('[data-cy="request-summary"]')).toHaveLength(1);
  });

  it.each([
    [
      'CUTOFF_PASSED',
      'server text',
      'The cut-off date has passed. Changes are no longer permitted.',
    ],
    ['REQUEST_CANCELLED', 'server text', 'This request has been cancelled and cannot be updated.'],
    ['VALIDATION_ERROR', 'Pickup date is invalid', 'Pickup date is invalid'],
  ])('shows a friendly error for %s and re-enables save', async (code, message, expected) => {
    mockUpdateRequest.mockRejectedValue(apiError(code, message, 400));
    await mountAndWait(container);
    q(container, 'edit-button')!.click();

    submitEditForm(container);

    const formError = container.querySelector<HTMLElement>('.manage-form-error')!;
    await vi.waitFor(() => expect(formError.hidden).toBe(false));
    expect(formError.getAttribute('role')).toBe('alert');
    expect(formError.textContent).toBe(expected);
    const save = q<HTMLButtonElement>(container, 'save-button')!;
    expect(save.disabled).toBe(false);
    expect(save.textContent).toBe('💾 Save Changes');
  });

  it('shows a generic error for non-API save failures and hides it on resubmit', async () => {
    mockUpdateRequest
      .mockRejectedValueOnce(new TypeError('network'))
      .mockReturnValueOnce(new Promise(() => {}));
    await mountAndWait(container);
    q(container, 'edit-button')!.click();

    submitEditForm(container);

    const formError = container.querySelector<HTMLElement>('.manage-form-error')!;
    await vi.waitFor(() => expect(formError.hidden).toBe(false));
    expect(formError.textContent).toBe('¡Ay! Something went wrong. Please try again.');

    submitEditForm(container);
    expect(formError.hidden).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Cancel dialog
// ---------------------------------------------------------------------------
describe('Editable request — cancel dialog', () => {
  beforeEach(() => {
    mockGetRequest.mockResolvedValue(makeRequest());
  });

  it('opens the confirmation dialog when Cancel Order is clicked', async () => {
    await mountAndWait(container);
    const dialog = q<HTMLDialogElement>(container, 'cancel-dialog')!;
    expect(dialog.hasAttribute('open')).toBe(false);

    q(container, 'cancel-button')!.click();

    expect(dialog.hasAttribute('open')).toBe(true);
    expect(dialog.textContent).toMatch(/Cancel your order\?/);
    expect(q(container, 'cancel-confirm')!.textContent).toBe('Yes, cancel it');
    expect(q(container, 'cancel-dismiss')!.textContent).toBe('Keep my order');
  });

  it('dismiss closes the dialog without cancelling', async () => {
    await mountAndWait(container);
    q(container, 'cancel-button')!.click();

    q(container, 'cancel-dismiss')!.click();

    expect(q(container, 'cancel-dialog')!.hasAttribute('open')).toBe(false);
    expect(mockCancelRequest).not.toHaveBeenCalled();
    expect(q(container, 'request-summary')).not.toBeNull();
  });

  it('confirm closes the dialog, cancels, and shows the cancelled message', async () => {
    mockCancelRequest.mockResolvedValue(undefined);
    await mountAndWait(container);
    q(container, 'cancel-button')!.click();

    q(container, 'cancel-confirm')!.click();

    expect(mockCancelRequest).toHaveBeenCalledWith(REQUEST_ID);
    await vi.waitFor(() => expect(q(container, 'cancelled-message')).not.toBeNull());
    const msg = q(container, 'cancelled-message')!;
    expect(msg.textContent).toMatch(/Your order has been cancelled/);
    expect(msg.querySelector('a[href="#/"]')).not.toBeNull();
    expect(q(container, 'request-summary')).toBeNull();
    expect(q(container, 'cancel-dialog')).toBeNull();
  });

  it('shows the API error message when cancellation fails, reusing the error element', async () => {
    mockCancelRequest
      .mockRejectedValueOnce(apiError('CUTOFF_PASSED', 'Too late to cancel', 409))
      .mockRejectedValueOnce(new TypeError('network'));
    await mountAndWait(container);

    q(container, 'cancel-button')!.click();
    q(container, 'cancel-confirm')!.click();

    await vi.waitFor(() => expect(q(container, 'cancel-error')).not.toBeNull());
    const errorEl = q(container, 'cancel-error')!;
    expect(errorEl.textContent).toBe('Too late to cancel');
    expect(errorEl.getAttribute('role')).toBe('alert');
    expect(container.querySelector('.page-wrapper')!.firstElementChild).toBe(errorEl);
    expect(q(container, 'cancel-dialog')!.hasAttribute('open')).toBe(false);

    // Second failure (non-API) updates the same element instead of adding another
    errorEl.hidden = true;
    q(container, 'cancel-button')!.click();
    q(container, 'cancel-confirm')!.click();

    await vi.waitFor(() =>
      expect(errorEl.textContent).toBe('¡Ay! Something went wrong. Please try again.')
    );
    expect(errorEl.hidden).toBe(false);
    expect(container.querySelectorAll('[data-cy="cancel-error"]')).toHaveLength(1);
    expect(q(container, 'request-summary')).not.toBeNull();
  });
});
