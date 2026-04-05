/**
 * Unit tests for src/services/auth.ts
 *
 * Verifies PKCE/state flow, verifyState behavior, isSessionExpired,
 * logout fetch call. Runs in jsdom environment.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';

// Mock import.meta.env before importing the module under test
vi.stubEnv('VITE_AUTH_URL', 'https://auth.coquito.gcardona.me');
vi.stubEnv('VITE_COGNITO_CLIENT_ID', 'test-client-id');

import { isSessionExpired, logout, redirectToLogin, verifyState } from '../../services/auth';

describe('auth service', () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  describe('redirectToLogin', () => {
    it('stores state and code_verifier in sessionStorage and builds a valid auth URL', async () => {
      // Capture the redirect
      let redirectedUrl = '';
      Object.defineProperty(window, 'location', {
        value: {
          ...window.location,
          origin: 'https://coquito.gcardona.me',
          set href(url: string) {
            redirectedUrl = url;
          },
          get href() {
            return 'https://coquito.gcardona.me/';
          },
        },
        writable: true,
      });

      await redirectToLogin();

      const state = sessionStorage.getItem('auth_state');
      const codeVerifier = sessionStorage.getItem('auth_code_verifier');

      expect(state).toBeTruthy();
      expect(codeVerifier).toBeTruthy();

      expect(redirectedUrl).toContain('state=');
      expect(redirectedUrl).toContain('code_challenge=');
      expect(redirectedUrl).toContain('client_id=test-client-id');
      expect(redirectedUrl).toContain('redirect_uri=');
    });
  });

  describe('verifyState', () => {
    it('returns true and clears sessionStorage when state matches', () => {
      sessionStorage.setItem('auth_state', 'matching-value');
      sessionStorage.setItem('auth_code_verifier', 'some-verifier');

      const result = verifyState('matching-value');

      expect(result).toBe(true);
      expect(sessionStorage.getItem('auth_state')).toBeNull();
      expect(sessionStorage.getItem('auth_code_verifier')).toBeNull();
    });

    it('returns false when state does not match', () => {
      sessionStorage.setItem('auth_state', 'original-state');

      const result = verifyState('wrong-value');

      expect(result).toBe(false);
    });

    it('returns false when auth_state is not in sessionStorage', () => {
      const result = verifyState('any-value');
      expect(result).toBe(false);
    });
  });

  describe('isSessionExpired', () => {
    it('returns true on a 401 Response', () => {
      const response = new Response(null, { status: 401 });
      expect(isSessionExpired(response)).toBe(true);
    });

    it('returns false on a 200 Response', () => {
      const response = new Response(null, { status: 200 });
      expect(isSessionExpired(response)).toBe(false);
    });

    it('returns false on a 403 Response', () => {
      const response = new Response(null, { status: 403 });
      expect(isSessionExpired(response)).toBe(false);
    });
  });

  describe('logout', () => {
    it('calls POST /auth/logout', async () => {
      const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue(new Response(null, { status: 200 }));

      // Prevent redirectToLogin from actually navigating
      Object.defineProperty(window, 'location', {
        value: { ...window.location, href: '' },
        writable: true,
      });

      await logout();

      expect(fetchSpy).toHaveBeenCalledWith('/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });
    });
  });
});
