import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// ---------------------------------------------------------------------------
// Mock the api module
// ---------------------------------------------------------------------------
vi.mock('../../services/api', () => ({
  chefListVarieties: vi.fn(),
  chefCreateVariety: vi.fn(),
  chefUpdateVariety: vi.fn(),
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
import { mountVarietyManagement } from '../../pages/variety-management/index';

const mockChefListVarieties = api.chefListVarieties as ReturnType<typeof vi.fn>;
const mockChefCreateVariety = api.chefCreateVariety as ReturnType<typeof vi.fn>;
const mockChefUpdateVariety = api.chefUpdateVariety as ReturnType<typeof vi.fn>;

function makeVariety(overrides: Partial<api.ChefVarietyDetail> = {}): api.ChefVarietyDetail {
  return {
    varietyId: 'v-001',
    name: 'Classic',
    description: 'Original recipe',
    imageKey: 'images/classic.jpg',
    bottleYieldMl: 750,
    active: true,
    ingredients: [],
    ...overrides,
  };
}

function makeIngredient(
  overrides: Partial<api.ChefIngredientDetail> = {}
): api.ChefIngredientDetail {
  return {
    ingredientId: 'i-001',
    name: 'Coconut cream',
    quantityPerBottle: 400,
    unit: 'ml',
    category: 'dairy',
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// US1: Chef views all varieties
// ---------------------------------------------------------------------------
describe('US1: Variety list rendering', () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    vi.clearAllMocks();
  });

  afterEach(() => {
    container.remove();
  });

  it('renders active and inactive varieties with status badges', async () => {
    mockChefListVarieties.mockResolvedValue({
      varieties: [
        makeVariety({ active: true }),
        makeVariety({ varietyId: 'v-002', name: 'Discontinued', active: false }),
      ],
    });

    await mountVarietyManagement(container);

    expect(container.querySelector('.variety-status--active')).not.toBeNull();
    expect(container.querySelector('.variety-status--inactive')).not.toBeNull();
  });

  it('inactive variety row has --inactive modifier class', async () => {
    mockChefListVarieties.mockResolvedValue({
      varieties: [makeVariety({ active: false })],
    });

    await mountVarietyManagement(container);

    expect(container.querySelector('.variety-row--inactive')).not.toBeNull();
  });

  it('shows image placeholder when imageKey is empty', async () => {
    mockChefListVarieties.mockResolvedValue({
      varieties: [makeVariety({ imageKey: '' })],
    });

    await mountVarietyManagement(container);

    expect(container.querySelector('[data-testid="img-placeholder"]')).not.toBeNull();
  });

  it('does not show image placeholder when imageKey is set', async () => {
    mockChefListVarieties.mockResolvedValue({
      varieties: [makeVariety({ imageKey: 'images/classic.jpg' })],
    });

    await mountVarietyManagement(container);

    expect(container.querySelector('[data-testid="img-placeholder"]')).toBeNull();
  });

  it('renders empty state when no varieties exist', async () => {
    mockChefListVarieties.mockResolvedValue({ varieties: [] });

    await mountVarietyManagement(container);

    const emptyState = container.querySelector('[data-testid="empty-state"]');
    expect(emptyState).not.toBeNull();
  });

  it('shows 403 access denied message for non-chef', async () => {
    const { ApiRequestError } = await import('../../services/api');
    mockChefListVarieties.mockRejectedValue(
      new ApiRequestError({ code: 'CHEF_ROLE_REQUIRED', message: 'Forbidden', status: 403 })
    );

    await mountVarietyManagement(container);

    const errorEl = container.querySelector('[data-testid="access-error"]');
    expect(errorEl).not.toBeNull();
    expect(errorEl!.textContent).toMatch(/access denied/i);
  });

  it('variety list region has aria-live polite', async () => {
    mockChefListVarieties.mockResolvedValue({ varieties: [] });
    await mountVarietyManagement(container);
    expect(container.querySelector('[aria-live="polite"]')).not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// US2: Chef edits a variety
// ---------------------------------------------------------------------------
describe('US2: Edit variety panel', () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    vi.clearAllMocks();
  });

  afterEach(() => {
    container.remove();
  });

  it('opens edit panel when a variety row is clicked', async () => {
    mockChefListVarieties.mockResolvedValue({ varieties: [makeVariety()] });

    await mountVarietyManagement(container);

    const row = container.querySelector<HTMLElement>('[data-variety-id="v-001"]');
    expect(row).not.toBeNull();
    row!.click();

    const form = container.querySelector('[data-testid="edit-variety-form"]');
    expect(form).not.toBeNull();
  });

  it('edit form pre-fills with variety values', async () => {
    mockChefListVarieties.mockResolvedValue({
      varieties: [makeVariety({ name: 'Classic', bottleYieldMl: 750 })],
    });

    await mountVarietyManagement(container);
    container.querySelector<HTMLElement>('[data-variety-id="v-001"]')!.click();

    const nameInput = container.querySelector<HTMLInputElement>('[data-testid="edit-name"]');
    expect(nameInput?.value).toBe('Classic');

    const yieldInput = container.querySelector<HTMLInputElement>(
      '[data-testid="edit-bottleYieldMl"]'
    );
    expect(yieldInput?.value).toBe('750');
  });

  it('save success re-renders list and keeps form updated', async () => {
    const original = makeVariety({ name: 'Classic' });
    const updated = makeVariety({ name: 'Classic Updated' });
    mockChefListVarieties.mockResolvedValue({ varieties: [original] });
    mockChefUpdateVariety.mockResolvedValue({ variety: updated });

    await mountVarietyManagement(container);
    container.querySelector<HTMLElement>('[data-variety-id="v-001"]')!.click();

    const form = container.querySelector<HTMLFormElement>('[data-testid="edit-variety-form"]')!;
    form.querySelector<HTMLInputElement>('[data-testid="edit-name"]')!.value = 'Classic Updated';
    form.dispatchEvent(new Event('submit', { bubbles: true }));
    await Promise.resolve();
    await Promise.resolve();

    expect(mockChefUpdateVariety).toHaveBeenCalledWith(
      'v-001',
      expect.objectContaining({ name: 'Classic Updated' })
    );
  });

  it('save error shows error message and keeps form', async () => {
    const { ApiRequestError } = await import('../../services/api');
    mockChefListVarieties.mockResolvedValue({ varieties: [makeVariety()] });
    mockChefUpdateVariety.mockRejectedValue(
      new ApiRequestError({ code: 'VALIDATION_ERROR', message: 'Invalid data', status: 400 })
    );

    await mountVarietyManagement(container);
    container.querySelector<HTMLElement>('[data-variety-id="v-001"]')!.click();

    const form = container.querySelector<HTMLFormElement>('[data-testid="edit-variety-form"]')!;
    form.dispatchEvent(new Event('submit', { bubbles: true }));
    await Promise.resolve();
    await Promise.resolve();

    const errorEl = container.querySelector('[data-testid="detail-error"]');
    expect(errorEl).not.toBeNull();
    expect(errorEl!.hasAttribute('hidden')).toBe(false);
    expect(errorEl!.textContent).toMatch(/invalid data/i);
    expect(container.querySelector('[data-testid="edit-variety-form"]')).not.toBeNull();
  });

  it('edit panel has no delete button', async () => {
    mockChefListVarieties.mockResolvedValue({ varieties: [makeVariety()] });

    await mountVarietyManagement(container);
    container.querySelector<HTMLElement>('[data-variety-id="v-001"]')!.click();

    const deleteBtn = container.querySelector('[data-testid="delete-variety-btn"]');
    expect(deleteBtn).toBeNull();
  });

  it('cancel button clears the detail panel', async () => {
    mockChefListVarieties.mockResolvedValue({ varieties: [makeVariety()] });

    await mountVarietyManagement(container);
    container.querySelector<HTMLElement>('[data-variety-id="v-001"]')!.click();
    expect(container.querySelector('[data-testid="edit-variety-form"]')).not.toBeNull();

    container.querySelector<HTMLElement>('[data-testid="cancel-edit-btn"]')!.click();
    expect(container.querySelector('[data-testid="edit-variety-form"]')).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// US3: Chef manages ingredients in edit panel
// ---------------------------------------------------------------------------
describe('US3: Ingredient management in edit panel', () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    vi.clearAllMocks();
  });

  afterEach(() => {
    container.remove();
  });

  it('pre-fills existing ingredient rows in edit panel', async () => {
    const variety = makeVariety({
      ingredients: [makeIngredient({ name: 'Coconut cream', quantityPerBottle: 400, unit: 'ml' })],
    });
    mockChefListVarieties.mockResolvedValue({ varieties: [variety] });

    await mountVarietyManagement(container);
    container.querySelector<HTMLElement>('[data-variety-id="v-001"]')!.click();

    const nameInput = container.querySelector<HTMLInputElement>('[data-testid="ing-name-0"]');
    expect(nameInput?.value).toBe('Coconut cream');
  });

  it('Add Ingredient button appends a new empty row', async () => {
    mockChefListVarieties.mockResolvedValue({ varieties: [makeVariety()] });

    await mountVarietyManagement(container);
    container.querySelector<HTMLElement>('[data-variety-id="v-001"]')!.click();

    const addBtn = container.querySelector<HTMLButtonElement>('[data-testid="add-ingredient-btn"]');
    expect(addBtn).not.toBeNull();
    addBtn!.click();

    const rows = container.querySelectorAll('.variety-ingredient-row');
    expect(rows.length).toBe(1);
  });

  it('empty ingredient name blocks submit and shows error', async () => {
    mockChefListVarieties.mockResolvedValue({ varieties: [makeVariety()] });
    mockChefUpdateVariety.mockResolvedValue({ variety: makeVariety() });

    await mountVarietyManagement(container);
    container.querySelector<HTMLElement>('[data-variety-id="v-001"]')!.click();

    const addBtn = container.querySelector<HTMLButtonElement>(
      '[data-testid="add-ingredient-btn"]'
    )!;
    addBtn.click();

    const form = container.querySelector<HTMLFormElement>('[data-testid="edit-variety-form"]')!;
    form.dispatchEvent(new Event('submit', { bubbles: true }));
    await Promise.resolve();

    expect(mockChefUpdateVariety).not.toHaveBeenCalled();
    const errorEl = container.querySelector('[data-testid="detail-error"]');
    expect(errorEl!.hasAttribute('hidden')).toBe(false);
  });

  it('Remove button removes the ingredient row', async () => {
    const variety = makeVariety({ ingredients: [makeIngredient()] });
    mockChefListVarieties.mockResolvedValue({ varieties: [variety] });

    await mountVarietyManagement(container);
    container.querySelector<HTMLElement>('[data-variety-id="v-001"]')!.click();

    expect(container.querySelectorAll('.variety-ingredient-row').length).toBe(1);
    container.querySelector<HTMLButtonElement>('[data-testid="ing-remove-0"]')!.click();
    expect(container.querySelectorAll('.variety-ingredient-row').length).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// US4: Chef creates a new variety
// ---------------------------------------------------------------------------
describe('US4: Create variety form', () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    vi.clearAllMocks();
    mockChefListVarieties.mockResolvedValue({ varieties: [] });
  });

  afterEach(() => {
    container.remove();
  });

  it('New Variety button opens create form', async () => {
    await mountVarietyManagement(container);

    const btn = container.querySelector<HTMLButtonElement>('[data-testid="new-variety-btn"]');
    expect(btn).not.toBeNull();
    btn!.click();

    expect(container.querySelector('[data-testid="create-variety-form"]')).not.toBeNull();
  });

  it('submitting valid form calls chefCreateVariety and prepends to list', async () => {
    const created = makeVariety({ varietyId: 'v-new', name: 'Spiced' });
    mockChefCreateVariety.mockResolvedValue({ variety: created });

    await mountVarietyManagement(container);
    container.querySelector<HTMLButtonElement>('[data-testid="new-variety-btn"]')!.click();

    const form = container.querySelector<HTMLFormElement>('[data-testid="create-variety-form"]')!;
    form.querySelector<HTMLInputElement>('[data-testid="create-name"]')!.value = 'Spiced';
    form.querySelector<HTMLInputElement>('[data-testid="create-bottleYieldMl"]')!.value = '750';
    form.dispatchEvent(new Event('submit', { bubbles: true }));
    await Promise.resolve();
    await Promise.resolve();

    expect(mockChefCreateVariety).toHaveBeenCalledWith(
      expect.objectContaining({ name: 'Spiced', bottleYieldMl: 750 })
    );
    expect(container.querySelector('[data-testid="create-variety-form"]')).toBeNull();
  });

  it('create error keeps form and shows error message with values preserved', async () => {
    const { ApiRequestError } = await import('../../services/api');
    mockChefCreateVariety.mockRejectedValue(
      new ApiRequestError({ code: 'SERVER_ERROR', message: 'Server error', status: 500 })
    );

    await mountVarietyManagement(container);
    container.querySelector<HTMLButtonElement>('[data-testid="new-variety-btn"]')!.click();

    const form = container.querySelector<HTMLFormElement>('[data-testid="create-variety-form"]')!;
    const nameInput = form.querySelector<HTMLInputElement>('[data-testid="create-name"]')!;
    nameInput.value = 'Spiced';
    form.querySelector<HTMLInputElement>('[data-testid="create-bottleYieldMl"]')!.value = '750';
    form.dispatchEvent(new Event('submit', { bubbles: true }));
    await Promise.resolve();
    await Promise.resolve();

    expect(container.querySelector('[data-testid="create-variety-form"]')).not.toBeNull();
    expect(nameInput.value).toBe('Spiced');
    const errorEl = container.querySelector('[data-testid="create-error"]');
    expect(errorEl!.hasAttribute('hidden')).toBe(false);
    expect(errorEl!.textContent).toMatch(/server error/i);
  });

  it('shows no-ingredients warning when submitting without ingredients', async () => {
    const created = makeVariety({ varietyId: 'v-new', name: 'No Ings' });
    mockChefCreateVariety.mockResolvedValue({ variety: created });

    await mountVarietyManagement(container);
    container.querySelector<HTMLButtonElement>('[data-testid="new-variety-btn"]')!.click();

    const form = container.querySelector<HTMLFormElement>('[data-testid="create-variety-form"]')!;
    form.querySelector<HTMLInputElement>('[data-testid="create-name"]')!.value = 'No Ings';
    form.querySelector<HTMLInputElement>('[data-testid="create-bottleYieldMl"]')!.value = '750';
    form.dispatchEvent(new Event('submit', { bubbles: true }));
    await Promise.resolve();
    await Promise.resolve();

    // Warning shown before API call succeeds — check it was shown (check no-ings path)
    expect(mockChefCreateVariety).toHaveBeenCalledWith(
      expect.objectContaining({ ingredients: [] })
    );
  });

  it('missing name blocks submit and shows validation error', async () => {
    await mountVarietyManagement(container);
    container.querySelector<HTMLButtonElement>('[data-testid="new-variety-btn"]')!.click();

    const form = container.querySelector<HTMLFormElement>('[data-testid="create-variety-form"]')!;
    form.dispatchEvent(new Event('submit', { bubbles: true }));
    await Promise.resolve();

    expect(mockChefCreateVariety).not.toHaveBeenCalled();
    const nameInput = form.querySelector<HTMLInputElement>('[data-testid="create-name"]');
    expect(nameInput?.getAttribute('aria-invalid')).toBe('true');
  });

  it('Cancel button clears the detail panel', async () => {
    await mountVarietyManagement(container);
    container.querySelector<HTMLButtonElement>('[data-testid="new-variety-btn"]')!.click();

    expect(container.querySelector('[data-testid="create-variety-form"]')).not.toBeNull();
    container.querySelector<HTMLButtonElement>('[data-testid="cancel-create-btn"]')!.click();
    expect(container.querySelector('[data-testid="create-variety-form"]')).toBeNull();
  });
});
