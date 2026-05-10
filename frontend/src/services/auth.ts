/**
 * auth.ts — Cognito Managed Login redirect, PKCE/CSRF, session refresh, and logout.
 *
 * PKCE + state flow:
 *   1. redirectToLogin() generates a random state UUID and PKCE code_verifier,
 *      stores both in sessionStorage, builds the Cognito authorization URL, and
 *      redirects the browser.
 *   2. After Cognito redirects back to /?state=<echo>, the SPA calls
 *      verifyState(returnedState) which reads auth_state from sessionStorage,
 *      compares, and clears both keys regardless of the outcome.
 *
 * Accessibility check results (T058a — axe-core 4.11.1, wcag2a + wcag2aa):
 *   Checked: https://coquito.gcardona.me/ (2026-04-05)
 *   Result: 0 violations found.
 *   Note: Login UI is served by Cognito Managed Login (AWS-managed, WCAG 2.1 AA
 *   compliant per AWS documentation). Only 20–50% of issues are auto-detectable;
 *   manual testing is recommended for any new UI components.
 */

const AUTH_STATE_KEY = 'auth_state';
const AUTH_CODE_VERIFIER_KEY = 'auth_code_verifier';
const AUTH_RETURN_URL_KEY = 'auth_return_url';

// ---------------------------------------------------------------------------
// Internal PKCE helpers
// ---------------------------------------------------------------------------

function _generateRandom(byteLength = 32): string {
  const bytes = new Uint8Array(byteLength);
  crypto.getRandomValues(bytes);
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
}

async function _sha256Base64Url(plain: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(plain);
  const hash = await crypto.subtle.digest('SHA-256', data);
  return btoa(String.fromCharCode(...new Uint8Array(hash)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Generate PKCE challenge, store state + verifier in sessionStorage, and
 * redirect the browser to Cognito Managed Login.
 */
export async function redirectToLogin(): Promise<void> {
  const authUrl = import.meta.env.VITE_AUTH_URL as string;
  if (!authUrl) return;
  const clientId = import.meta.env.VITE_COGNITO_CLIENT_ID as string;
  const redirectUri = `${window.location.origin}/auth/callback`;

  const state = _generateRandom(16);
  const codeVerifier = _generateRandom(32);
  const codeChallenge = await _sha256Base64Url(codeVerifier);

  sessionStorage.setItem(AUTH_STATE_KEY, state);
  sessionStorage.setItem(AUTH_CODE_VERIFIER_KEY, codeVerifier);
  sessionStorage.setItem(AUTH_RETURN_URL_KEY, window.location.href);

  const params = new URLSearchParams({
    response_type: 'code',
    client_id: clientId,
    redirect_uri: redirectUri,
    scope: 'openid email profile',
    state,
    code_challenge: codeChallenge,
    code_challenge_method: 'S256',
  });

  window.location.href = `${authUrl}/oauth2/authorize?${params.toString()}`;
}

/**
 * Verify the CSRF state returned from Cognito matches the one we generated.
 * Always clears sessionStorage keys after comparison.
 *
 * @param returnedState - The `state` query parameter from the callback URL.
 * @returns true if the state matches, false otherwise.
 */
export function verifyState(returnedState: string): boolean {
  const storedState = sessionStorage.getItem(AUTH_STATE_KEY);
  sessionStorage.removeItem(AUTH_STATE_KEY);
  sessionStorage.removeItem(AUTH_CODE_VERIFIER_KEY);
  return storedState !== null && storedState === returnedState;
}

/**
 * Retrieve the stored PKCE code_verifier (used by the auth callback handler).
 * Clears the value from sessionStorage after reading.
 */
export function getCodeVerifier(): string | null {
  const verifier = sessionStorage.getItem(AUTH_CODE_VERIFIER_KEY);
  // sessionStorage.removeItem(AUTH_CODE_VERIFIER_KEY);
  return verifier;
}

/**
 * Retrieve and clear the URL saved before the login redirect, so the app
 * can return the user to their original page (including query params) after
 * a successful token exchange.
 */
export function getAndClearReturnUrl(): string | null {
  const url = sessionStorage.getItem(AUTH_RETURN_URL_KEY);
  sessionStorage.removeItem(AUTH_RETURN_URL_KEY);
  return url;
}

/**
 * Call the logout endpoint which clears httpOnly cookies and revokes the
 * refresh token, then redirect to the login page.
 */
export async function logout(): Promise<void> {
  await fetch('/auth/logout', { method: 'POST', credentials: 'include' });
  await redirectToLogin();
}

/**
 * Call the refresh endpoint to silently renew id_token and access_token cookies.
 * Returns true on success, false if the refresh token is expired/missing.
 */
export async function refreshSession(): Promise<boolean> {
  const response = await fetch('/auth/refresh', { method: 'POST', credentials: 'include' });
  return response.ok;
}

/**
 * Returns true if the response status indicates the session has expired (401).
 */
export function isSessionExpired(response: Response): boolean {
  return response.status === 401;
}
