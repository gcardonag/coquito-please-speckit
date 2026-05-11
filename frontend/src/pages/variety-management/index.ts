import './variety-management.css';
import {
  ApiRequestError,
  type ChefIngredientDetail,
  type ChefVarietyDetail,
  type IngredientPayload,
  chefCreateVariety,
  chefListVarieties,
  chefUpdateVariety,
} from '../../services/api';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let varieties: ChefVarietyDetail[] = [];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function el<T extends HTMLElement>(tag: string, attrs: Record<string, string> = {}, text = ''): T {
  const elem = document.createElement(tag) as T;
  for (const [k, v] of Object.entries(attrs)) elem.setAttribute(k, v);
  if (text) elem.textContent = text;
  return elem;
}

function statusBadge(active: boolean): HTMLElement {
  const span = el<HTMLSpanElement>('span', {
    class: `variety-status variety-status--${active ? 'active' : 'inactive'}`,
    'aria-label': `Status: ${active ? 'active' : 'inactive'}`,
  });
  span.textContent = active ? 'Active' : 'Inactive';
  return span;
}

// ---------------------------------------------------------------------------
// Render list
// ---------------------------------------------------------------------------
function renderList(container: HTMLElement): void {
  const listEl = container.querySelector<HTMLElement>('[data-testid="variety-list"]');
  if (!listEl) return;
  listEl.innerHTML = '';

  if (varieties.length === 0) {
    const empty = el('div', { class: 'variety-empty', 'data-testid': 'empty-state' });
    const msg = el('p', { class: 'variety-empty__message' });
    msg.textContent = 'No varieties yet. Create the first one.';
    empty.appendChild(msg);
    listEl.appendChild(empty);
    return;
  }

  const ul = el('ul', { class: 'variety-list', role: 'list' });
  for (const variety of varieties) {
    const li = el<HTMLLIElement>('li', {
      class: `variety-row${variety.active ? '' : ' variety-row--inactive'}`,
      role: 'listitem',
      tabindex: '0',
      'data-variety-id': variety.varietyId,
    });

    if (!variety.imageKey) {
      const placeholder = el('div', {
        class: 'variety-img-placeholder',
        'aria-hidden': 'true',
        'data-testid': 'img-placeholder',
      });
      li.appendChild(placeholder);
    }

    const info = el('div', { class: 'variety-row__info' });
    const name = el('div', { class: 'variety-row__name' }, variety.name);
    const meta = el('div', { class: 'variety-row__meta' });
    meta.textContent = `${variety.bottleYieldMl} ml · ${variety.ingredients.length} ingredient${variety.ingredients.length !== 1 ? 's' : ''}`;
    info.appendChild(name);
    if (variety.description) {
      const desc = el('div', { class: 'variety-row__desc' }, variety.description);
      info.appendChild(desc);
    }
    info.appendChild(meta);

    li.appendChild(info);
    li.appendChild(statusBadge(variety.active));

    const openDetail = () => renderDetail(container, variety);
    li.addEventListener('click', openDetail);
    li.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') openDetail();
    });

    ul.appendChild(li);
  }
  listEl.appendChild(ul);
}

