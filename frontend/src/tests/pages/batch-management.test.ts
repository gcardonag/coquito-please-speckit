/**
 * T013 / T031 / T045: Unit tests for batch-management page
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// ---------------------------------------------------------------------------
// Mock the api module
// ---------------------------------------------------------------------------
vi.mock('../../services/api', () => ({
  listBatches: vi.fn(),
  listVarieties: vi.fn(),
  createBatch: vi.fn(),
  updateBatch: vi.fn(),
  updateBatchStatus: vi.fn(),
  getMe: vi.fn(),
  listBatchAccess: vi.fn(),
  searchUsers: vi.fn(),
  grantBatchAccess: vi.fn(),
  revokeBatchAccess: vi.fn(),
  createUser: vi.fn(),
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
import { mountBatchManagement } from '../../pages/batch-management/index';

const mockListBatches = api.listBatches as ReturnType<typeof vi.fn>;
const mockListVarieties = api.listVarieties as ReturnType<typeof vi.fn>;
const mockCreateBatch = api.createBatch as ReturnType<typeof vi.fn>;
const mockUpdateBatch = api.updateBatch as ReturnType<typeof vi.fn>;
const mockUpdateBatchStatus = api.updateBatchStatus as ReturnType<typeof vi.fn>;
const mockListBatchAccess = api.listBatchAccess as ReturnType<typeof vi.fn>;
const mockSearchUsers = api.searchUsers as ReturnType<typeof vi.fn>;
const mockGrantBatchAccess = api.grantBatchAccess as ReturnType<typeof vi.fn>;
const mockRevokeBatchAccess = api.revokeBatchAccess as ReturnType<typeof vi.fn>;
const mockCreateUser = api.createUser as ReturnType<typeof vi.fn>;

function makeBatch(overrides: Partial<api.BatchSummary> = {}): api.BatchSummary {
  return {
    batchId: 'b-001',
    batchName: 'Holiday 2026',
    cutoffDate: '2026-11-15',
    maxBottleVolumeMl: 1000,
    status: 'OPEN',
    availableVarietyIds: ['classic', 'chocolate'],
    activeRequestCount: 3,
    createdAt: '2026-05-01T00:00:00Z',
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// User Story 1 — View All Batches
// ---------------------------------------------------------------------------
describe('US1: Batch list rendering', () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    vi.clearAllMocks();
  });

  afterEach(() => {
    container.remove();
  });

  it('renders batch list with status badges when batches exist', async () => {
    mockListBatches.mockResolvedValue({
      batches: [
        makeBatch({ status: 'OPEN' }),
        makeBatch({ batchId: 'b-002', batchName: 'Summer 2026', status: 'CLOSED' }),
      ],
    });

    await mountBatchManagement(container);

    expect(container.querySelector('[data-status="OPEN"]')).not.toBeNull();
    expect(container.querySelector('[data-status="CLOSED"]')).not.toBeNull();
  });

  it('renders empty state when no batches exist', async () => {
    mockListBatches.mockResolvedValue({ batches: [] });

    await mountBatchManagement(container);

    const emptyState = container.querySelector('[data-testid="empty-state"]');
    expect(emptyState).not.toBeNull();
    expect(emptyState!.textContent).toMatch(/create/i);
  });

  it('renders each batch row with name, cutoff date, variety count', async () => {
    mockListBatches.mockResolvedValue({ batches: [makeBatch()] });

    await mountBatchManagement(container);

    expect(container.textContent).toContain('Holiday 2026');
    expect(container.textContent).toContain('2026-11-15');
    expect(container.textContent).toContain('2'); // 2 varieties
  });

  it('batch list region has aria-live polite for loading state', async () => {
    mockListBatches.mockResolvedValue({ batches: [] });
    await mountBatchManagement(container);
    const live = container.querySelector('[aria-live="polite"]');
    expect(live).not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// User Story 2 — Create a New Batch
// ---------------------------------------------------------------------------
describe('US2: Create batch form', () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    vi.clearAllMocks();
    mockListBatches.mockResolvedValue({ batches: [] });
    mockListVarieties.mockResolvedValue({
      varieties: [
        { varietyId: 'classic', name: 'Classic', description: '', imageUrl: '' },
        { varietyId: 'chocolate', name: 'Chocolate', description: '', imageUrl: '' },
      ],
    });
  });

  afterEach(() => {
    container.remove();
  });

  it('shows create form when New Batch button is clicked', async () => {
    await mountBatchManagement(container);
    const btn = container.querySelector<HTMLButtonElement>('[data-testid="new-batch-btn"]');
    expect(btn).not.toBeNull();
    btn!.click();
    await Promise.resolve();
    expect(container.querySelector('[data-testid="create-batch-form"]')).not.toBeNull();
  });

  it('submitting valid form calls createBatch and adds batch to list', async () => {
    const newBatch = makeBatch({ batchId: 'b-new', batchName: 'New Batch', status: 'OPEN' });
    mockCreateBatch.mockResolvedValue(newBatch);

    await mountBatchManagement(container);
    container.querySelector<HTMLButtonElement>('[data-testid="new-batch-btn"]')!.click();
    await Promise.resolve();

    const form = container.querySelector<HTMLFormElement>('[data-testid="create-batch-form"]')!;
    const nameInput = form.querySelector<HTMLInputElement>('[name="batchName"]')!;
    const dateInput = form.querySelector<HTMLInputElement>('[name="cutoffDate"]')!;
    const volumeInput = form.querySelector<HTMLInputElement>('[name="maxBottleVolumeMl"]')!;
    const classicCheckbox = form.querySelector<HTMLInputElement>('[value="classic"]')!;

    nameInput.value = 'New Batch';
    dateInput.value = '2030-12-01';
    volumeInput.value = '750';
    classicCheckbox.checked = true;

    form.dispatchEvent(new Event('submit', { bubbles: true }));
    await Promise.resolve();
    await Promise.resolve();

    expect(mockCreateBatch).toHaveBeenCalledWith({
      batchName: 'New Batch',
      cutoffDate: '2030-12-01',
      maxBottleVolumeMl: 750,
      availableVarietyIds: ['classic'],
    });
  });

  it('shows BATCH_NAME_CONFLICT error without clearing form', async () => {
    const { ApiRequestError } = await import('../../services/api');
    mockCreateBatch.mockRejectedValue(
      new ApiRequestError({
        code: 'BATCH_NAME_CONFLICT',
        message: "A batch named 'New Batch' already exists.",
        status: 400,
      })
    );

    await mountBatchManagement(container);
    container.querySelector<HTMLButtonElement>('[data-testid="new-batch-btn"]')!.click();
    await Promise.resolve();

    const form = container.querySelector<HTMLFormElement>('[data-testid="create-batch-form"]')!;
    form.querySelector<HTMLInputElement>('[name="batchName"]')!.value = 'New Batch';
    form.querySelector<HTMLInputElement>('[name="cutoffDate"]')!.value = '2030-12-01';
    form.querySelector<HTMLInputElement>('[name="maxBottleVolumeMl"]')!.value = '750';
    form.querySelector<HTMLInputElement>('[value="classic"]')!.checked = true;

    form.dispatchEvent(new Event('submit', { bubbles: true }));
    await Promise.resolve();
    await Promise.resolve();

    expect(container.textContent).toMatch(/already exists/i);
    expect(form.querySelector<HTMLInputElement>('[name="batchName"]')!.value).toBe('New Batch');
  });
});

// ---------------------------------------------------------------------------
// User Story 3 — Edit an Existing Batch
// ---------------------------------------------------------------------------
describe('US3: Edit existing batch', () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    vi.clearAllMocks();
    mockListVarieties.mockResolvedValue({ varieties: [] });
  });

  afterEach(() => {
    container.remove();
  });

  it('OPEN batch renders editable fields', async () => {
    mockListBatches.mockResolvedValue({ batches: [makeBatch({ status: 'OPEN' })] });
    await mountBatchManagement(container);

    const row = container.querySelector<HTMLElement>('[data-batch-id="b-001"]')!;
    row.click();
    await Promise.resolve();

    const nameInput = container.querySelector<HTMLInputElement>('[data-testid="edit-batchName"]');
    expect(nameInput).not.toBeNull();
    expect(nameInput!.disabled).toBe(false);
  });

  it('COMPLETED batch renders read-only fields', async () => {
    mockListBatches.mockResolvedValue({ batches: [makeBatch({ status: 'COMPLETED' })] });
    await mountBatchManagement(container);

    const row = container.querySelector<HTMLElement>('[data-batch-id="b-001"]')!;
    row.click();
    await Promise.resolve();

    const nameInput = container.querySelector<HTMLInputElement>('[data-testid="edit-batchName"]')!;
    expect(nameInput.disabled).toBe(true);
    const saveBtn = container.querySelector('[data-testid="save-batch-btn"]');
    expect(saveBtn).toBeNull();
    expect(container.textContent).toMatch(/finalized/i);
  });

  it('OPEN→CLOSED shows confirmation dialog with request count', async () => {
    mockListBatches.mockResolvedValue({
      batches: [makeBatch({ status: 'OPEN', activeRequestCount: 5 })],
    });
    await mountBatchManagement(container);

    container.querySelector<HTMLElement>('[data-batch-id="b-001"]')!.click();
    await Promise.resolve();

    const closeBtn = container.querySelector<HTMLButtonElement>('[data-testid="close-batch-btn"]')!;
    closeBtn.click();
    await Promise.resolve();

    const dialog = container.querySelector('[role="dialog"]');
    expect(dialog).not.toBeNull();
    expect(dialog!.textContent).toContain('5');
  });

  it('CLOSED→COMPLETED transitions without dialog', async () => {
    const closedBatch = makeBatch({ status: 'CLOSED', activeRequestCount: 0 });
    const completedBatch = { ...closedBatch, status: 'COMPLETED' as const };
    mockListBatches.mockResolvedValue({ batches: [closedBatch] });
    mockUpdateBatchStatus.mockResolvedValue(completedBatch);

    await mountBatchManagement(container);
    container.querySelector<HTMLElement>('[data-batch-id="b-001"]')!.click();
    await Promise.resolve();

    const completeBtn = container.querySelector<HTMLButtonElement>(
      '[data-testid="complete-batch-btn"]'
    )!;
    completeBtn.click();
    await Promise.resolve();
    await Promise.resolve();

    expect(mockUpdateBatchStatus).toHaveBeenCalledWith('b-001', 'COMPLETED');
    expect(container.querySelector('[role="dialog"]')).toBeNull();
  });

  it('VARIETY_HAS_REQUESTS error surfaces with specific message', async () => {
    const { ApiRequestError } = await import('../../services/api');
    mockListBatches.mockResolvedValue({ batches: [makeBatch({ status: 'OPEN' })] });
    mockUpdateBatch.mockRejectedValue(
      new ApiRequestError({
        code: 'VARIETY_HAS_REQUESTS',
        message: "Variety 'classic' cannot be removed — confirmed requests exist for it.",
        status: 400,
      })
    );
    mockListVarieties.mockResolvedValue({
      varieties: [{ varietyId: 'classic', name: 'Classic', description: '', imageUrl: '' }],
    });

    await mountBatchManagement(container);
    container.querySelector<HTMLElement>('[data-batch-id="b-001"]')!.click();
    await Promise.resolve();

    const saveBtn = container.querySelector<HTMLButtonElement>('[data-testid="save-batch-btn"]')!;
    saveBtn.click();
    await Promise.resolve();
    await Promise.resolve();

    expect(container.textContent).toMatch(/cannot be removed/i);
  });
});

// ---------------------------------------------------------------------------
// Shared helpers for the extended suites below
// ---------------------------------------------------------------------------

/** Drain pending microtasks (chained awaits inside event handlers) deterministically. */
async function flush(): Promise<void> {
  for (let i = 0; i < 10; i++) await Promise.resolve();
}

