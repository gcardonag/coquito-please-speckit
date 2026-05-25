import './batch-management.css';
import {
  ApiRequestError,
  type BatchAccessUser,
  type BatchSummary,
  type CreateBatchPayload,
  type CurrentUser,
  type UpdateBatchPayload,
  createBatch,
  createUser,
  grantBatchAccess,
  listBatchAccess,
  listBatches,
  listVarieties,
  revokeBatchAccess,
  searchUsers,
  updateBatch,
  updateBatchStatus,
  type VarietySummary,
} from '../../services/api';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let batches: BatchSummary[] = [];
let currentUser: CurrentUser | null = null;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function el<T extends HTMLElement>(tag: string, attrs: Record<string, string> = {}, text = ''): T {
  const elem = document.createElement(tag) as T;
  for (const [k, v] of Object.entries(attrs)) elem.setAttribute(k, v);
  if (text) elem.textContent = text;
  return elem;
}

function statusBadge(status: BatchSummary['status']): HTMLElement {
  const span = el<HTMLSpanElement>('span', {
    class: `batch-status batch-status--${status}`,
    'data-status': status,
    'aria-label': `Status: ${status}`,
  });
  span.textContent = status;
  return span;
}

// ---------------------------------------------------------------------------
// Render list
// ---------------------------------------------------------------------------
function renderList(container: HTMLElement): void {
  const list = container.querySelector<HTMLElement>('[data-testid="batch-list"]');
  if (!list) return;
  list.innerHTML = '';

  if (batches.length === 0) {
    const empty = el('div', { class: 'batch-empty', 'data-testid': 'empty-state' });
    const msg = el('p', { class: 'batch-empty__message' });
    msg.textContent = 'No batches yet. Create the first one to start taking orders.';
    empty.appendChild(msg);
    list.appendChild(empty);
    return;
  }

  const ul = el('ul', { class: 'batch-list', role: 'list' });
  for (const batch of batches) {
    const li = el<HTMLLIElement>('li', {
      class: 'batch-row',
      role: 'listitem',
      tabindex: '0',
      'data-batch-id': batch.batchId,
    });

    const info = el('div', { class: 'batch-row__info' });
    const name = el('div', { class: 'batch-row__name' }, batch.batchName);
    const meta = el('div', { class: 'batch-row__meta' });
    meta.textContent = `Cutoff: ${batch.cutoffDate} · ${batch.availableVarietyIds.length} varieties · ${batch.activeRequestCount} requests`;
    info.appendChild(name);
    info.appendChild(meta);

    li.appendChild(info);
    li.appendChild(statusBadge(batch.status));

    const openDetail = () => renderDetail(container, batch);
    li.addEventListener('click', openDetail);
    li.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') openDetail();
    });

    ul.appendChild(li);
  }
  list.appendChild(ul);
}

// ---------------------------------------------------------------------------
// Render detail / edit panel
// ---------------------------------------------------------------------------
async function renderDetail(container: HTMLElement, batch: BatchSummary): Promise<void> {
  const detailEl = container.querySelector<HTMLElement>('[data-testid="batch-detail"]');
  if (!detailEl) return;

  const isReadOnly = batch.status === 'COMPLETED';
  let varieties: VarietySummary[] = [];
  try {
    const res = await listVarieties();
    varieties = res.varieties;
  } catch {
    // non-fatal; variety checkboxes will just be empty
  }

  detailEl.innerHTML = '';

  const title = el('h3', { class: 'batch-form__title' });
  title.textContent = isReadOnly ? batch.batchName : `Edit: ${batch.batchName}`;
  detailEl.appendChild(title);

  if (isReadOnly) {
    const finalized = el(
      'div',
      { class: 'batch-finalized' },
      'Finalized — this batch cannot be edited'
    );
    detailEl.appendChild(finalized);
    renderReadOnlyFields(detailEl, batch, varieties);
    return;
  }

  const errorEl = el('div', { class: 'batch-error', 'data-testid': 'detail-error', hidden: '' });
  detailEl.appendChild(errorEl);

  const form = renderEditForm(batch, varieties);
  detailEl.appendChild(form);

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorEl.removeAttribute('hidden');
    errorEl.textContent = '';

    const payload: UpdateBatchPayload = {};
    const nameVal = (
      form.querySelector<HTMLInputElement>('[data-testid="edit-batchName"]')?.value ?? ''
    ).trim();
    const dateVal = (
      form.querySelector<HTMLInputElement>('[data-testid="edit-cutoffDate"]')?.value ?? ''
    ).trim();
    const volVal =
      form.querySelector<HTMLInputElement>('[data-testid="edit-maxBottleVolumeMl"]')?.value ?? '';
    const checked = Array.from(
      form.querySelectorAll<HTMLInputElement>('input[type="checkbox"]:checked')
    ).map((c) => c.value);

    if (nameVal) payload.batchName = nameVal;
    if (dateVal) payload.cutoffDate = dateVal;
    if (volVal) payload.maxBottleVolumeMl = parseInt(volVal, 10);
    if (checked.length > 0) payload.availableVarietyIds = checked;

    try {
      const updated = await updateBatch(batch.batchId, payload);
      const idx = batches.findIndex((b) => b.batchId === batch.batchId);
      if (idx !== -1) batches[idx] = updated;
      renderList(container);
      renderDetail(container, updated);
    } catch (err) {
      if (err instanceof ApiRequestError) {
        errorEl.textContent = err.message;
      } else {
        errorEl.textContent = 'An unexpected error occurred. Please try again.';
      }
    }
  });

  renderStatusControls(detailEl, container, batch);

  if (currentUser?.role === 'chef' && batch.status === 'OPEN') {
    renderManageAccessPanel(detailEl, batch);
  }
}

