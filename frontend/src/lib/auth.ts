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
  client_id?: string | null;
  store_id?: string | null;
  machine_empresa_id?: string;
  companies?: Array<{ id: string; nome: string }>;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

let accessTokenInMemory: string | null = null;
let sessionInMemory: unknown = null;

function getBaseUrl(): string {
  let rawBaseUrl = import.meta.env.VITE_API_URL || "";
  rawBaseUrl = rawBaseUrl.replace(/\/api\/v1\/?$/, "");
  rawBaseUrl = rawBaseUrl.replace(/\/$/, "");
  return rawBaseUrl;
}

export const authStorage = {
  getAccessToken(): string | null {
    return accessTokenInMemory;
  },
  setAccessToken(accessToken: string) {
    accessTokenInMemory = accessToken;
  },
  setSession(session: unknown) {
    sessionInMemory = session;
  },
  getSession<T>(): T | null {
    return (sessionInMemory as T) || null;
  },
  clearTokens() {
    accessTokenInMemory = null;
    sessionInMemory = null;
  },
};

export async function nativeLogin(email: string, password: string): Promise<AuthResponse> {
  const baseUrl = getBaseUrl();
  const res = await fetch(`${baseUrl}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: "Falha na autenticação" }));
    const errorMsg = errorData.detail || errorData.error || "Credenciais inválidas.";
    throw new Error(errorMsg);
  }

  const data: AuthResponse = await res.json();
  authStorage.setAccessToken(data.access_token);

  const sessionData = {
    success: true,
    user: data.user,
  };
  authStorage.setSession(sessionData);

  return data;
}

export async function nativeRefreshToken(): Promise<string | null> {
  try {
    const baseUrl = getBaseUrl();
    const res = await fetch(`${baseUrl}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({}),
    });

    if (!res.ok) {
      authStorage.clearTokens();
      return null;
    }

    const data = await res.json();
    if (data.access_token) {
      authStorage.setAccessToken(data.access_token);
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
        credentials: "include",
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
      authStorage.setSession(sessionData);
      return data.user;
    }
  }

  return null;
}
