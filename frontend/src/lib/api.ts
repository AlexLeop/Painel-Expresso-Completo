import { authStorage, nativeRefreshToken } from "./auth";

export async function authFetch(url: string, options: RequestInit = {}) {
  let token = authStorage.getAccessToken();

  if (!token) {
    token = await nativeRefreshToken();
  }

  if (!token) {
    if (window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
    throw new Error("Usuário não está autenticado");
  }

  const headers = new Headers(options.headers || {});
  headers.set("Authorization", `Bearer ${token}`);

  // A preferência só é enviada pelo proprietário da plataforma; o backend
  // revalida o papel e o operador em todas as operações.
  const storedSession = authStorage.getSession<any>();
  if (
    storedSession?.user?.is_platform_admin &&
    storedSession.user.company_id &&
    storedSession.user.company_id !== "global"
  ) {
    headers.set("X-Operator-Id", String(storedSession.user.company_id));
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

  if (response.status === 401) {
    const renewedToken = await nativeRefreshToken();
    if (renewedToken) {
      headers.set("Authorization", `Bearer ${renewedToken}`);
      response = await fetch(`${BASE_URL}${url}`, {
        ...options,
        headers,
        credentials: "include",
      });
    } else {
      authStorage.clearTokens();
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
      throw new Error("Sessão expirada. Faça login novamente.");
    }
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
    
    // Se a renovacao funcionou mas o endpoint respondeu 401/403, e restricao de permissao do recurso.
    // NAO limpamos tokens nem forcamos redirecionamento para /login para evitar loop infinito.
    throw new Error(customError);
  }

  return response;
}

/**
 * Retorna somente o snapshot em memória; credenciais nunca são persistidas no browser.
 */
export function getSession(): {
  basicAuth: string;
  user: Record<string, unknown>;
} | null {
  return authStorage.getSession();
}
