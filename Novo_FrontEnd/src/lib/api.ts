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

  // When deployed together, frontend and backend are on the same domain — use relative URLs
  const BASE_URL = import.meta.env.VITE_API_URL || "";

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${url}`, {
      ...options,
      headers,
      credentials: "include",
    });
  } catch (error) {
    console.error("Network Error no global authFetch:", error);
    // Aqui garantimos a resiliência no React exibindo um erro que não quebra o sistema silenciosamente
    throw new Error("Erro de conexão. Verifique sua internet ou tente novamente mais tarde.");
  }

  if (response.status === 401) {
    localStorage.removeItem("nevesgo:session");
    if (window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
    throw new Error("Sessão expirada ou acesso negado (401).");
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