const chef: api.CurrentUser = { userId: 'chef-1', role: 'chef', email: 'chef@example.com' };

function q<T extends HTMLElement = HTMLElement>(root: ParentNode, testid: string): T | null {
  return root.querySelector<T>(`[data-testid="${testid}"]`);
}

async function openBatch(container: HTMLElement, batchId = 'b-001'): Promise<void> {
  container.querySelector<HTMLElement>(`[data-batch-id="${batchId}"]`)!.click();
  await flush();
}

function makeApiError(code: string, message: string, status = 400): Error {
  return new api.ApiRequestError({ code, message, status } as never);
}

// ---------------------------------------------------------------------------
// Mount — load failures
// ---------------------------------------------------------------------------
describe('Mount: batch list load failures', () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    vi.clearAllMocks();
  });

  afterEach(() => {
    container.remove();
  });

  it('shows an access-denied message on a 403', async () => {
    mockListBatches.mockRejectedValue(makeApiError('FORBIDDEN', 'nope', 403));
    await mountBatchManagement(container);
    expect(q(container, 'batch-list')!.textContent).toBe(
      'Access denied. Only chefs can view batch management.'
    );
  });

  it('shows a generic load failure for other errors', async () => {
    mockListBatches.mockRejectedValue(new Error('network down'));
    await mountBatchManagement(container);
    expect(q(container, 'batch-list')!.textContent).toBe(
      'Failed to load batches. Please refresh and try again.'
    );
  });

  it('shows a generic load failure for non-403 API errors', async () => {
    mockListBatches.mockRejectedValue(makeApiError('INTERNAL', 'boom', 500));
    await mountBatchManagement(container);
    expect(q(container, 'batch-list')!.textContent).toMatch(/Failed to load batches/);
  });
});

