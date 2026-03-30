import './manage-request.css';
import {
  getRequest,
  updateRequest,
  cancelRequest,
  ApiRequestError,
  type RequestResponse,
  type UpdateRequestPayload,
} from '../../services/api';
import {
  createLabeledInput,
  setFieldError,
  clearFieldError,
} from '../../components/form/labeled-input';

// ---------------------------------------------------------------------------
// Manage Request page — view, edit, and cancel an existing coquito request
// ---------------------------------------------------------------------------

export function mountManageRequest(container: HTMLElement, requestId: string): void {
  container.innerHTML = renderLoading();

  getRequest(requestId)
    .then((req) => renderPage(container, requestId, req))
    .catch((err: unknown) => {
      if (err instanceof ApiRequestError && err.status === 404) {
        container.innerHTML = renderNotFound();
      } else {
        container.innerHTML = renderLoadError();
      }
    });
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

function renderPage(container: HTMLElement, requestId: string, req: RequestResponse): void {
  container.innerHTML = '';

  const hero = document.createElement('header');
  hero.className = 'manage-hero';
  hero.innerHTML = `
    <p class="manage-hero__eyebrow">Tu pedido de coquito 🥥</p>
    <h1 class="manage-hero__heading">Your Request</h1>
  `;
  container.appendChild(hero);

  const wrap = document.createElement('div');
  wrap.className = 'page-wrapper';

  if (!req.editable) {
    wrap.appendChild(buildLockedBanner(req));
    wrap.appendChild(buildSummaryCard(req));
  } else {
    const summaryEl = buildSummaryCard(req);
    const editFormEl = buildEditForm(
      requestId,
      req,
      () => {
        // on successful save: rebuild page with updated request
        getRequest(requestId).then((updated) => renderPage(container, requestId, updated));
      },
      () => {
        // on discard: show summary again, hide form
        summaryEl.hidden = false;
        editFormEl.hidden = true;
      }
    );
    editFormEl.hidden = true;

    const dialog = buildCancelDialog(requestId, container);

    const actionsEl = buildActions(
      () => {
        summaryEl.hidden = true;
        editFormEl.hidden = false;
      },
      () => {
        (dialog as HTMLDialogElement).showModal();
      }
    );

    summaryEl.appendChild(actionsEl);
    wrap.appendChild(summaryEl);
    wrap.appendChild(editFormEl);
    wrap.appendChild(dialog);
  }

  container.appendChild(wrap);
}

function buildSummaryCard(req: RequestResponse): HTMLElement {
  const card = document.createElement('div');
  card.className = 'summary-card';
  card.dataset.cy = 'request-summary';

  const varietyName = req.variety?.name ?? req.variety?.varietyId ?? '';

  card.innerHTML = `
    <h2 class="summary-card__title">Order Details</h2>
    <div class="summary-row">
      <span class="summary-row__label">Name</span>
      <span class="summary-row__value">${escapeHtml(req.requesterName)}</span>
    </div>
    <div class="summary-row">
      <span class="summary-row__label">Variety</span>
      <span class="summary-row__value">${escapeHtml(varietyName)}</span>
    </div>
    <div class="summary-row">
      <span class="summary-row__label">Pickup date</span>
      <span class="summary-row__value">${escapeHtml(req.pickupDate)}</span>
    </div>
    <div class="summary-row">
      <span class="summary-row__label">Pickup time</span>
      <span class="summary-row__value">${escapeHtml(req.pickupTime)}</span>
    </div>
    <div class="summary-row">
      <span class="summary-row__label">Location</span>
      <span class="summary-row__value">${escapeHtml(req.exchangeLocation)}</span>
    </div>
    <div class="summary-row">
      <span class="summary-row__label">Bottle provided</span>
      <span class="summary-row__value">${req.bottleProvided ? `Yes (${req.bottleVolumeMl}ml)` : 'No'}</span>
    </div>
    <div class="summary-row">
      <span class="summary-row__label">Cost contribution</span>
      <span class="summary-row__value">${req.costContribution ? 'Yes, happy to contribute' : 'No'}</span>
    </div>
  `;

  return card;
}

function buildActions(onEdit: () => void, onCancel: () => void): HTMLElement {
  const actions = document.createElement('div');
  actions.className = 'manage-actions';

  const editBtn = document.createElement('button');
  editBtn.type = 'button';
  editBtn.className = 'btn-edit';
  editBtn.dataset.cy = 'edit-button';
  editBtn.textContent = '✏️ Edit Order';
  editBtn.addEventListener('click', onEdit);

  const cancelBtn = document.createElement('button');
  cancelBtn.type = 'button';
  cancelBtn.className = 'btn-cancel-request';
  cancelBtn.dataset.cy = 'cancel-button';
  cancelBtn.textContent = 'Cancel Order';
  cancelBtn.addEventListener('click', onCancel);

  actions.appendChild(editBtn);
  actions.appendChild(cancelBtn);
  return actions;
}

function buildLockedBanner(req: RequestResponse): HTMLElement {
  const banner = document.createElement('div');
  banner.className = 'locked-banner';
  banner.dataset.cy = 'locked-banner';
  const cutoff = req.batch?.cutoffDate ?? 'the cut-off date';
  banner.innerHTML = `
    <div class="locked-banner__icon">🔒</div>
    <h2 class="locked-banner__heading">Changes are no longer available</h2>
    <p class="locked-banner__text">
      The cut-off date (${escapeHtml(cutoff)}) has passed.
      Your coquito is being prepared with love — gracias for your order! 🥥
    </p>
  `;
  return banner;
}

function buildEditForm(
  requestId: string,
  req: RequestResponse,
  onSaved: () => void,
  onDiscard: () => void
): HTMLElement {
  const card = document.createElement('div');
  card.className = 'edit-form-card';

  const title = document.createElement('h2');
  title.className = 'edit-form-card__title';
  title.textContent = 'Edit Your Order';

  const form = document.createElement('form');
  form.dataset.cy = 'edit-form';
  form.setAttribute('aria-label', 'Edit coquito request form');
  form.noValidate = true;

  // Pickup date
  const dateField = createLabeledInput({
    id: 'edit-pickup-date',
    label: 'Pickup date',
    type: 'date',
    required: true,
  });
  const dateInput = dateField.querySelector<HTMLInputElement>('input')!;
  dateInput.value = req.pickupDate;
  dateInput.dataset.cy = 'pickup-date';
  if (req.batch?.cutoffDate) {
    dateInput.min = req.batch.cutoffDate;
  }

  // Pickup time
  const timeField = createLabeledInput({
    id: 'edit-pickup-time',
    label: 'Pickup time',
    type: 'time',
    required: true,
  });
  const timeInput = timeField.querySelector<HTMLInputElement>('input')!;
  timeInput.value = req.pickupTime;
  timeInput.dataset.cy = 'pickup-time';

  const dateTimeRow = document.createElement('div');
  dateTimeRow.className = 'date-time-row';
  dateTimeRow.appendChild(dateField);
  dateTimeRow.appendChild(timeField);

  // Location
  const locationField = createLabeledInput({
    id: 'edit-exchange-location',
    label: 'Exchange location',
    required: true,
    placeholder: 'e.g. 123 Palmas St, Apt 4B',
  });
  const locationInput = locationField.querySelector<HTMLInputElement>('input')!;
  locationInput.value = req.exchangeLocation;
  locationInput.dataset.cy = 'exchange-location';

  // Form error
  const formError = document.createElement('div');
  formError.className = 'manage-form-error';
  formError.setAttribute('role', 'alert');
  formError.hidden = true;

  // Actions
  const editActions = document.createElement('div');
  editActions.className = 'edit-actions';

  const saveBtn = document.createElement('button');
  saveBtn.type = 'submit';
  saveBtn.className = 'btn-save';
  saveBtn.dataset.cy = 'save-button';
  saveBtn.textContent = '💾 Save Changes';

  const discardBtn = document.createElement('button');
  discardBtn.type = 'button';
  discardBtn.className = 'btn-discard';
  discardBtn.textContent = 'Discard';
  discardBtn.addEventListener('click', onDiscard);

  editActions.appendChild(saveBtn);
  editActions.appendChild(discardBtn);

  form.appendChild(dateTimeRow);
  form.appendChild(locationField);
  form.appendChild(formError);
  form.appendChild(editActions);

  card.appendChild(title);
  card.appendChild(form);

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    handleSave(form, formError, saveBtn, requestId, req, onSaved);
  });

  return card;
}

