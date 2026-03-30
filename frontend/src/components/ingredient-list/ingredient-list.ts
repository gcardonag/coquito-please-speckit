// Ingredient list component — grouped by variety with acquired checkboxes

import type { VarietyIngredients, IngredientItem } from '../../services/api';

export interface IngredientListOptions {
  byVariety: VarietyIngredients[];
  totals: Array<{ name: string; totalQuantity: number; unit: string; category: string }>;
  onToggleAcquired: (ingredientId: string, acquired: boolean) => void;
}

export function createIngredientList(opts: IngredientListOptions): HTMLElement {
  const wrapper = document.createElement('div');
  wrapper.className = 'ingredient-list';

  for (const variety of opts.byVariety) {
    wrapper.appendChild(buildVarietySection(variety, opts.onToggleAcquired));
  }

  if (opts.totals.length > 0) {
    wrapper.appendChild(buildTotalsSection(opts.totals));
  }

  return wrapper;
}

function buildVarietySection(
  variety: VarietyIngredients,
  onToggle: (id: string, acquired: boolean) => void
): HTMLElement {
  const section = document.createElement('section');
  section.className = 'variety-section';
  section.dataset.cy = 'variety-section';

  const heading = document.createElement('h2');
  heading.className = 'variety-section__heading';
  heading.textContent = `${variety.varietyName} (${variety.confirmedCount} orders)`;
  section.appendChild(heading);

  const list = document.createElement('ul');
  list.className = 'ingredient-rows';

  for (const ing of variety.ingredients) {
    list.appendChild(buildIngredientRow(ing, onToggle));
  }

  section.appendChild(list);
  return section;
}

function buildIngredientRow(
  ing: IngredientItem,
  onToggle: (id: string, acquired: boolean) => void
): HTMLElement {
  const li = document.createElement('li');
  li.className = `ingredient-row${ing.acquired ? ' ingredient-row--acquired' : ''}`;
  li.id = `row-${ing.ingredientId}`;

  const checkboxId = `check-${ing.ingredientId}`;

  const checkbox = document.createElement('input');
  checkbox.type = 'checkbox';
  checkbox.id = checkboxId;
  checkbox.className = 'ingredient-check';
  checkbox.dataset.cy = `ingredient-check-${ing.ingredientId}`;
  checkbox.checked = ing.acquired;
  // Label element provides accessible name; aria-describedby adds context
  checkbox.setAttribute('aria-describedby', `desc-${ing.ingredientId}`);

  checkbox.addEventListener('change', () => {
    const nowAcquired = checkbox.checked;
    li.classList.toggle('ingredient-row--acquired', nowAcquired);
    onToggle(ing.ingredientId, nowAcquired);
  });

  const label = document.createElement('label');
  label.htmlFor = checkboxId;
  label.className = 'ingredient-label';

  const nameSpan = document.createElement('span');
  nameSpan.className = 'ingredient-name';
  nameSpan.id = `desc-${ing.ingredientId}`;
  nameSpan.textContent = ing.name;

  const qtySpan = document.createElement('span');
  qtySpan.className = 'ingredient-qty';
  qtySpan.textContent = `${ing.totalQuantity} ${ing.unit}`;

  const categorySpan = document.createElement('span');
  categorySpan.className = 'ingredient-category';
  categorySpan.textContent = ing.category;

  label.appendChild(nameSpan);
  label.appendChild(qtySpan);
  label.appendChild(categorySpan);

  li.appendChild(checkbox);
  li.appendChild(label);
  return li;
}

function buildTotalsSection(
  totals: Array<{ name: string; totalQuantity: number; unit: string; category: string }>
): HTMLElement {
  const section = document.createElement('section');
  section.className = 'totals-section';
  section.dataset.cy = 'totals-section';

  const heading = document.createElement('h2');
  heading.className = 'totals-section__heading';
  heading.textContent = 'Total Shopping List';
  section.appendChild(heading);

  const table = document.createElement('table');
  table.className = 'totals-table';

  const thead = document.createElement('thead');
  thead.innerHTML = `
    <tr>
      <th scope="col">Ingredient</th>
      <th scope="col">Quantity</th>
      <th scope="col">Category</th>
    </tr>
  `;
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  for (const item of totals) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${escapeHtml(item.name)}</td>
      <td>${item.totalQuantity} ${escapeHtml(item.unit)}</td>
      <td>${escapeHtml(item.category)}</td>
    `;
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  section.appendChild(table);

  return section;
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
