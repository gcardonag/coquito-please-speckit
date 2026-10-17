/**
 * T044: Unit tests for src/main.ts (app bootstrap).
 *
 * main.ts runs its startup at import time: the auth callback, the health banner, the
 * global header (with chef links once GET /me resolves) and the hash router. Each test
 * arranges the URL, env, and mocks, then re-imports the module after `vi.resetModules()`
 * so the startup runs again from a clean state.
 *
 * The auth service, GET /me, and the page modules are mocked; the header and banner
 * components are real, so assertions are made against the rendered DOM.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { CurrentUser } from '../services/api';

const mocks = vi.hoisted(() => ({
  getAndClearReturnUrl: vi.fn<() => string | null>(),
  getCodeVerifier: vi.fn<() => string | null>(),
  isSessionExpired: vi.fn((response: Response) => response.status === 401),
  logout: vi.fn<() => Promise<void>>(),
  redirectToLogin: vi.fn<() => Promise<void>>(),
  verifyState: vi.fn<(state: string) => boolean>(),
  getMe: vi.fn<() => Promise<CurrentUser>>(),
  mountRequestForm: vi.fn<(el: HTMLElement) => void>(),
  mountManageRequest: vi.fn<(el: HTMLElement, id: string) => void>(),
  mountCookView: vi.fn<(el: HTMLElement) => void>(),
  mountBatchManagement: vi.fn<(el: HTMLElement, user: CurrentUser | null) => Promise<void>>(),
  mountVarietyManagement: vi.fn<(el: HTMLElement) => Promise<void>>(),
}));

vi.mock('../services/auth', () => ({
  getAndClearReturnUrl: mocks.getAndClearReturnUrl,
  getCodeVerifier: mocks.getCodeVerifier,
  isSessionExpired: mocks.isSessionExpired,
  logout: mocks.logout,
  redirectToLogin: mocks.redirectToLogin,
  verifyState: mocks.verifyState,
}));
vi.mock('../services/api', () => ({ getMe: mocks.getMe }));
vi.mock('../pages/request-form/index', () => ({ mountRequestForm: mocks.mountRequestForm }));
vi.mock('../pages/manage-request/index', () => ({
  mountManageRequest: mocks.mountManageRequest,
}));
vi.mock('../pages/cook-view/index', () => ({ mountCookView: mocks.mountCookView }));
vi.mock('../pages/batch-management/index', () => ({
  mountBatchManagement: mocks.mountBatchManagement,
}));
vi.mock('../pages/variety-management/index', () => ({
  mountVarietyManagement: mocks.mountVarietyManagement,
}));

const API_URL = 'https://api.test';
const CHEF: CurrentUser = { userId: 'u-1', role: 'chef', email: 'chef@example.com' };
const REQUESTER: CurrentUser = { userId: 'u-2', role: 'requester', email: 'r@example.com' };

/** Every listener main.ts (and the real header) adds to window, so tests can remove them. */
let windowListeners: Array<[string, EventListenerOrEventListenerObject]> = [];
let fetchMock: ReturnType<typeof vi.fn>;

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

/** Set the current URL (path + search + hash) without triggering navigation. */
function setUrl(url: string): void {
  history.replaceState(null, '', url);
}

/** Let pending promise chains and dynamic imports settle. */
async function flush(): Promise<void> {
  for (let i = 0; i < 10; i++) {
    await new Promise((resolve) => setTimeout(resolve, 0));
  }
}

/** Import main.ts fresh, running its startup, and wait for it to settle. */
async function boot(): Promise<typeof import('../main')> {
  vi.resetModules();
  const mod = await import('../main');
  await flush();
  return mod;
}

function banner(): HTMLElement | null {
  return document.getElementById('app-banner');
}

beforeEach(() => {
  document.body.innerHTML = '<div id="app" role="main"></div>';
  sessionStorage.clear();
  setUrl('/#/');

  vi.stubEnv('VITE_API_URL', API_URL);

  // Default: health check succeeds; tests override per scenario.
  fetchMock = vi.fn(async () => jsonResponse({ status: 'ok' }));
  vi.stubGlobal('fetch', fetchMock);

  mocks.getAndClearReturnUrl.mockReturnValue(null);
  mocks.getCodeVerifier.mockReturnValue('verifier-123');
  mocks.logout.mockResolvedValue(undefined);
  mocks.redirectToLogin.mockResolvedValue(undefined);
  mocks.verifyState.mockReturnValue(true);
  mocks.getMe.mockResolvedValue(REQUESTER);
  mocks.mountBatchManagement.mockResolvedValue(undefined);
  mocks.mountVarietyManagement.mockResolvedValue(undefined);

  windowListeners = [];
  const original = window.addEventListener.bind(window);
  vi.spyOn(window, 'addEventListener').mockImplementation(
    (type: string, listener: EventListenerOrEventListenerObject, options?: unknown) => {
      windowListeners.push([type, listener]);
      original(type, listener, options as AddEventListenerOptions);
    }
  );
});

