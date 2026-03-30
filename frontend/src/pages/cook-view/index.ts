import './cook-view.css';
import { getIngredientList, markIngredientAcquired, ApiRequestError } from '../../services/api';
import { createIngredientList } from '../../components/ingredient-list/ingredient-list';

// ---------------------------------------------------------------------------
// Cook View page — ingredient shopping list for the cook
// Reads cookSecret and batchId from URL query params (appended to hash)
// ---------------------------------------------------------------------------

export function mountCookView(container: HTMLElement): void {
  // Parse query params from the hash: /#/cook?batchId=xxx&cookSecret=yyy
  const search = window.location.hash.split('?')[1] ?? '';
  const params = new URLSearchParams(search);
  const cookSecret = params.get('cookSecret') ?? '';
  const batchId = params.get('batchId') ?? '';

  if (!cookSecret) {
    container.innerHTML = renderAccessDenied();
    return;
  }

  container.innerHTML = renderLoading();

  getIngredientList(batchId, cookSecret)
    .then((data) => {
      container.innerHTML = '';

      const page = document.createElement('div');
      page.className = 'cook-page';

      // Header
      page.insertAdjacentHTML(
        'beforeend',
        `<header class="cook-header">
          <p class="cook-header__eyebrow">El arte del coquito</p>
          <h1 class="cook-header__title">${escapeHtml(data.batchName)}</h1>
          <p class="cook-header__subtitle">${data.totalConfirmedRequests} confirmed orders</p>
        </header>`
      );

      // Preview banner
      if (!data.isFinalized) {
        const banner = document.createElement('div');
        banner.className = 'preview-banner';
        banner.setAttribute('role', 'alert');
        banner.dataset.cy = 'preview-banner';
        banner.textContent = 'PREVIEW — subject to change until the cut-off date passes';
        page.appendChild(banner);
      }

      // Main content
      const main = document.createElement('main');
      main.className = 'cook-main';

      const list = createIngredientList({
        byVariety: data.byVariety,
        totals: data.totals,
        onToggleAcquired: (ingredientId, acquired) => {
          markIngredientAcquired(batchId, ingredientId, acquired, cookSecret).catch(() => {
            // best-effort; checkbox state already updated optimistically
          });
        },
      });

      main.appendChild(list);
      page.appendChild(main);
      container.appendChild(page);
    })
    .catch((err: unknown) => {
      if (err instanceof ApiRequestError && err.status === 401) {
        container.innerHTML = renderAccessDenied();
      } else {
        container.innerHTML = `
          <div class="page-wrapper">
            <div class="card form-error" role="alert">
              Oops! No se pudo cargar la lista. Please try again later.
            </div>
          </div>`;
      }
    });
}

function renderLoading(): string {
  return `
    <div class="page-wrapper" style="text-align:center; padding-top:4rem;">
      <p>Cargando la lista de ingredientes… 🥥</p>
    </div>`;
}

function renderAccessDenied(): string {
  return `
    <div class="page-wrapper">
      <div class="access-denied-card" data-cy="access-denied">
        <div class="access-denied-card__icon" aria-hidden="true">🔒</div>
        <h1 class="access-denied-card__heading">Access Denied</h1>
        <p>This page requires a valid cook secret. Please use the link provided by el jefe del coquito.</p>
      </div>
    </div>`;
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