// ---------------------------------------------------------------------------
// Ingredient rows
// ---------------------------------------------------------------------------
function renderIngredientRow(
  container: HTMLElement,
  ingredient?: ChefIngredientDetail,
  idx = 0
): HTMLElement {
  const row = el('div', {
    class: 'variety-ingredient-row',
    'data-testid': `ingredient-row-${idx}`,
  });

  if (ingredient?.ingredientId) {
    const hiddenId = el<HTMLInputElement>('input', {
      type: 'hidden',
      name: `ing-id-${idx}`,
      value: ingredient.ingredientId,
    });
    row.appendChild(hiddenId);
  }

  const nameField = el('div', {
    class: 'variety-ingredient-row__field variety-ingredient-row__field--name',
  });
  const nameLabel = el('label', { class: 'variety-form__label', for: `ing-name-${idx}` }, 'Name');
  const nameInput = el<HTMLInputElement>('input', {
    class: 'variety-form__input',
    type: 'text',
    id: `ing-name-${idx}`,
    name: `ing-name-${idx}`,
    'aria-required': 'true',
    'data-testid': `ing-name-${idx}`,
    value: ingredient?.name ?? '',
  });
  nameField.appendChild(nameLabel);
  nameField.appendChild(nameInput);

  const qtyField = el('div', { class: 'variety-ingredient-row__field' });
  const qtyLabel = el('label', { class: 'variety-form__label', for: `ing-qty-${idx}` }, 'Qty');
  const qtyInput = el<HTMLInputElement>('input', {
    class: 'variety-form__input',
    type: 'number',
    id: `ing-qty-${idx}`,
    name: `ing-qty-${idx}`,
    min: '0.001',
    step: 'any',
    'aria-required': 'true',
    'data-testid': `ing-qty-${idx}`,
    value: ingredient != null ? String(ingredient.quantityPerBottle) : '',
  });
  qtyField.appendChild(qtyLabel);
  qtyField.appendChild(qtyInput);

  const unitField = el('div', { class: 'variety-ingredient-row__field' });
  const unitLabel = el('label', { class: 'variety-form__label', for: `ing-unit-${idx}` }, 'Unit');
  const unitInput = el<HTMLInputElement>('input', {
    class: 'variety-form__input',
    type: 'text',
    id: `ing-unit-${idx}`,
    name: `ing-unit-${idx}`,
    'aria-required': 'true',
    'data-testid': `ing-unit-${idx}`,
    value: ingredient?.unit ?? '',
  });
  unitField.appendChild(unitLabel);
  unitField.appendChild(unitInput);

  const catField = el('div', { class: 'variety-ingredient-row__field' });
  const catLabel = el('label', { class: 'variety-form__label', for: `ing-cat-${idx}` }, 'Category');
  const catInput = el<HTMLInputElement>('input', {
    class: 'variety-form__input',
    type: 'text',
    id: `ing-cat-${idx}`,
    name: `ing-cat-${idx}`,
    'aria-required': 'true',
    'data-testid': `ing-cat-${idx}`,
    value: ingredient?.category ?? '',
  });
  catField.appendChild(catLabel);
  catField.appendChild(catInput);

  const removeBtn = el<HTMLButtonElement>(
    'button',
    {
      type: 'button',
      class: 'btn btn--secondary variety-ingredient-row__remove',
      'data-testid': `ing-remove-${idx}`,
      'aria-label': 'Remove ingredient',
    },
    'Remove'
  );
  removeBtn.addEventListener('click', () => {
    row.remove();
    reindexIngredientRows(container);
  });

  row.appendChild(nameField);
  row.appendChild(qtyField);
  row.appendChild(unitField);
  row.appendChild(catField);
  row.appendChild(removeBtn);

  return row;
}

function reindexIngredientRows(container: HTMLElement): void {
  const rows = container.querySelectorAll<HTMLElement>('.variety-ingredient-row');
  rows.forEach((row, i) => {
    row.setAttribute('data-testid', `ingredient-row-${i}`);
    const inputs = row.querySelectorAll<HTMLInputElement | HTMLButtonElement>(
      '[id^="ing-"], [name^="ing-"], [data-testid^="ing-"], [for^="ing-"]'
    );
    inputs.forEach((el) => {
      for (const attr of ['id', 'name', 'for', 'data-testid'] as const) {
        const v = el.getAttribute(attr);
        if (v) el.setAttribute(attr, v.replace(/-\d+$/, `-${i}`));
      }
    });
  });
}

function collectIngredientRows(form: HTMLFormElement): IngredientPayload[] {
  const rows = form.querySelectorAll<HTMLElement>('.variety-ingredient-row');
  const result: IngredientPayload[] = [];
  rows.forEach((row) => {
    const nameInput = row.querySelector<HTMLInputElement>('input[name^="ing-name"]');
    const qtyInput = row.querySelector<HTMLInputElement>('input[name^="ing-qty"]');
    const unitInput = row.querySelector<HTMLInputElement>('input[name^="ing-unit"]');
    const catInput = row.querySelector<HTMLInputElement>('input[name^="ing-cat"]');
    const idInput = row.querySelector<HTMLInputElement>('input[name^="ing-id"]');

    const ingredient: IngredientPayload = {
      name: nameInput?.value.trim() ?? '',
      quantityPerBottle: parseFloat(qtyInput?.value ?? '0'),
      unit: unitInput?.value.trim() ?? '',
      category: catInput?.value.trim() ?? '',
    };
    if (idInput?.value) ingredient.ingredientId = idInput.value;
    result.push(ingredient);
  });
  return result;
}