afterEach(() => {
  for (const [type, listener] of windowListeners) {
    window.removeEventListener(type, listener);
  }
  vi.restoreAllMocks();
  vi.clearAllMocks();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  document.body.innerHTML = '';
  sessionStorage.clear();
  setUrl('/');
});

// ---------------------------------------------------------------------------
// Routing
// ---------------------------------------------------------------------------
describe('main: hash routing', () => {
  it('renders the request form for #/', async () => {
    setUrl('/#/');
    await boot();
    expect(mocks.mountRequestForm).toHaveBeenCalledTimes(1);
    expect(mocks.mountRequestForm).toHaveBeenCalledWith(document.getElementById('app'));
  });

  it('treats an empty hash as #/', async () => {
    setUrl('/');
    await boot();
    expect(mocks.mountRequestForm).toHaveBeenCalledTimes(1);
  });

  it('ignores the query string when matching routes', async () => {
    setUrl('/#/?batchId=b-1');
    await boot();
    expect(mocks.mountRequestForm).toHaveBeenCalledTimes(1);
  });

  it('renders manage-request with the id from #/manage/:id', async () => {
    setUrl('/#/manage/req-42');
    await boot();
    expect(mocks.mountManageRequest).toHaveBeenCalledWith(document.getElementById('app'), 'req-42');
  });

  it('renders the cook view for #/cook', async () => {
    setUrl('/#/cook');
    await boot();
    expect(mocks.mountCookView).toHaveBeenCalledWith(document.getElementById('app'));
  });

  it('renders batch management for #/batches with the current user', async () => {
    mocks.getMe.mockResolvedValue(CHEF);
    setUrl('/#/batches');
    await boot();
    expect(mocks.mountBatchManagement).toHaveBeenCalledWith(document.getElementById('app'), CHEF);
  });

  it('passes a null user to batch management when GET /me fails', async () => {
    mocks.getMe.mockRejectedValue(new Error('401'));
    setUrl('/#/batches');
    await boot();
    expect(mocks.mountBatchManagement).toHaveBeenCalledWith(document.getElementById('app'), null);
  });

  it('renders variety management for #/varieties', async () => {
    setUrl('/#/varieties');
    await boot();
    expect(mocks.mountVarietyManagement).toHaveBeenCalledWith(document.getElementById('app'));
  });

  it('clears previous #app content before mounting a page', async () => {
    document.getElementById('app')!.innerHTML = '<p class="stale">old</p>';
    setUrl('/#/cook');
    await boot();
    expect(document.querySelector('#app .stale')).toBeNull();
  });

  it('renders a not-found card with a link home for an unknown route', async () => {
    setUrl('/#/nope');
    await boot();
    const card = document.querySelector('#app .card.not-found');
    expect(card).not.toBeNull();
    expect(card!.querySelector('h1')?.textContent).toBe('¡Ay, bendito!');
    const link = card!.querySelector<HTMLAnchorElement>('a.not-found__link');
    expect(link?.getAttribute('href')).toBe('#/');
    expect(link?.textContent).toBe('Go back to order coquito');
    expect(mocks.mountRequestForm).not.toHaveBeenCalled();
  });

  it('does not match #/manage/ without an id', async () => {
    setUrl('/#/manage/');
    await boot();
    expect(document.querySelector('#app .not-found')).not.toBeNull();
    expect(mocks.mountManageRequest).not.toHaveBeenCalled();
  });

  it('re-navigates on hashchange', async () => {
    setUrl('/#/');
    await boot();
    expect(mocks.mountRequestForm).toHaveBeenCalledTimes(1);

    setUrl('/#/cook');
    window.dispatchEvent(new HashChangeEvent('hashchange'));
    await flush();
    expect(mocks.mountCookView).toHaveBeenCalledTimes(1);

    setUrl('/#/missing');
    window.dispatchEvent(new HashChangeEvent('hashchange'));
    await flush();
    expect(document.querySelector('#app .not-found')).not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Auth callback
// ---------------------------------------------------------------------------
describe('main: auth callback', () => {
  it('redirects to login when there is no code or state', async () => {
    setUrl('/#/');
    await boot();
    expect(mocks.redirectToLogin).toHaveBeenCalledTimes(1);
    expect(mocks.verifyState).not.toHaveBeenCalled();
    expect(banner()).toBeNull();
  });

  it('exchanges the code and restores the saved return URL on success', async () => {
    mocks.getAndClearReturnUrl.mockReturnValue('/?batchId=b-9#/cook');
    fetchMock.mockImplementation(async (url: string) =>
      String(url).includes('/auth/callback')
        ? new Response(null, { status: 200 })
        : jsonResponse({ status: 'ok' })
    );
    setUrl('/auth/callback?code=abc&state=xyz');
    await boot();

    const exchange = fetchMock.mock.calls.find(([url]) => String(url).includes('/auth/callback'));
    expect(exchange).toBeDefined();
    const exchangeUrl = new URL(String(exchange![0]));
    expect(exchangeUrl.origin + exchangeUrl.pathname).toBe(`${API_URL}/auth/callback`);
    expect(exchangeUrl.searchParams.get('code')).toBe('abc');
    expect(exchangeUrl.searchParams.get('state')).toBe('xyz');
    expect(exchangeUrl.searchParams.get('code_verifier')).toBe('verifier-123');
    expect(exchange![1]).toEqual({ method: 'POST', credentials: 'include' });

    expect(window.location.pathname).toBe('/');
    expect(window.location.search).toBe('?batchId=b-9');
    expect(window.location.hash).toBe('#/cook');
    expect(mocks.redirectToLogin).not.toHaveBeenCalled();
    expect(banner()).toBeNull();
    expect(mocks.mountCookView).toHaveBeenCalledTimes(1);
  });

  it('falls back to / and an empty verifier when nothing was stored', async () => {
    mocks.getAndClearReturnUrl.mockReturnValue(null);
    mocks.getCodeVerifier.mockReturnValue(null);
    vi.stubEnv('VITE_API_URL', undefined);
    setUrl('/auth/callback?code=abc');
    await boot();

    const [url] = fetchMock.mock.calls[0];
    expect(String(url).startsWith('/auth/callback?')).toBe(true);
    const params = new URLSearchParams(String(url).split('?')[1]);
    expect(params.get('state')).toBe('');
    expect(params.get('code_verifier')).toBe('');
    expect(window.location.pathname).toBe('/');
    expect(window.location.search).toBe('');
    expect(mocks.mountRequestForm).toHaveBeenCalledTimes(1);
  });

  it('shows an error banner when the token exchange is rejected', async () => {
    fetchMock.mockImplementation(async (url: string) =>
      String(url).includes('/auth/callback')
        ? new Response(null, { status: 400 })
        : jsonResponse({ status: 'ok' })
    );
    setUrl('/auth/callback?code=abc&state=xyz');
    await boot();

    expect(banner()?.textContent).toContain(
      'Authentication error: token exchange failed. Please log in again.'
    );
    expect(banner()?.classList.contains('app-banner--error')).toBe(true);
    expect(mocks.getAndClearReturnUrl).not.toHaveBeenCalled();
    expect(window.location.pathname).toBe('/auth/callback');
  });

  it('shows an error banner when the auth service is unreachable', async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (String(url).includes('/auth/callback')) throw new TypeError('Failed to fetch');
      return jsonResponse({ status: 'ok' });
    });
    setUrl('/auth/callback?code=abc&state=xyz');
    await boot();

    expect(banner()?.textContent).toContain(
      'Authentication error: could not reach the auth service. Please try again.'
    );
    expect(banner()?.classList.contains('app-banner--error')).toBe(true);
    expect(mocks.getAndClearReturnUrl).not.toHaveBeenCalled();
  });

  it('shows a state-mismatch banner, strips code/state from the URL and redirects', async () => {
    mocks.verifyState.mockReturnValue(false);
    setUrl('/?state=bad&keep=1#/cook');
    await boot();

    expect(mocks.verifyState).toHaveBeenCalledWith('bad');
    expect(banner()?.textContent).toContain(
      'Authentication error: state mismatch. Please log in again.'
    );
    expect(banner()?.classList.contains('app-banner--error')).toBe(true);
    expect(window.location.search).toBe('?keep=1');
    expect(window.location.hash).toBe('#/cook');
    expect(mocks.redirectToLogin).toHaveBeenCalledTimes(1);
  });

  it('strips the query entirely when state is valid and no other params remain', async () => {
    mocks.verifyState.mockReturnValue(true);
    setUrl('/?state=good#/');
    await boot();

    expect(banner()).toBeNull();
    expect(window.location.search).toBe('');
    expect(window.location.hash).toBe('#/');
    expect(mocks.redirectToLogin).toHaveBeenCalledTimes(1);
  });
});

// ---------------------------------------------------------------------------
// Health banner
// ---------------------------------------------------------------------------
describe('main: health status banner', () => {
  it('skips the health check when VITE_API_URL is not set', async () => {
    vi.stubEnv('VITE_API_URL', '');
    await boot();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(banner()).toBeNull();
  });

  it('shows no banner when the API reports status ok', async () => {
    await boot();
    expect(fetchMock).toHaveBeenCalledWith(`${API_URL}/health`, { credentials: 'include' });
    expect(banner()).toBeNull();
  });

  it('warns when the API reports an unexpected status', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ status: 'degraded' }));
    await boot();
    expect(banner()?.textContent).toContain('API health check returned unexpected status.');
    expect(banner()?.classList.contains('app-banner--warn')).toBe(true);
  });

  it('warns when the health endpoint returns a non-OK response', async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 502 }));
    await boot();
    expect(banner()?.textContent).toContain('API is unreachable. Some features may not work.');
    expect(banner()?.classList.contains('app-banner--warn')).toBe(true);
  });

  it('stays silent on a network error', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));
    await boot();
    expect(fetchMock).toHaveBeenCalledWith(`${API_URL}/health`, { credentials: 'include' });
    expect(banner()).toBeNull();
    expect(mocks.mountRequestForm).toHaveBeenCalledTimes(1);
  });
});

