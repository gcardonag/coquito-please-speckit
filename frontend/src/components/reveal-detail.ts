/** Media query for the desktop breakpoint, where list and detail sit side by side. */
const DESKTOP_QUERY = '(min-width: 64em)';

/**
 * Bring a list/detail page's detail panel into view after the user selects an item.
 *
 * Below the desktop breakpoint the detail panel is stacked under the list, so it is scrolled to
 * the top of the viewport. At desktop width the panel already sits beside the list and nothing
 * happens. No smooth behavior is requested, so `prefers-reduced-motion` is respected.
 * A missing panel, or an environment without `matchMedia`/`scrollIntoView` (e.g. jsdom), is a
 * no-op.
 */
export function revealDetail(detailEl: HTMLElement | null): void {
  if (!detailEl || typeof window.matchMedia !== 'function') return;
  if (typeof detailEl.scrollIntoView !== 'function') return;
  if (!window.matchMedia(DESKTOP_QUERY).matches) {
    detailEl.scrollIntoView({ block: 'start' });
  }
}