function validateIngredients(form: HTMLFormElement): boolean {
  const rows = form.querySelectorAll<HTMLElement>('.variety-ingredient-row');
  let valid = true;
  rows.forEach((row) => {
    const nameInput = row.querySelector<HTMLInputElement>('input[name^="ing-name"]');
    if (nameInput && !nameInput.value.trim()) {
      nameInput.setAttribute('aria-invalid', 'true');
      valid = false;
    } else {
      nameInput?.removeAttribute('aria-invalid');
    }
  });
  return valid;
}

function addIngredientRow(ingredientsEl: HTMLElement): void {
  const existingRows = ingredientsEl.querySelectorAll('.variety-ingredient-row').length;
  const newRow = renderIngredientRow(ingredientsEl, undefined, existingRows);
  ingredientsEl.appendChild(newRow);
}

// ---------------------------------------------------------------------------
// Render detail / edit panel
// ---------------------------------------------------------------------------
function renderDetail(container: HTMLElement, variety: ChefVarietyDetail): void {
  const detailEl = container.querySelector<HTMLElement>('[data-testid="variety-detail"]');
  if (!detailEl) return;
  detailEl.innerHTML = '';

  const form = el<HTMLFormElement>('form', {
    'data-testid': 'edit-variety-form',
    class: 'variety-form',
  });

  const title = el('h3', { class: 'variety-form__title' }, `Edit: ${variety.name}`);
  detailEl.appendChild(title);

  const errorEl = el('div', {
    class: 'variety-error',
    'data-testid': 'detail-error',
    hidden: '',
  });
  detailEl.appendChild(errorEl);

  // Name
  const nameWrap = el('div', { class: 'variety-form__field' });
  const nameLabel = el<HTMLLabelElement>(
    'label',
    { class: 'variety-form__label', for: 'edit-name' },
    'Name'
  );
  const nameInput = el<HTMLInputElement>('input', {
    class: 'variety-form__input',
    type: 'text',
    id: 'edit-name',
    name: 'name',
    value: variety.name,
    'aria-required': 'true',
    'data-testid': 'edit-name',
  });
  nameWrap.appendChild(nameLabel);
  nameWrap.appendChild(nameInput);
  form.appendChild(nameWrap);

  // Description
  const descWrap = el('div', { class: 'variety-form__field' });
  const descLabel = el<HTMLLabelElement>(
    'label',
    { class: 'variety-form__label', for: 'edit-description' },
    'Description'
  );
  const descInput = el<HTMLInputElement>('input', {
    class: 'variety-form__input',
    type: 'text',
    id: 'edit-description',
    name: 'description',
    value: variety.description,
    'data-testid': 'edit-description',
  });
  descWrap.appendChild(descLabel);
  descWrap.appendChild(descInput);
  form.appendChild(descWrap);

  // Image Key
  const imageWrap = el('div', { class: 'variety-form__field' });
  const imageLabel = el<HTMLLabelElement>(
    'label',
    { class: 'variety-form__label', for: 'edit-imageKey' },
    'Image Key'
  );
  const imageInput = el<HTMLInputElement>('input', {
    class: 'variety-form__input',
    type: 'text',
    id: 'edit-imageKey',
    name: 'imageKey',
    value: variety.imageKey,
    'data-testid': 'edit-imageKey',
  });
  imageWrap.appendChild(imageLabel);
  imageWrap.appendChild(imageInput);
  form.appendChild(imageWrap);

  // Bottle Yield
  const yieldWrap = el('div', { class: 'variety-form__field' });
  const yieldLabel = el<HTMLLabelElement>(
    'label',
    { class: 'variety-form__label', for: 'edit-bottleYieldMl' },
    'Bottle Yield (ml)'
  );
  const yieldInput = el<HTMLInputElement>('input', {
    class: 'variety-form__input',
    type: 'number',
    id: 'edit-bottleYieldMl',
    name: 'bottleYieldMl',
    min: '1',
    value: String(variety.bottleYieldMl),
    'aria-required': 'true',
    'data-testid': 'edit-bottleYieldMl',
  });
  yieldWrap.appendChild(yieldLabel);
  yieldWrap.appendChild(yieldInput);
  form.appendChild(yieldWrap);

  // Active toggle
  const activeWrap = el('div', { class: 'variety-form__field variety-form__field--checkbox' });
  const activeCheckbox = el<HTMLInputElement>('input', {
    class: 'variety-form__checkbox',
    type: 'checkbox',
    id: 'edit-active',
    name: 'active',
    'data-testid': 'edit-active',
  });
  activeCheckbox.checked = variety.active;
  const activeLabel = el<HTMLLabelElement>(
    'label',
    { class: 'variety-form__label', for: 'edit-active' },
    'Active'
  );
  activeWrap.appendChild(activeCheckbox);
  activeWrap.appendChild(activeLabel);
  form.appendChild(activeWrap);

  // Ingredients
  const ingredientsSection = el('div', { class: 'variety-form__field' });
  const ingLabel = el('div', { class: 'variety-form__label' }, 'Ingredients');
  ingredientsSection.appendChild(ingLabel);
  const ingredientsEl = el('div', {
    class: 'variety-form__ingredients',
    'data-testid': 'ingredients-container',
  });
  variety.ingredients.forEach((ing, i) => {
    ingredientsEl.appendChild(renderIngredientRow(ingredientsEl, ing, i));
  });
  ingredientsSection.appendChild(ingredientsEl);
  const addIngBtn = el<HTMLButtonElement>(
    'button',
    {
      type: 'button',
      class: 'btn btn--secondary',
      'data-testid': 'add-ingredient-btn',
    },
    'Add Ingredient'
  );
  addIngBtn.addEventListener('click', () => addIngredientRow(ingredientsEl));
  ingredientsSection.appendChild(addIngBtn);
  form.appendChild(ingredientsSection);

  // Actions
  const actions = el('div', { class: 'variety-form__actions' });
  const saveBtn = el<HTMLButtonElement>(
    'button',
    {
      type: 'submit',
      class: 'btn btn--primary',
      'data-testid': 'save-variety-btn',
    },
    'Save Changes'
  );
  const cancelBtn = el<HTMLButtonElement>(
    'button',
    {
      type: 'button',
      class: 'btn btn--secondary',
      'data-testid': 'cancel-edit-btn',
    },
    'Cancel'
  );
  cancelBtn.addEventListener('click', () => {
    detailEl.innerHTML = '';
  });
  actions.appendChild(saveBtn);
  actions.appendChild(cancelBtn);
  form.appendChild(actions);

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorEl.setAttribute('hidden', '');
    errorEl.textContent = '';

    if (!validateIngredients(form)) {
      errorEl.removeAttribute('hidden');
      errorEl.textContent = 'Each ingredient must have a name.';
      return;
    }

    const payload = {
      name: nameInput.value.trim(),
      description: descInput.value,
      imageKey: imageInput.value,
      bottleYieldMl: parseInt(yieldInput.value, 10),
      active: activeCheckbox.checked,
      ingredients: collectIngredientRows(form),
    };

    try {
      const { variety: updated } = await chefUpdateVariety(variety.varietyId, payload);
      const idx = varieties.findIndex((v) => v.varietyId === variety.varietyId);
      if (idx !== -1) varieties[idx] = updated;
      renderList(container);
      renderDetail(container, updated);
    } catch (err) {
      errorEl.removeAttribute('hidden');
      errorEl.textContent =
        err instanceof ApiRequestError ? err.message : 'An unexpected error occurred.';
    }
  });

  detailEl.appendChild(form);
}

