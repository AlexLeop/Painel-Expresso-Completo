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
    const controller = new AbortController();
    const validateSession = async () => {
      try {
        const res = await fetch("/api/auth/me", { signal: controller.signal });
        if (res.ok) {
          const data = await res.json();
          if (data.authenticated) {
            const newSession = {
              success: true,
              user: data.user,
              basicAuth: data.basicAuth,
            };
            localStorage.setItem("nevesgo:session", JSON.stringify(newSession));
            setSession(newSession);
          } else {
            throw new Error("Not authenticated");
          }
        } else {
          throw new Error("Not authenticated");
        }
      } catch (err: any) {
        if (err.name === "AbortError") return; // Ignore aborted requests
        const storedSession = localStorage.getItem("nevesgo:session");
        if (storedSession) {
          try {
            setSession(JSON.parse(storedSession));
          } catch {
            localStorage.removeItem("nevesgo:session");
          }
        } else {
          localStorage.removeItem("nevesgo:session");
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    };

    validateSession();
    return () => {
      controller.abort();
    };
  }, []);

  const login = (newSession: SessionData) => {
    localStorage.setItem("nevesgo:session", JSON.stringify(newSession));
    setSession(newSession);
  };

  const logout = () => {
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
