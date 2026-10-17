import 'cypress-axe';

// ---------------------------------------------------------------------------
// Layout + accessibility assertions shared by the responsive-*.cy.ts specs.
// Geometry checks re-query the DOM inside a retrying `should` callback, so they
// wait for layout to settle without fixed timeouts.
// ---------------------------------------------------------------------------

/** WCAG 2.1 AA rule tags passed to axe by `checkA11yAtViewport`. */
const A11Y_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'];

/** Minimum hit-area height (px) for interactive elements; mirrors --touch-target-min. */
const MIN_TOUCH_TARGET_PX = 44;

/** Allowed difference (px) between two element tops that count as "the same row". */
const SAME_ROW_TOLERANCE_PX = 8;

declare global {
  namespace Cypress {
    interface Chainable {
      /** Assert the page has no horizontal scroll (documentElement scrollWidth <= clientWidth). */
      assertNoHorizontalOverflow(): Chainable<void>;
      /**
       * Assert the first match of `selA` sits to the left of the first match of `selB` on the
       * same row: tops within 8px and A's right edge <= B's left edge.
       */
      assertSideBySide(selA: string, selB: string): Chainable<void>;
      /** Assert the first match of `selB` starts at or below the bottom of the first match of `selA`. */
      assertStacked(selA: string, selB: string): Chainable<void>;
      /** Assert every visible match of `sel` is at least 44px tall (at least one must be visible). */
      assertMinTouchTarget(sel: string): Chainable<void>;
      /** Inject axe and check the whole page against WCAG 2.1 AA tags at the current viewport. */
      checkA11yAtViewport(): Chainable<void>;
    }
  }
}

/** Bounding rect of the first element matching `sel`, failing clearly when nothing matches. */
function rectOf(sel: string): DOMRect {
  const el = Cypress.$(sel).get(0);
  expect(el, `element for "${sel}"`).to.exist;
  return el!.getBoundingClientRect();
}

Cypress.Commands.add('assertNoHorizontalOverflow', () => {
  cy.document().should((doc) => {
    const { scrollWidth, clientWidth } = doc.documentElement;
    expect(scrollWidth, 'document scrollWidth <= clientWidth').to.be.at.most(clientWidth);
  });
});

Cypress.Commands.add('assertSideBySide', (selA: string, selB: string) => {
  cy.get(selA).should('be.visible');
  cy.get(selB).should('be.visible');
  cy.document().should(() => {
    const a = rectOf(selA);
    const b = rectOf(selB);
    expect(Math.abs(a.top - b.top), `"${selA}" and "${selB}" tops differ by`).to.be.at.most(
      SAME_ROW_TOLERANCE_PX
    );
    expect(a.right, `"${selA}" right edge <= "${selB}" left edge`).to.be.at.most(b.left);
  });
});

Cypress.Commands.add('assertStacked', (selA: string, selB: string) => {
  cy.get(selA).should('be.visible');
  cy.get(selB).should('be.visible');
  cy.document().should(() => {
    const a = rectOf(selA);
    const b = rectOf(selB);
    expect(b.top, `"${selB}" top >= "${selA}" bottom`).to.be.at.least(a.bottom);
  });
});

Cypress.Commands.add('assertMinTouchTarget', (sel: string) => {
  cy.get(sel).should(($els) => {
    const visible = $els.filter(':visible');
    expect(visible.length, `visible elements for "${sel}"`).to.be.greaterThan(0);
    visible.each((_i, el) => {
      // Round to absorb sub-pixel layout (e.g. 43.998px for a 44px min-height).
      const height = Math.round(el.getBoundingClientRect().height);
      const label = el.id ? `#${el.id}` : (el.textContent ?? '').trim().slice(0, 40);
      expect(height, `height of ${el.tagName.toLowerCase()} "${label}"`).to.be.at.least(
        MIN_TOUCH_TARGET_PX
      );
    });
  });
});

Cypress.Commands.add('checkA11yAtViewport', () => {
  cy.injectAxe();
  cy.checkA11y(undefined, { runOnly: { type: 'tag', values: A11Y_TAGS } }, (violations) => {
    // Log each violation with its offending selectors, in the runner and in the terminal
    // (via the `log` task) so headless CI failures are diagnosable from the job log.
    violations.forEach((v) => {
      const message = `${v.id} (${v.impact}): ${v.help} — ${v.nodes.map((n) => n.target).join(', ')}`;
      Cypress.log({ name: 'a11y', message });
      cy.task('log', `a11y violation: ${message}`);
    });
  });
});