function renderReadOnlyFields(
  detailEl: HTMLElement,
  batch: BatchSummary,
  varieties: VarietySummary[]
): void {
  const fields: Array<[string, string, string]> = [
    ['Name', batch.batchName, 'batchName'],
    ['Cutoff Date', batch.cutoffDate, 'cutoffDate'],
    ['Max Bottle Volume', `${batch.maxBottleVolumeMl} ml`, 'maxBottleVolumeMl'],
    ['Status', batch.status, 'status'],
    [
      'Varieties',
      batch.availableVarietyIds
        .map((id) => varieties.find((v) => v.varietyId === id)?.name ?? id)
        .join(', ') || '—',
      'varieties',
    ],
  ];
  for (const [label, value, testid] of fields) {
    const wrap = el('div', { class: 'batch-form__field' });
    wrap.appendChild(el('span', { class: 'batch-form__label' }, label));
    const valEl = el<HTMLInputElement>('input', {
      class: 'batch-form__input',
      type: 'text',
      value,
      disabled: '',
      'data-testid': `edit-${testid}`,
      'aria-label': label,
    });
    wrap.appendChild(valEl);
    detailEl.appendChild(wrap);
  }
}

function renderEditForm(batch: BatchSummary, varieties: VarietySummary[]): HTMLFormElement {
  const form = el<HTMLFormElement>('form', { 'data-testid': 'edit-batch-form' });

  // Name field
  const nameWrap = el('div', { class: 'batch-form__field' });
  const nameLabel = el<HTMLLabelElement>(
    'label',
    { class: 'batch-form__label', for: 'edit-name' },
    'Batch Name'
  );
  const nameInput = el<HTMLInputElement>('input', {
    class: 'batch-form__input',
    type: 'text',
    id: 'edit-name',
    name: 'batchName',
    value: batch.batchName,
    'data-testid': 'edit-batchName',
    'aria-required': 'true',
  });
  nameWrap.appendChild(nameLabel);
  nameWrap.appendChild(nameInput);
  form.appendChild(nameWrap);

  // Cutoff date field
  const dateWrap = el('div', { class: 'batch-form__field' });
  const dateLabel = el<HTMLLabelElement>(
    'label',
    { class: 'batch-form__label', for: 'edit-date' },
    'Cutoff Date'
  );
  const dateInput = el<HTMLInputElement>('input', {
    class: 'batch-form__input',
    type: 'date',
    id: 'edit-date',
    name: 'cutoffDate',
    value: batch.cutoffDate,
    'data-testid': 'edit-cutoffDate',
    'aria-required': 'true',
  });
  dateWrap.appendChild(dateLabel);
  dateWrap.appendChild(dateInput);
  form.appendChild(dateWrap);

  // Volume field
  const volWrap = el('div', { class: 'batch-form__field' });
  const volLabel = el<HTMLLabelElement>(
    'label',
    { class: 'batch-form__label', for: 'edit-volume' },
    'Max Bottle Volume (ml)'
  );
  const volInput = el<HTMLInputElement>('input', {
    class: 'batch-form__input',
    type: 'number',
    id: 'edit-volume',
    name: 'maxBottleVolumeMl',
    value: String(batch.maxBottleVolumeMl),
    min: '1',
    'data-testid': 'edit-maxBottleVolumeMl',
    'aria-required': 'true',
  });
  volWrap.appendChild(volLabel);
  volWrap.appendChild(volInput);
  form.appendChild(volWrap);

  // Varieties fieldset
  const fieldset = el<HTMLFieldSetElement>('fieldset', {
    class: 'batch-form__field',
    role: 'group',
    'aria-label': 'Available Varieties',
  });
  const legend = el('legend', { class: 'batch-form__label' }, 'Available Varieties');
  fieldset.appendChild(legend);
  const varList = el('div', { class: 'batch-form__variety-list' });
  for (const v of varieties) {
    const item = el('div', { class: 'batch-form__variety-item' });
    const cb = el<HTMLInputElement>('input', {
      class: 'batch-form__checkbox',
      type: 'checkbox',
      id: `edit-variety-${v.varietyId}`,
      name: 'variety',
      value: v.varietyId,
    });
    cb.checked = batch.availableVarietyIds.includes(v.varietyId);
    const lbl = el<HTMLLabelElement>('label', { for: `edit-variety-${v.varietyId}` }, v.name);
    item.appendChild(cb);
    item.appendChild(lbl);
    varList.appendChild(item);
  }
  fieldset.appendChild(varList);
  form.appendChild(fieldset);

  // Actions
  const actions = el('div', { class: 'batch-form__actions' });
  const saveBtn = el<HTMLButtonElement>(
    'button',
    {
      type: 'submit',
      class: 'btn btn--primary',
      'data-testid': 'save-batch-btn',
    },
    'Save Changes'
  );
  actions.appendChild(saveBtn);
  form.appendChild(actions);

  return form;
}

