import './styles/global.css';
import { isSessionExpired, logout, redirectToLogin, verifyState } from './services/auth';

// ---------------------------------------------------------------------------
// Hash-based router
// Routes:
//   #/             → request-form page
//   #/manage/:id   → manage-request page
//   #/cook         → cook-view page
//   (anything else) → 404
// ---------------------------------------------------------------------------

interface Route {
  pattern: RegExp;
  render: (params: Record<string, string>) => Promise<void>;
}

const appEl = document.querySelector<HTMLDivElement>('#app')!;

async function renderRequestForm(_params: Record<string, string>): Promise<void> {
  const { mountRequestForm } = await import('./pages/request-form/index');
  appEl.innerHTML = '';
  mountRequestForm(appEl);
}

async function renderManageRequest(params: Record<string, string>): Promise<void> {
  const { mountManageRequest } = await import('./pages/manage-request/index');
  appEl.innerHTML = '';
  mountManageRequest(appEl, params['id'] ?? '');
}

async function renderCookView(_params: Record<string, string>): Promise<void> {
  const { mountCookView } = await import('./pages/cook-view/index');
  appEl.innerHTML = '';
  mountCookView(appEl);
}

function renderNotFound(): void {
  appEl.innerHTML = `
    <div class="page-wrapper">
      <div class="card" style="text-align:center; margin-top: 4rem;">
        <h1>¡Ay, bendito!</h1>
        <p>That page doesn't exist. <a href="#/">Go back to order coquito</a>.</p>
      </div>
    </div>
  `;
}

const routes: Route[] = [
  {
    pattern: /^#\/$/,
    render: renderRequestForm,
  },
  {
    pattern: /^#\/manage\/([^/]+)$/,
    render: (params) => renderManageRequest(params),
  },
  {
    pattern: /^#\/cook$/,
    render: renderCookView,
  },
];

function parseHash(hash: string): { route: Route; params: Record<string, string> } | null {
  const normalized = hash || '#/';
  // Strip query string before matching routes (query params are parsed by individual pages)
  const pathOnly = normalized.split('?')[0];

  for (const route of routes) {
    const match = pathOnly.match(route.pattern);
    if (match) {
      const params: Record<string, string> = {};
      // manage route captures id at index 1
      if (match[1]) params['id'] = match[1];
      return { route, params };
    }
  }
  return null;
}

async function navigate(): Promise<void> {
  const hash = window.location.hash || '#/';
  const result = parseHash(hash);

  if (result) {
    await result.route.render(result.params);
  } else {
    renderNotFound();
  }
}

// ---------------------------------------------------------------------------
// API fetch wrapper — handles 401 (session expired) and 503 (service down)
// ---------------------------------------------------------------------------
export async function apiFetch(input: RequestInfo, init?: RequestInit): Promise<Response> {
  const apiUrl = (import.meta.env.VITE_API_URL as string | undefined) ?? '';
  const url = typeof input === 'string' ? `${apiUrl}${input}` : input;
  const response = await fetch(url, { credentials: 'include', ...init });

  if (isSessionExpired(response)) {
    await redirectToLogin();
    // redirectToLogin navigates away; return the response for callers that need it
  } else if (response.status === 503) {
    showBanner('Service temporarily unavailable — please try again.', 'warn');
  }

  return response;
}

// ---------------------------------------------------------------------------
// Auth: CSRF state verification on callback return
// ---------------------------------------------------------------------------
function handleAuthCallback(): void {
  const params = new URLSearchParams(window.location.search);
  const returnedState = params.get('state');

  if (returnedState !== null) {
    const valid = verifyState(returnedState);
    if (!valid) {
      showBanner('Authentication error: state mismatch. Please log in again.', 'error');
    }
    // Remove ?state= from URL without reload
    const cleanUrl = window.location.pathname + window.location.hash;
    history.replaceState(null, '', cleanUrl);
  }
}

// ---------------------------------------------------------------------------
// Health status banner (T030)
// ---------------------------------------------------------------------------
async function showHealthStatus(): Promise<void> {
  const apiUrl = (import.meta.env.VITE_API_URL as string | undefined) ?? '';
  if (!apiUrl) return;

  try {
    const resp = await fetch(`${apiUrl}/health`, { credentials: 'include' });
    if (resp.ok) {
      const data = (await resp.json()) as { status?: string };
      if (data.status !== 'ok') {
        showBanner('API health check returned unexpected status.', 'warn');
      }
    } else {
      showBanner('API is unreachable. Some features may not work.', 'warn');
    }
  } catch {
    // No network or API not deployed yet — silent in development
  }
}

// ---------------------------------------------------------------------------
// Utility: show a dismissible notification banner
// ---------------------------------------------------------------------------
function showBanner(message: string, type: 'warn' | 'error' = 'warn'): void {
  const existing = document.getElementById('app-banner');
  if (existing) existing.remove();

  const banner = document.createElement('div');
  banner.id = 'app-banner';
  banner.style.cssText = [
    'position:fixed;top:0;left:0;right:0;z-index:9999;padding:0.75rem 1rem',
    'display:flex;align-items:center;justify-content:space-between',
    `background:${type === 'error' ? '#c0392b' : '#e67e22'};color:#fff;font-size:0.9rem`,
  ].join(';');
  banner.innerHTML = `<span>${message}</span><button onclick="this.parentElement.remove()" style="background:none;border:none;color:#fff;font-size:1.25rem;cursor:pointer;padding:0 0.5rem">×</button>`;
  document.body.prepend(banner);
}

// ---------------------------------------------------------------------------
// Logout button: injected into the app root after initial render
// ---------------------------------------------------------------------------
function renderLogoutButton(): void {
  if (document.getElementById('logout-btn')) return;

  const btn = document.createElement('button');
  btn.id = 'logout-btn';
  btn.textContent = 'Log out';
  btn.style.cssText =
    'position:fixed;bottom:1rem;right:1rem;padding:0.5rem 1rem;cursor:pointer;z-index:9998';
  btn.addEventListener('click', () => logout());
  document.body.appendChild(btn);
}

// ---------------------------------------------------------------------------
// Startup
// ---------------------------------------------------------------------------
handleAuthCallback();
showHealthStatus();
renderLogoutButton();

// Initial render + listen for hash changes
window.addEventListener('hashchange', () => {
  navigate();
});

navigate();
