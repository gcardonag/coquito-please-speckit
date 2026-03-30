// Cost contribution yes/no toggle

export function createCostToggle(): HTMLDivElement {
  const wrapper = document.createElement('div');
  wrapper.className = 'form-field';

  const fieldset = document.createElement('fieldset');
  fieldset.className = 'toggle-group';

  const legend = document.createElement('legend');
  legend.textContent = 'Would you like to contribute to the cost?';
  fieldset.appendChild(legend);

  const options: Array<{ value: string; label: string; cy: string }> = [
    { value: 'true', label: 'Yes, happy to contribute', cy: 'cost-contribution-yes' },
    { value: 'false', label: 'No, thank you', cy: 'cost-contribution-no' },
  ];

  options.forEach(({ value, label, cy }, idx) => {
    const optLabel = document.createElement('label');
    optLabel.className = 'toggle-option';
    optLabel.htmlFor = `cost-${value}`;

    const radio = document.createElement('input');
    radio.type = 'radio';
    radio.name = 'costContribution';
    radio.id = `cost-${value}`;
    radio.value = value;
    radio.dataset.cy = cy;
    if (idx === 0) radio.checked = true;

    optLabel.appendChild(radio);
    optLabel.appendChild(document.createTextNode(` ${label}`));
    fieldset.appendChild(optLabel);
  });

  wrapper.appendChild(fieldset);
  return wrapper;
}

export function getCostContribution(): boolean {
  const checked = document.querySelector<HTMLInputElement>(
    'input[name="costContribution"]:checked'
  );
  return checked?.value === 'true';
}