function renderStatusControls(
  detailEl: HTMLElement,
  container: HTMLElement,
  batch: BatchSummary
): void {
  const controls = el('div', { class: 'batch-controls' });

  if (batch.status === 'OPEN') {
    const closeBtn = el<HTMLButtonElement>(
      'button',
      {
        type: 'button',
        class: 'btn btn--secondary',
        'data-testid': 'close-batch-btn',
      },
      'Close Batch'
    );
    closeBtn.addEventListener('click', () => showCloseConfirmation(container, batch));
    controls.appendChild(closeBtn);
  }

  if (batch.status === 'CLOSED') {
    const completeBtn = el<HTMLButtonElement>(
      'button',
      {
        type: 'button',
        class: 'btn btn--secondary',
        'data-testid': 'complete-batch-btn',
      },
      'Mark Complete'
    );
    completeBtn.addEventListener('click', async () => {
      const errorEl = detailEl.querySelector<HTMLElement>('[data-testid="detail-error"]');
      try {
        const updated = await updateBatchStatus(batch.batchId, 'COMPLETED');
        const idx = batches.findIndex((b) => b.batchId === batch.batchId);
        if (idx !== -1) batches[idx] = updated;
        renderList(container);
        renderDetail(container, updated);
      } catch (err) {
        if (errorEl) {
          errorEl.removeAttribute('hidden');
          errorEl.textContent =
            err instanceof ApiRequestError ? err.message : 'An unexpected error occurred.';
        }
      }
    });
    controls.appendChild(completeBtn);
  }

  if (controls.children.length > 0) detailEl.appendChild(controls);
}

function showCloseConfirmation(container: HTMLElement, batch: BatchSummary): void {
  const overlay = el('div', {
    class: 'batch-dialog-overlay',
  });
  const dialog = el('div', {
    class: 'batch-dialog',
    role: 'dialog',
    'aria-modal': 'true',
    'aria-labelledby': 'close-dialog-title',
  });

  const title = el(
    'h4',
    { class: 'batch-dialog__title', id: 'close-dialog-title' },
    'Close Batch?'
  );
  const msg = el('p', { class: 'batch-dialog__message' });
  msg.textContent = `This batch currently has ${batch.activeRequestCount} active request${batch.activeRequestCount !== 1 ? 's' : ''}. Closing will prevent new orders. Are you sure?`;

  const actions = el('div', { class: 'batch-dialog__actions' });

  const cancelBtn = el<HTMLButtonElement>(
    'button',
    {
      type: 'button',
      class: 'btn btn--secondary',
      'data-testid': 'dialog-cancel-btn',
    },
    'Cancel'
  );
  cancelBtn.addEventListener('click', () => overlay.remove());

  const confirmBtn = el<HTMLButtonElement>(
    'button',
    {
      type: 'button',
      class: 'btn btn--primary',
      'data-testid': 'dialog-confirm-btn',
    },
    'Close Batch'
  );
  confirmBtn.addEventListener('click', async () => {
    overlay.remove();
    const detailEl = container.querySelector<HTMLElement>('[data-testid="batch-detail"]');
    try {
      const updated = await updateBatchStatus(batch.batchId, 'CLOSED');
      const idx = batches.findIndex((b) => b.batchId === batch.batchId);
      if (idx !== -1) batches[idx] = updated;
      renderList(container);
      renderDetail(container, updated);
    } catch (err) {
      if (detailEl) {
        const errorEl = detailEl.querySelector<HTMLElement>('[data-testid="detail-error"]');
        if (errorEl) {
          errorEl.removeAttribute('hidden');
          errorEl.textContent =
            err instanceof ApiRequestError ? err.message : 'An unexpected error occurred.';
        }
      }
    }
  });

  actions.appendChild(cancelBtn);
  actions.appendChild(confirmBtn);
  dialog.appendChild(title);
  dialog.appendChild(msg);
  dialog.appendChild(actions);
  overlay.appendChild(dialog);
  container.appendChild(overlay);

  confirmBtn.focus();
}

