import { authFetch } from "../lib/api";

export interface BrandingPublic {
  brand_name: string;
  logo_url: string | null;
  favicon_url: string | null;
  color_primary: string;
  color_secondary: string;
  color_accent: string;
  theme_mode: "light" | "dark" | "auto";
}

export interface BrandingFull {
  id?: string;
  operator_id?: string;
  brand_name: string;
  logo_url: string | null;
  favicon_url: string | null;
  color_primary: string;
  color_secondary: string;
  color_accent: string;
  color_background: string;
  color_surface: string;
  color_text: string;
  dark_color_background: string;
  dark_color_surface: string;
  dark_color_text: string;
  theme_mode: "light" | "dark" | "auto";
}

export const DEFAULT_BRANDING: BrandingFull = {
  brand_name: "Expresso Neves",
  logo_url: null,
  favicon_url: null,
  color_primary: "#E55C00",
  color_secondary: "#4f46e5",
  color_accent: "#f59e0b",
  color_background: "#F9F9FA",
  color_surface: "#ffffff",
  color_text: "#18181b",
  dark_color_background: "#0a0a0a",
  dark_color_surface: "#171717",
  dark_color_text: "#fafafa",
  theme_mode: "light",
};

function getBaseUrl(): string {
  let rawBaseUrl = import.meta.env.VITE_API_URL || "";
  rawBaseUrl = rawBaseUrl.replace(/\/api\/v1\/?$/, "");
  rawBaseUrl = rawBaseUrl.replace(/\/$/, "");
  return rawBaseUrl;
}

export async function fetchPublicBranding(slug: string): Promise<BrandingPublic | null> {
  if (!slug) return null;
  try {
    const baseUrl = getBaseUrl();
    const res = await fetch(`${baseUrl}/api/v1/branding/public/${encodeURIComponent(slug)}`);
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.warn("Erro ao buscar branding público:", err);
    return null;
  }
}

export async function fetchBranding(): Promise<BrandingFull> {
  try {
    const res = await authFetch("/api/v1/branding/");
    if (!res.ok) {
      return DEFAULT_BRANDING;
    }
    const data = await res.json();
    return { ...DEFAULT_BRANDING, ...data };
  } catch (err) {
    console.warn("Erro ao carregar branding autenticado:", err);
    return DEFAULT_BRANDING;
  }
}

export async function updateBranding(payload: Partial<BrandingFull>): Promise<BrandingFull> {
  const res = await authFetch("/api/v1/branding/", {
    method: "PUT",
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || err.detail || "Erro ao atualizar personalização de marca.");
  }

  return await res.json();
}

export async function uploadBrandingLogo(file: File): Promise<string> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await authFetch("/api/v1/branding/logo", {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Erro no upload do logo.");
  }

  const data = await res.json();
  return data.logo_url;
}

export async function uploadBrandingFavicon(file: File): Promise<string> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await authFetch("/api/v1/branding/favicon", {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Erro no upload do favicon.");
  }

  const data = await res.json();
  return data.favicon_url;
}
