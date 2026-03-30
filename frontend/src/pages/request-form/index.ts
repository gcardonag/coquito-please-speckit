import './request-form.css';
import {
  getBatchConfig,
  createRequest,
  ApiRequestError,
  type BatchConfig,
  type CreateRequestPayload,
} from '../../services/api';
import {
  createLabeledInput,
  setFieldError,
  clearFieldError,
} from '../../components/form/labeled-input';
import {
  createVarietySelector,
  getSelectedVarietyId,
} from '../../components/form/variety-selector';
import {
  createBottlePreference,
  isBottleProvided,
  getBottleVolumeMl,
} from '../../components/form/bottle-preference';
import { createCostToggle, getCostContribution } from '../../components/form/cost-toggle';

// ---------------------------------------------------------------------------
// Request form page
// ---------------------------------------------------------------------------

export function mountRequestForm(container: HTMLElement): void {
  // Read batchId from URL: /#/?batchId=xxx
  const search = window.location.hash.split('?')[1] ?? '';
  const params = new URLSearchParams(search);
  const batchId = params.get('batchId') ?? (import.meta.env.VITE_BATCH_ID as string) ?? '';

  container.innerHTML = renderLoadingState();

  getBatchConfig(batchId)
    .then((batch) => {
      container.innerHTML = '';
      renderForm(container, batch);
    })
    .catch(() => {
      container.innerHTML = `
        <div class="page-wrapper">
          <div class="card form-error" role="alert">
            Oops! We couldn't load the batch details. Please try again later.
          </div>
        </div>`;
    });
}

function renderLoadingState(): string {
  return `
    <div class="page-wrapper" style="text-align:center; padding-top:4rem;">
      <p>Cargando... Loading the coquito batch details...</p>
    </div>`;
}

function renderForm(container: HTMLElement, batch: BatchConfig): void {
  // Hero
  const hero = document.createElement('header');
  hero.className = 'form-hero';
  hero.innerHTML = `
    <p class="form-hero__eyebrow">Hecho con amor 🥥</p>
    <h1 class="form-hero__heading" data-cy="form-heading">Coquito Please!</h1>
    <p class="form-hero__tagline">
      El coquito es más que una bebida &mdash; es una tradición, un abrazo,
      y el sabor de las fiestas Puertorriqueñas.
      Place your order below and we'll take care of the rest.
    </p>
    <span class="batch-badge" data-cy="batch-name">${escapeHtml(batch.batchName)}</span>
  `;

  // Form card
  const card = document.createElement('div');
  card.className = 'request-form-card';

  const form = document.createElement('form');
  form.id = 'coquito-request-form';
  form.setAttribute('aria-label', 'Coquito request form');
  form.noValidate = true;

  // Fields
  const nameField = createLabeledInput({
    id: 'requester-name',
    label: 'Your name',
    required: true,
    autocomplete: 'given-name',
    placeholder: 'e.g. María Rivera',
  });

  const emailField = createLabeledInput({
    id: 'requester-email',
    label: 'Your email (for reminders)',
    type: 'email',
    required: true,
    autocomplete: 'email',
    placeholder: 'e.g. maria@example.com',
  });

  const varietySelector = createVarietySelector(batch.availableVarieties);

  // Date + time row
  const dateTimeRow = document.createElement('div');
  dateTimeRow.className = 'date-time-row';

  const dateField = createLabeledInput({
    id: 'pickup-date',
    label: 'Pickup date',
    type: 'date',
    required: true,
  });
  // Set min date = day after cutoff
  const dateInput = dateField.querySelector<HTMLInputElement>('input')!;
  dateInput.min = batch.cutoffDate;

  const timeField = createLabeledInput({
    id: 'pickup-time',
    label: 'Pickup time',
    type: 'time',
    required: true,
  });

  dateTimeRow.appendChild(dateField);
  dateTimeRow.appendChild(timeField);

  const locationField = createLabeledInput({
    id: 'exchange-location',
    label: 'Exchange location',
    required: true,
    placeholder: 'e.g. 123 Palmas St, Apt 4B',
  });

  const bottlePref = createBottlePreference(batch.maxBottleVolumeMl);
  const costToggle = createCostToggle();

  // Form-level error region
  const formError = document.createElement('div');
  formError.className = 'form-error';
  formError.dataset.cy = 'form-error';
  formError.setAttribute('role', 'alert');
  formError.hidden = true;

  // Submit button
  const submitBtn = document.createElement('button');
  submitBtn.type = 'submit';
  submitBtn.className = 'submit-btn';
  submitBtn.dataset.cy = 'submit-button';
  submitBtn.textContent = '🥥 Request my coquito';

  form.appendChild(nameField);
  form.appendChild(emailField);
  form.appendChild(varietySelector);
  form.appendChild(dateTimeRow);
  form.appendChild(locationField);
  form.appendChild(bottlePref);
  form.appendChild(costToggle);
  form.appendChild(formError);
  form.appendChild(submitBtn);

  // Status region for confirmation
  const statusRegion = document.createElement('div');
  statusRegion.setAttribute('role', 'status');
  statusRegion.setAttribute('aria-live', 'polite');

  card.appendChild(form);
  card.appendChild(statusRegion);
  container.appendChild(hero);
  container.appendChild(card);

  // Attach submit handler
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    handleSubmit(form, formError, statusRegion, batch, submitBtn);
  });
}

