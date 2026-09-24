import React, { createContext, useContext, useState, useEffect } from "react";
import {
  authStorage,
  fetchCurrentProfile,
  nativeLogout,
  nativeRefreshToken,
  User as AuthUser,
} from "../lib/auth";

export interface Company {
  id: string;
  nome: string;
  documento?: string;
  cnpj?: string;
  telefone?: string;
  endereco?: string;
}

export type User = AuthUser;

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

    const initAuth = async () => {
      try {
        let token = authStorage.getAccessToken();
        if (!token) {
          token = await nativeRefreshToken();
          if (!token) return;
        }

        const user = await fetchCurrentProfile();
        if (user && mounted) {
          const newSession: SessionData = {
            success: true,
            user,
          };
          const preferredOperator = sessionStorage.getItem("nevesgo:preferred_operator");
          if (
            user.is_platform_admin &&
            preferredOperator &&
            user.companies?.some((company) => company.id === preferredOperator)
          ) {
            newSession.user.company_id = preferredOperator;
            newSession.user.machine_empresa_id = preferredOperator;
          }
          authStorage.setSession(newSession);
          setSession(newSession);
        } else if (mounted) {
          authStorage.clearTokens();
          setSession(null);
        }
      } catch {
        if (mounted) {
          authStorage.clearTokens();
          setSession(null);
        }
      } finally {
        if (mounted) setIsLoading(false);
      }
    };

    initAuth();

    return () => {
      mounted = false;
    };
  }, []);

  const login = (newSession: SessionData) => {
    authStorage.setSession(newSession);
    setSession(newSession);
  };

  const logout = async () => {
    await nativeLogout();
    sessionStorage.removeItem("nevesgo:preferred_operator");
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
      if (session.user.is_platform_admin) {
        sessionStorage.setItem("nevesgo:preferred_operator", companyId);
      }
      authStorage.setSession(updatedSession);
      setSession(updatedSession);

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