// ---------------------------------------------------------------------------
// Create batch form
// ---------------------------------------------------------------------------
async function showCreateForm(container: HTMLElement): Promise<void> {
  const detailEl = container.querySelector<HTMLElement>('[data-testid="batch-detail"]');
  if (!detailEl) return;

  let varieties: VarietySummary[] = [];
  try {
    const res = await listVarieties();
    varieties = res.varieties;
  } catch {
    // non-fatal
  }

  detailEl.innerHTML = '';

  const title = el('h3', { class: 'batch-form__title' }, 'New Batch');
  detailEl.appendChild(title);

  const errorEl = el('div', { class: 'batch-error', hidden: '', 'data-testid': 'create-error' });
  detailEl.appendChild(errorEl);

  const form = el<HTMLFormElement>('form', {
    'data-testid': 'create-batch-form',
    class: 'batch-form',
  });

  // Name
  const nameWrap = el('div', { class: 'batch-form__field' });
  const nameLabel = el<HTMLLabelElement>(
    'label',
    { class: 'batch-form__label', for: 'create-name' },
    'Batch Name'
  );
  const nameInput = el<HTMLInputElement>('input', {
    class: 'batch-form__input',
    type: 'text',
    id: 'create-name',
    name: 'batchName',
    'aria-required': 'true',
    'data-testid': 'create-batchName',
  });
  const nameError = el('div', {
    class: 'batch-form__error',
    role: 'alert',
    id: 'name-error',
    hidden: '',
  });
  nameInput.setAttribute('aria-describedby', 'name-error');
  nameWrap.appendChild(nameLabel);
  nameWrap.appendChild(nameInput);
  nameWrap.appendChild(nameError);
  form.appendChild(nameWrap);

  // Cutoff date
  const dateWrap = el('div', { class: 'batch-form__field' });
  const dateLabel = el<HTMLLabelElement>(
    'label',
    { class: 'batch-form__label', for: 'create-date' },
    'Cutoff Date'
  );
  const dateInput = el<HTMLInputElement>('input', {
    class: 'batch-form__input',
    type: 'date',
    id: 'create-date',
    name: 'cutoffDate',
    'aria-required': 'true',
    'data-testid': 'create-cutoffDate',
  });
  const dateError = el('div', {
    class: 'batch-form__error',
    role: 'alert',
    id: 'date-error',
    hidden: '',
  });
  dateInput.setAttribute('aria-describedby', 'date-error');
  dateWrap.appendChild(dateLabel);
  dateWrap.appendChild(dateInput);
  dateWrap.appendChild(dateError);
  form.appendChild(dateWrap);

  // Volume
  const volWrap = el('div', { class: 'batch-form__field' });
  const volLabel = el<HTMLLabelElement>(
    'label',
    { class: 'batch-form__label', for: 'create-volume' },
    'Max Bottle Volume (ml)'
  );
  const volInput = el<HTMLInputElement>('input', {
    class: 'batch-form__input',
    type: 'number',
    id: 'create-volume',
    name: 'maxBottleVolumeMl',
    min: '1',
    'aria-required': 'true',
    'data-testid': 'create-maxBottleVolumeMl',
  });
  volWrap.appendChild(volLabel);
  volWrap.appendChild(volInput);
  form.appendChild(volWrap);

  // Varieties fieldset
  const fieldset = el<HTMLFieldSetElement>('fieldset', {
    class: 'batch-form__field',
    role: 'group',
    'aria-label': 'Available Varieties',
  });
  const legend = el('legend', { class: 'batch-form__label' }, 'Available Varieties');
  fieldset.appendChild(legend);
  const varList = el('div', { class: 'batch-form__variety-list' });
  for (const v of varieties) {
    const item = el('div', { class: 'batch-form__variety-item' });
    const cb = el<HTMLInputElement>('input', {
      class: 'batch-form__checkbox',
      type: 'checkbox',
      id: `create-variety-${v.varietyId}`,
      name: 'variety',
      value: v.varietyId,
    });
    const lbl = el<HTMLLabelElement>('label', { for: `create-variety-${v.varietyId}` }, v.name);
    item.appendChild(cb);
    item.appendChild(lbl);
    varList.appendChild(item);
  }
  fieldset.appendChild(varList);
  form.appendChild(fieldset);

  // Actions
  const actions = el('div', { class: 'batch-form__actions' });
  const submitBtn = el<HTMLButtonElement>(
    'button',
    {
      type: 'submit',
      class: 'btn btn--primary',
      'data-testid': 'create-submit-btn',
    },
    'Create Batch'
  );
  const cancelBtn = el<HTMLButtonElement>(
    'button',
    {
      type: 'button',
      class: 'btn btn--secondary',
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

    nameError.setAttribute('hidden', '');
    nameInput.removeAttribute('aria-invalid');
    dateError.setAttribute('hidden', '');
    dateInput.removeAttribute('aria-invalid');
    errorEl.setAttribute('hidden', '');
    errorEl.textContent = '';

    const batchName = nameInput.value.trim();
    const cutoffDate = dateInput.value.trim();
    const maxBottleVolumeMl = parseInt(volInput.value, 10);
    const availableVarietyIds = Array.from(
      form.querySelectorAll<HTMLInputElement>('input[type="checkbox"]:checked')
    ).map((c) => c.value);

    let valid = true;
    if (!batchName) {
      nameInput.setAttribute('aria-invalid', 'true');
      nameError.textContent = 'Batch name is required.';
      nameError.removeAttribute('hidden');
      valid = false;
    }
    if (!cutoffDate) {
      dateInput.setAttribute('aria-invalid', 'true');
      dateError.textContent = 'Cutoff date is required.';
      dateError.removeAttribute('hidden');
      valid = false;
    }
    if (!valid) return;

    const payload: CreateBatchPayload = {
      batchName,
      cutoffDate,
      maxBottleVolumeMl,
      availableVarietyIds,
    };

    try {
      const created = await createBatch(payload);
      batches = [created, ...batches];
      renderList(container);
      detailEl.innerHTML = '';
    } catch (err) {
      if (err instanceof ApiRequestError) {
        errorEl.textContent = err.message;
        errorEl.removeAttribute('hidden');
        if (err.code === 'BATCH_NAME_CONFLICT') {
          nameInput.setAttribute('aria-invalid', 'true');
          nameError.textContent = err.message;
          nameError.removeAttribute('hidden');
        }
        if (err.code === 'CUTOFF_DATE_IN_PAST') {
          dateInput.setAttribute('aria-invalid', 'true');
          dateError.textContent = err.message;
          dateError.removeAttribute('hidden');
        }
      } else {
        errorEl.textContent = 'An unexpected error occurred. Please try again.';
        errorEl.removeAttribute('hidden');
      }
    }
  });

  detailEl.appendChild(form);
}