// ---------------------------------------------------------------------------
// Create variety form
// ---------------------------------------------------------------------------
function showCreateForm(container: HTMLElement): void {
  const detailEl = container.querySelector<HTMLElement>('[data-testid="variety-detail"]');
  if (!detailEl) return;
  detailEl.innerHTML = '';

  const form = el<HTMLFormElement>('form', {
    'data-testid': 'create-variety-form',
    class: 'variety-form',
  });

  const title = el('h3', { class: 'variety-form__title' }, 'New Variety');
  detailEl.appendChild(title);

  const warningEl = el('div', {
    class: 'variety-warning',
    'data-testid': 'no-ingredients-warning',
    hidden: '',
  });
  warningEl.textContent = 'No ingredients added. The variety will be created without any.';
  detailEl.appendChild(warningEl);

  const errorEl = el('div', {
    class: 'variety-error',
    'data-testid': 'create-error',
    hidden: '',
  });
  detailEl.appendChild(errorEl);

  // Name
  const nameWrap = el('div', { class: 'variety-form__field' });
  const nameLabel = el<HTMLLabelElement>(
    'label',
    { class: 'variety-form__label', for: 'create-name' },
    'Name'
  );
  const nameInput = el<HTMLInputElement>('input', {
    class: 'variety-form__input',
    type: 'text',
    id: 'create-name',
    name: 'name',
    'aria-required': 'true',
    'data-testid': 'create-name',
  });
  const nameError = el('div', {
    class: 'variety-form__error',
    role: 'alert',
    id: 'create-name-error',
    hidden: '',
  });
  nameInput.setAttribute('aria-describedby', 'create-name-error');
  nameWrap.appendChild(nameLabel);
  nameWrap.appendChild(nameInput);
  nameWrap.appendChild(nameError);
  form.appendChild(nameWrap);

  // Description
  const descWrap = el('div', { class: 'variety-form__field' });
  const descLabel = el<HTMLLabelElement>(
    'label',
    { class: 'variety-form__label', for: 'create-description' },
    'Description'
  );
  const descInput = el<HTMLInputElement>('input', {
    class: 'variety-form__input',
    type: 'text',
    id: 'create-description',
    name: 'description',
    'data-testid': 'create-description',
  });
  descWrap.appendChild(descLabel);
  descWrap.appendChild(descInput);
  form.appendChild(descWrap);

  // Image Key
  const imageWrap = el('div', { class: 'variety-form__field' });
  const imageLabel = el<HTMLLabelElement>(
    'label',
    { class: 'variety-form__label', for: 'create-imageKey' },
    'Image Key'
  );
  const imageInput = el<HTMLInputElement>('input', {
    class: 'variety-form__input',
    type: 'text',
    id: 'create-imageKey',
    name: 'imageKey',
    'data-testid': 'create-imageKey',
  });
  imageWrap.appendChild(imageLabel);
  imageWrap.appendChild(imageInput);
  form.appendChild(imageWrap);

  // Bottle Yield
  const yieldWrap = el('div', { class: 'variety-form__field' });
  const yieldLabel = el<HTMLLabelElement>(
    'label',
    { class: 'variety-form__label', for: 'create-bottleYieldMl' },
    'Bottle Yield (ml)'
  );
  const yieldInput = el<HTMLInputElement>('input', {
    class: 'variety-form__input',
    type: 'number',
    id: 'create-bottleYieldMl',
    name: 'bottleYieldMl',
    min: '1',
    'aria-required': 'true',
    'data-testid': 'create-bottleYieldMl',
  });
  yieldWrap.appendChild(yieldLabel);
  yieldWrap.appendChild(yieldInput);
  form.appendChild(yieldWrap);

  // Active toggle
  const activeWrap = el('div', { class: 'variety-form__field variety-form__field--checkbox' });
  const activeCheckbox = el<HTMLInputElement>('input', {
    class: 'variety-form__checkbox',
    type: 'checkbox',
    id: 'create-active',
    name: 'active',
    'data-testid': 'create-active',
  });
  activeCheckbox.checked = true;
  const activeLabel = el<HTMLLabelElement>(
    'label',
    { class: 'variety-form__label', for: 'create-active' },
    'Active'
  );
  activeWrap.appendChild(activeCheckbox);
  activeWrap.appendChild(activeLabel);
  form.appendChild(activeWrap);

  // Ingredients
  const ingredientsSection = el('div', { class: 'variety-form__field' });
  const ingLabel = el('div', { class: 'variety-form__label' }, 'Ingredients');
  ingredientsSection.appendChild(ingLabel);
  const ingredientsEl = el('div', {
    class: 'variety-form__ingredients',
    'data-testid': 'ingredients-container',
  });
  ingredientsSection.appendChild(ingredientsEl);
  const addIngBtn = el<HTMLButtonElement>(
    'button',
    {
      type: 'button',
      class: 'btn btn--secondary',
      'data-testid': 'add-ingredient-btn',
    },
    'Add Ingredient'
  );
  addIngBtn.addEventListener('click', () => addIngredientRow(ingredientsEl));
  ingredientsSection.appendChild(addIngBtn);
  form.appendChild(ingredientsSection);

  // Actions
  const actions = el('div', { class: 'variety-form__actions' });
  const submitBtn = el<HTMLButtonElement>(
    'button',
    {
      type: 'submit',
      class: 'btn btn--primary',
      'data-testid': 'create-submit-btn',
    },
    'Create Variety'
  );
  const cancelBtn = el<HTMLButtonElement>(
    'button',
    {
      type: 'button',
      class: 'btn btn--secondary',
      'data-testid': 'cancel-create-btn',
    },
    'Cancel'
  );
  cancelBtn.addEventListener('click', () => {
    detailEl.innerHTML = '';
  });
  actions.appendChild(submitBtn);
  actions.appendChild(cancelBtn);
  form.appendChild(actions);

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorEl.setAttribute('hidden', '');
    errorEl.textContent = '';
    warningEl.setAttribute('hidden', '');
    nameError.setAttribute('hidden', '');
    nameInput.removeAttribute('aria-invalid');

    const name = nameInput.value.trim();
    if (!name) {
      nameInput.setAttribute('aria-invalid', 'true');
      nameError.textContent = 'Name is required.';
      nameError.removeAttribute('hidden');
      return;
    }

    if (!validateIngredients(form)) {
      errorEl.removeAttribute('hidden');
      errorEl.textContent = 'Each ingredient must have a name.';
      return;
    }

    const ingredientRows = collectIngredientRows(form);

    if (ingredientRows.length === 0) {
      warningEl.removeAttribute('hidden');
    }

    const payload = {
      name,
      description: descInput.value,
      imageKey: imageInput.value,
      bottleYieldMl: parseInt(yieldInput.value, 10),
      active: activeCheckbox.checked,
      ingredients: ingredientRows,
    };

    try {
      const { variety: created } = await chefCreateVariety(payload);
      varieties = [created, ...varieties];
      renderList(container);
      detailEl.innerHTML = '';
    } catch (err) {
      warningEl.setAttribute('hidden', '');
      errorEl.removeAttribute('hidden');
      errorEl.textContent =
        err instanceof ApiRequestError ? err.message : 'An unexpected error occurred.';
    }
  });

  detailEl.appendChild(form);
}

