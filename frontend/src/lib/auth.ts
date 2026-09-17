/**
 * Native Authentication Client
 * Replaces Supabase Auth with direct calls to Django Ninja Native Auth API.
 */

export interface User {
  id?: string;
  email: string;
  name: string;
  role: string;
  is_platform_admin?: boolean;
  company_id: string;
  operator_id?: string | null;
  machine_empresa_id?: string;
  companies?: Array<{ id: string; nome: string }>;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

const ACCESS_TOKEN_KEY = "nevesgo:access_token";
const REFRESH_TOKEN_KEY = "nevesgo:refresh_token";
const SESSION_KEY = "nevesgo:session";

function getBaseUrl(): string {
  let rawBaseUrl = import.meta.env.VITE_API_URL || "";
  rawBaseUrl = rawBaseUrl.replace(/\/api\/v1\/?$/, "");
  rawBaseUrl = rawBaseUrl.replace(/\/$/, "");
  return rawBaseUrl;
}

export const authStorage = {
  getAccessToken(): string | null {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  },
  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },
  setTokens(accessToken: string, refreshToken?: string) {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    if (refreshToken) {
      localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    }
  },
  clearTokens() {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(SESSION_KEY);
  },
};

export async function nativeLogin(email: string, password: string): Promise<AuthResponse> {
  const baseUrl = getBaseUrl();
  const res = await fetch(`${baseUrl}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: "Falha na autenticação" }));
    const errorMsg = errorData.detail || errorData.error || "Credenciais inválidas.";
    throw new Error(errorMsg);
  }

  const data: AuthResponse = await res.json();
  authStorage.setTokens(data.access_token, data.refresh_token);

  const sessionData = {
    success: true,
    user: data.user,
  };
  localStorage.setItem(SESSION_KEY, JSON.stringify(sessionData));

  return data;
}

export async function nativeRefreshToken(): Promise<string | null> {
  const refreshToken = authStorage.getRefreshToken();
  if (!refreshToken) {
    authStorage.clearTokens();
    return null;
  }

  try {
    const baseUrl = getBaseUrl();
    const res = await fetch(`${baseUrl}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!res.ok) {
      authStorage.clearTokens();
      return null;
    }

    const data = await res.json();
    if (data.access_token) {
      authStorage.setTokens(data.access_token);
      return data.access_token;
    }
  } catch {
    authStorage.clearTokens();
    return null;
  }

  return null;
}

export async function nativeLogout(): Promise<void> {
  const token = authStorage.getAccessToken();
  const baseUrl = getBaseUrl();

  if (token) {
    try {
      await fetch(`${baseUrl}/api/auth/logout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });
    } catch {
      // Ignora erro no logout remoto
    }
  }

  authStorage.clearTokens();
}

export async function fetchCurrentProfile(): Promise<User | null> {
  const token = authStorage.getAccessToken();
  if (!token) return null;

  const baseUrl = getBaseUrl();
  let res = await fetch(`${baseUrl}/api/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  // Se o access_token expirou, tenta refresh
  if (res.status === 401) {
    const newToken = await nativeRefreshToken();
    if (!newToken) return null;

    res = await fetch(`${baseUrl}/api/auth/me`, {
      headers: { Authorization: `Bearer ${newToken}` },
    });
  }

  if (res.ok) {
    const data = await res.json();
    if (data.authenticated && data.user) {
      const sessionData = {
        success: true,
        user: data.user,
      };
      localStorage.setItem(SESSION_KEY, JSON.stringify(sessionData));
      return data.user;
    }
  }

  return null;
}