// ---------------------------------------------------------------------------
// Manage Access panel
// ---------------------------------------------------------------------------
function renderManageAccessPanel(detailEl: HTMLElement, batch: BatchSummary): void {
  const panel = el('div', { class: 'access-panel', 'data-testid': 'manage-access-panel' });

  const toggle = el<HTMLButtonElement>('button', {
    type: 'button',
    class: 'btn btn--secondary access-panel__toggle',
    'data-testid': 'manage-access-toggle',
    'aria-expanded': 'false',
  }, 'Manage Access ▼');

  const body = el('div', { class: 'access-panel__body', hidden: '' });
  panel.appendChild(toggle);
  panel.appendChild(body);
  detailEl.appendChild(panel);

  toggle.addEventListener('click', () => {
    const expanded = toggle.getAttribute('aria-expanded') === 'true';
    toggle.setAttribute('aria-expanded', String(!expanded));
    if (expanded) {
      body.setAttribute('hidden', '');
    } else {
      body.removeAttribute('hidden');
      refreshAccessPanel(body, batch);
    }
  });
}

async function refreshAccessPanel(body: HTMLElement, batch: BatchSummary): Promise<void> {
  body.innerHTML = '<p class="access-panel__loading">Loading…</p>';
  try {
    const result = await listBatchAccess(batch.batchId);
    body.innerHTML = '';
    renderSearchSection(body, batch);
    renderNewUserForm(body, batch, result.users);
    renderAccessList(body, batch, result.users);
  } catch (err) {
    body.innerHTML = '';
    const msg = el('p', { class: 'access-panel__error', role: 'alert' });
    msg.textContent =
      err instanceof ApiRequestError ? err.message : 'Failed to load the access list. Please refresh and try again.';
    body.appendChild(msg);
  }
}

