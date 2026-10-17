/**
 * Unit tests for the cook view's ingredient list component: variety sections, acquired
 * checkboxes, and the keyboard-reachable totals table.
 */
import { describe, expect, it, vi } from 'vitest';
import {
  createIngredientList,
  type IngredientListOptions,
} from '../../components/ingredient-list/ingredient-list';

function makeOptions(overrides: Partial<IngredientListOptions> = {}): IngredientListOptions {
  return {
    byVariety: [
      {
        varietyId: 'v-classic',
        varietyName: 'Classic',
        confirmedCount: 2,
        ingredients: [
          {
            ingredientId: 'i-rum',
            name: 'Rum',
            totalQuantity: 2,
            unit: 'bottle',
            category: 'alcohol',
            acquired: false,
          },
          {
            ingredientId: 'i-coconut',
            name: 'Coconut cream',
            totalQuantity: 4,
            unit: 'can',
            category: 'dairy',
            acquired: true,
          },
        ],
      },
    ],
    totals: [{ name: '<Rum>', totalQuantity: 2, unit: 'bottle', category: 'alcohol' }],
    onToggleAcquired: vi.fn(),
    ...overrides,
  } as IngredientListOptions;
}

describe('createIngredientList', () => {
  it('renders one section per variety with its order count and ingredient rows', () => {
    const list = createIngredientList(makeOptions());
    const sections = list.querySelectorAll('[data-cy="variety-section"]');
    expect(sections).toHaveLength(1);
    expect(sections[0].querySelector('h2')?.textContent).toBe('Classic (2 orders)');

    const rows = list.querySelectorAll('.ingredient-row');
    expect(rows).toHaveLength(2);
    expect(rows[0].querySelector('.ingredient-name')?.textContent).toBe('Rum');
    expect(rows[0].querySelector('.ingredient-qty')?.textContent).toBe('2 bottle');
    expect(rows[0].querySelector('.ingredient-category')?.textContent).toBe('alcohol');
  });

  it('reflects the acquired state and labels each checkbox', () => {
    const list = createIngredientList(makeOptions());
    const rum = list.querySelector<HTMLInputElement>('#check-i-rum')!;
    const coconut = list.querySelector<HTMLInputElement>('#check-i-coconut')!;
    expect(rum.checked).toBe(false);
    expect(coconut.checked).toBe(true);
    expect(list.querySelector('#row-i-coconut')?.classList).toContain('ingredient-row--acquired');
    expect(list.querySelector('label[for="check-i-rum"]')).not.toBeNull();
    expect(rum.getAttribute('aria-describedby')).toBe('desc-i-rum');
  });

  it('toggles the row style and reports the change when a checkbox is ticked', () => {
    const onToggleAcquired = vi.fn();
    const list = createIngredientList(makeOptions({ onToggleAcquired }));
    const rum = list.querySelector<HTMLInputElement>('#check-i-rum')!;

    rum.checked = true;
    rum.dispatchEvent(new Event('change'));
    expect(list.querySelector('#row-i-rum')?.classList).toContain('ingredient-row--acquired');
    expect(onToggleAcquired).toHaveBeenCalledWith('i-rum', true);

    rum.checked = false;
    rum.dispatchEvent(new Event('change'));
    expect(list.querySelector('#row-i-rum')?.classList).not.toContain('ingredient-row--acquired');
    expect(onToggleAcquired).toHaveBeenLastCalledWith('i-rum', false);
  });

  it('wraps the totals table in a focusable region labelled by its heading', () => {
    const list = createIngredientList(makeOptions());
    const totals = list.querySelector('[data-cy="totals-section"]')!;
    const region = totals.querySelector<HTMLElement>('.totals-scroll')!;
    expect(region.getAttribute('role')).toBe('region');
    expect(region.tabIndex).toBe(0);
    const heading = totals.querySelector(`#${region.getAttribute('aria-labelledby')}`);
    expect(heading?.textContent).toBe('Total Shopping List');
    expect(region.querySelector('table.totals-table')).not.toBeNull();
  });

  it('renders totals rows with HTML escaped', () => {
    const list = createIngredientList(makeOptions());
    const cells = list.querySelectorAll('.totals-table tbody td');
    expect([...cells].map((td) => td.textContent)).toEqual(['<Rum>', '2 bottle', 'alcohol']);
    expect(list.querySelector('.totals-table tbody script, .totals-table tbody rum')).toBeNull();
  });

  it('omits the totals section when there are no totals', () => {
    const list = createIngredientList(makeOptions({ totals: [] }));
    expect(list.querySelector('[data-cy="totals-section"]')).toBeNull();
  });
});
