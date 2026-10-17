/** Visual severity of a banner; maps to the `.app-banner--warn` / `--error` modifiers. */
export type BannerType = 'warn' | 'error';

/**
 * Show a dismissible page-level notice as the first child of `<body>`, above the app
 * header and in normal document flow, so it pushes content down instead of covering it.
 * Any banner already showing is replaced. The message is rendered as plain text.
 */
export function showBanner(message: string, type: BannerType = 'warn'): void {
  document.getElementById('app-banner')?.remove();

  const banner = document.createElement('div');
  banner.id = 'app-banner';
  banner.className = `app-banner app-banner--${type}`;
  banner.setAttribute('role', 'alert');

  const text = document.createElement('span');
  text.textContent = message;

  const close = document.createElement('button');
  close.type = 'button';
  close.className = 'app-banner__close';
  close.setAttribute('aria-label', 'Dismiss');
  close.textContent = '×';
  close.addEventListener('click', () => banner.remove());

  banner.append(text, close);
  document.body.prepend(banner);
}
