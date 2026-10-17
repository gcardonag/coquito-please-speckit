/**
 * Viewport sizes ([width, height] in px) used by the responsive-*.cy.ts specs.
 * mobile < 40em, tablet 40em–64em, desktop >= 64em (see the breakpoint block in tokens.css).
 * Usage: `cy.viewport(...VIEWPORTS.desktop)`.
 */
export const VIEWPORTS = {
  mobile: [375, 660],
  tablet: [768, 1024],
  desktop: [1280, 800],
} as const;