function renderSearchSection(body: HTMLElement, batch: BatchSummary): void {
  const section = el('div', { class: 'access-search' });
  const label = el<HTMLLabelElement>('label', {
    class: 'batch-form__label',
    for: 'access-search-input',
  }, 'Search users:');
  const input = el<HTMLInputElement>('input', {
    class: 'batch-form__input',
    type: 'search',
    id: 'access-search-input',
    'data-testid': 'access-search-input',
    placeholder: 'Name or email…',
    'aria-label': 'Search users by name or email',
  });
  const btn = el<HTMLButtonElement>('button', {
    type: 'button',
    class: 'btn btn--secondary',
    'data-testid': 'access-search-btn',
  }, 'Search');
  const resultsEl = el('div', { class: 'access-results', 'data-testid': 'access-search-results', 'aria-live': 'polite' });

  btn.addEventListener('click', () => runSearch(input.value.trim(), resultsEl, body, batch));
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') runSearch(input.value.trim(), resultsEl, body, batch);
  });

  section.appendChild(label);
  section.appendChild(input);
  section.appendChild(btn);
  section.appendChild(resultsEl);
  body.appendChild(section);
}

async function runSearch(
  query: string,
  resultsEl: HTMLElement,
  body: HTMLElement,
  batch: BatchSummary,
): Promise<void> {
  if (!query) {
    resultsEl.textContent = '';
    return;
  }
  resultsEl.textContent = 'Searching…';
  try {
    const { users } = await searchUsers(query);
    resultsEl.innerHTML = '';
    if (users.length === 0) {
      const msg = el('p', { class: 'access-empty', 'data-testid': 'search-empty' });
      msg.textContent = 'No users found. Try creating a new user below.';
      resultsEl.appendChild(msg);
      return;
    }
    const list = el('ul', { class: 'access-user-list', role: 'list' });
    for (const u of users) {
      const li = el('li', { class: 'access-user-row', role: 'listitem' });
      const info = el('span', { class: 'access-user-row__info' });
      info.textContent = `${u.firstName}${u.lastName ? ' ' + u.lastName : ''} (${u.email})`;
      const grantBtn = el<HTMLButtonElement>('button', {
        type: 'button',
        class: 'btn btn--primary access-user-row__grant',
        'data-testid': `grant-btn-${u.userId}`,
      }, 'Grant Access');
      grantBtn.addEventListener('click', () => handleGrant(u.userId, body, batch));
      li.appendChild(info);
      li.appendChild(grantBtn);
      list.appendChild(li);
    }
    if (users.length === 20) {
      const hint = el('p', { class: 'access-truncation-hint' });
      hint.textContent = 'Showing first 20 results — refine your search for more.';
      resultsEl.appendChild(hint);
    }
    resultsEl.appendChild(list);
  } catch (err) {
    resultsEl.textContent =
      err instanceof ApiRequestError ? err.message : 'Search failed. Please try again.';
  }
}

async function handleGrant(userId: string, body: HTMLElement, batch: BatchSummary): Promise<void> {
  try {
    await grantBatchAccess(batch.batchId, userId);
    refreshAccessPanel(body, batch);
  } catch (err) {
    const msg = err instanceof ApiRequestError ? err.message : 'Failed to grant access. Please try again.';
    showAccessError(body, msg);
  }
}

