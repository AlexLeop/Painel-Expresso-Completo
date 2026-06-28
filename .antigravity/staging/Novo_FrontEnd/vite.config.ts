import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import path from "path";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  // Load env from both current dir AND parent dir (where .env.local lives)
  const envLocal = loadEnv(mode, "..", ""); // parent = platform/
  const envFrontend = loadEnv(mode, ".", ""); // current = Novo_FrontEnd/
  const env = { ...envLocal, ...envFrontend };

  // Map NEXT_PUBLIC_* → VITE_* for Supabase (Vercel only sets NEXT_PUBLIC_ vars)
  const supabaseUrl =
    env.VITE_SUPABASE_URL ||
    env.NEXT_PUBLIC_SUPABASE_URL ||
    process.env.VITE_SUPABASE_URL ||
    process.env.NEXT_PUBLIC_SUPABASE_URL ||
    "";
  const supabaseAnonKey =
    env.VITE_SUPABASE_ANON_KEY ||
    env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
    process.env.VITE_SUPABASE_ANON_KEY ||
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
    "";

  return {
    plugins: [react(), tailwindcss()],
    // Default base path for standalone deployment
    base: "/",
    // Default build output (dist)
    build: {
      outDir: "dist",
      emptyOutDir: false, // Don't empty outDir completely because esbuild might run concurrently or after and we want both
      // Generate manifest for cache busting
      manifest: true,
    },
    define: {
      "import.meta.env.VITE_SUPABASE_URL": JSON.stringify(supabaseUrl),
      "import.meta.env.VITE_SUPABASE_ANON_KEY": JSON.stringify(supabaseAnonKey),
      "process.env.GEMINI_API_KEY": JSON.stringify(env.GEMINI_API_KEY),
      "process.env.GOOGLE_MAPS_PLATFORM_KEY": JSON.stringify(
        env.GOOGLE_MAPS_PLATFORM_KEY || "",
      ),
    },
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      hmr: process.env.DISABLE_HMR !== "true",
      watch: process.env.DISABLE_HMR === "true" ? null : {},
      proxy: {
        "/api": {
          target: process.env.VITE_API_URL || "http://localhost:3000",
          changeOrigin: true,
        },
      },
    },
  };
});