// ---------------------------------------------------------------------------
// Detail panel — opening, keyboard, revealDetail, read-only fields
// ---------------------------------------------------------------------------
describe('Detail panel: opening and reveal', () => {
  let container: HTMLDivElement;
  const originalMatchMedia = window.matchMedia;
  const originalScroll = HTMLElement.prototype.scrollIntoView;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    vi.clearAllMocks();
    mockListBatches.mockResolvedValue({ batches: [makeBatch()] });
    mockListVarieties.mockResolvedValue({ varieties: [] });
  });

  afterEach(() => {
    container.remove();
    window.matchMedia = originalMatchMedia;
    HTMLElement.prototype.scrollIntoView = originalScroll;
  });

  function stubViewport(desktop: boolean): ReturnType<typeof vi.fn> {
    window.matchMedia = vi.fn().mockReturnValue({ matches: desktop }) as never;
    const scroll = vi.fn();
    HTMLElement.prototype.scrollIntoView = scroll as never;
    return scroll;
  }

  it('opens the detail panel with Enter and Space, but not other keys', async () => {
    await mountBatchManagement(container);
    const row = container.querySelector<HTMLElement>('[data-batch-id="b-001"]')!;

    row.dispatchEvent(new KeyboardEvent('keydown', { key: 'a' }));
    await flush();
    expect(q(container, 'edit-batch-form')).toBeNull();

    row.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
    await flush();
    expect(q(container, 'edit-batch-form')).not.toBeNull();

    q(container, 'batch-detail')!.innerHTML = '';
    row.dispatchEvent(new KeyboardEvent('keydown', { key: ' ' }));
    await flush();
    expect(q(container, 'edit-batch-form')).not.toBeNull();
  });

  it('scrolls the detail panel into view below the desktop breakpoint when a row is opened', async () => {
    const scroll = stubViewport(false);
    await mountBatchManagement(container);
    await openBatch(container);
    expect(scroll).toHaveBeenCalledTimes(1);
    expect(scroll.mock.contexts[0]).toBe(q(container, 'batch-detail'));
  });

  it('does not scroll at desktop width when a row is opened', async () => {
    const scroll = stubViewport(true);
    await mountBatchManagement(container);
    await openBatch(container);
    expect(q(container, 'edit-batch-form')).not.toBeNull();
    expect(scroll).not.toHaveBeenCalled();
  });

  it('scrolls the create form into view below the desktop breakpoint', async () => {
    const scroll = stubViewport(false);
    await mountBatchManagement(container);
    q<HTMLButtonElement>(container, 'new-batch-btn')!.click();
    await flush();
    expect(q(container, 'create-batch-form')).not.toBeNull();
    expect(scroll.mock.contexts[0]).toBe(q(container, 'batch-detail'));
  });

  it('still renders the edit form when varieties fail to load', async () => {
    mockListVarieties.mockRejectedValue(new Error('down'));
    await mountBatchManagement(container);
    await openBatch(container);
    const form = q(container, 'edit-batch-form')!;
    expect(form).not.toBeNull();
    expect(form.querySelectorAll('input[type="checkbox"]')).toHaveLength(0);
    expect(container.textContent).toContain('Edit: Holiday 2026');
  });

  it('pre-checks the batch varieties in the edit form', async () => {
    mockListVarieties.mockResolvedValue({
      varieties: [
        { varietyId: 'classic', name: 'Classic', description: '', imageUrl: '' },
        { varietyId: 'mango', name: 'Mango', description: '', imageUrl: '' },
      ],
    });
    await mountBatchManagement(container);
    await openBatch(container);
    expect(container.querySelector<HTMLInputElement>('#edit-variety-classic')!.checked).toBe(true);
    expect(container.querySelector<HTMLInputElement>('#edit-variety-mango')!.checked).toBe(false);
  });

  it('COMPLETED batch shows variety names, falling back to the id when unknown', async () => {
    mockListBatches.mockResolvedValue({
      batches: [makeBatch({ status: 'COMPLETED', availableVarietyIds: ['classic', 'ghost'] })],
    });
    mockListVarieties.mockResolvedValue({
      varieties: [{ varietyId: 'classic', name: 'Classic', description: '', imageUrl: '' }],
    });
    await mountBatchManagement(container);
    await openBatch(container);
    expect(q<HTMLInputElement>(container, 'edit-varieties')!.value).toBe('Classic, ghost');
    expect(q<HTMLInputElement>(container, 'edit-maxBottleVolumeMl')!.value).toBe('1000 ml');
    expect(q(container, 'close-batch-btn')).toBeNull();
    expect(q(container, 'complete-batch-btn')).toBeNull();
  });

  it('COMPLETED batch with no varieties shows a dash', async () => {
    mockListBatches.mockResolvedValue({
      batches: [makeBatch({ status: 'COMPLETED', availableVarietyIds: [] })],
    });
    await mountBatchManagement(container);
    await openBatch(container);
    expect(q<HTMLInputElement>(container, 'edit-varieties')!.value).toBe('—');
  });
});