function handleSave(
  form: HTMLFormElement,
  formError: HTMLElement,
  saveBtn: HTMLButtonElement,
  requestId: string,
  original: RequestResponse,
  onSaved: () => void
): void {
  formError.hidden = true;

  clearFieldError('edit-pickup-date');
  clearFieldError('edit-pickup-time');
  clearFieldError('edit-exchange-location');

  const pickupDate = form.querySelector<HTMLInputElement>('#edit-pickup-date')?.value ?? '';
  const pickupTime = form.querySelector<HTMLInputElement>('#edit-pickup-time')?.value ?? '';
  const location =
    form.querySelector<HTMLInputElement>('#edit-exchange-location')?.value.trim() ?? '';

  let valid = true;

  if (!pickupDate) {
    setFieldError('edit-pickup-date', 'When would you like to pick up your coquito?');
    valid = false;
  }
  if (!pickupTime) {
    setFieldError('edit-pickup-time', 'What time works for you?');
    valid = false;
  }
  if (!location) {
    setFieldError('edit-exchange-location', 'Where should we meet?');
    valid = false;
  }

  if (!valid) return;

  const payload: UpdateRequestPayload = {};
  if (pickupDate !== original.pickupDate) payload.pickupDate = pickupDate;
  if (pickupTime !== original.pickupTime) payload.pickupTime = pickupTime;
  if (location !== original.exchangeLocation) payload.exchangeLocation = location;

  saveBtn.disabled = true;
  saveBtn.textContent = 'Saving...';

  updateRequest(requestId, payload)
    .then(() => {
      onSaved();
    })
    .catch((err: unknown) => {
      saveBtn.disabled = false;
      saveBtn.textContent = '💾 Save Changes';

      let msg = '¡Ay! Something went wrong. Please try again.';
      if (err instanceof ApiRequestError) {
        if (err.code === 'CUTOFF_PASSED') {
          msg = 'The cut-off date has passed. Changes are no longer permitted.';
        } else if (err.code === 'REQUEST_CANCELLED') {
          msg = 'This request has been cancelled and cannot be updated.';
        } else {
          msg = err.message;
        }
      }
      formError.textContent = msg;
      formError.hidden = false;
    });
}

