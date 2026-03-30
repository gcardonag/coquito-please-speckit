// Bottle preference toggle + conditional volume input

export function createBottlePreference(maxVolumeMl: number): HTMLDivElement {
  const wrapper = document.createElement('div');
  wrapper.className = 'form-field bottle-preference';

  const legend = document.createElement('fieldset');
  legend.className = 'toggle-group';

  const legendEl = document.createElement('legend');
  legendEl.textContent = 'Will you bring your own bottle?';
  legend.appendChild(legendEl);

  // No option (default)
  const labelNo = document.createElement('label');
  labelNo.className = 'toggle-option';
  labelNo.htmlFor = 'bottle-provided-no';

  const radioNo = document.createElement('input');
  radioNo.type = 'radio';
  radioNo.name = 'bottleProvided';
  radioNo.id = 'bottle-provided-no';
  radioNo.value = 'false';
  radioNo.checked = true;
  radioNo.dataset.cy = 'bottle-provided-no';

  labelNo.appendChild(radioNo);
  labelNo.appendChild(document.createTextNode(' No, please provide one'));

  // Yes option
  const labelYes = document.createElement('label');
  labelYes.className = 'toggle-option';
  labelYes.htmlFor = 'bottle-provided-yes';

  const radioYes = document.createElement('input');
  radioYes.type = 'radio';
  radioYes.name = 'bottleProvided';
  radioYes.id = 'bottle-provided-yes';
  radioYes.value = 'true';
  radioYes.dataset.cy = 'bottle-provided-yes';

  labelYes.appendChild(radioYes);
  labelYes.appendChild(document.createTextNode(` Yes, I'll bring my own`));

  legend.appendChild(labelNo);
  legend.appendChild(labelYes);

  // Conditional volume input
  const volumeWrapper = document.createElement('div');
  volumeWrapper.className = 'volume-input';
  volumeWrapper.hidden = true;

  const volumeLabel = document.createElement('label');
  volumeLabel.htmlFor = 'bottle-volume';
  volumeLabel.textContent = `Bottle volume (ml, max ${maxVolumeMl}ml) *`;

  const volumeInput = document.createElement('input');
  volumeInput.type = 'number';
  volumeInput.id = 'bottle-volume';
  volumeInput.name = 'bottleVolumeMl';
  volumeInput.dataset.cy = 'bottle-volume';
  volumeInput.min = '1';
  volumeInput.max = String(maxVolumeMl);
  volumeInput.placeholder = `e.g. 750`;
  volumeInput.setAttribute('aria-describedby', 'error-bottle-volume');

  const volumeError = document.createElement('span');
  volumeError.className = 'field-error text-error';
  volumeError.id = 'error-bottle-volume';
  volumeError.dataset.cy = 'error-bottle-volume';
  volumeError.setAttribute('role', 'alert');
  volumeError.setAttribute('aria-live', 'polite');
  volumeError.hidden = true;

  volumeWrapper.appendChild(volumeLabel);
  volumeWrapper.appendChild(volumeInput);
  volumeWrapper.appendChild(volumeError);

  // Toggle volume input visibility
  function updateVolume() {
    const showing = radioYes.checked;
    volumeWrapper.hidden = !showing;
    if (!showing) {
      volumeInput.value = '';
    }
  }

  radioNo.addEventListener('change', updateVolume);
  radioYes.addEventListener('change', updateVolume);

  wrapper.appendChild(legend);
  wrapper.appendChild(volumeWrapper);
  return wrapper;
}

export function isBottleProvided(): boolean {
  const checked = document.querySelector<HTMLInputElement>('input[name="bottleProvided"]:checked');
  return checked?.value === 'true';
}

export function getBottleVolumeMl(): number | null {
  const input = document.getElementById('bottle-volume') as HTMLInputElement | null;
  if (!input || !input.value) return null;
  return parseInt(input.value, 10);
}