// ---------------------------------------------------------------------------
// Edit form — save
// ---------------------------------------------------------------------------
describe('Edit form: save', () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    vi.clearAllMocks();
    mockListBatches.mockResolvedValue({ batches: [makeBatch()] });
    mockListVarieties.mockResolvedValue({
      varieties: [{ varietyId: 'classic', name: 'Classic', description: '', imageUrl: '' }],
    });
  });

  afterEach(() => {
    container.remove();
  });

  it('saves edited fields and re-renders the list and detail with the update', async () => {
    mockUpdateBatch.mockResolvedValue(
      makeBatch({ batchName: 'Renamed', cutoffDate: '2026-12-01', maxBottleVolumeMl: 500 })
    );
    await mountBatchManagement(container);
    await openBatch(container);

    q<HTMLInputElement>(container, 'edit-batchName')!.value = '  Renamed  ';
    q<HTMLInputElement>(container, 'edit-cutoffDate')!.value = '2026-12-01';
    q<HTMLInputElement>(container, 'edit-maxBottleVolumeMl')!.value = '500';
    q<HTMLButtonElement>(container, 'save-batch-btn')!.click();
    await flush();

    expect(mockUpdateBatch).toHaveBeenCalledWith('b-001', {
      batchName: 'Renamed',
      cutoffDate: '2026-12-01',
      maxBottleVolumeMl: 500,
      availableVarietyIds: ['classic'],
    });
    expect(container.querySelector('.batch-row__name')!.textContent).toBe('Renamed');
    expect(container.querySelector('.batch-form__title')!.textContent).toBe('Edit: Renamed');
    expect(q(container, 'detail-error')!.hasAttribute('hidden')).toBe(true);
  });

  it('omits blank fields and unchecked varieties from the update payload', async () => {
    mockUpdateBatch.mockResolvedValue(makeBatch());
    await mountBatchManagement(container);
    await openBatch(container);

    q<HTMLInputElement>(container, 'edit-batchName')!.value = '   ';
    q<HTMLInputElement>(container, 'edit-cutoffDate')!.value = '';
    q<HTMLInputElement>(container, 'edit-maxBottleVolumeMl')!.value = '';
    container.querySelector<HTMLInputElement>('#edit-variety-classic')!.checked = false;
    q<HTMLButtonElement>(container, 'save-batch-btn')!.click();
    await flush();

    expect(mockUpdateBatch).toHaveBeenCalledWith('b-001', {});
  });

  it('shows a generic error when save fails unexpectedly', async () => {
    mockUpdateBatch.mockRejectedValue(new Error('boom'));
    await mountBatchManagement(container);
    await openBatch(container);
    q<HTMLButtonElement>(container, 'save-batch-btn')!.click();
    await flush();

    const err = q(container, 'detail-error')!;
    expect(err.hasAttribute('hidden')).toBe(false);
    expect(err.textContent).toBe('An unexpected error occurred. Please try again.');
  });
});

