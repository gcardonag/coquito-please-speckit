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
