import React, { createContext, useContext, useState, useEffect } from "react";

export interface Company {
  id: string;
  nome: string;
  documento?: string;
  cnpj?: string;
  telefone?: string;
  endereco?: string;
}

export interface User {
  id?: string;
  email: string;
  name: string;
  role: string;
  companies?: Company[];
  company_id: string;
}

export interface SessionData {
  success: boolean;
  user: User;
  basicAuth?: string;
}

interface AuthContextType {
  session: SessionData | null;
  login: (session: SessionData) => void;
  logout: () => void;
  isLoading: boolean;
  changeTenant: (companyId: string) => Promise<void>;
  globalSearch: string;
  setGlobalSearch: (term: string) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<SessionData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [globalSearch, setGlobalSearch] = useState("");

  useEffect(() => {
    let mounted = true;

    const loadProfile = async (supabaseSession: any) => {
      try {
        const { authFetch } = await import("../lib/api");
        const res = await authFetch("/api/auth/me");
        if (res.ok) {
          const data = await res.json();
          if (data.authenticated && mounted) {
            const newSession = {
              success: true,
              user: data.user,
            };
            localStorage.setItem("nevesgo:session", JSON.stringify(newSession));
            setSession(newSession);
          }
        }
      } catch (err) {
        if (mounted) {
          localStorage.removeItem("nevesgo:session");
          setSession(null);
        }
      } finally {
        if (mounted) setIsLoading(false);
      }
    };

    import("../lib/supabase").then(({ supabase }) => {
      supabase.auth.getSession().then(({ data: { session } }) => {
        if (session) {
          loadProfile(session);
        } else {
          if (mounted) {
            localStorage.removeItem("nevesgo:session");
            setSession(null);
            setIsLoading(false);
          }
        }
      });

      supabase.auth.onAuthStateChange((_event, session) => {
        if (session) {
          loadProfile(session);
        } else {
          if (mounted) {
            localStorage.removeItem("nevesgo:session");
            setSession(null);
            setIsLoading(false);
          }
        }
      });
    });

    return () => {
      mounted = false;
    };
  }, []);

  const login = (newSession: SessionData) => {
    localStorage.setItem("nevesgo:session", JSON.stringify(newSession));
    setSession(newSession);
  };

  const logout = async () => {
    const { supabase } = await import("../lib/supabase");
    await supabase.auth.signOut();
    localStorage.removeItem("nevesgo:session");
    setSession(null);
  };

  const changeTenant = async (companyId: string) => {
    if (session) {
      const updatedSession = {
        ...session,
        user: {
          ...session.user,
          company_id: companyId,
        },
      };
      localStorage.setItem("nevesgo:session", JSON.stringify(updatedSession));
      setSession(updatedSession);

      try {
        await fetch("/api/auth/change-tenant", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ company_id: companyId }),
        });
      } catch (err) {
        console.error("Failed to change tenant on backend:", err);
      }

      window.location.reload();
    }
  };

  const contextValue = React.useMemo(
    () => ({
      session,
      login,
      logout,
      isLoading,
      changeTenant,
      globalSearch,
      setGlobalSearch,
    }),
    [session, isLoading, globalSearch],
  );

  return (
    <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
