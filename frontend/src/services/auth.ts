/**
 * Auth service: OIDC status, login redirect, token storage, current user.
 */

const API_URL =
  typeof import.meta !== "undefined" && import.meta.env?.VITE_API_URL
    ? String(import.meta.env.VITE_API_URL).replace(/\/$/, "")
    : "";

export interface AuthStatusResponse {
  auth_enabled: boolean;
  mode: string;
  oidc_issuer?: string | null;
  ga4gh_passport_support: boolean;
  supported_providers: string[];
}

export interface AuthUser {
  sub?: string;
  email?: string;
  name?: string;
  roles?: string[];
  passports?: unknown[];
  visas?: unknown[];
}

export const authService = {
  async getStatus(): Promise<AuthStatusResponse> {
    const res = await fetch(`${API_URL}/api/v1/auth/status`);
    if (!res.ok) throw new Error("Failed to fetch auth status");
    return res.json();
  },

  login(): void {
    this.loginWithProvider("oidc");
  },

  loginWithProvider(provider: "oidc" | "google" | "microsoft"): void {
    const params = new URLSearchParams({ provider });
    window.location.href = `${API_URL}/api/v1/auth/login?${params.toString()}`;
  },

  logout(): void {
    localStorage.removeItem("access_token");
    window.location.href = "/";
  },

  getToken(): string | null {
    return localStorage.getItem("access_token");
  },

  setToken(token: string): void {
    localStorage.setItem("access_token", token);
  },

  async getMe(): Promise<AuthUser | null> {
    const token = this.getToken();
    if (!token) return null;
    const res = await fetch(`${API_URL}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return null;
    return res.json();
  },
};
