// Cypress support file — import custom commands here
import './commands';

/**
 * Force classic (layout-occupying) 15px scrollbars on every platform. macOS uses overlay
 * scrollbars while Linux CI and Windows reserve space for them, which changes the usable
 * viewport width; styling ::-webkit-scrollbar makes Chromium/Electron reserve that space
 * everywhere so layout assertions behave the same locally and in CI.
 */
Cypress.on('window:before:load', (win) => {
  const style = win.document.createElement('style');
  style.textContent = '::-webkit-scrollbar { width: 15px; height: 15px; }';
  win.document.documentElement.appendChild(style);
});
