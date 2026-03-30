// Variety card-style radio group

import type { VarietySummary } from '../../services/api';

export function createVarietySelector(varieties: VarietySummary[]): HTMLFieldSetElement {
  const fieldset = document.createElement('fieldset');
  fieldset.className = 'variety-selector';

  const legend = document.createElement('legend');
  legend.textContent = 'Choose your coquito *';
  fieldset.appendChild(legend);

  const grid = document.createElement('div');
  grid.className = 'variety-grid';

  varieties.forEach((v) => {
    const label = document.createElement('label');
    label.className = 'variety-card';
    label.htmlFor = `variety-${v.varietyId}`;

    const radio = document.createElement('input');
    radio.type = 'radio';
    radio.name = 'varietyId';
    radio.id = `variety-${v.varietyId}`;
    radio.value = v.varietyId;
    radio.dataset.cy = 'variety-option';
    radio.setAttribute('aria-required', 'true');

    const img = document.createElement('img');
    img.src = v.imageUrl;
    img.alt = v.name;
    img.className = 'variety-card__image';
    img.width = 80;
    img.height = 80;

    const name = document.createElement('span');
    name.className = 'variety-card__name';
    name.textContent = v.name;

    const desc = document.createElement('span');
    desc.className = 'variety-card__desc text-muted';
    desc.textContent = v.description;

    label.appendChild(radio);
    label.appendChild(img);
    label.appendChild(name);
    label.appendChild(desc);
    grid.appendChild(label);
  });

  const error = document.createElement('span');
  error.className = 'field-error text-error';
  error.id = 'error-varietyId';
  error.dataset.cy = 'error-variety';
  error.setAttribute('role', 'alert');
  error.setAttribute('aria-live', 'polite');
  error.hidden = true;

  fieldset.appendChild(grid);
  fieldset.appendChild(error);
  return fieldset;
}

export function getSelectedVarietyId(): string {
  const checked = document.querySelector<HTMLInputElement>('input[name="varietyId"]:checked');
  return checked?.value ?? '';
}
