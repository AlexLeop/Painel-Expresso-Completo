import { supabase } from "./supabase";

export async function authFetch(url: string, options: RequestInit = {}) {
  const { data: sessionData, error } = await supabase.auth.getSession();
  const token = sessionData?.session?.access_token;

  if (!token) {
    if (window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
    throw new Error("Usuário não está autenticado");
  }

  const headers = new Headers(options.headers || {});
  headers.set("Authorization", `Bearer ${token}`);

  // Injetar X-Tenant-Id buscando do localStorage, caso a API precise
  const storedSessionStr = localStorage.getItem("nevesgo:session");
  if (storedSessionStr) {
    try {
      const storedSession = JSON.parse(storedSessionStr);
      if (storedSession?.user?.company_id) {
        headers.set("X-Tenant-Id", String(storedSession.user.company_id));
      }
      if (storedSession?.user?.role) {
        headers.set("X-User-Role", storedSession.user.role);
      }
      if (storedSession?.user?.email) {
        headers.set("X-User-Email", storedSession.user.email);
      }
    } catch (e) {
      // Ignora erro de parse
    }
  }

  if (
    options.body &&
    (!options.headers ||
      !(options.headers as Record<string, string>)["Content-Type"])
  ) {
    headers.set("Content-Type", "application/json");
  }

  // Sanitize VITE_API_URL to strip trailing slash or `/api/v1` suffix
  // so that authFetch("/api/...") works correctly and doesn't duplicate paths
  let rawBaseUrl = import.meta.env.VITE_API_URL || "";
  rawBaseUrl = rawBaseUrl.replace(/\/api\/v1\/?$/, ""); // strip /api/v1 or /api/v1/
  rawBaseUrl = rawBaseUrl.replace(/\/$/, ""); // strip any trailing slash
  const BASE_URL = rawBaseUrl;

  let response: Response;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000); // 15s timeout

  try {
    response = await fetch(`${BASE_URL}${url}`, {
      ...options,
      headers,
      credentials: "include",
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
  } catch (error: any) {
    clearTimeout(timeoutId);
    console.error("Network Error no global authFetch:", error);
    
    let errorMessage = "Erro de conexão. Verifique sua internet ou tente novamente mais tarde.";
    if (error.name === "AbortError") {
      errorMessage = "A requisição demorou muito para responder (Timeout).";
    }

    // Dispatch custom event for global toast
    window.dispatchEvent(
      new CustomEvent("nevesgo:network-error", { detail: errorMessage })
    );

    // Aqui garantimos a resiliência no React exibindo um erro que não quebra o sistema silenciosamente
    throw new Error(errorMessage);
  }

  if (response.status === 401 || response.status === 403) {
    const is403 = response.status === 403;
    let customError = "Sessão expirada ou acesso negado (401).";
    
    if (is403 || response.status === 401) {
      try {
        const errorData = await response.clone().json();
        console.error("403/401 Payload do Backend:", errorData);
        if (errorData.error) customError = errorData.error;
        if (errorData.detail) customError = errorData.detail;
      } catch (e) {
        // Fallback
        customError = is403 ? "Acesso negado. Sua conta não possui permissões no sistema." : "Token inválido ou expirado.";
      }
      window.dispatchEvent(new CustomEvent("nevesgo:network-error", { detail: customError }));
    }
    
    localStorage.removeItem("nevesgo:session");
    if (window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
    throw new Error(customError);
  }

  return response;
}

/**
 * Returns the parsed session object from localStorage, or null if not authenticated.
 */
export function getSession(): {
  basicAuth: string;
  user: Record<string, unknown>;
} | null {
  const sessionString = localStorage.getItem("nevesgo:session");
  if (!sessionString) return null;
  try {
    return JSON.parse(sessionString);
  } catch {
    return null;
  }
}
