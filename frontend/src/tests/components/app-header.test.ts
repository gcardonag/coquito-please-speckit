/**
 * T024: Unit tests for the global app header (US5).
 * Layout is covered by cypress/e2e/responsive-shell.cy.ts; these tests cover rendering,
 * aria-current syncing and Log out wiring.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { renderAppHeader, showChefNav } from '../../components/app-header/app-header';

/** Reset the body to the shape of index.html: a lone `#app` main landmark. */
function resetBody(): void {
  document.body.innerHTML = '<div id="app" role="main"></div>';
}

describe('US5: renderAppHeader', () => {
  beforeEach(() => {
    resetBody();
    window.location.hash = '#/';
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('inserts header.app-header immediately before #app', () => {
    const header = renderAppHeader({ isChef: false, onLogout: vi.fn() });
    expect(header.tagName).toBe('HEADER');
    expect(header.classList.contains('app-header')).toBe(true);
    expect(header.nextElementSibling?.id).toBe('app');
  });

  it('renders a brand link to the home page', () => {
    renderAppHeader({ isChef: false, onLogout: vi.fn() });
    const brand = document.querySelector<HTMLAnchorElement>('.app-header__brand');
    expect(brand?.getAttribute('href')).toBe('#/');
    expect(brand?.textContent).toBe('Coquito Please');
  });

  it('renders the 2 chef nav links for a chef', () => {
    renderAppHeader({ isChef: true, onLogout: vi.fn() });
    const nav = document.getElementById('chef-nav');
    expect(nav?.getAttribute('aria-label')).toBe('Chef');
    const hrefs = [...document.querySelectorAll('#chef-nav a')].map((a) => a.getAttribute('href'));
    expect(hrefs).toEqual(['#/batches', '#/varieties']);
  });

  it('renders no chef nav for a non-chef', () => {
    renderAppHeader({ isChef: false, onLogout: vi.fn() });
    expect(document.getElementById('chef-nav')).toBeNull();
    expect(document.querySelectorAll('.app-header__link')).toHaveLength(0);
  });

  it('is idempotent: a second call returns the same single header', () => {
    const first = renderAppHeader({ isChef: true, onLogout: vi.fn() });
    const second = renderAppHeader({ isChef: true, onLogout: vi.fn() });
    expect(second).toBe(first);
    expect(document.querySelectorAll('header.app-header')).toHaveLength(1);
  });

  it('marks the link for the current hash with aria-current="page"', () => {
    window.location.hash = '#/batches';
    renderAppHeader({ isChef: true, onLogout: vi.fn() });
    expect(document.querySelector('a[href="#/batches"]')?.getAttribute('aria-current')).toBe(
      'page'
    );
    expect(document.querySelector('a[href="#/varieties"]')?.hasAttribute('aria-current')).toBe(
      false
    );
  });

  it('moves aria-current when the hash changes', () => {
    window.location.hash = '#/batches';
    renderAppHeader({ isChef: true, onLogout: vi.fn() });

    window.location.hash = '#/varieties';
    window.dispatchEvent(new HashChangeEvent('hashchange'));

    expect(document.querySelector('a[href="#/varieties"]')?.getAttribute('aria-current')).toBe(
      'page'
    );
    expect(document.querySelector('a[href="#/batches"]')?.hasAttribute('aria-current')).toBe(false);
  });

  it('ignores the query string when matching the current link', () => {
    window.location.hash = '#/batches?foo=1';
    renderAppHeader({ isChef: true, onLogout: vi.fn() });
    expect(document.querySelector('a[href="#/batches"]')?.getAttribute('aria-current')).toBe(
      'page'
    );
  });

  it('calls the injected logout callback when #logout-btn is clicked', () => {
    const onLogout = vi.fn();
    renderAppHeader({ isChef: false, onLogout });
    const btn = document.getElementById('logout-btn') as HTMLButtonElement;
    expect(btn.type).toBe('button');
    expect(btn.textContent).toBe('Log out');
    btn.click();
    expect(onLogout).toHaveBeenCalledTimes(1);
  });
});

describe('US5: showChefNav (chef links added after /me resolves)', () => {
  beforeEach(() => {
    resetBody();
    window.location.hash = '#/varieties';
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('adds the chef nav between the brand and Log out on an existing header', () => {
    const header = renderAppHeader({ isChef: false, onLogout: vi.fn() });
    showChefNav(header);
    const order = [...header.querySelector('.app-header__inner')!.children].map(
      (el) => el.id || el.className
    );
    expect(order).toEqual(['app-header__brand', 'chef-nav', 'logout-btn']);
  });

  it('marks the current route link with aria-current="page"', () => {
    const header = renderAppHeader({ isChef: false, onLogout: vi.fn() });
    showChefNav(header);
    expect(document.querySelector('a[href="#/varieties"]')?.getAttribute('aria-current')).toBe(
      'page'
    );
  });

  it('is idempotent: calling it twice leaves a single nav', () => {
    const header = renderAppHeader({ isChef: true, onLogout: vi.fn() });
    showChefNav(header);
    expect(document.querySelectorAll('#chef-nav')).toHaveLength(1);
  });
});
