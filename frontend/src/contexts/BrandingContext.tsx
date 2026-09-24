import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";
import {
  BrandingFull,
  DEFAULT_BRANDING,
  fetchBranding,
  fetchPublicBranding,
  updateBranding as apiUpdateBranding,
} from "../services/branding";
import { useAuth } from "./AuthContext";

interface BrandingContextType {
  branding: BrandingFull;
  isLoading: boolean;
  refreshBranding: () => Promise<void>;
  updateCustomBranding: (payload: Partial<BrandingFull>) => Promise<BrandingFull>;
}

const BrandingContext = createContext<BrandingContextType | undefined>(undefined);

export function BrandingProvider({ children }: { children: React.ReactNode }) {
  const { session } = useAuth();
  const [branding, setBranding] = useState<BrandingFull>(DEFAULT_BRANDING);
  const [isLoading, setIsLoading] = useState(true);
  const requestVersion = useRef(0);

  // Aplica as variáveis CSS e favicon no documento
  const applyBrandingToDOM = useCallback((b: BrandingFull) => {
    const root = document.documentElement;

    root.style.setProperty("--brand-primary", b.color_primary);
    root.style.setProperty("--brand-secondary", b.color_secondary);
    root.style.setProperty("--brand-accent", b.color_accent);
    root.style.setProperty("--brand-bg", b.color_background);
    root.style.setProperty("--brand-surface", b.color_surface);
    root.style.setProperty("--brand-text", b.color_text);
    root.style.setProperty("--brand-dark-bg", b.dark_color_background);
    root.style.setProperty("--brand-dark-surface", b.dark_color_surface);
    root.style.setProperty("--brand-dark-text", b.dark_color_text);

    // Gerencia tema claro/escuro
    if (b.theme_mode === "dark") {
      root.setAttribute("data-theme", "dark");
    } else if (b.theme_mode === "light") {
      root.removeAttribute("data-theme");
    } else if (b.theme_mode === "auto") {
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      if (prefersDark) {
        root.setAttribute("data-theme", "dark");
      } else {
        root.removeAttribute("data-theme");
      }
    }

    // Favicon dinâmico
    let link = document.querySelector("link[rel~='icon']") as HTMLLinkElement | null;
    if (!link) {
      link = document.createElement("link");
      link.rel = "icon";
      document.head.appendChild(link);
    }
    link.href = b.favicon_url || "/favicon.ico";

    // Título da página
    document.title = `${b.brand_name || DEFAULT_BRANDING.brand_name} - Painel Logístico`;
  }, []);

  const loadBranding = useCallback(async () => {
    const version = ++requestVersion.current;
    setIsLoading(true);
    try {
      if (session?.user) {
        // Usuário autenticado: busca branding completo
        const data = await fetchBranding();
        if (version !== requestVersion.current) return;
        setBranding(data);
        applyBrandingToDOM(data);
      } else {
        // Usuário não autenticado: verifica se há slug na URL (ex: ?op=slug)
        const params = new URLSearchParams(window.location.search);
        const opSlug = params.get("op");

        if (opSlug) {
          const pub = await fetchPublicBranding(opSlug);
          if (pub) {
            const merged: BrandingFull = {
              ...DEFAULT_BRANDING,
              brand_name: pub.brand_name,
              logo_url: pub.logo_url,
              favicon_url: pub.favicon_url,
              color_primary: pub.color_primary,
              color_secondary: pub.color_secondary,
              color_accent: pub.color_accent,
              theme_mode: pub.theme_mode,
            };
            if (version !== requestVersion.current) return;
            setBranding(merged);
            applyBrandingToDOM(merged);
            return;
          }
        }

        // Sem slug ou não encontrado: usa padrão
        if (version !== requestVersion.current) return;
        setBranding(DEFAULT_BRANDING);
        applyBrandingToDOM(DEFAULT_BRANDING);
      }
    } catch (err) {
      console.warn("Erro ao inicializar branding:", err);
      if (version !== requestVersion.current) return;
      setBranding(DEFAULT_BRANDING);
      applyBrandingToDOM(DEFAULT_BRANDING);
    } finally {
      if (version === requestVersion.current) setIsLoading(false);
    }
  }, [session, applyBrandingToDOM]);

  useEffect(() => {
    loadBranding();
  }, [loadBranding]);

  useEffect(() => {
    if (branding.theme_mode !== "auto") return;
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const syncTheme = () => {
      document.documentElement.toggleAttribute("data-theme", media.matches);
    };
    media.addEventListener("change", syncTheme);
    return () => media.removeEventListener("change", syncTheme);
  }, [branding.theme_mode]);

  const updateCustomBranding = async (payload: Partial<BrandingFull>): Promise<BrandingFull> => {
    const updated = await apiUpdateBranding(payload);
    setBranding(updated);
    applyBrandingToDOM(updated);
    return updated;
  };

  return (
    <BrandingContext.Provider
      value={{
        branding,
        isLoading,
        refreshBranding: loadBranding,
        updateCustomBranding,
      }}
    >
      {children}
    </BrandingContext.Provider>
  );
}

export function useBranding(): BrandingContextType {
  const context = useContext(BrandingContext);
  if (!context) {
    throw new Error("useBranding must be used within a BrandingProvider");
  }
  return context;
}