// ---------------------------------------------------------------------------
// Header
// ---------------------------------------------------------------------------
describe('main: app header', () => {
  it('renders the header before #app with chef links for a chef', async () => {
    mocks.getMe.mockResolvedValue(CHEF);
    await boot();
    const header = document.querySelector('header.app-header');
    expect(header?.nextElementSibling?.id).toBe('app');
    const links = [...document.querySelectorAll('#chef-nav a')].map((a) => a.getAttribute('href'));
    expect(links).toEqual(['#/batches', '#/varieties']);
  });

  it('renders the header without chef links for a non-chef', async () => {
    mocks.getMe.mockResolvedValue(REQUESTER);
    await boot();
    expect(document.querySelector('header.app-header')).not.toBeNull();
    expect(document.getElementById('chef-nav')).toBeNull();
    expect(document.getElementById('logout-btn')).not.toBeNull();
  });

  it('keeps the header without chef links when GET /me fails', async () => {
    mocks.getMe.mockRejectedValue(new Error('unauthorized'));
    await boot();
    expect(document.querySelector('header.app-header')).not.toBeNull();
    expect(document.getElementById('chef-nav')).toBeNull();
    expect(mocks.mountRequestForm).toHaveBeenCalledTimes(1);
  });

  it('wires Log out to the auth service', async () => {
    await boot();
    document.getElementById('logout-btn')!.click();
    expect(mocks.logout).toHaveBeenCalledTimes(1);
  });
});

