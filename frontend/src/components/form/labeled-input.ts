// Labeled text/email/number input with error slot

export interface LabeledInputOptions {
  id: string;
  label: string;
  type?: string;
  placeholder?: string;
  required?: boolean;
  min?: number;
  max?: number;
  autocomplete?: string;
}

export function createLabeledInput(opts: LabeledInputOptions): HTMLDivElement {
  const wrapper = document.createElement('div');
  wrapper.className = 'form-field';

  const label = document.createElement('label');
  label.htmlFor = opts.id;
  label.textContent = opts.label + (opts.required ? ' *' : '');

  const input = document.createElement('input');
  input.type = opts.type ?? 'text';
  input.id = opts.id;
  input.name = opts.id;
  input.dataset.cy = opts.id;
  input.setAttribute('aria-required', opts.required ? 'true' : 'false');
  if (opts.placeholder) input.placeholder = opts.placeholder;
  if (opts.autocomplete) input.setAttribute('autocomplete', opts.autocomplete);
  if (opts.min !== undefined) input.min = String(opts.min);
  if (opts.max !== undefined) input.max = String(opts.max);

  const error = document.createElement('span');
  error.className = 'field-error text-error';
  error.id = `error-${opts.id}`;
  error.dataset.cy = `error-${opts.id}`;
  error.setAttribute('role', 'alert');
  error.setAttribute('aria-live', 'polite');
  error.hidden = true;

  wrapper.appendChild(label);
  wrapper.appendChild(input);
  wrapper.appendChild(error);
  return wrapper;
}

export function setFieldError(fieldId: string, message: string): void {
  const input = document.getElementById(fieldId) as HTMLInputElement | null;
  const errorEl = document.getElementById(`error-${fieldId}`);
  if (input) {
    input.setAttribute('aria-invalid', 'true');
    input.classList.add('input--error');
  }
  if (errorEl) {
    errorEl.textContent = message;
    errorEl.hidden = false;
  }
}

export function clearFieldError(fieldId: string): void {
  const input = document.getElementById(fieldId) as HTMLInputElement | null;
  const errorEl = document.getElementById(`error-${fieldId}`);
  if (input) {
    input.removeAttribute('aria-invalid');
    input.classList.remove('input--error');
  }
  if (errorEl) {
    errorEl.textContent = '';
    errorEl.hidden = true;
  }
}
