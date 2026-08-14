/**
 * Auth service: OIDC status, login redirect, cookie session (no localStorage tokens).
 */

const API_URL =
  typeof import.meta !== "undefined" && import.meta.env?.VITE_API_URL
    ? String(import.meta.env.VITE_API_URL).replace(/\/$/, "")
    : "";

const fetchOpts: RequestInit = { credentials: "include" };

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
  isolation_mode?: "user" | "team" | "open";
  team_id?: string;
  scope?: Record<string, string>;
}

export const authService = {
  async getStatus(): Promise<AuthStatusResponse> {
    const res = await fetch(`${API_URL}/api/v1/auth/status`, fetchOpts);
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

  async logout(): Promise<void> {
    try {
      await fetch(`${API_URL}/api/v1/auth/logout`, {
        ...fetchOpts,
        method: "POST",
      });
    } finally {
      window.location.href = "/login";
    }
  },

  async getMe(): Promise<AuthUser | null> {
    const res = await fetch(`${API_URL}/api/v1/auth/me`, fetchOpts);
    if (!res.ok) return null;
    return res.json();
  },
};