// ---------------------------------------------------------------------------
// apiFetch
// ---------------------------------------------------------------------------
describe('main: apiFetch', () => {
  it('prefixes string paths with VITE_API_URL and sends credentials', async () => {
    const { apiFetch } = await boot();
    fetchMock.mockClear();
    fetchMock.mockResolvedValue(jsonResponse({ ok: true }));

    const resp = await apiFetch('/api/v1/things', { method: 'PATCH' });

    expect(resp.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledWith(`${API_URL}/api/v1/things`, {
      credentials: 'include',
      method: 'PATCH',
    });
    expect(mocks.redirectToLogin).toHaveBeenCalledTimes(1); // only the startup call
    expect(banner()).toBeNull();
  });

  it('passes Request objects through unchanged', async () => {
    const { apiFetch } = await boot();
    fetchMock.mockClear();
    fetchMock.mockResolvedValue(jsonResponse({}));
    const request = new Request('https://elsewhere.test/x');

    await apiFetch(request);

    expect(fetchMock).toHaveBeenCalledWith(request, { credentials: 'include' });
  });

  it('uses an empty prefix when VITE_API_URL is unset', async () => {
    vi.stubEnv('VITE_API_URL', undefined);
    const { apiFetch } = await boot();
    fetchMock.mockClear();
    fetchMock.mockResolvedValue(jsonResponse({}));

    await apiFetch('/api/v1/me');

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/me', { credentials: 'include' });
  });

  it('redirects to login on 401', async () => {
    const { apiFetch } = await boot();
    mocks.redirectToLogin.mockClear();
    fetchMock.mockResolvedValue(new Response(null, { status: 401 }));

    const resp = await apiFetch('/api/v1/me');

    expect(resp.status).toBe(401);
    expect(mocks.redirectToLogin).toHaveBeenCalledTimes(1);
    expect(banner()).toBeNull();
  });

  it('shows a warning banner on 503', async () => {
    const { apiFetch } = await boot();
    mocks.redirectToLogin.mockClear();
    fetchMock.mockResolvedValue(new Response(null, { status: 503 }));

    const resp = await apiFetch('/api/v1/me');

    expect(resp.status).toBe(503);
    expect(banner()?.textContent).toContain('Service temporarily unavailable — please try again.');
    expect(banner()?.classList.contains('app-banner--warn')).toBe(true);
    expect(mocks.redirectToLogin).not.toHaveBeenCalled();
  });
});