// ---------------------------------------------------------------------------
// Status transitions
// ---------------------------------------------------------------------------
describe('Status transitions', () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    vi.clearAllMocks();
    mockListVarieties.mockResolvedValue({ varieties: [] });
  });

  afterEach(() => {
    container.remove();
  });

  async function openCloseDialog(activeRequestCount = 3): Promise<HTMLElement> {
    mockListBatches.mockResolvedValue({
      batches: [makeBatch({ status: 'OPEN', activeRequestCount })],
    });
    await mountBatchManagement(container);
    await openBatch(container);
    q<HTMLButtonElement>(container, 'close-batch-btn')!.click();
    return container.querySelector<HTMLElement>('[role="dialog"]')!;
  }

  it('uses singular wording for a single active request and focuses confirm', async () => {
    const dialog = await openCloseDialog(1);
    expect(dialog.textContent).toContain('currently has 1 active request.');
    expect(document.activeElement).toBe(q(container, 'dialog-confirm-btn'));
  });

  it('uses plural wording for multiple active requests', async () => {
    const dialog = await openCloseDialog(3);
    expect(dialog.textContent).toContain('currently has 3 active requests.');
  });

  it('Cancel dismisses the close dialog without changing status', async () => {
    await openCloseDialog();
    q<HTMLButtonElement>(container, 'dialog-cancel-btn')!.click();
    await flush();
    expect(container.querySelector('[role="dialog"]')).toBeNull();
    expect(mockUpdateBatchStatus).not.toHaveBeenCalled();
  });

  it('confirming closes the batch and updates list badge and detail controls', async () => {
    mockUpdateBatchStatus.mockResolvedValue(makeBatch({ status: 'CLOSED' }));
    await openCloseDialog();
    q<HTMLButtonElement>(container, 'dialog-confirm-btn')!.click();
    await flush();

    expect(mockUpdateBatchStatus).toHaveBeenCalledWith('b-001', 'CLOSED');
    expect(container.querySelector('[role="dialog"]')).toBeNull();
    expect(container.querySelector('[data-status="CLOSED"]')).not.toBeNull();
    expect(q(container, 'close-batch-btn')).toBeNull();
    expect(q(container, 'complete-batch-btn')).not.toBeNull();
  });

  it('shows the API error message when closing fails', async () => {
    mockUpdateBatchStatus.mockRejectedValue(makeApiError('INVALID_TRANSITION', 'Cannot close.'));
    await openCloseDialog();
    q<HTMLButtonElement>(container, 'dialog-confirm-btn')!.click();
    await flush();

    const err = q(container, 'detail-error')!;
    expect(err.hasAttribute('hidden')).toBe(false);
    expect(err.textContent).toBe('Cannot close.');
  });

  it('shows a generic error when closing fails unexpectedly', async () => {
    mockUpdateBatchStatus.mockRejectedValue(new Error('boom'));
    await openCloseDialog();
    q<HTMLButtonElement>(container, 'dialog-confirm-btn')!.click();
    await flush();
    expect(q(container, 'detail-error')!.textContent).toBe('An unexpected error occurred.');
  });

  it('marking complete renders the finalized read-only view', async () => {
    mockListBatches.mockResolvedValue({ batches: [makeBatch({ status: 'CLOSED' })] });
    mockUpdateBatchStatus.mockResolvedValue(makeBatch({ status: 'COMPLETED' }));
    await mountBatchManagement(container);
    await openBatch(container);
    q<HTMLButtonElement>(container, 'complete-batch-btn')!.click();
    await flush();

    expect(container.querySelector('[data-status="COMPLETED"]')).not.toBeNull();
    expect(container.textContent).toMatch(/Finalized/);
    expect(q(container, 'save-batch-btn')).toBeNull();
  });

  it('shows the API error message when completing fails', async () => {
    mockListBatches.mockResolvedValue({ batches: [makeBatch({ status: 'CLOSED' })] });
    mockUpdateBatchStatus.mockRejectedValue(makeApiError('INVALID_TRANSITION', 'Not yet.'));
    await mountBatchManagement(container);
    await openBatch(container);
    q<HTMLButtonElement>(container, 'complete-batch-btn')!.click();
    await flush();
    const err = q(container, 'detail-error')!;
    expect(err.hasAttribute('hidden')).toBe(false);
    expect(err.textContent).toBe('Not yet.');
  });

  it('shows a generic error when completing fails unexpectedly', async () => {
    mockListBatches.mockResolvedValue({ batches: [makeBatch({ status: 'CLOSED' })] });
    mockUpdateBatchStatus.mockRejectedValue(new Error('boom'));
    await mountBatchManagement(container);
    await openBatch(container);
    q<HTMLButtonElement>(container, 'complete-batch-btn')!.click();
    await flush();
    expect(q(container, 'detail-error')!.textContent).toBe('An unexpected error occurred.');
  });
});

