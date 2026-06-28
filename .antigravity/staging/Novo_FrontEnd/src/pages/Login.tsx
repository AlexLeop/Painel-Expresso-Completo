import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, Eye, EyeOff, Loader2 } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { supabase } from "../lib/supabase";

type AuthMode = "login" | "register" | "recover" | "set_password";

type RegisterForm = {
  nome_fantasia: string;
  documento: string;
  telefone: string;
  email: string;
  password: string;
  cep: string;
  endereco: string;
  complemento: string;
  bairro: string;
  cidade: string;
  uf: string;
  lat: string;
  lng: string;
  website: string;
};

const INITIAL_REGISTER: RegisterForm = {
  nome_fantasia: "",
  documento: "",
  telefone: "",
  email: "",
  password: "",
  cep: "",
  endereco: "",
  complemento: "",
  bairro: "",
  cidade: "",
  uf: "",
  lat: "",
  lng: "",
  website: "",
};

function formatCNPJ(value: string) {
  const digits = value.replace(/\D/g, "").slice(0, 14);
  return digits
    .replace(/^(\d{2})(\d)/, "$1.$2")
    .replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
    .replace(/\.(\d{3})(\d)/, ".$1/$2")
    .replace(/(\d{4})(\d)/, "$1-$2");
}

function formatPhone(value: string) {
  const digits = value.replace(/\D/g, "").slice(0, 11);
  if (digits.length <= 10) {
    return digits.replace(/^(\d{2})(\d{4})(\d{0,4})/, "($1) $2-$3");
  }
  return digits.replace(/^(\d{2})(\d{5})(\d{0,4})/, "($1) $2-$3");
}

function formatCEP(value: string) {
  const digits = value.replace(/\D/g, "").slice(0, 8);
  return digits.replace(/^(\d{5})(\d)/, "$1-$2");
}

function validateCNPJ(cnpj: string): boolean {
  const digits = cnpj.replace(/\D/g, "");
  if (digits.length !== 14) return false;
  if (/^(\d)\1{13}$/.test(digits)) return false;

  let sum = 0;
  let weight = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  for (let i = 0; i < 12; i++) sum += parseInt(digits[i]) * weight[i];
  let rem = sum % 11;
  if (parseInt(digits[12]) !== (rem < 2 ? 0 : 11 - rem)) return false;

  sum = 0;
  weight = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  for (let i = 0; i < 13; i++) sum += parseInt(digits[i]) * weight[i];
  rem = sum % 11;
  if (parseInt(digits[13]) !== (rem < 2 ? 0 : 11 - rem)) return false;

  return true;
}

function BrandingPanel() {
  return (
    <div className="login-branding">
      <div style={{ marginBottom: "40px" }}>
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "14px",
            marginBottom: "32px",
          }}
        >
          <img
            src="/favicon.ico"
            alt="Expresso Neves"
            style={{
              width: "52px",
              height: "52px",
              borderRadius: "14px",
              objectFit: "contain",
            }}
          />
          <div>
            <div
              style={{
                fontSize: "1.6rem",
                fontWeight: 800,
                letterSpacing: "-0.03em",
              }}
            >
              EXPRESSO NEVES
            </div>
            <div
              style={{
                fontSize: "0.72rem",
                opacity: 0.6,
                fontWeight: 500,
                letterSpacing: "0.15em",
                textTransform: "uppercase",
              }}
            >
              Portal Logístico
            </div>
          </div>
        </div>

        <h1
          className="login-hero-title"
          style={{
            fontSize: "2.6rem",
            fontWeight: 800,
            lineHeight: 1.15,
            letterSpacing: "-0.04em",
            marginBottom: "16px",
          }}
        >
          Gestão de
          <br />
          <span style={{ color: "#E55C00" }}>Entregas</span> Inteligente
        </h1>
        <p
          className="login-hero-subtitle"
          style={{
            fontSize: "1rem",
            opacity: 0.55,
            lineHeight: 1.6,
            maxWidth: "420px",
          }}
        >
          Controle financeiro, rastreamento em tempo real e relatórios
          automatizados para sua operação de logística.
        </p>
      </div>

      <div
        className="login-pills"
        style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}
      >
        {[
          "Mapa em Tempo Real",
          "Relatórios Financeiros",
          "Diárias Automáticas",
          "API Machine",
        ].map((f) => (
          <span
            key={f}
            style={{
              padding: "6px 14px",
              borderRadius: "20px",
              border: "1px solid rgba(255,255,255,0.12)",
              fontSize: "0.72rem",
              fontWeight: 500,
              color: "rgba(255,255,255,0.5)",
              background: "rgba(255,255,255,0.04)",
            }}
          >
            {f}
          </span>
        ))}
      </div>
    </div>
  );
}