function buildCancelDialog(requestId: string, container: HTMLElement): HTMLElement {
  const dialog = document.createElement('dialog');
  dialog.className = 'cancel-dialog';
  dialog.dataset.cy = 'cancel-dialog';

  dialog.innerHTML = `
    <div class="cancel-dialog__icon">🥥</div>
    <h2 class="cancel-dialog__heading">Cancel your order?</h2>
    <p class="cancel-dialog__body">
      ¿Estás seguro? Once cancelled, your coquito reservation will be released.
      You can always place a new order before the cut-off date.
    </p>
    <div class="cancel-dialog__actions">
      <button type="button" class="btn-confirm-cancel" data-cy="cancel-confirm">Yes, cancel it</button>
      <button type="button" class="btn-dismiss-cancel" data-cy="cancel-dismiss">Keep my order</button>
    </div>
  `;

  dialog.querySelector('[data-cy="cancel-dismiss"]')!.addEventListener('click', () => {
    (dialog as HTMLDialogElement).close();
  });

  dialog.querySelector('[data-cy="cancel-confirm"]')!.addEventListener('click', () => {
    (dialog as HTMLDialogElement).close();
    handleCancel(requestId, container);
  });

  return dialog;
}

function handleCancel(requestId: string, container: HTMLElement): void {
  cancelRequest(requestId)
    .then(() => {
      const wrap = container.querySelector('.page-wrapper');
      if (wrap) {
        wrap.innerHTML = renderCancelledMessage();
      }
    })
    .catch((err: unknown) => {
      let msg = '¡Ay! Something went wrong. Please try again.';
      if (err instanceof ApiRequestError) {
        msg = err.message;
      }
      const existingError = container.querySelector<HTMLElement>('[data-cy="cancel-error"]');
      if (existingError) {
        existingError.textContent = msg;
        existingError.hidden = false;
      } else {
        const errorEl = document.createElement('div');
        errorEl.className = 'manage-form-error';
        errorEl.dataset.cy = 'cancel-error';
        errorEl.setAttribute('role', 'alert');
        errorEl.textContent = msg;
        container.querySelector('.page-wrapper')?.prepend(errorEl);
      }
    });
}

// ---------------------------------------------------------------------------
// Static HTML states
// ---------------------------------------------------------------------------

function renderLoading(): string {
  return `
    <div class="page-wrapper" style="text-align:center; padding-top:4rem;">
      <p>Cargando... Loading your order details...</p>
    </div>`;
}

function renderNotFound(): string {
  return `
    <div class="page-wrapper">
      <div class="not-found-card" data-cy="not-found-message">
        <div class="not-found-card__icon">🥺</div>
        <h2 class="not-found-card__heading">Order not found</h2>
        <p>
          We couldn't find that coquito order. Double-check your link, or
          <a href="#/">place a new request</a>.
        </p>
      </div>
    </div>`;
}

function renderLoadError(): string {
  return `
    <div class="page-wrapper">
      <div class="card form-error" role="alert" style="max-width:560px;margin:2rem auto;">
        ¡Ay, algo pasó! We couldn't load your order. Please try again later.
      </div>
    </div>`;
}

function renderCancelledMessage(): string {
  return `
    <div class="cancelled-card" data-cy="cancelled-message">
      <div class="cancelled-card__icon">✅</div>
      <h2 class="cancelled-card__heading">Your order has been cancelled</h2>
      <p class="cancelled-card__text">
        No worries — we hope to make you coquito again soon. 🥥<br>
        If you change your mind, you can always place a new order before the cut-off date.
      </p>
      <a href="#/" class="cancelled-card__link">Place a new request</a>
    </div>
  `;
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
