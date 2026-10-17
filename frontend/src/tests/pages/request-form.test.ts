import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// ---------------------------------------------------------------------------
// Mock the api module
// ---------------------------------------------------------------------------
vi.mock('../../services/api', () => ({
  getBatchConfig: vi.fn(),
  createRequest: vi.fn(),
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
import { mountRequestForm } from '../../pages/request-form/index';

const mockGetBatchConfig = api.getBatchConfig as ReturnType<typeof vi.fn>;
const mockCreateRequest = api.createRequest as ReturnType<typeof vi.fn>;

function makeBatch(overrides: Partial<api.BatchConfig> = {}): api.BatchConfig {
  return {
    batchId: 'b-001',
    batchName: 'Navidad 2026',
    cutoffDate: '2026-12-01',
    maxBottleVolumeMl: 1000,
    status: 'OPEN',
    availableVarieties: [
      {
        varietyId: 'v-001',
        name: 'Classic',
        description: 'Original recipe',
        imageUrl: '/images/classic.jpg',
      },
      {
        varietyId: 'v-002',
        name: 'Nutella',
        description: 'Chocolate hazelnut',
        imageUrl: '/images/nutella.jpg',
      },
    ],
    ...overrides,
  };
}

function makeResponse(overrides: Partial<api.RequestResponse> = {}): api.RequestResponse {
  return {
    requestId: 'r-123',
    status: 'PENDING',
    requesterName: 'María Rivera',
    variety: { varietyId: 'v-001', name: 'Classic' },
    pickupDate: '2026-12-20',
    pickupTime: '14:00',
    exchangeLocation: '123 Palmas St',
    bottleProvided: false,
    bottleVolumeMl: null,
    costContribution: true,
    reminders: [],
    createdAt: '2026-10-16T00:00:00Z',
    ...overrides,
  };
}

// Poll quickly so tests settle as soon as mocked promises resolve
function waitFor(assertion: () => void): Promise<void> {
  return vi.waitFor(assertion, { interval: 1 });
}

function q<T extends Element = HTMLElement>(container: HTMLElement, cy: string): T | null {
  return container.querySelector<T>(`[data-cy="${cy}"]`);
}

function setValue(container: HTMLElement, cy: string, value: string): void {
  const input = q<HTMLInputElement>(container, cy);
  if (!input) throw new Error(`missing input ${cy}`);
  input.value = value;
}

function check(el: HTMLInputElement): void {
  el.checked = true;
  el.dispatchEvent(new Event('change', { bubbles: true }));
}

function fillValidForm(container: HTMLElement): void {
  setValue(container, 'requester-name', '  María Rivera  ');
  setValue(container, 'requester-email', 'maria@example.com');
  check(container.querySelector<HTMLInputElement>('#variety-v-001')!);
  setValue(container, 'pickup-date', '2026-12-20');
  setValue(container, 'pickup-time', '14:00');
  setValue(container, 'exchange-location', '123 Palmas St');
}

function submit(container: HTMLElement): void {
  const form = container.querySelector<HTMLFormElement>('#coquito-request-form')!;
  form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
}

function errorText(container: HTMLElement, cy: string): string {
  const el = q(container, cy)!;
  return el.hidden ? '' : (el.textContent ?? '');
}

async function mountReady(
  container: HTMLElement,
  batch: api.BatchConfig = makeBatch()
): Promise<void> {
  mockGetBatchConfig.mockResolvedValue(batch);
  mountRequestForm(container);
  await waitFor(() => {
    expect(container.querySelector('#coquito-request-form')).not.toBeNull();
  });
}

// ---------------------------------------------------------------------------
// Shared setup
// ---------------------------------------------------------------------------
let container: HTMLDivElement;
const originalHash = window.location.hash;

beforeEach(() => {
  vi.clearAllMocks();
  window.location.hash = '#/?batchId=b-001';
  container = document.createElement('div');
  document.body.appendChild(container);
});

afterEach(() => {
  container.remove();
  window.location.hash = originalHash;
});

// ---------------------------------------------------------------------------
// Load states
// ---------------------------------------------------------------------------
describe('Request form: load states', () => {
  it('shows the loading state while the batch config is pending', () => {
    mockGetBatchConfig.mockReturnValue(new Promise(() => {}));

    mountRequestForm(container);

    expect(container.textContent).toContain('Loading the coquito batch details');
    expect(mockGetBatchConfig).toHaveBeenCalledWith('b-001');
  });

  it('reads the batchId from the hash query string', async () => {
    window.location.hash = '#/?batchId=xmas%2Fspecial';
    await mountReady(container);

    expect(mockGetBatchConfig).toHaveBeenCalledWith('xmas/special');
  });

  it('falls back to a non-hash batchId source when the hash has no query', async () => {
    window.location.hash = '#/';
    await mountReady(container);

    expect(mockGetBatchConfig).toHaveBeenCalledTimes(1);
    const arg = mockGetBatchConfig.mock.calls[0][0];
    expect(typeof arg).toBe('string');
    expect(arg).not.toBe('b-001');
  });

  it('shows a config error alert when the batch cannot be loaded', async () => {
    mockGetBatchConfig.mockRejectedValue(new Error('network down'));

    mountRequestForm(container);

    await waitFor(() => {
      expect(container.querySelector('[role="alert"]')?.textContent).toContain(
        "We couldn't load the batch details"
      );
    });
    expect(container.querySelector('form')).toBeNull();
  });

  it('shows a closed message and no form when the batch is CLOSED', async () => {
    mockGetBatchConfig.mockResolvedValue(makeBatch({ status: 'CLOSED' }));

    mountRequestForm(container);

    await waitFor(() => {
      expect(container.querySelector('[role="alert"]')?.textContent).toContain(
        'no longer available to take requests'
      );
    });
    expect(container.querySelector('form')).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Form render
// ---------------------------------------------------------------------------
describe('Request form: render', () => {
  it('renders the hero with an escaped batch name', async () => {
    await mountReady(container, makeBatch({ batchName: `<b>"Tom's" & Co</b>` }));

    expect(q(container, 'form-heading')?.textContent).toBe('Coquito Please!');
    const badge = q(container, 'batch-name')!;
    expect(badge.textContent).toBe(`<b>"Tom's" & Co</b>`);
    expect(badge.querySelector('b')).toBeNull();
  });

  it('groups name+email and date+time in .field-pair wrappers', async () => {
    await mountReady(container);

    const pairs = container.querySelectorAll('.field-pair');
    expect(pairs).toHaveLength(2);

    const [contact, dateTime] = Array.from(pairs);
    const contactIds = Array.from(contact.querySelectorAll('input')).map((i) => i.id);
    expect(contactIds).toEqual(['requester-name', 'requester-email']);
    expect(contact.children).toHaveLength(2);

    const dateTimeIds = Array.from(dateTime.querySelectorAll('input')).map((i) => i.id);
    expect(dateTimeIds).toEqual(['pickup-date', 'pickup-time']);
    expect(dateTime.children).toHaveLength(2);

    // Location is not paired
    expect(q(container, 'exchange-location')?.closest('.field-pair')).toBeNull();
  });

  it('renders all form controls with correct types and constraints', async () => {
    await mountReady(container);

    const form = container.querySelector<HTMLFormElement>('#coquito-request-form')!;
    expect(form.noValidate).toBe(true);
    expect(form.getAttribute('aria-label')).toBe('Coquito request form');

    expect(q<HTMLInputElement>(container, 'requester-email')?.type).toBe('email');
    expect(q<HTMLInputElement>(container, 'pickup-date')?.min).toBe('2026-12-01');
    expect(q<HTMLInputElement>(container, 'pickup-time')?.type).toBe('time');
    expect(container.querySelectorAll('[data-cy="variety-option"]')).toHaveLength(2);
    expect(q<HTMLButtonElement>(container, 'submit-button')?.textContent).toContain(
      'Request my coquito'
    );
    expect(q(container, 'form-error')?.hidden).toBe(true);
    expect(container.querySelector('[role="status"][aria-live="polite"]')).not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------
describe('Request form: validation', () => {
  it('shows an error for every required field on an empty submit', async () => {
    await mountReady(container);

    submit(container);

    expect(errorText(container, 'error-requester-name')).toContain('We need your name');
    expect(errorText(container, 'error-requester-email')).toContain('We need your email');
    expect(errorText(container, 'error-variety')).toContain('Pick your coquito variety');
    expect(errorText(container, 'error-pickup-date')).toContain('When would you like');
    expect(errorText(container, 'error-pickup-time')).toContain('What time works');
    expect(errorText(container, 'error-exchange-location')).toContain('Where should we meet');
    expect(q(container, 'requester-name')?.getAttribute('aria-invalid')).toBe('true');
    expect(mockCreateRequest).not.toHaveBeenCalled();
  });

  it('rejects a malformed email', async () => {
    await mountReady(container);
    fillValidForm(container);
    setValue(container, 'requester-email', 'not-an-email');

    submit(container);

    expect(errorText(container, 'error-requester-email')).toContain("doesn't look right");
    expect(mockCreateRequest).not.toHaveBeenCalled();
  });

  it('clears previous field errors once the field is fixed', async () => {
    await mountReady(container);
    submit(container);
    expect(errorText(container, 'error-requester-name')).not.toBe('');

    mockCreateRequest.mockReturnValue(new Promise(() => {}));
    fillValidForm(container);
    submit(container);

    expect(errorText(container, 'error-requester-name')).toBe('');
    expect(errorText(container, 'error-variety')).toBe('');
    expect(q(container, 'requester-name')?.hasAttribute('aria-invalid')).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Bottle volume reveal
// ---------------------------------------------------------------------------
describe('Request form: bottle volume reveal', () => {
  function volumeWrapper(): HTMLElement {
    return q(container, 'bottle-volume')!.closest<HTMLElement>('.volume-input')!;
  }

  it('reveals the volume input only when bringing a bottle', async () => {
    await mountReady(container);
    expect(volumeWrapper().hidden).toBe(true);

    check(q<HTMLInputElement>(container, 'bottle-provided-yes')!);
    expect(volumeWrapper().hidden).toBe(false);
    expect(volumeWrapper().textContent).toContain('max 1000ml');

    setValue(container, 'bottle-volume', '500');
    check(q<HTMLInputElement>(container, 'bottle-provided-no')!);
    expect(volumeWrapper().hidden).toBe(true);
    expect(q<HTMLInputElement>(container, 'bottle-volume')?.value).toBe('');
  });

  it('requires a volume when bringing a bottle', async () => {
    await mountReady(container);
    fillValidForm(container);
    check(q<HTMLInputElement>(container, 'bottle-provided-yes')!);

    submit(container);

    expect(errorText(container, 'error-bottle-volume')).toContain("bottle's volume in ml");
    expect(mockCreateRequest).not.toHaveBeenCalled();
  });

  it('rejects a volume above the batch maximum', async () => {
    await mountReady(container);
    fillValidForm(container);
    check(q<HTMLInputElement>(container, 'bottle-provided-yes')!);
    setValue(container, 'bottle-volume', '1500');

    submit(container);

    expect(errorText(container, 'error-bottle-volume')).toContain('maximum is 1000ml');
    expect(mockCreateRequest).not.toHaveBeenCalled();
  });

  it('submits the bottle volume when within the maximum', async () => {
    mockCreateRequest.mockResolvedValue(makeResponse({ bottleProvided: true }));
    await mountReady(container);
    fillValidForm(container);
    check(q<HTMLInputElement>(container, 'bottle-provided-yes')!);
    setValue(container, 'bottle-volume', '750');

    submit(container);

    expect(errorText(container, 'error-bottle-volume')).toBe('');
    expect(mockCreateRequest).toHaveBeenCalledWith(
      expect.objectContaining({ bottleProvided: true, bottleVolumeMl: 750 })
    );
  });
});

// ---------------------------------------------------------------------------
// Submission
// ---------------------------------------------------------------------------
describe('Request form: submission', () => {
  it('sends the payload, disables the button and shows the confirmation', async () => {
    let resolve!: (r: api.RequestResponse) => void;
    mockCreateRequest.mockReturnValue(
      new Promise<api.RequestResponse>((r) => {
        resolve = r;
      })
    );
    await mountReady(container);
    fillValidForm(container);
    check(q<HTMLInputElement>(container, 'cost-contribution-no')!);

    submit(container);

    const button = q<HTMLButtonElement>(container, 'submit-button')!;
    expect(button.disabled).toBe(true);
    expect(button.textContent).toBe('Sending your request...');
    expect(mockCreateRequest).toHaveBeenCalledTimes(1);
    const payload = mockCreateRequest.mock.calls[0][0] as api.CreateRequestPayload;
    expect(payload).toMatchObject({
      requesterName: 'María Rivera',
      requesterEmail: 'maria@example.com',
      batchId: 'b-001',
      varietyId: 'v-001',
      pickupDate: '2026-12-20',
      pickupTime: '14:00',
      exchangeLocation: '123 Palmas St',
      bottleProvided: false,
      bottleVolumeMl: null,
      costContribution: false,
    });
    expect(payload.idempotencyKey).toMatch(/^[0-9a-f-]{36}$/);

    resolve(makeResponse({ requesterName: '<i>María</i>' }));

    await waitFor(() => {
      expect(q(container, 'confirmation-card')).not.toBeNull();
    });
    const card = q(container, 'confirmation-card')!;
    expect(card.closest('[role="status"]')).not.toBeNull();
    expect(container.querySelector<HTMLFormElement>('#coquito-request-form')!.hidden).toBe(true);
    expect(card.textContent).toContain('¡Tu coquito está reservado!');
    expect(card.textContent).toContain('<i>María</i>');
    expect(card.querySelector('i')).toBeNull();
    expect(card.textContent).toContain('Classic');
    expect(card.textContent).toContain('2026-12-20');
    expect(card.textContent).toContain('14:00');
    expect(card.textContent).toContain('123 Palmas St');
    expect(card.textContent).toContain('Navidad 2026');
    expect(q<HTMLAnchorElement>(container, 'manage-link')?.getAttribute('href')).toBe(
      '#/manage/r-123'
    );
  });

  it.each([
    [
      'BATCH_CLOSED',
      'Batch closed',
      'Ordering is closed for this pickup date. The batch request cutoff is 2026-12-01',
    ],
    [
      'BOTTLE_VOLUME_EXCEEDED',
      'Too big',
      'Your bottle volume exceeds the maximum allowed (1000ml)',
    ],
    ['VALIDATION_ERROR', 'pickupDate is invalid', 'Oops! pickupDate is invalid'],
    ['INTERNAL_ERROR', 'boom', 'Something went wrong'],
  ])('shows a friendly message for API error %s', async (code, message, expected) => {
    mockCreateRequest.mockRejectedValue(new api.ApiRequestError({ code, message, status: 400 }));
    await mountReady(container);
    fillValidForm(container);

    submit(container);

    await waitFor(() => {
      expect(q(container, 'form-error')?.hidden).toBe(false);
    });
    expect(q(container, 'form-error')?.textContent).toContain(expected);
    const button = q<HTMLButtonElement>(container, 'submit-button')!;
    expect(button.disabled).toBe(false);
    expect(button.textContent).toBe('🥥 Request my coquito');
    expect(container.querySelector<HTMLFormElement>('#coquito-request-form')!.hidden).toBe(false);
    expect(q(container, 'confirmation-card')).toBeNull();
  });

  it('shows the generic message for a non-API error and hides it on resubmit', async () => {
    mockCreateRequest.mockRejectedValueOnce(new TypeError('Failed to fetch'));
    await mountReady(container);
    fillValidForm(container);

    submit(container);

    await waitFor(() => {
      expect(q(container, 'form-error')?.hidden).toBe(false);
    });
    expect(q(container, 'form-error')?.textContent).toContain('¡Ay, algo pasó!');

    mockCreateRequest.mockReturnValueOnce(new Promise(() => {}));
    submit(container);
    expect(q(container, 'form-error')?.hidden).toBe(true);
  });
});