// ---------------------------------------------------------------------------
// Create form — validation, errors, success, cancel
// ---------------------------------------------------------------------------
describe('Create form: validation and outcomes', () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    vi.clearAllMocks();
    mockListBatches.mockResolvedValue({ batches: [] });
    mockListVarieties.mockResolvedValue({ varieties: [] });
  });

  afterEach(() => {
    container.remove();
  });

  async function openCreate(): Promise<HTMLFormElement> {
    await mountBatchManagement(container);
    q<HTMLButtonElement>(container, 'new-batch-btn')!.click();
    await flush();
    return q<HTMLFormElement>(container, 'create-batch-form')!;
  }

  function fill(form: HTMLFormElement, name: string, date: string): void {
    q<HTMLInputElement>(form, 'create-batchName')!.value = name;
    q<HTMLInputElement>(form, 'create-cutoffDate')!.value = date;
    q<HTMLInputElement>(form, 'create-maxBottleVolumeMl')!.value = '750';
  }

  it('shows required-field errors and does not call the API when empty', async () => {
    const form = await openCreate();
    q<HTMLButtonElement>(container, 'create-submit-btn')!.click();
    await flush();

    expect(mockCreateBatch).not.toHaveBeenCalled();
    expect(container.querySelector('#name-error')!.textContent).toBe('Batch name is required.');
    expect(container.querySelector('#date-error')!.textContent).toBe('Cutoff date is required.');
    expect(q(form, 'create-batchName')!.getAttribute('aria-invalid')).toBe('true');
    expect(q(form, 'create-cutoffDate')!.getAttribute('aria-invalid')).toBe('true');
  });

  it('flags the date field on CUTOFF_DATE_IN_PAST', async () => {
    mockCreateBatch.mockRejectedValue(
      makeApiError('CUTOFF_DATE_IN_PAST', 'Cutoff date must be in the future.')
    );
    const form = await openCreate();
    fill(form, 'Old', '2000-01-01');
    q<HTMLButtonElement>(container, 'create-submit-btn')!.click();
    await flush();

    expect(q(container, 'create-error')!.textContent).toBe('Cutoff date must be in the future.');
    expect(container.querySelector('#date-error')!.hasAttribute('hidden')).toBe(false);
    expect(q(form, 'create-cutoffDate')!.getAttribute('aria-invalid')).toBe('true');
    expect(container.querySelector('#name-error')!.hasAttribute('hidden')).toBe(true);
  });

  it('shows a generic error when creation fails unexpectedly', async () => {
    mockCreateBatch.mockRejectedValue(new Error('boom'));
    const form = await openCreate();
    fill(form, 'X', '2030-01-01');
    q<HTMLButtonElement>(container, 'create-submit-btn')!.click();
    await flush();

    const err = q(container, 'create-error')!;
    expect(err.hasAttribute('hidden')).toBe(false);
    expect(err.textContent).toBe('An unexpected error occurred. Please try again.');
  });

  it('adds the created batch to the list and clears the form on success', async () => {
    mockCreateBatch.mockResolvedValue(makeBatch({ batchId: 'b-new', batchName: 'Fresh' }));
    const form = await openCreate();
    fill(form, 'Fresh', '2030-01-01');
    q<HTMLButtonElement>(container, 'create-submit-btn')!.click();
    await flush();

    expect(container.querySelector('[data-batch-id="b-new"]')!.textContent).toContain('Fresh');
    expect(q(container, 'empty-state')).toBeNull();
    expect(q(container, 'create-batch-form')).toBeNull();
  });

  it('Cancel clears the create form', async () => {
    await openCreate();
    const cancel = Array.from(
      q(container, 'create-batch-form')!.querySelectorAll<HTMLButtonElement>('button')
    ).find((b) => b.textContent === 'Cancel')!;
    cancel.click();
    expect(q(container, 'create-batch-form')).toBeNull();
    expect(q(container, 'batch-detail')!.innerHTML).toBe('');
  });

  it('still renders the create form when varieties fail to load', async () => {
    mockListVarieties.mockRejectedValue(new Error('down'));
    const form = await openCreate();
    expect(form).not.toBeNull();
    expect(form.querySelectorAll('input[type="checkbox"]')).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// Manage Access panel
// ---------------------------------------------------------------------------
describe('Manage Access panel', () => {
  let container: HTMLDivElement;

  const alice: api.BatchAccessUser = {
    userId: 'u-alice',
    email: 'alice@example.com',
    firstName: 'Alice',
    lastName: 'Smith',
    grantedAt: '2026-05-01T00:00:00Z',
  };
  const bob: api.BatchAccessUser = {
    userId: 'u-bob',
    email: 'bob@example.com',
    firstName: 'Bob',
    grantedAt: '2026-05-01T00:00:00Z',
  };

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    vi.clearAllMocks();
    mockListBatches.mockResolvedValue({ batches: [makeBatch({ status: 'OPEN' })] });
    mockListVarieties.mockResolvedValue({ varieties: [] });
    mockListBatchAccess.mockResolvedValue({ users: [] });
  });

  afterEach(() => {
    container.remove();
    document.querySelectorAll('[data-testid="revoke-overlay"]').forEach((n) => n.remove());
  });

  async function openPanel(): Promise<HTMLElement> {
    await mountBatchManagement(container, chef);
    await openBatch(container);
    q<HTMLButtonElement>(container, 'manage-access-toggle')!.click();
    await flush();
    return container.querySelector<HTMLElement>('.access-panel__body')!;
  }

  async function search(body: HTMLElement, query: string): Promise<HTMLElement> {
    q<HTMLInputElement>(body, 'access-search-input')!.value = query;
    q<HTMLButtonElement>(body, 'access-search-btn')!.click();
    await flush();
    return q(body, 'access-search-results')!;
  }

  // -- visibility / toggle -------------------------------------------------
  it('is not rendered for non-chef users', async () => {
    await mountBatchManagement(container, { userId: 'u', role: 'requester', email: 'r@x.com' });
    await openBatch(container);
    expect(q(container, 'manage-access-panel')).toBeNull();
  });

  it('is not rendered when no user is provided', async () => {
    await mountBatchManagement(container);
    await openBatch(container);
    expect(q(container, 'manage-access-panel')).toBeNull();
  });

  it('is not rendered for a chef on a CLOSED batch', async () => {
    mockListBatches.mockResolvedValue({ batches: [makeBatch({ status: 'CLOSED' })] });
    await mountBatchManagement(container, chef);
    await openBatch(container);
    expect(q(container, 'manage-access-panel')).toBeNull();
  });

  it('toggle expands (loading the access list) and collapses the panel', async () => {
    await mountBatchManagement(container, chef);
    await openBatch(container);
    const toggle = q<HTMLButtonElement>(container, 'manage-access-toggle')!;
    const body = container.querySelector<HTMLElement>('.access-panel__body')!;
    expect(body.hasAttribute('hidden')).toBe(true);
    expect(toggle.getAttribute('aria-expanded')).toBe('false');

    toggle.click();
    expect(body.textContent).toContain('Loading…');
    await flush();
    expect(toggle.getAttribute('aria-expanded')).toBe('true');
    expect(body.hasAttribute('hidden')).toBe(false);
    expect(mockListBatchAccess).toHaveBeenCalledWith('b-001');
    expect(q(body, 'access-empty-state')!.textContent).toBe(
      'No users have been granted access to this batch.'
    );

    toggle.click();
    expect(toggle.getAttribute('aria-expanded')).toBe('false');
    expect(body.hasAttribute('hidden')).toBe(true);
  });

  it('lists users with access, with and without a last name', async () => {
    mockListBatchAccess.mockResolvedValue({ users: [alice, bob] });
    const body = await openPanel();
    const list = q(body, 'access-user-list')!;
    const rows = list.querySelectorAll('li');
    expect(rows).toHaveLength(2);
    expect(rows[0].textContent).toContain('Alice Smith (alice@example.com)');
    expect(rows[1].querySelector('.access-user-row__name')!.textContent).toBe('Bob');
    expect(q(body, 'remove-btn-u-alice')).not.toBeNull();
  });

  it('shows the API error message when the access list fails to load', async () => {
    mockListBatchAccess.mockRejectedValue(makeApiError('FORBIDDEN', 'Not your batch.', 403));
    const body = await openPanel();
    expect(body.querySelector('[role="alert"]')!.textContent).toBe('Not your batch.');
  });

  it('shows a generic message when the access list fails unexpectedly', async () => {
    mockListBatchAccess.mockRejectedValue(new Error('boom'));
    const body = await openPanel();
    expect(body.querySelector('[role="alert"]')!.textContent).toBe(
      'Failed to load the access list. Please refresh and try again.'
    );
  });

  // -- search ---------------------------------------------------------------
  it('does not search for an empty query', async () => {
    const body = await openPanel();
    const results = await search(body, '   ');
    expect(mockSearchUsers).not.toHaveBeenCalled();
    expect(results.textContent).toBe('');
  });

  it('renders search results with grant buttons', async () => {
    mockSearchUsers.mockResolvedValue({ users: [alice, bob] });
    const body = await openPanel();
    const results = await search(body, ' ali ');
    expect(mockSearchUsers).toHaveBeenCalledWith('ali');
    expect(results.textContent).toContain('Alice Smith (alice@example.com)');
    expect(results.textContent).toContain('Bob (bob@example.com)');
    expect(q(results, 'grant-btn-u-alice')!.textContent).toBe('Grant Access');
    expect(results.querySelector('.access-truncation-hint')).toBeNull();
  });

  it('searches when Enter is pressed in the search input, not on other keys', async () => {
    mockSearchUsers.mockResolvedValue({ users: [] });
    const body = await openPanel();
    const input = q<HTMLInputElement>(body, 'access-search-input')!;
    input.value = 'zed';
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'a' }));
    await flush();
    expect(mockSearchUsers).not.toHaveBeenCalled();

    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
    expect(q(body, 'access-search-results')!.textContent).toBe('Searching…');
    await flush();
    expect(mockSearchUsers).toHaveBeenCalledWith('zed');
    expect(q(body, 'search-empty')!.textContent).toBe(
      'No users found. Try creating a new user below.'
    );
  });

  it('shows a truncation hint when 20 results are returned', async () => {
    const many = Array.from({ length: 20 }, (_, i) => ({
      ...bob,
      userId: `u-${i}`,
      email: `u${i}@example.com`,
    }));
    mockSearchUsers.mockResolvedValue({ users: many });
    const body = await openPanel();
    const results = await search(body, 'u');
    expect(results.querySelectorAll('li')).toHaveLength(20);
    expect(results.querySelector('.access-truncation-hint')!.textContent).toBe(
      'Showing first 20 results — refine your search for more.'
    );
  });

  it('shows the API error message when search fails', async () => {
    mockSearchUsers.mockRejectedValue(makeApiError('BAD_QUERY', 'Query too short.'));
    const body = await openPanel();
    const results = await search(body, 'a');
    expect(results.textContent).toBe('Query too short.');
  });

  it('shows a generic message when search fails unexpectedly', async () => {
    mockSearchUsers.mockRejectedValue(new Error('boom'));
    const body = await openPanel();
    const results = await search(body, 'a');
    expect(results.textContent).toBe('Search failed. Please try again.');
  });

  // -- grant ----------------------------------------------------------------
  it('granting access refreshes the access list', async () => {
    mockSearchUsers.mockResolvedValue({ users: [alice] });
    mockGrantBatchAccess.mockResolvedValue({});
    const body = await openPanel();
    const results = await search(body, 'ali');

    mockListBatchAccess.mockResolvedValue({ users: [alice] });
    q<HTMLButtonElement>(results, 'grant-btn-u-alice')!.click();
    await flush();

    expect(mockGrantBatchAccess).toHaveBeenCalledWith('b-001', 'u-alice');
    expect(mockListBatchAccess).toHaveBeenCalledTimes(2);
    expect(q(body, 'access-user-list')!.textContent).toContain('Alice Smith');
  });

  it('shows a single access error when grant fails repeatedly', async () => {
    mockSearchUsers.mockResolvedValue({ users: [alice] });
    mockGrantBatchAccess.mockRejectedValueOnce(makeApiError('ALREADY_GRANTED', 'Already has it.'));
    mockGrantBatchAccess.mockRejectedValueOnce(new Error('boom'));
    const body = await openPanel();
    const results = await search(body, 'ali');

    q<HTMLButtonElement>(results, 'grant-btn-u-alice')!.click();
    await flush();
    expect(q(body, 'access-error')!.textContent).toBe('Already has it.');

    q<HTMLButtonElement>(results, 'grant-btn-u-alice')!.click();
    await flush();
    const errors = body.querySelectorAll('[data-testid="access-error"]');
    expect(errors).toHaveLength(1);
    expect(errors[0].textContent).toBe('Failed to grant access. Please try again.');
    expect(body.firstElementChild).toBe(errors[0]);
  });

  // -- new user -------------------------------------------------------------
  describe('+ New User', () => {
    async function openNewUserForm(): Promise<HTMLElement> {
      const body = await openPanel();
      q<HTMLButtonElement>(body, 'new-user-toggle')!.click();
      return body;
    }

    function fillNewUser(body: HTMLElement, email: string, first: string, last = ''): void {
      q<HTMLInputElement>(body, 'new-user-email')!.value = email;
      q<HTMLInputElement>(body, 'new-user-firstName')!.value = first;
      q<HTMLInputElement>(body, 'new-user-lastName')!.value = last;
    }

    function submit(body: HTMLElement): void {
      q<HTMLFormElement>(body, 'new-user-form')!.dispatchEvent(
        new Event('submit', { bubbles: true, cancelable: true })
      );
    }

    it('toggle shows and hides the new-user form', async () => {
      const body = await openPanel();
      const toggle = q<HTMLButtonElement>(body, 'new-user-toggle')!;
      const wrap = body.querySelector<HTMLElement>('.access-new-user__form')!;
      expect(wrap.hasAttribute('hidden')).toBe(true);
      toggle.click();
      expect(wrap.hasAttribute('hidden')).toBe(false);
      expect(toggle.getAttribute('aria-expanded')).toBe('true');
      toggle.click();
      expect(wrap.hasAttribute('hidden')).toBe(true);
      expect(toggle.getAttribute('aria-expanded')).toBe('false');
    });

    it('requires email and first name', async () => {
      const body = await openNewUserForm();
      fillNewUser(body, 'new@example.com', '  ');
      submit(body);
      await flush();
      expect(mockCreateUser).not.toHaveBeenCalled();
      const err = q(body, 'new-user-error')!;
      expect(err.hasAttribute('hidden')).toBe(false);
      expect(err.textContent).toBe('Email and first name are required.');
    });

    it('creates the user, grants access, collapses the form and refreshes', async () => {
      mockCreateUser.mockResolvedValue({ userId: 'u-new' });
      mockGrantBatchAccess.mockResolvedValue({});
      const body = await openNewUserForm();
      fillNewUser(body, ' new@example.com ', 'Nina', 'Lopez');

      mockListBatchAccess.mockResolvedValue({
        users: [{ ...bob, userId: 'u-new', email: 'new@example.com', firstName: 'Nina' }],
      });
      submit(body);
      await flush();

      expect(mockCreateUser).toHaveBeenCalledWith({
        email: 'new@example.com',
        firstName: 'Nina',
        lastName: 'Lopez',
      });
      expect(mockGrantBatchAccess).toHaveBeenCalledWith('b-001', 'u-new');
      expect(mockListBatchAccess).toHaveBeenCalledTimes(2);
      expect(q(body, 'access-user-list')!.textContent).toContain('Nina (new@example.com)');
      expect(q(body, 'new-user-toggle')!.getAttribute('aria-expanded')).toBe('false');
    });

    it('sends lastName as undefined when blank', async () => {
      mockCreateUser.mockResolvedValue({ userId: 'u-new' });
      mockGrantBatchAccess.mockResolvedValue({});
      const body = await openNewUserForm();
      fillNewUser(body, 'new@example.com', 'Nina');
      submit(body);
      await flush();
      expect(mockCreateUser).toHaveBeenCalledWith({
        email: 'new@example.com',
        firstName: 'Nina',
        lastName: undefined,
      });
    });

    it('shows the API error and re-enables submit when user creation fails', async () => {
      mockCreateUser.mockRejectedValue(makeApiError('USER_EXISTS', 'That email is taken.'));
      const body = await openNewUserForm();
      fillNewUser(body, 'dup@example.com', 'Dup');
      submit(body);
      expect(q<HTMLButtonElement>(body, 'new-user-submit')!.disabled).toBe(true);
      await flush();

      expect(q<HTMLButtonElement>(body, 'new-user-submit')!.disabled).toBe(false);
      expect(q(body, 'new-user-error')!.textContent).toBe('That email is taken.');
      expect(mockGrantBatchAccess).not.toHaveBeenCalled();
    });

    it('shows a generic error when user creation fails unexpectedly', async () => {
      mockCreateUser.mockRejectedValue(new Error('boom'));
      const body = await openNewUserForm();
      fillNewUser(body, 'x@example.com', 'X');
      submit(body);
      await flush();
      expect(q(body, 'new-user-error')!.textContent).toBe('Failed to create user.');
    });

    it('offers a retry when the user is created but the grant fails, and retry grants', async () => {
      mockCreateUser.mockResolvedValue({ userId: 'u-new' });
      mockGrantBatchAccess.mockRejectedValueOnce(new Error('boom'));
      const body = await openNewUserForm();
      fillNewUser(body, 'new@example.com', 'Nina');
      submit(body);
      await flush();

      const err = q(body, 'new-user-error')!;
      expect(err.hasAttribute('hidden')).toBe(false);
      expect(err.textContent).toContain(
        'User "new@example.com" was created but access grant failed.'
      );
      expect(q<HTMLButtonElement>(body, 'new-user-submit')!.disabled).toBe(false);

      mockGrantBatchAccess.mockResolvedValueOnce({});
      q<HTMLButtonElement>(err, 'grant-retry-btn')!.click();
      expect(err.hasAttribute('hidden')).toBe(true);
      await flush();

      expect(mockGrantBatchAccess).toHaveBeenLastCalledWith('b-001', 'u-new');
      expect(mockListBatchAccess).toHaveBeenCalledTimes(2);
    });
  });

  // -- revoke ---------------------------------------------------------------
  describe('revoke', () => {
    async function openRevokeDialog(): Promise<HTMLElement> {
      mockListBatchAccess.mockResolvedValue({ users: [alice, bob] });
      const body = await openPanel();
      q<HTMLButtonElement>(body, 'remove-btn-u-alice')!.click();
      return body;
    }

    it('shows a confirmation dialog naming the user, with focus on Remove', async () => {
      await openRevokeDialog();
      const overlay = q(document, 'revoke-overlay')!;
      expect(overlay.querySelector('[role="dialog"]')!.textContent).toContain(
        'Remove Alice Smith (alice@example.com) from this batch?'
      );
      expect(document.activeElement).toBe(q(overlay, 'revoke-confirm-btn'));
    });

    it('names a user without a last name correctly', async () => {
      mockListBatchAccess.mockResolvedValue({ users: [bob] });
      const body = await openPanel();
      q<HTMLButtonElement>(body, 'remove-btn-u-bob')!.click();
      expect(q(document, 'revoke-overlay')!.textContent).toContain(
        'Remove Bob (bob@example.com) from this batch?'
      );
    });

    it('Cancel dismisses the dialog without revoking', async () => {
      await openRevokeDialog();
      q<HTMLButtonElement>(document, 'revoke-cancel-btn')!.click();
      expect(q(document, 'revoke-overlay')).toBeNull();
      expect(mockRevokeBatchAccess).not.toHaveBeenCalled();
    });

    it('confirming revokes access and refreshes the list', async () => {
      mockRevokeBatchAccess.mockResolvedValue(undefined);
      const body = await openRevokeDialog();
      mockListBatchAccess.mockResolvedValue({ users: [bob] });
      q<HTMLButtonElement>(document, 'revoke-confirm-btn')!.click();
      await flush();

      expect(q(document, 'revoke-overlay')).toBeNull();
      expect(mockRevokeBatchAccess).toHaveBeenCalledWith('b-001', 'u-alice');
      expect(q(body, 'remove-btn-u-alice')).toBeNull();
      expect(q(body, 'remove-btn-u-bob')).not.toBeNull();
    });

    it('shows the API error message when revoke fails', async () => {
      mockRevokeBatchAccess.mockRejectedValue(makeApiError('NOT_FOUND', 'Grant not found.', 404));
      const body = await openRevokeDialog();
      q<HTMLButtonElement>(document, 'revoke-confirm-btn')!.click();
      await flush();
      expect(q(body, 'access-error')!.textContent).toBe('Grant not found.');
      expect(q(body, 'remove-btn-u-alice')).not.toBeNull();
    });

    it('shows a generic message when revoke fails unexpectedly', async () => {
      mockRevokeBatchAccess.mockRejectedValue(new Error('boom'));
      const body = await openRevokeDialog();
      q<HTMLButtonElement>(document, 'revoke-confirm-btn')!.click();
      await flush();
      expect(q(body, 'access-error')!.textContent).toBe(
        'Failed to revoke access. Please try again.'
      );
    });
  });
});
