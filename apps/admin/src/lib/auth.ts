/**
 * Unified authentication management for frontend.
 *
 * Consolidates authentication logic from multiple sources:
 * - services/incidents.ts (getAdminToken, getAuthHeaders)
 * - services/logs.ts (getAdminToken, AUTH_HEADER)
 * - lib/http.ts (token handling)
 *
 * Provides single source of truth for auth operations.
 */

/**
 * Authentication token manager.
 * Centralizes token retrieval logic from different storage sources.
 */
export const authManager = {
  /**
   * Gets the admin authentication token from storage.
   * Checks sessionStorage first (admin), then localStorage (fallback).
   *
   * This replaces duplicate getAdminToken implementations.
   */
  getToken(): string | null {
    if (typeof window === 'undefined') return null;

    return (
      sessionStorage.getItem('access_token_admin') ||
      localStorage.getItem('access_token')
    );
  },

  /**
   * Sets the authentication token in appropriate storage.
   * Uses sessionStorage for admin tokens, localStorage for regular tokens.
   */
  setToken(token: string, isAdmin: boolean = false): void {
    if (typeof window === 'undefined') return;

    if (isAdmin) {
      sessionStorage.setItem('access_token_admin', token);
    } else {
      localStorage.setItem('access_token', token);
    }
  },

  /**
   * Clears all authentication tokens.
   */
  clearTokens(): void {
    if (typeof window === 'undefined') return;

    sessionStorage.removeItem('access_token_admin');
    localStorage.removeItem('access_token');
  },

  /**
   * Checks if user is authenticated.
   */
  isAuthenticated(): boolean {
    return this.getToken() !== null;
  },

  /**
   * Gets authentication headers for API requests.
   * Standardizes header format across all services.
   *
   * This replaces duplicate getAuthHeaders implementations.
   */
  getHeaders(contentType: string = 'application/json'): Record<string, string> {
    const token = this.getToken();
    const headers: Record<string, string> = {};

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    if (contentType) {
      headers['Content-Type'] = contentType;
    }

    return headers;
  },

  /**
   * Gets headers for admin-specific requests.
   * Ensures admin token is used when available.
   */
  getAdminHeaders(contentType: string = 'application/json'): Record<string, string> {
    if (typeof window === 'undefined') return {};

    const adminToken = sessionStorage.getItem('access_token_admin');
    const headers: Record<string, string> = {};

    if (adminToken) {
      headers['Authorization'] = `Bearer ${adminToken}`;
    }

    if (contentType) {
      headers['Content-Type'] = contentType;
    }

    return headers;
  },

  /**
   * Refresh token handler placeholder.
   * This should be connected to the actual refresh mechanism.
   */
  async refreshToken(): Promise<string | null> {
    // This would integrate with the actual token refresh endpoint
    // For now, returns the current token if available
    return this.getToken();
  }
};

/**
 * Legacy exports for backward compatibility.
 * These maintain the old API while using the new unified implementation.
 */
export const getAdminToken = () => authManager.getToken();
export const getAuthHeaders = () => authManager.getHeaders();
export const AUTH_HEADER = () => authManager.getHeaders();

/**
 * Authentication context type definitions.
 */
export interface AuthContext {
  token: string | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  user: any | null;
}

/**
 * Hook for accessing authentication context.
 * This would typically integrate with React Context or state management.
 */
export const useAuth = (): AuthContext => {
  const token = authManager.getToken();
  const isAdmin = typeof window !== 'undefined' && sessionStorage.getItem('access_token_admin') !== null;

  return {
    token,
    isAuthenticated: token !== null,
    isAdmin,
    user: null // This would be populated from token claims or user profile
  };
};