function TabButton({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        flex: 1,
        padding: "10px 12px",
        borderRadius: "10px",
        border: "1px solid #E5E5E5",
        background: active
          ? "linear-gradient(135deg, #E55C00, #CC5200)"
          : "#FFFFFF",
        color: active ? "#FFFFFF" : "#666666",
        fontWeight: 800,
        fontSize: "0.8rem",
        letterSpacing: "0.02em",
        cursor: "pointer",
      }}
    >
      {label}
    </button>
  );
}

export function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [mode, setMode] = useState<AuthMode>("login");

  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState("");

  const [recoverEmail, setRecoverEmail] = useState("");
  const [recoverLoading, setRecoverLoading] = useState(false);
  const [recoverMessage, setRecoverMessage] = useState<string | null>(null);
  const [recoverError, setRecoverError] = useState<string | null>(null);

  const [resetPassword, setResetPassword] = useState("");
  const [resetPassword2, setResetPassword2] = useState("");
  const [resetLoading, setResetLoading] = useState(false);
  const [resetError, setResetError] = useState<string | null>(null);
  const [resetSuccess, setResetSuccess] = useState<string | null>(null);
  const [resetTokens, setResetTokens] = useState<{
    accessToken: string;
    refreshToken: string;
  } | null>(null);

  const [registerForm, setRegisterForm] =
    useState<RegisterForm>(INITIAL_REGISTER);
  const [registerSubmitting, setRegisterSubmitting] = useState(false);
  const [registerSuccess, setRegisterSuccess] = useState(false);
  const [registerError, setRegisterError] = useState<string | null>(null);
  const [cnpjError, setCnpjError] = useState<string | null>(null);
  const [contractNumber, setContractNumber] = useState<string | null>(null);
  const [showRegisterPassword, setShowRegisterPassword] = useState(false);

  const BASE_URL = useMemo(() => import.meta.env.VITE_API_URL || "", []);

  const labelStyle: React.CSSProperties = useMemo(
    () => ({
      display: "block",
      fontSize: "0.72rem",
      fontWeight: 700,
      color: "#666666",
      textTransform: "uppercase",
      letterSpacing: "0.08em",
      marginBottom: "6px",
    }),
    [],
  );

  const inputStyle: React.CSSProperties = useMemo(
    () => ({
      width: "100%",
      padding: "12px 14px",
      border: "2px solid #E5E5E5",
      borderRadius: "10px",
      fontSize: "0.9rem",
      color: "#333333",
      background: "#F9F9F9",
      outline: "none",
      transition: "border-color 0.2s",
      boxSizing: "border-box",
    }),
    [],
  );

  useEffect(() => {
    const hash = String(window.location.hash || "").replace(/^#/, "");
    if (!hash) return;
    const params = new URLSearchParams(hash);
    const type = params.get("type") || "";
    const accessToken = params.get("access_token") || "";
    const refreshToken = params.get("refresh_token") || "";
    if (type === "recovery" && accessToken && refreshToken) {
      setResetTokens({ accessToken, refreshToken });
      setMode("set_password");
    }
  }, []);

  const handleLogin = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setLoginLoading(true);
      setLoginError("");
      try {
        const { data, error } = await supabase.auth.signInWithPassword({
          email: loginEmail,
          password: loginPassword,
        });

        if (error || !data.session) {
          throw new Error(error?.message || "Credenciais inválidas ou erro no servidor");
        }

        // O AuthContext.tsx agora intercepta a sessão automaticamente
        // e vai redirecionar a página dependendo do profile retornado do Django.
        // Para uma UX rápida, se quisermos apenas não travar aqui:
        // navigate("/"); será gerenciado externamente pelo App/ProtectedRoutes, 
        // ou podemos dar force navigate aqui depois de um pequeno delay aguardando AuthContext
        
        // Simulação rápida para redirecionar
        setTimeout(() => {
          navigate("/");
        }, 500);

      } catch (err) {
        const msg = err instanceof Error ? err.message : "Falha ao fazer login";
        setLoginError(msg);
      } finally {
        setLoginLoading(false);
      }
    },
    [loginEmail, loginPassword, navigate],
  );

  const lookupCEP = useCallback(async (cep: string) => {
    const digits = cep.replace(/\D/g, "");
    if (digits.length !== 8) return;
    try {
      const viaRes = await fetch(`https://viacep.com.br/ws/${digits}/json/`);
      if (viaRes.ok) {
        const data = await viaRes.json();
        if (!data.erro) {
          setRegisterForm((prev) => ({
            ...prev,
            endereco: data.logradouro || prev.endereco,
            bairro: data.bairro || prev.bairro,
            cidade: data.localidade || prev.cidade,
            uf: data.uf || prev.uf,
          }));
        }
      }

      try {
        const geoRes = await fetch(
          `https://nominatim.openstreetmap.org/search?postalcode=${digits}&country=BR&format=json&limit=1`,
          { headers: { "User-Agent": "NevesGo/1.0" } },
        );
        if (geoRes.ok) {
          const geoData = await geoRes.json();
          if (Array.isArray(geoData) && geoData.length > 0) {
            setRegisterForm((prev) => ({
              ...prev,
              lat: String(geoData[0].lat || prev.lat),
              lng: String(geoData[0].lon || prev.lng),
            }));
          }
        }
      } catch {
        return;
      }
    } catch {
      return;
    }
  }, []);

  const registerEmailError = useMemo(() => {
    const v = registerForm.email.trim();
    if (!v) return null;
    if (!v.includes("@")) return "Informe um e-mail válido.";
    return null;
  }, [registerForm.email]);

  const registerPasswordError = useMemo(() => {
    const v = registerForm.password;
    if (!v) return null;
    if (v.length < 6) return "A senha deve ter pelo menos 6 caracteres.";
    return null;
  }, [registerForm.password]);

  const handleRegister = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setRegisterError(null);
      setCnpjError(null);

      if (!validateCNPJ(registerForm.documento)) {
        setCnpjError("CNPJ inválido. Verifique os dígitos.");
        return;
      }
      if (registerEmailError) {
        setRegisterError(registerEmailError);
        return;
      }
      if (registerPasswordError) {
        setRegisterError(registerPasswordError);
        return;
      }

      setRegisterSubmitting(true);
      try {
        const res = await fetch(`${BASE_URL}/api/auth/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(registerForm),
        });

        const data = await res.json().catch(() => ({}));
        if (res.ok && data.success) {
          setRegisterSuccess(true);
          setContractNumber(data.numero_contrato || null);
        } else {
          const msg =
            data?.details?.errors?.[0]?.message ||
            data?.error ||
            "Erro ao cadastrar. Tente novamente.";
          setRegisterError(String(msg));
        }
      } catch {
        setRegisterError(
          "Erro de conexão. Verifique sua internet e tente novamente.",
        );
      } finally {
        setRegisterSubmitting(false);
      }
    },
    [BASE_URL, registerForm, registerEmailError, registerPasswordError],
  );

  const handleRecover = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setRecoverError(null);
      setRecoverMessage(null);
      setRecoverLoading(true);
      try {
        const email = recoverEmail.trim().toLowerCase();
        if (!email || !email.includes("@")) {
          setRecoverError("Informe um e-mail válido.");
          return;
        }
        const redirectTo = `${window.location.origin}/login`;
        const { error } = await supabase.auth.resetPasswordForEmail(email, {
          redirectTo,
        });
        if (error) {
          setRecoverError(
            "Não foi possível iniciar a recuperação. Verifique o e-mail e tente novamente.",
          );
          return;
        }
        setRecoverMessage(
          "Se este e-mail estiver cadastrado, você receberá instruções para redefinir a senha.",
        );
      } finally {
        setRecoverLoading(false);
      }
    },
    [recoverEmail],
  );

  const handleSetPassword = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setResetError(null);
      setResetSuccess(null);
      if (!resetTokens) {
        setResetError("Link inválido. Solicite a recuperação novamente.");
        return;
      }
      if (!resetPassword || resetPassword.length < 6) {
        setResetError("A senha deve ter pelo menos 6 caracteres.");
        return;
      }
      if (resetPassword !== resetPassword2) {
        setResetError("As senhas não conferem.");
        return;
      }
      setResetLoading(true);
      try {
        const { error: sessionError } = await supabase.auth.setSession({
          access_token: resetTokens.accessToken,
          refresh_token: resetTokens.refreshToken,
        });
        if (sessionError) {
          setResetError("Sessão inválida. Solicite a recuperação novamente.");
          return;
        }
        const { error: updateError } = await supabase.auth.updateUser({
          password: resetPassword,
        });
        if (updateError) {
          setResetError("Não foi possível atualizar a senha. Tente novamente.");
          return;
        }
        setResetSuccess(
          "Senha atualizada com sucesso. Faça login para continuar.",
        );
        try {
          await supabase.auth.signOut();
        } catch {
          return;
        }
        window.location.hash = "";
        setMode("login");
      } finally {
        setResetLoading(false);
      }
    },
    [resetPassword, resetPassword2, resetTokens],
  );

  const footer = (
    <div
      style={{
        marginTop: "12px",
        textAlign: "center",
        fontSize: "0.7rem",
        color: "#999999",
      }}
    >
      © {new Date().getFullYear()} Expresso Neves • Portal Logístico
    </div>
  );

  if (registerSuccess) {
    return (
      <div className="login-container">
        <BrandingPanel />
        <div className="login-card-wrapper">
          <div className="login-card" style={{ textAlign: "center" }}>
            <div style={{ marginBottom: "14px" }}>
              <CheckCircle2 size={46} color="#16a34a" />
            </div>
            <h2
              style={{
                fontSize: "1.5rem",
                fontWeight: 800,
                color: "#333333",
                letterSpacing: "-0.03em",
              }}
            >
              Cadastro enviado!
            </h2>
            <p
              style={{
                fontSize: "0.9rem",
                color: "#666666",
                marginTop: "8px",
                lineHeight: 1.5,
              }}
            >
              Sua empresa foi registrada e está aguardando aprovação.
            </p>
            {contractNumber && (
              <div
                style={{
                  marginTop: "14px",
                  fontSize: "0.85rem",
                  color: "#333333",
                }}
              >
                Número do contrato: <strong>{contractNumber}</strong>
              </div>
            )}
            <button
              type="button"
              onClick={() => {
                setRegisterSuccess(false);
                setRegisterForm(INITIAL_REGISTER);
                setMode("login");
              }}
              style={{
                width: "100%",
                padding: "13px",
                border: "none",
                borderRadius: "10px",
                background: "linear-gradient(135deg, #E55C00, #CC5200)",
                color: "white",
                fontSize: "0.9rem",
                fontWeight: 700,
                cursor: "pointer",
                transition: "opacity 0.2s, transform 0.15s",
                boxShadow: "0 4px 14px rgba(229, 92, 0, 0.35)",
                marginTop: "22px",
              }}
            >
              Ir para Login
            </button>
            {footer}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="login-container">
      <BrandingPanel />
      <div className="login-card-wrapper">
        <div className="login-card">
          <div style={{ display: "flex", gap: "10px", marginBottom: "18px" }}>
            <TabButton
              active={mode === "login"}
              label="Entrar"
              onClick={() => setMode("login")}
            />
            <TabButton
              active={mode === "register"}
              label="Cadastro"
              onClick={() => setMode("register")}
            />
          </div>

          {mode === "recover" && (
            <>
              <div style={{ textAlign: "center", marginBottom: "24px" }}>
                <h2
                  style={{
                    fontSize: "1.35rem",
                    fontWeight: 800,
                    color: "#333333",
                    letterSpacing: "-0.03em",
                  }}
                >
                  Recuperar Senha
                </h2>
                <p
                  style={{
                    fontSize: "0.82rem",
                    color: "#999999",
                    marginTop: "6px",
                  }}
                >
                  Enviaremos um link para redefinir sua senha.
                </p>
              </div>

              {recoverError && (
                <div
                  style={{
                    padding: "10px 14px",
                    borderRadius: "10px",
                    background: "#FEF2F2",
                    border: "1px solid #FECACA",
                    color: "#DC2626",
                    fontSize: "0.8rem",
                    fontWeight: 500,
                    marginBottom: "14px",
                    textAlign: "center",
                  }}
                >
                  {recoverError}
                </div>
              )}
              {recoverMessage && (
                <div
                  style={{
                    padding: "10px 14px",
                    borderRadius: "10px",
                    background: "#ECFDF5",
                    border: "1px solid #A7F3D0",
                    color: "#047857",
                    fontSize: "0.8rem",
                    fontWeight: 500,
                    marginBottom: "14px",
                    textAlign: "center",
                  }}
                >
                  {recoverMessage}
                </div>
              )}

              <form onSubmit={handleRecover}>
                <div style={{ marginBottom: "18px" }}>
                  <label style={labelStyle}>Email</label>
                  <input
                    type="email"
                    value={recoverEmail}
                    onChange={(e) => setRecoverEmail(e.target.value)}
                    placeholder="seu@email.com"
                    required
                    autoComplete="email"
                    style={inputStyle}
                    onFocus={(e) =>
                      (e.currentTarget.style.borderColor = "#E55C00")
                    }
                    onBlur={(e) =>
                      (e.currentTarget.style.borderColor = "#E5E5E5")
                    }
                  />
                </div>

                <button
                  type="submit"
                  disabled={recoverLoading}
                  style={{
                    width: "100%",
                    padding: "13px",
                    border: "none",
                    borderRadius: "10px",
                    background: recoverLoading
                      ? "#FFB380"
                      : "linear-gradient(135deg, #E55C00, #CC5200)",
                    color: "white",
                    fontSize: "0.9rem",
                    fontWeight: 700,
                    cursor: recoverLoading ? "not-allowed" : "pointer",
                    transition: "opacity 0.2s, transform 0.15s",
                    boxShadow: "0 4px 14px rgba(229, 92, 0, 0.35)",
                  }}
                >
                  {recoverLoading ? "Enviando..." : "Enviar link"}
                </button>

                <div style={{ marginTop: "16px", textAlign: "center" }}>
                  <button
                    type="button"
                    onClick={() => setMode("login")}
                    style={{
                      background: "none",
                      border: "none",
                      color: "#E55C00",
                      fontWeight: 800,
                      cursor: "pointer",
                      fontSize: "0.82rem",
                    }}
                  >
                    Voltar ao Login
                  </button>
                </div>
              </form>
              {footer}
            </>
          )}

          {mode === "set_password" && (
            <>
              <div style={{ textAlign: "center", marginBottom: "24px" }}>
                <h2
                  style={{
                    fontSize: "1.35rem",
                    fontWeight: 800,
                    color: "#333333",
                    letterSpacing: "-0.03em",
                  }}
                >
                  Definir nova senha
                </h2>
                <p
                  style={{
                    fontSize: "0.82rem",
                    color: "#999999",
                    marginTop: "6px",
                  }}
                >
                  Escolha uma nova senha para sua conta.
                </p>
              </div>

              {resetError && (
                <div
                  style={{
                    padding: "10px 14px",
                    borderRadius: "10px",
                    background: "#FEF2F2",
                    border: "1px solid #FECACA",
                    color: "#DC2626",
                    fontSize: "0.8rem",
                    fontWeight: 500,
                    marginBottom: "14px",
                    textAlign: "center",
                  }}
                >
                  {resetError}
                </div>
              )}
              {resetSuccess && (
                <div
                  style={{
                    padding: "10px 14px",
                    borderRadius: "10px",
                    background: "#ECFDF5",
                    border: "1px solid #A7F3D0",
                    color: "#047857",
                    fontSize: "0.8rem",
                    fontWeight: 500,
                    marginBottom: "14px",
                    textAlign: "center",
                  }}
                >
                  {resetSuccess}
                </div>
              )}

              <form onSubmit={handleSetPassword}>
                <div style={{ marginBottom: "18px" }}>
                  <label style={labelStyle}>Nova senha</label>
                  <input
                    type="password"
                    value={resetPassword}
                    onChange={(e) => setResetPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    style={inputStyle}
                    onFocus={(e) =>
                      (e.currentTarget.style.borderColor = "#E55C00")
                    }
                    onBlur={(e) =>
                      (e.currentTarget.style.borderColor = "#E5E5E5")
                    }
                  />
                </div>
                <div style={{ marginBottom: "18px" }}>
                  <label style={labelStyle}>Confirmar senha</label>
                  <input
                    type="password"
                    value={resetPassword2}
                    onChange={(e) => setResetPassword2(e.target.value)}
                    placeholder="••••••••"
                    required
                    style={inputStyle}
                    onFocus={(e) =>
                      (e.currentTarget.style.borderColor = "#E55C00")
                    }
                    onBlur={(e) =>
                      (e.currentTarget.style.borderColor = "#E5E5E5")
                    }
                  />
                </div>

                <button
                  type="submit"
                  disabled={resetLoading}
                  style={{
                    width: "100%",
                    padding: "13px",
                    border: "none",
                    borderRadius: "10px",
                    background: resetLoading
                      ? "#FFB380"
                      : "linear-gradient(135deg, #E55C00, #CC5200)",
                    color: "white",
                    fontSize: "0.9rem",
                    fontWeight: 700,
                    cursor: resetLoading ? "not-allowed" : "pointer",
                    transition: "opacity 0.2s, transform 0.15s",
                    boxShadow: "0 4px 14px rgba(229, 92, 0, 0.35)",
                  }}
                >
                  {resetLoading ? "Atualizando..." : "Atualizar senha"}
                </button>
              </form>
              {footer}
            </>
          )}

          {mode === "login" && (
            <>
              <div style={{ textAlign: "center", marginBottom: "22px" }}>
                <h2
                  style={{
                    fontSize: "1.4rem",
                    fontWeight: 800,
                    color: "#333333",
                    letterSpacing: "-0.03em",
                  }}
                >
                  Entrar no Painel
                </h2>
                <p
                  style={{
                    fontSize: "0.82rem",
                    color: "#999999",
                    marginTop: "6px",
                  }}
                >
                  Use suas credenciais da Machine
                </p>
              </div>

              {loginError && (
                <div
                  style={{
                    padding: "10px 14px",
                    borderRadius: "10px",
                    background: "#FEF2F2",
                    border: "1px solid #FECACA",
                    color: "#DC2626",
                    fontSize: "0.8rem",
                    fontWeight: 500,
                    marginBottom: "18px",
                    textAlign: "center",
                  }}
                >
                  {loginError}
                </div>
              )}

              <form onSubmit={handleLogin}>
                <div style={{ marginBottom: "18px" }}>
                  <label style={labelStyle}>Email</label>
                  <input
                    id="login-email"
                    type="email"
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    placeholder="seu@email.com"
                    required
                    autoComplete="email"
                    style={inputStyle}
                    onFocus={(e) =>
                      (e.currentTarget.style.borderColor = "#E55C00")
                    }
                    onBlur={(e) =>
                      (e.currentTarget.style.borderColor = "#E5E5E5")
                    }
                  />
                </div>

                <div style={{ marginBottom: "18px" }}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <label style={{ ...labelStyle, marginBottom: 0 }}>
                      Senha
                    </label>
                    <button
                      type="button"
                      onClick={() => {
                        setRecoverEmail(loginEmail);
                        setMode("recover");
                      }}
                      style={{
                        background: "none",
                        border: "none",
                        padding: 0,
                        cursor: "pointer",
                        fontSize: "0.78rem",
                        fontWeight: 800,
                        color: "#E55C00",
                      }}
                    >
                      Esqueci minha senha
                    </button>
                  </div>
                  <div style={{ position: "relative", marginTop: "6px" }}>
                    <input
                      id="login-password"
                      type={showLoginPassword ? "text" : "password"}
                      value={loginPassword}
                      onChange={(e) => setLoginPassword(e.target.value)}
                      placeholder="••••••••"
                      required
                      autoComplete="current-password"
                      style={{ ...inputStyle, paddingRight: "44px" }}
                      onFocus={(e) =>
                        (e.currentTarget.style.borderColor = "#E55C00")
                      }
                      onBlur={(e) =>
                        (e.currentTarget.style.borderColor = "#E5E5E5")
                      }
                    />
                    <button
                      type="button"
                      onClick={() => setShowLoginPassword((v) => !v)}
                      style={{
                        position: "absolute",
                        right: "12px",
                        top: "50%",
                        transform: "translateY(-50%)",
                        background: "none",
                        border: "none",
                        cursor: "pointer",
                        color: "#999",
                        padding: "4px",
                        lineHeight: 1,
                      }}
                      tabIndex={-1}
                      aria-label={
                        showLoginPassword ? "Ocultar senha" : "Mostrar senha"
                      }
                    >
                      {showLoginPassword ? (
                        <EyeOff size={18} />
                      ) : (
                        <Eye size={18} />
                      )}
                    </button>
                  </div>
                </div>

                <button
                  id="login-submit"
                  type="submit"
                  disabled={loginLoading}
                  style={{
                    width: "100%",
                    padding: "13px",
                    border: "none",
                    borderRadius: "10px",
                    background: loginLoading
                      ? "#FFB380"
                      : "linear-gradient(135deg, #E55C00, #CC5200)",
                    color: "white",
                    fontSize: "0.9rem",
                    fontWeight: 700,
                    cursor: loginLoading ? "not-allowed" : "pointer",
                    transition: "opacity 0.2s, transform 0.15s",
                    boxShadow: "0 4px 14px rgba(229, 92, 0, 0.35)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "10px",
                  }}
                >
                  {loginLoading ? (
                    <>
                      <Loader2 size={18} className="animate-spin" />
                      Autenticando...
                    </>
                  ) : (
                    "Entrar"
                  )}
                </button>
              </form>
              {footer}
            </>
          )}

          {mode === "register" && (
            <>
              <div style={{ textAlign: "center", marginBottom: "18px" }}>
                <h2
                  style={{
                    fontSize: "1.4rem",
                    fontWeight: 800,
                    color: "#333333",
                    letterSpacing: "-0.03em",
                  }}
                >
                  Cadastro de Empresa
                </h2>
                <p
                  style={{
                    fontSize: "0.82rem",
                    color: "#999999",
                    marginTop: "6px",
                  }}
                >
                  Crie sua conta e registre sua loja
                </p>
              </div>

              {(registerError || cnpjError) && (
                <div
                  style={{
                    padding: "10px 14px",
                    borderRadius: "10px",
                    background: "#FEF2F2",
                    border: "1px solid #FECACA",
                    color: "#DC2626",
                    fontSize: "0.8rem",
                    fontWeight: 500,
                    marginBottom: "14px",
                    textAlign: "center",
                  }}
                >
                  {cnpjError || registerError}
                </div>
              )}

              <form onSubmit={handleRegister}>
                <input
                  type="text"
                  value={registerForm.website}
                  onChange={(e) =>
                    setRegisterForm((p) => ({ ...p, website: e.target.value }))
                  }
                  style={{ display: "none" }}
                  tabIndex={-1}
                  autoComplete="off"
                />

                <div style={{ marginBottom: "14px" }}>
                  <label style={labelStyle}>Nome Fantasia</label>
                  <input
                    value={registerForm.nome_fantasia}
                    onChange={(e) =>
                      setRegisterForm((p) => ({
                        ...p,
                        nome_fantasia: e.target.value,
                      }))
                    }
                    placeholder="Nome da loja"
                    required
                    style={inputStyle}
                    onFocus={(e) =>
                      (e.currentTarget.style.borderColor = "#E55C00")
                    }
                    onBlur={(e) =>
                      (e.currentTarget.style.borderColor = "#E5E5E5")
                    }
                  />
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "12px",
                    marginBottom: "14px",
                  }}
                >
                  <div>
                    <label style={labelStyle}>CNPJ</label>
                    <input
                      value={registerForm.documento}
                      onChange={(e) => {
                        const next = formatCNPJ(e.target.value);
                        setRegisterForm((p) => ({ ...p, documento: next }));
                        setCnpjError(null);
                      }}
                      placeholder="00.000.000/0000-00"
                      required
                      style={inputStyle}
                      onFocus={(e) =>
                        (e.currentTarget.style.borderColor = "#E55C00")
                      }
                      onBlur={(e) => {
                        e.currentTarget.style.borderColor = "#E5E5E5";
                        if (
                          registerForm.documento &&
                          !validateCNPJ(registerForm.documento)
                        ) {
                          setCnpjError("CNPJ inválido. Verifique os dígitos.");
                        }
                      }}
                    />
                  </div>
                  <div>
                    <label style={labelStyle}>Telefone</label>
                    <input
                      value={registerForm.telefone}
                      onChange={(e) =>
                        setRegisterForm((p) => ({
                          ...p,
                          telefone: formatPhone(e.target.value),
                        }))
                      }
                      placeholder="(00) 00000-0000"
                      required
                      style={inputStyle}
                      onFocus={(e) =>
                        (e.currentTarget.style.borderColor = "#E55C00")
                      }
                      onBlur={(e) =>
                        (e.currentTarget.style.borderColor = "#E5E5E5")
                      }
                    />
                  </div>
                </div>

                <div style={{ marginBottom: "14px" }}>
                  <label style={labelStyle}>Email</label>
                  <input
                    type="email"
                    value={registerForm.email}
                    onChange={(e) =>
                      setRegisterForm((p) => ({ ...p, email: e.target.value }))
                    }
                    placeholder="seu@email.com"
                    required
                    style={inputStyle}
                    onFocus={(e) =>
                      (e.currentTarget.style.borderColor = "#E55C00")
                    }
                    onBlur={(e) =>
                      (e.currentTarget.style.borderColor = "#E5E5E5")
                    }
                  />
                  {registerEmailError && (
                    <div
                      style={{
                        marginTop: "6px",
                        fontSize: "0.78rem",
                        color: "#DC2626",
                        fontWeight: 600,
                      }}
                    >
                      {registerEmailError}
                    </div>
                  )}
                </div>

                <div style={{ marginBottom: "14px" }}>
                  <label style={labelStyle}>Senha</label>
                  <div style={{ position: "relative" }}>
                    <input
                      type={showRegisterPassword ? "text" : "password"}
                      value={registerForm.password}
                      onChange={(e) =>
                        setRegisterForm((p) => ({
                          ...p,
                          password: e.target.value,
                        }))
                      }
                      placeholder="••••••••"
                      required
                      style={{ ...inputStyle, paddingRight: "44px" }}
                      onFocus={(e) =>
                        (e.currentTarget.style.borderColor = "#E55C00")
                      }
                      onBlur={(e) =>
                        (e.currentTarget.style.borderColor = "#E5E5E5")
                      }
                    />
                    <button
                      type="button"
                      onClick={() => setShowRegisterPassword((v) => !v)}
                      style={{
                        position: "absolute",
                        right: "12px",
                        top: "50%",
                        transform: "translateY(-50%)",
                        background: "none",
                        border: "none",
                        cursor: "pointer",
                        color: "#999",
                        padding: "4px",
                        lineHeight: 1,
                      }}
                      tabIndex={-1}
                      aria-label={
                        showRegisterPassword ? "Ocultar senha" : "Mostrar senha"
                      }
                    >
                      {showRegisterPassword ? (
                        <EyeOff size={18} />
                      ) : (
                        <Eye size={18} />
                      )}
                    </button>
                  </div>
                  {registerPasswordError && (
                    <div
                      style={{
                        marginTop: "6px",
                        fontSize: "0.78rem",
                        color: "#DC2626",
                        fontWeight: 600,
                      }}
                    >
                      {registerPasswordError}
                    </div>
                  )}
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "140px 1fr",
                    gap: "12px",
                    marginBottom: "14px",
                  }}
                >
                  <div>
                    <label style={labelStyle}>CEP</label>
                    <input
                      value={registerForm.cep}
                      onChange={(e) => {
                        const next = formatCEP(e.target.value);
                        setRegisterForm((p) => ({ ...p, cep: next }));
                        if (next.replace(/\D/g, "").length === 8) {
                          lookupCEP(next);
                        }
                      }}
                      placeholder="00000-000"
                      style={inputStyle}
                      onFocus={(e) =>
                        (e.currentTarget.style.borderColor = "#E55C00")
                      }
                      onBlur={(e) =>
                        (e.currentTarget.style.borderColor = "#E5E5E5")
                      }
                    />
                  </div>
                  <div>
                    <label style={labelStyle}>Endereço</label>
                    <input
                      value={registerForm.endereco}
                      onChange={(e) =>
                        setRegisterForm((p) => ({
                          ...p,
                          endereco: e.target.value,
                        }))
                      }
                      placeholder="Rua, número"
                      style={inputStyle}
                      onFocus={(e) =>
                        (e.currentTarget.style.borderColor = "#E55C00")
                      }
                      onBlur={(e) =>
                        (e.currentTarget.style.borderColor = "#E5E5E5")
                      }
                    />
                  </div>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "12px",
                    marginBottom: "14px",
                  }}
                >
                  <div>
                    <label style={labelStyle}>Bairro</label>
                    <input
                      value={registerForm.bairro}
                      onChange={(e) =>
                        setRegisterForm((p) => ({
                          ...p,
                          bairro: e.target.value,
                        }))
                      }
                      placeholder="Bairro"
                      style={inputStyle}
                      onFocus={(e) =>
                        (e.currentTarget.style.borderColor = "#E55C00")
                      }
                      onBlur={(e) =>
                        (e.currentTarget.style.borderColor = "#E5E5E5")
                      }
                    />
                  </div>
                  <div>
                    <label style={labelStyle}>Complemento</label>
                    <input
                      value={registerForm.complemento}
                      onChange={(e) =>
                        setRegisterForm((p) => ({
                          ...p,
                          complemento: e.target.value,
                        }))
                      }
                      placeholder="Opcional"
                      style={inputStyle}
                      onFocus={(e) =>
                        (e.currentTarget.style.borderColor = "#E55C00")
                      }
                      onBlur={(e) =>
                        (e.currentTarget.style.borderColor = "#E5E5E5")
                      }
                    />
                  </div>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 70px",
                    gap: "12px",
                    marginBottom: "14px",
                  }}
                >
                  <div>
                    <label style={labelStyle}>Cidade</label>
                    <input
                      value={registerForm.cidade}
                      onChange={(e) =>
                        setRegisterForm((p) => ({
                          ...p,
                          cidade: e.target.value,
                        }))
                      }
                      placeholder="Cidade"
                      style={inputStyle}
                      onFocus={(e) =>
                        (e.currentTarget.style.borderColor = "#E55C00")
                      }
                      onBlur={(e) =>
                        (e.currentTarget.style.borderColor = "#E5E5E5")
                      }
                    />
                  </div>
                  <div>
                    <label style={labelStyle}>UF</label>
                    <input
                      value={registerForm.uf}
                      onChange={(e) =>
                        setRegisterForm((p) => ({
                          ...p,
                          uf: e.target.value.toUpperCase().slice(0, 2),
                        }))
                      }
                      placeholder="UF"
                      style={inputStyle}
                      onFocus={(e) =>
                        (e.currentTarget.style.borderColor = "#E55C00")
                      }
                      onBlur={(e) =>
                        (e.currentTarget.style.borderColor = "#E5E5E5")
                      }
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={registerSubmitting}
                  style={{
                    width: "100%",
                    padding: "13px",
                    border: "none",
                    borderRadius: "10px",
                    background: registerSubmitting
                      ? "#FFB380"
                      : "linear-gradient(135deg, #E55C00, #CC5200)",
                    color: "white",
                    fontSize: "0.9rem",
                    fontWeight: 700,
                    cursor: registerSubmitting ? "not-allowed" : "pointer",
                    transition: "opacity 0.2s, transform 0.15s",
                    boxShadow: "0 4px 14px rgba(229, 92, 0, 0.35)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "10px",
                  }}
                >
                  {registerSubmitting ? (
                    <>
                      <Loader2 size={18} className="animate-spin" />
                      Enviando...
                    </>
                  ) : (
                    "Cadastrar"
                  )}
                </button>
              </form>
              {footer}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