function renderNewUserForm(body: HTMLElement, batch: BatchSummary, _users: BatchAccessUser[]): void {
  const section = el('div', { class: 'access-new-user' });

  const toggleBtn = el<HTMLButtonElement>('button', {
    type: 'button',
    class: 'btn btn--secondary',
    'data-testid': 'new-user-toggle',
    'aria-expanded': 'false',
  }, '+ New User');

  const formWrap = el('div', { class: 'access-new-user__form', hidden: '' });
  section.appendChild(toggleBtn);
  section.appendChild(formWrap);
  body.appendChild(section);

  toggleBtn.addEventListener('click', () => {
    const open = toggleBtn.getAttribute('aria-expanded') === 'true';
    toggleBtn.setAttribute('aria-expanded', String(!open));
    if (open) formWrap.setAttribute('hidden', ''); else formWrap.removeAttribute('hidden');
  });

  const form = el<HTMLFormElement>('form', { 'data-testid': 'new-user-form' });

  const emailWrap = el('div', { class: 'batch-form__field' });
  const emailLabel = el<HTMLLabelElement>('label', { class: 'batch-form__label', for: 'nu-email' }, 'Email *');
  const emailInput = el<HTMLInputElement>('input', {
    class: 'batch-form__input',
    type: 'email',
    id: 'nu-email',
    'data-testid': 'new-user-email',
    required: '',
    'aria-required': 'true',
  });
  emailWrap.appendChild(emailLabel);
  emailWrap.appendChild(emailInput);

  const firstWrap = el('div', { class: 'batch-form__field' });
  const firstLabel = el<HTMLLabelElement>('label', { class: 'batch-form__label', for: 'nu-first' }, 'First Name *');
  const firstInput = el<HTMLInputElement>('input', {
    class: 'batch-form__input',
    type: 'text',
    id: 'nu-first',
    'data-testid': 'new-user-firstName',
    required: '',
    'aria-required': 'true',
  });
  firstWrap.appendChild(firstLabel);
  firstWrap.appendChild(firstInput);

  const lastWrap = el('div', { class: 'batch-form__field' });
  const lastLabel = el<HTMLLabelElement>('label', { class: 'batch-form__label', for: 'nu-last' }, 'Last Name');
  const lastInput = el<HTMLInputElement>('input', {
    class: 'batch-form__input',
    type: 'text',
    id: 'nu-last',
    'data-testid': 'new-user-lastName',
  });
  lastWrap.appendChild(lastLabel);
  lastWrap.appendChild(lastInput);

  const errorEl = el('div', {
    class: 'batch-form__error',
    role: 'alert',
    hidden: '',
    'data-testid': 'new-user-error',
  });

  const actions = el('div', { class: 'batch-form__actions' });
  const submitBtn = el<HTMLButtonElement>('button', {
    type: 'submit',
    class: 'btn btn--primary',
    'data-testid': 'new-user-submit',
  }, 'Create & Grant Access');

  actions.appendChild(submitBtn);
  form.appendChild(emailWrap);
  form.appendChild(firstWrap);
  form.appendChild(lastWrap);
  form.appendChild(errorEl);
  form.appendChild(actions);
  formWrap.appendChild(form);

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorEl.setAttribute('hidden', '');
    errorEl.textContent = '';

    const email = emailInput.value.trim();
    const firstName = firstInput.value.trim();
    const lastName = lastInput.value.trim() || undefined;

    if (!email || !firstName) {
      errorEl.textContent = 'Email and first name are required.';
      errorEl.removeAttribute('hidden');
      return;
    }

    submitBtn.disabled = true;
    let createdUserId: string | null = null;
    try {
      const created = await createUser({ email, firstName, lastName });
      createdUserId = created.userId;
    } catch (err) {
      submitBtn.disabled = false;
      errorEl.textContent =
        err instanceof ApiRequestError ? err.message : 'Failed to create user.';
      errorEl.removeAttribute('hidden');
      return;
    }

    try {
      await grantBatchAccess(batch.batchId, createdUserId);
      form.reset();
      toggleBtn.setAttribute('aria-expanded', 'false');
      formWrap.setAttribute('hidden', '');
      refreshAccessPanel(body, batch);
    } catch (err) {
      submitBtn.disabled = false;
      const userEmail = email;
      const userId = createdUserId;
      errorEl.removeAttribute('hidden');
      errorEl.innerHTML = '';
      const msg = document.createTextNode(
        `User "${userEmail}" was created but access grant failed. `
      );
      const retryBtn = el<HTMLButtonElement>('button', {
        type: 'button',
        class: 'btn btn--secondary',
        'data-testid': 'grant-retry-btn',
      }, 'Grant access');
      retryBtn.addEventListener('click', () => {
        errorEl.setAttribute('hidden', '');
        handleGrant(userId, body, batch);
      });
      errorEl.appendChild(msg);
      errorEl.appendChild(retryBtn);
    }
  });
}