function handleSubmit(
  form: HTMLFormElement,
  formErrorEl: HTMLDivElement,
  statusRegion: HTMLDivElement,
  batch: BatchConfig,
  submitBtn: HTMLButtonElement
): void {
  formErrorEl.hidden = true;

  // Gather values
  const name = (document.getElementById('requester-name') as HTMLInputElement)?.value.trim() ?? '';
  const email =
    (document.getElementById('requester-email') as HTMLInputElement)?.value.trim() ?? '';
  const varietyId = getSelectedVarietyId();
  const pickupDate = (document.getElementById('pickup-date') as HTMLInputElement)?.value ?? '';
  const pickupTime = (document.getElementById('pickup-time') as HTMLInputElement)?.value ?? '';
  const location =
    (document.getElementById('exchange-location') as HTMLInputElement)?.value.trim() ?? '';
  const bottleProvided = isBottleProvided();
  const bottleVolumeMl = getBottleVolumeMl();
  const costContribution = getCostContribution();

  // Client-side validation
  let valid = true;

  clearFieldError('requester-name');
  clearFieldError('requester-email');
  clearFieldError('pickup-date');
  clearFieldError('pickup-time');
  clearFieldError('exchange-location');
  clearFieldError('bottle-volume');

  const errorEl = document.getElementById('error-varietyId');
  if (errorEl) {
    errorEl.hidden = true;
    errorEl.textContent = '';
  }

  if (!name) {
    setFieldError('requester-name', '¡Oye! We need your name so we know who the coquito is for.');
    valid = false;
  }

  const emailRe = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
  if (!email) {
    setFieldError('requester-email', 'We need your email to send you reminders — ¡promesa!');
    valid = false;
  } else if (!emailRe.test(email)) {
    setFieldError('requester-email', "That email doesn't look right. Please double-check it.");
    valid = false;
  }

  if (!varietyId) {
    if (errorEl) {
      errorEl.textContent = "Pick your coquito variety — they're all delicious!";
      errorEl.hidden = false;
    }
    valid = false;
  }

  if (!pickupDate) {
    setFieldError('pickup-date', 'When would you like to pick up your coquito?');
    valid = false;
  }

  if (!pickupTime) {
    setFieldError('pickup-time', 'What time works for you?');
    valid = false;
  }

  if (!location) {
    setFieldError(
      'exchange-location',
      'Where should we meet? Include an address or a well-known spot.'
    );
    valid = false;
  }

  if (bottleProvided) {
    if (!bottleVolumeMl) {
      setFieldError('bottle-volume', `Please enter your bottle's volume in ml.`);
      valid = false;
    } else if (bottleVolumeMl > batch.maxBottleVolumeMl) {
      setFieldError(
        'bottle-volume',
        `Your bottle is a bit too grand — maximum is ${batch.maxBottleVolumeMl}ml. 🥥`
      );
      valid = false;
    }
  }

  if (!valid) return;

  // Submit
  submitBtn.disabled = true;
  submitBtn.textContent = 'Sending your request...';

  const payload: CreateRequestPayload = {
    idempotencyKey: crypto.randomUUID(),
    requesterName: name,
    requesterEmail: email,
    batchId: batch.batchId,
    varietyId,
    pickupDate,
    pickupTime,
    exchangeLocation: location,
    bottleProvided,
    bottleVolumeMl,
    costContribution,
  };

  createRequest(payload)
    .then((resp) => {
      form.hidden = true;
      statusRegion.innerHTML = renderConfirmation(resp, batch);
    })
    .catch((err: unknown) => {
      submitBtn.disabled = false;
      submitBtn.textContent = '🥥 Request my coquito';

      let message = '¡Ay, algo pasó! Something went wrong. Please try again in a moment.';

      if (err instanceof ApiRequestError) {
        if (err.code === 'BATCH_CLOSED') {
          message =
            'The ordering window for this date is closed. Please choose a different pickup date.';
        } else if (err.code === 'BOTTLE_VOLUME_EXCEEDED') {
          message = `Your bottle volume exceeds the maximum allowed (${batch.maxBottleVolumeMl}ml). Please adjust.`;
        } else if (err.code === 'VALIDATION_ERROR') {
          message = `Oops! ${err.message}`;
        }
      }

      formErrorEl.textContent = message;
      formErrorEl.hidden = false;
    });
}

function renderConfirmation(
  resp: Awaited<ReturnType<typeof createRequest>>,
  batch: BatchConfig
): string {
  const varietyName = resp.variety.name;
  const manageUrl = `#/manage/${resp.requestId}`;

  return `
    <div class="confirmation-card" data-cy="confirmation-card">
      <div class="confirmation-card__icon">🥥</div>
      <h2 class="confirmation-card__heading">¡Tu coquito está reservado!</h2>
      <p>Your coquito request has been received. We'll see you soon!</p>

      <div class="confirmation-summary">
        <p><strong>Name:</strong> ${escapeHtml(resp.requesterName)}</p>
        <p><strong>Variety:</strong> ${escapeHtml(varietyName)}</p>
        <p><strong>Date:</strong> ${escapeHtml(resp.pickupDate)}</p>
        <p><strong>Time:</strong> ${escapeHtml(resp.pickupTime)}</p>
        <p><strong>Location:</strong> ${escapeHtml(resp.exchangeLocation)}</p>
        <p><strong>Batch:</strong> ${escapeHtml(batch.batchName)}</p>
      </div>

      <p class="text-muted">
        We'll send you reminder emails before your pickup date.
        You can update or cancel your order any time before the cut-off date.
      </p>

      <a href="${manageUrl}" class="manage-link-btn" data-cy="manage-link">
        View My Order
      </a>
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