// ---------------------------------------------------------------------------
// Mount
// ---------------------------------------------------------------------------
export async function mountVarietyManagement(container: HTMLElement): Promise<void> {
  container.innerHTML = `
    <div class="variety-management">
      <div class="variety-management__header">
        <h2 class="variety-management__title">Manage Varieties</h2>
        <button class="btn btn--primary" data-testid="new-variety-btn" type="button">New Variety</button>
      </div>
      <div aria-live="polite" data-testid="variety-list" aria-label="Variety list"></div>
      <div data-testid="variety-detail"></div>
    </div>
  `;

  container
    .querySelector<HTMLButtonElement>('[data-testid="new-variety-btn"]')!
    .addEventListener('click', () => showCreateForm(container));

  const listRegion = container.querySelector<HTMLElement>('[data-testid="variety-list"]')!;
  listRegion.textContent = 'Loading varieties…';

  try {
    const result = await chefListVarieties();
    varieties = result.varieties;
    renderList(container);
  } catch (err) {
    listRegion.innerHTML = '';
    const errorEl = el('div', { class: 'variety-error', 'data-testid': 'access-error' });
    errorEl.textContent =
      err instanceof ApiRequestError && err.status === 403
        ? 'Access denied. Only chefs can view variety management.'
        : 'Failed to load varieties. Please refresh and try again.';
    listRegion.appendChild(errorEl);
  }
}