function renderAccessList(
  body: HTMLElement,
  batch: BatchSummary,
  users: BatchAccessUser[],
): void {
  const section = el('div', { class: 'access-list-section' });
  const heading = el('p', { class: 'access-list__heading' }, '── Users with access ──');
  section.appendChild(heading);

  if (users.length === 0) {
    const empty = el('p', {
      class: 'access-empty',
      'data-testid': 'access-empty-state',
    });
    empty.textContent = 'No users have been granted access to this batch.';
    section.appendChild(empty);
    body.appendChild(section);
    return;
  }

  const list = el('ul', { class: 'access-user-list', role: 'list', 'data-testid': 'access-user-list' });
  for (const u of users) {
    const li = el('li', { class: 'access-user-row', role: 'listitem' });
    const name = el('span', { class: 'access-user-row__name' });
    name.textContent = `${u.firstName}${u.lastName ? ' ' + u.lastName : ''}`;
    const email = el('span', { class: 'access-user-row__email' });
    email.textContent = ` (${u.email})`;
    li.appendChild(name);
    li.appendChild(email);

    const removeBtn = el<HTMLButtonElement>('button', {
      type: 'button',
      class: 'btn btn--secondary access-user-row__remove',
      'data-testid': `remove-btn-${u.userId}`,
    }, 'Remove');
    removeBtn.addEventListener('click', () => showRevokeConfirmation(body, batch, u));
    li.appendChild(removeBtn);
    list.appendChild(li);
  }
  section.appendChild(list);
  body.appendChild(section);
}

function showRevokeConfirmation(
  body: HTMLElement,
  batch: BatchSummary,
  user: BatchAccessUser,
): void {
  const overlay = el('div', { class: 'batch-dialog-overlay', 'data-testid': 'revoke-overlay' });
  const dialog = el('div', {
    class: 'batch-dialog',
    role: 'dialog',
    'aria-modal': 'true',
    'aria-labelledby': 'revoke-dialog-title',
  });

  const title = el('h4', { class: 'batch-dialog__title', id: 'revoke-dialog-title' }, 'Remove Access?');
  const msg = el('p', { class: 'batch-dialog__message' });
  msg.textContent = `Remove ${user.firstName}${user.lastName ? ' ' + user.lastName : ''} (${user.email}) from this batch?`;

  const actions = el('div', { class: 'batch-dialog__actions' });

  const cancelBtn = el<HTMLButtonElement>('button', {
    type: 'button',
    class: 'btn btn--secondary',
    'data-testid': 'revoke-cancel-btn',
  }, 'Cancel');
  cancelBtn.addEventListener('click', () => overlay.remove());

  const confirmBtn = el<HTMLButtonElement>('button', {
    type: 'button',
    class: 'btn btn--primary',
    'data-testid': 'revoke-confirm-btn',
  }, 'Remove');
  confirmBtn.addEventListener('click', async () => {
    overlay.remove();
    try {
      await revokeBatchAccess(batch.batchId, user.userId);
      refreshAccessPanel(body, batch);
    } catch (err) {
      const errMsg = err instanceof ApiRequestError ? err.message : 'Failed to revoke access. Please try again.';
      showAccessError(body, errMsg);
    }
  });

  actions.appendChild(cancelBtn);
  actions.appendChild(confirmBtn);
  dialog.appendChild(title);
  dialog.appendChild(msg);
  dialog.appendChild(actions);
  overlay.appendChild(dialog);
  document.body.appendChild(overlay);
  confirmBtn.focus();
}

function showAccessError(body: HTMLElement, message: string): void {
  const existing = body.querySelector('[data-testid="access-error"]');
  if (existing) existing.remove();
  const err = el('p', { class: 'access-panel__error', role: 'alert', 'data-testid': 'access-error' });
  err.textContent = message;
  body.prepend(err);
}

// ---------------------------------------------------------------------------
// Mount
// ---------------------------------------------------------------------------
export async function mountBatchManagement(
  container: HTMLElement,
  user?: CurrentUser | null,
): Promise<void> {
  currentUser = user ?? null;
  container.innerHTML = `
    <div class="batch-management">
      <div class="batch-management__header">
        <h2 class="batch-management__title">Manage Batches</h2>
        <button class="btn btn--primary" data-testid="new-batch-btn" type="button">New Batch</button>
      </div>
      <div aria-live="polite" data-testid="batch-list" aria-label="Batch list"></div>
      <div data-testid="batch-detail"></div>
    </div>
  `;

  container
    .querySelector<HTMLButtonElement>('[data-testid="new-batch-btn"]')!
    .addEventListener('click', () => showCreateForm(container));

  const listRegion = container.querySelector<HTMLElement>('[data-testid="batch-list"]')!;
  listRegion.textContent = 'Loading batches…';

  try {
    const result = await listBatches();
    batches = result.batches;
    renderList(container);
  } catch (err) {
    listRegion.innerHTML = '';
    const errorEl = el('div', { class: 'batch-error' });
    errorEl.textContent =
      err instanceof ApiRequestError && err.status === 403
        ? 'Access denied. Only chefs can view batch management.'
        : 'Failed to load batches. Please refresh and try again.';
    listRegion.appendChild(errorEl);
  }
}
