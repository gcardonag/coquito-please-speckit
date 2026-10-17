// 007 US1 — Variety management list/detail and ingredient-row layout at each viewport.
// See specs/007-responsive-layout/contracts/ui-layout.md (Flow 5).
import { VIEWPORTS } from '../support/viewports';

const INGREDIENTS = [
  {
    ingredientId: 'i-1',
    name: 'Coconut cream',
    quantityPerBottle: 1,
    unit: 'can',
    category: 'dairy',
  },
  {
    ingredientId: 'i-2',
    name: 'Evaporated milk',
    quantityPerBottle: 1,
    unit: 'can',
    category: 'dairy',
  },
  {
    ingredientId: 'i-3',
    name: 'White rum',
    quantityPerBottle: 250,
    unit: 'ml',
    category: 'alcohol',
  },
];

const VARIETIES = ['Classic', 'Chocolate', 'Pistachio', 'Nutella', 'Guava', 'Pumpkin'].map(
  (name, i) => ({
    varietyId: `v-${i + 1}`,
    name,
    description: `${name} coquito`,
    imageKey: '',
    bottleYieldMl: 750,
    active: i !== 5,
    ingredients: i === 0 ? INGREDIENTS : [],
  })
);

/** Test ids of the first ingredient row's controls, in visual (DOM) order. */
const ROW_CONTROLS = ['ing-name-0', 'ing-qty-0', 'ing-unit-0', 'ing-cat-0', 'ing-remove-0'].map(
  (id) => `[data-testid=${id}]`
);
const ROW_INPUTS = ROW_CONTROLS.slice(0, 4);

/** Minimum width (px) of a stacked ingredient input below desktop width (spec US1 scenario 6). */
const MIN_STACKED_INPUT_WIDTH_PX = 120;

/** Minimum Remove button width (px); its height is checked by assertMinTouchTarget. */
const MIN_TOUCH_TARGET_PX = 44;

function stubApi(): void {
  cy.intercept('GET', '**/me', {
    body: { userId: 'u-chef', role: 'chef', email: 'chef@example.com' },
  });
  cy.intercept('GET', '**/chef/varieties', { body: { varieties: VARIETIES } }).as('getVarieties');
}

/** Open the variety that has three ingredients in the detail panel. */
function selectFirstVariety(): void {
  cy.get('[data-variety-id]').first().click();
  cy.get('[data-testid=edit-variety-form]').should('be.visible');
}

describe('007 US1 — Responsive variety management', () => {
  (Object.keys(VIEWPORTS) as Array<keyof typeof VIEWPORTS>).forEach((name) => {
    describe(`at ${name}`, () => {
      beforeEach(() => {
        stubApi();
        cy.viewport(...VIEWPORTS[name]);
        cy.visit('/#/varieties');
        cy.wait('@getVarieties');
      });

      it('has no horizontal overflow and no a11y violations', () => {
        selectFirstVariety();
        cy.assertNoHorizontalOverflow();
        cy.checkA11yAtViewport();
      });

      if (name === 'desktop') {
        it('shows the list and detail side by side', () => {
          selectFirstVariety();
          cy.assertSideBySide('[data-testid=variety-list]', '[data-testid=variety-detail]');
        });

        it('lays out each ingredient row on a single line', () => {
          selectFirstVariety();
          for (let i = 1; i < ROW_CONTROLS.length; i++) {
            cy.assertSideBySide(ROW_CONTROLS[i - 1], ROW_CONTROLS[i]);
          }
        });
      } else {
        it('stacks the detail below the list', () => {
          selectFirstVariety();
          cy.assertStacked('[data-testid=variety-list]', '[data-testid=variety-detail]');
        });

        it('stacks ingredient inputs at a comfortable width with a full-size Remove button', () => {
          selectFirstVariety();
          for (let i = 1; i < ROW_INPUTS.length; i++) {
            cy.assertStacked(ROW_INPUTS[i - 1], ROW_INPUTS[i]);
          }
          ROW_INPUTS.forEach((sel) => {
            cy.get(sel).invoke('outerWidth').should('be.at.least', MIN_STACKED_INPUT_WIDTH_PX);
          });
          cy.assertMinTouchTarget(ROW_CONTROLS[4]);
          cy.get(ROW_CONTROLS[4]).invoke('outerWidth').should('be.at.least', MIN_TOUCH_TARGET_PX);
        });
      }
    });
  });
});
