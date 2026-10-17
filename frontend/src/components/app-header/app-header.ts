import './app-header.css';

/** Options for {@link renderAppHeader}. */
export interface AppHeaderOptions {
  /** When true, the chef navigation links are rendered. */
  isChef: boolean;
  /** Called when the Log out button is clicked. */
  onLogout: () => void;
}

/** Chef-only navigation links, in display order. */
const CHEF_LINKS: ReadonlyArray<{ href: string; label: string }> = [
  { href: '#/batches', label: 'Manage Batches' },
  { href: '#/varieties', label: 'Manage Varieties' },
];

/**
 * Set `aria-current="page"` on the header link whose href matches the current route
 * (the hash without its query string) and clear it from every other link.
 */
function syncCurrentLink(header: HTMLElement): void {
  const route = (window.location.hash || '#/').split('?')[0];
  header.querySelectorAll<HTMLAnchorElement>('.app-header__link').forEach((link) => {
    if (link.getAttribute('href') === route) {
      link.setAttribute('aria-current', 'page');
    } else {
      link.removeAttribute('aria-current');
    }
  });
}

/** Build the chef `<nav>` with one link per entry in {@link CHEF_LINKS}. */
function buildChefNav(): HTMLElement {
  const nav = document.createElement('nav');
  nav.id = 'chef-nav';
  nav.className = 'app-header__nav';
  nav.setAttribute('aria-label', 'Chef');
  CHEF_LINKS.forEach(({ href, label }) => {
    const link = document.createElement('a');
    link.className = 'app-header__link';
    link.href = href;
    link.textContent = label;
    nav.appendChild(link);
  });
  return nav;
}

/**
 * Add the chef navigation links to an already-rendered header, between the brand and
 * Log out. Lets the header paint before the user's role is known. Idempotent.
 */
export function showChefNav(header: HTMLElement): void {
  if (header.querySelector('#chef-nav')) return;
  header.querySelector('#logout-btn')!.before(buildChefNav());
  syncCurrentLink(header);
}

/**
 * Render the global header (brand, chef links for chefs, Log out) as a banner landmark
 * immediately before `#app`, in normal document flow so it never covers page content.
 *
 * Idempotent: if a header already exists it is returned unchanged. On first render it
 * marks the current route's link with `aria-current="page"` and keeps it in sync on
 * every `hashchange`.
 */
export function renderAppHeader({ isChef, onLogout }: AppHeaderOptions): HTMLElement {
  const existing = document.querySelector<HTMLElement>('header.app-header');
  if (existing) return existing;

  const header = document.createElement('header');
  header.className = 'app-header';

  const inner = document.createElement('div');
  inner.className = 'app-header__inner';

  const brand = document.createElement('a');
  brand.className = 'app-header__brand';
  brand.href = '#/';
  brand.textContent = 'Coquito Please';
  inner.appendChild(brand);

  const logoutBtn = document.createElement('button');
  logoutBtn.id = 'logout-btn';
  logoutBtn.type = 'button';
  logoutBtn.className = 'btn btn--secondary app-header__logout';
  logoutBtn.textContent = 'Log out';
  logoutBtn.addEventListener('click', () => onLogout());
  inner.appendChild(logoutBtn);

  header.appendChild(inner);

  document.querySelector<HTMLDivElement>('#app')!.before(header);

  if (isChef) showChefNav(header);
  syncCurrentLink(header);
  window.addEventListener('hashchange', () => syncCurrentLink(header));
  return header;
}
