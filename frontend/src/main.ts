import './styles/global.css';

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

// Initial render + listen for hash changes
window.addEventListener('hashchange', () => {
  navigate();
});

navigate();
