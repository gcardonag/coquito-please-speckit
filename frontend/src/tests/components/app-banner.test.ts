/**
 * US5 scenario 3: unit tests for the page-level notice banner.
 * The banner must sit in normal flow at the top of <body> (before the header), use the
 * .app-banner classes instead of inline styles, and be dismissible with a real button.
 */
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { showBanner } from '../../components/app-banner/app-banner';

describe('US5: showBanner', () => {
  beforeEach(() => {
    document.body.innerHTML = '<header class="app-header"></header><div id="app"></div>';
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('inserts the banner as the first child of body, before the header', () => {
    showBanner('Service temporarily unavailable — please try again.', 'warn');
    const banner = document.body.firstElementChild as HTMLElement;
    expect(banner.id).toBe('app-banner');
    expect(banner.nextElementSibling?.classList.contains('app-header')).toBe(true);
  });

  it('uses the .app-banner classes and role=alert with no inline styles', () => {
    showBanner('Authentication error.', 'error');
    const banner = document.getElementById('app-banner')!;
    expect(banner.className).toBe('app-banner app-banner--error');
    expect(banner.getAttribute('role')).toBe('alert');
    expect(banner.hasAttribute('style')).toBe(false);
    expect(banner.querySelector('[style]')).toBeNull();
  });

  it('defaults to the warn modifier', () => {
    showBanner('API is unreachable.');
    expect(document.getElementById('app-banner')!.classList.contains('app-banner--warn')).toBe(
      true
    );
  });

  it('renders the message as text, not HTML', () => {
    showBanner('<img src=x onerror=alert(1)>');
    const banner = document.getElementById('app-banner')!;
    expect(banner.querySelector('img')).toBeNull();
    expect(banner.textContent).toContain('<img src=x onerror=alert(1)>');
  });

  it('replaces an existing banner instead of stacking a second one', () => {
    showBanner('first');
    showBanner('second');
    const banners = document.querySelectorAll('.app-banner');
    expect(banners).toHaveLength(1);
    expect(banners[0].textContent).toContain('second');
  });

  it('removes itself when the Dismiss button is clicked', () => {
    showBanner('closable');
    const close = document.querySelector<HTMLButtonElement>('.app-banner__close')!;
    expect(close.type).toBe('button');
    expect(close.getAttribute('aria-label')).toBe('Dismiss');
    expect(close.hasAttribute('onclick')).toBe(false);
    close.click();
    expect(document.getElementById('app-banner')).toBeNull();
  });
});
