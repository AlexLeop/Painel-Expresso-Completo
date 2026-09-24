import { useState, useEffect } from "react";
import {
  Building2,
  Bell,
  Key,
  User,
  Save,
  Globe,
  Database,
  Shield,
  CreditCard,
  Palette,
  Upload,
  ClipboardList,
  AlertTriangle,
  Info,
  Check,
  RefreshCw,
} from "lucide-react";
import { cn } from "../lib/utils";
import { useAuth } from "../contexts/AuthContext";
import { useBranding } from "../contexts/BrandingContext";
import {
  uploadBrandingLogo,
  uploadBrandingFavicon,
  DEFAULT_BRANDING,
} from "../services/branding";
import { authFetch } from "../lib/api";
import { useApiQuery } from "../lib/useApiQuery";

type TabId =
  | "perfil"
  | "empresa"
  | "whitelabel"
  | "regras"
  | "notificacoes"
  | "integracoes"
  | "faturamento";

const FUNCTIONAL_TABS: TabId[] = ["perfil", "regras", "whitelabel"];

function DevBanner() {
  return (
    <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3 mb-6">
      <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
      <div>
        <p className="text-sm font-bold text-amber-900">
          Funcionalidade em desenvolvimento
        </p>
        <p className="text-xs text-amber-700 mt-0.5">
          As alterações nesta aba são apenas visuais e não serão salvas. A
          persistência será habilitada em breve.
        </p>
      </div>
    </div>
  );
}

function WhiteLabelConfigPanel() {
  const { branding, updateCustomBranding } = useBranding();
  const [formData, setFormData] = useState({
    brand_name: branding.brand_name || "",
    color_primary: branding.color_primary || "#E55C00",
    color_secondary: branding.color_secondary || "#4f46e5",
    color_accent: branding.color_accent || "#f59e0b",
    color_background: branding.color_background || "#F9F9FA",
    color_surface: branding.color_surface || "#ffffff",
    color_text: branding.color_text || "#18181b",
    dark_color_background: branding.dark_color_background || "#0a0a0a",
    dark_color_surface: branding.dark_color_surface || "#171717",
    dark_color_text: branding.dark_color_text || "#fafafa",
    theme_mode: (branding.theme_mode as "light" | "dark" | "auto") || "light",
    logo_url: branding.logo_url || "",
    favicon_url: branding.favicon_url || "",
  });

  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [uploadingFavicon, setUploadingFavicon] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    setFormData({
      brand_name: branding.brand_name || "",
      color_primary: branding.color_primary || "#E55C00",
      color_secondary: branding.color_secondary || "#4f46e5",
      color_accent: branding.color_accent || "#f59e0b",
      color_background: branding.color_background || "#F9F9FA",
      color_surface: branding.color_surface || "#ffffff",
      color_text: branding.color_text || "#18181b",
      dark_color_background: branding.dark_color_background || "#0a0a0a",
      dark_color_surface: branding.dark_color_surface || "#171717",
      dark_color_text: branding.dark_color_text || "#fafafa",
      theme_mode: (branding.theme_mode as any) || "light",
      logo_url: branding.logo_url || "",
      favicon_url: branding.favicon_url || "",
    });
  }, [branding]);

  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingLogo(true);
    setErrorMsg(null);
    try {
      const url = await uploadBrandingLogo(file);
      setFormData((prev) => ({ ...prev, logo_url: url }));
    } catch (err: any) {
      setErrorMsg(err?.message || "Erro no upload do logo.");
    } finally {
      setUploadingLogo(false);
    }
  };

  const handleFaviconUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingFavicon(true);
    setErrorMsg(null);
    try {
      const url = await uploadBrandingFavicon(file);
      setFormData((prev) => ({ ...prev, favicon_url: url }));
    } catch (err: any) {
      setErrorMsg(err?.message || "Erro no upload do favicon.");
    } finally {
      setUploadingFavicon(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setErrorMsg(null);
    setSavedSuccess(false);
    try {
      await updateCustomBranding({
        ...formData,
        logo_url: formData.logo_url || null,
        favicon_url: formData.favicon_url || null,
      });
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 4000);
    } catch (err: any) {
      setErrorMsg(err?.message || "Erro ao salvar personalização.");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!window.confirm("Deseja restaurar as cores e configurações padrão da marca?")) return;
    setSaving(true);
    setErrorMsg(null);
    try {
      await updateCustomBranding({
        ...DEFAULT_BRANDING,
        brand_name: branding.brand_name,
        logo_url: null,
        favicon_url: null,
      });
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 4000);
    } catch (err: any) {
      setErrorMsg(err?.message || "Erro ao restaurar padrões.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm ring-1 ring-zinc-950/5 p-6 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-lg font-bold text-zinc-900 flex items-center gap-2">
            <Palette className="w-5 h-5 text-indigo-600" />
            Personalização de Marca (White-Label)
          </h3>
          <p className="text-sm text-zinc-500">
            Personalize a logo, cores e nome da sua empresa para que lojistas e motoristas vejam a sua marca.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleReset}
            disabled={saving}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-zinc-600 bg-zinc-100 hover:bg-zinc-200 rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Restaurar Padrões
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-white bg-zinc-900 hover:bg-zinc-800 rounded-lg shadow-sm transition-all focus:ring-2 focus:ring-zinc-900/20 disabled:opacity-50"
          >
            {saving ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : savedSuccess ? (
              <Check className="w-4 h-4 text-emerald-400" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            {saving ? "Salvando..." : savedSuccess ? "✓ Salvo!" : "Salvar Marca"}
          </button>
        </div>
      </div>

      {savedSuccess && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg p-3 text-xs flex items-center gap-2 animate-fadeIn">
          <Check className="w-4 h-4 text-emerald-600" />
          <span>Personalização aplicada com sucesso! Os clientes e lojistas já verão sua marca atualizada.</span>
        </div>
      )}

      {errorMsg && (
        <div className="bg-rose-50 border border-rose-200 text-rose-800 rounded-lg p-3 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      <div className="h-px w-full bg-zinc-100" />

      {/* Identidade: Nome da Marca */}
      <div className="space-y-4">
        <h4 className="text-sm font-semibold text-zinc-900">Nome da Operação / Marca</h4>
        <div className="max-w-md space-y-1.5">
          <label className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">
            Nome de Exibição
          </label>
          <input
            type="text"
            value={formData.brand_name}
            onChange={(e) => setFormData({ ...formData, brand_name: e.target.value })}
            placeholder="Ex: Minha Logística Express"
            className="w-full px-3 py-2 bg-white border border-zinc-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all shadow-sm"
          />
          <p className="text-[11px] text-zinc-400">
            Substitui "Expresso Neves" no topo da página, aba do navegador e no cabeçalho dos relatórios PDF.
          </p>
        </div>
      </div>

      {/* Uploads: Logo e Favicon */}
      <div className="space-y-4 pt-4 border-t border-zinc-100">
        <h4 className="text-sm font-semibold text-zinc-900">Logotipo e Ícone</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Logo Principal */}
          <div className="border border-zinc-200 rounded-xl p-4 flex flex-col items-center justify-center text-center gap-3 bg-zinc-50/50">
            <div className="w-24 h-16 bg-white rounded-lg border border-zinc-200 flex items-center justify-center overflow-hidden p-2 shadow-sm">
              {formData.logo_url ? (
                <img src={formData.logo_url} alt="Logo" className="max-h-full max-w-full object-contain" />
              ) : (
                <span className="text-[11px] font-semibold text-zinc-400">Sem Logo</span>
              )}
            </div>
            <div>
              <p className="text-sm font-medium text-zinc-900">Logo Principal</p>
              <p className="text-[11px] text-zinc-500 mt-0.5">PNG, SVG ou WebP (máx. 2MB)</p>
            </div>
            <label className="cursor-pointer text-xs font-semibold px-3 py-1.5 bg-white border border-zinc-200 rounded-lg hover:bg-zinc-50 transition-colors shadow-sm inline-flex items-center gap-1.5">
              <Upload className="w-3.5 h-3.5 text-zinc-500" />
              {uploadingLogo ? "Enviando..." : formData.logo_url ? "Trocar Logo" : "Upload Logo"}
              <input type="file" accept="image/png,image/jpeg,image/webp" onChange={handleLogoUpload} className="hidden" disabled={uploadingLogo} />
            </label>
          </div>

          {/* Favicon */}
          <div className="border border-zinc-200 rounded-xl p-4 flex flex-col items-center justify-center text-center gap-3 bg-zinc-50/50">
            <div className="w-14 h-14 bg-white rounded-lg border border-zinc-200 flex items-center justify-center overflow-hidden p-1 shadow-sm">
              {formData.favicon_url ? (
                <img src={formData.favicon_url} alt="Favicon" className="w-8 h-8 object-contain" />
              ) : (
                <span className="text-[10px] font-semibold text-zinc-400">Favicon</span>
              )}
            </div>
            <div>
              <p className="text-sm font-medium text-zinc-900">Favicon (Aba do Navegador)</p>
              <p className="text-[11px] text-zinc-500 mt-0.5">ICO ou PNG quadrado (máx. 100KB)</p>
            </div>
            <label className="cursor-pointer text-xs font-semibold px-3 py-1.5 bg-white border border-zinc-200 rounded-lg hover:bg-zinc-50 transition-colors shadow-sm inline-flex items-center gap-1.5">
              <Upload className="w-3.5 h-3.5 text-zinc-500" />
              {uploadingFavicon ? "Enviando..." : formData.favicon_url ? "Trocar Favicon" : "Upload Favicon"}
              <input type="file" accept="image/x-icon,image/png" onChange={handleFaviconUpload} className="hidden" disabled={uploadingFavicon} />
            </label>
          </div>
        </div>
      </div>

      {/* Paleta de Cores */}
      <div className="space-y-4 pt-4 border-t border-zinc-100">
        <h4 className="text-sm font-semibold text-zinc-900">Paleta de Cores da Marca</h4>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">
              Cor Primária
            </label>
            <div className="flex gap-2 items-center">
              <input
                type="color"
                value={formData.color_primary}
                onChange={(e) => setFormData({ ...formData, color_primary: e.target.value })}
                className="w-10 h-10 rounded cursor-pointer border border-zinc-200 p-0.5 shrink-0"
              />
              <input
                type="text"
                value={formData.color_primary}
                onChange={(e) => setFormData({ ...formData, color_primary: e.target.value })}
                className="w-full px-3 py-2 bg-white border border-zinc-200 rounded-lg text-sm font-mono uppercase focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all shadow-sm"
              />
            </div>
            <p className="text-[10px] text-zinc-400">Botões principais, links e cabeçalho de relatórios.</p>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">
              Cor Secundária
            </label>
            <div className="flex gap-2 items-center">
              <input
                type="color"
                value={formData.color_secondary}
                onChange={(e) => setFormData({ ...formData, color_secondary: e.target.value })}
                className="w-10 h-10 rounded cursor-pointer border border-zinc-200 p-0.5 shrink-0"
              />
              <input
                type="text"
                value={formData.color_secondary}
                onChange={(e) => setFormData({ ...formData, color_secondary: e.target.value })}
                className="w-full px-3 py-2 bg-white border border-zinc-200 rounded-lg text-sm font-mono uppercase focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all shadow-sm"
              />
            </div>
            <p className="text-[10px] text-zinc-400">Elementos de destaque, menu lateral e contrastes.</p>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">
              Cor de Acento / CTA
            </label>
            <div className="flex gap-2 items-center">
              <input
                type="color"
                value={formData.color_accent}
                onChange={(e) => setFormData({ ...formData, color_accent: e.target.value })}
                className="w-10 h-10 rounded cursor-pointer border border-zinc-200 p-0.5 shrink-0"
              />
              <input
                type="text"
                value={formData.color_accent}
                onChange={(e) => setFormData({ ...formData, color_accent: e.target.value })}
                className="w-full px-3 py-2 bg-white border border-zinc-200 rounded-lg text-sm font-mono uppercase focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all shadow-sm"
              />
            </div>
            <p className="text-[10px] text-zinc-400">Badges de status, alertas e chamadas especiais.</p>
          </div>
        </div>
      </div>

      {/* Modo de Tema */}
      <div className="space-y-4 pt-4 border-t border-zinc-100">
        <h4 className="text-sm font-semibold text-zinc-900">Modo de Tema</h4>
        <div className="flex gap-3">
          {(["light", "dark", "auto"] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => setFormData({ ...formData, theme_mode: mode })}
              className={cn(
                "px-4 py-2 rounded-lg text-xs font-semibold capitalize border transition-all",
                formData.theme_mode === mode
                  ? "bg-zinc-900 text-white border-zinc-900 shadow-sm"
                  : "bg-white text-zinc-700 border-zinc-200 hover:bg-zinc-50"
              )}
            >
              {mode === "light" ? "Claro (Padrão)" : mode === "dark" ? "Escuro" : "Automático (Sistema)"}
            </button>
          ))}
        </div>
      </div>

      {/* Live Preview Card */}
      <div className="space-y-4 pt-4 border-t border-zinc-100">
        <h4 className="text-sm font-semibold text-zinc-900">Prévia da Identidade Visual</h4>
        <div
          className="rounded-xl border border-zinc-200 p-6 transition-all"
          style={{
            backgroundColor: formData.color_background,
            color: formData.color_text,
          }}
        >
          <div
            className="rounded-xl p-4 border border-zinc-200/60 shadow-sm max-w-md mx-auto space-y-4"
            style={{ backgroundColor: formData.color_surface }}
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-white border border-zinc-200 flex items-center justify-center p-1 shadow-sm shrink-0">
                {formData.logo_url ? (
                  <img src={formData.logo_url} alt="Logo" className="w-7 h-7 object-contain" />
                ) : (
                  <div className="w-5 h-5 rounded-full" style={{ backgroundColor: formData.color_primary }} />
                )}
              </div>
              <div className="min-w-0">
                <div className="font-extrabold text-sm tracking-tight truncate">
                  {formData.brand_name || "Sua Marca Logística"}
                </div>
                <div className="text-[10px] tracking-wider uppercase opacity-60">Portal do Lojista</div>
              </div>
              <span
                className="ml-auto text-[10px] font-bold px-2 py-0.5 rounded-full text-white"
                style={{ backgroundColor: formData.color_accent }}
              >
                Ativo
              </span>
            </div>

            <p className="text-xs opacity-75">
              Esta é uma demonstração de como seus lojistas e clientes visualizarão seu painel personalizado.
            </p>

            <div className="flex gap-2">
              <button
                type="button"
                className="px-3 py-1.5 rounded-lg text-xs font-bold text-white shadow-sm transition-opacity hover:opacity-90"
                style={{ backgroundColor: formData.color_primary }}
              >
                Nova Entrega
              </button>
              <button
                type="button"
                className="px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors hover:bg-black/5"
                style={{ borderColor: formData.color_secondary, color: formData.color_secondary }}
              >
                Rastrear Pedido
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function Configuracoes() {
  const [activeTab, setActiveTab] = useState<TabId>("perfil");
  const { session } = useAuth();
  const user = session?.user;
  const normalizedRole = String(user?.role || "").toLowerCase();
  const isAdmin = Boolean(user?.is_platform_admin) || [
    "admin", "administrador", "operador_admin", "superadmin", "platform_admin",
  ].includes(normalizedRole);
  const currentCompany: any = Array.isArray(user?.companies) ? user.companies.find(
    (c: any) => String(c.id) === String(user?.machine_empresa_id || user?.company_id),
  ) : undefined;
  const companyName = currentCompany?.nome || user?.name || "";

  // Profile form state
  const [profileName, setProfileName] = useState(user?.name || "");
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileSaved, setProfileSaved] = useState(false);

  const handleSaveProfile = async () => {
    if (!user?.id) return;
    setProfileSaving(true);
    try {
      const res = await authFetch("/api/v1/db/users", {
        method: "PUT",
        body: JSON.stringify({ id: user.id, fullName: profileName }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.error || "Erro ao salvar perfil");
      }
      setProfileSaved(true);
      setTimeout(() => setProfileSaved(false), 3000);
    } catch (err: any) {
      alert(err?.message || "Falha ao salvar perfil.");
    } finally {
      setProfileSaving(false);
    }
  };

  // Configs state
  const { data: configsRaw, refresh: refreshConfigs } = useApiQuery<any>(
    user?.machine_empresa_id || user?.company_id
      ? `/api/v1/db/configs?company_id=${user?.machine_empresa_id || user?.company_id}`
      : null,
  );

  const [primaryColor, setPrimaryColor] = useState("#4f46e5");
  const [regrasForm, setRegrasForm] = useState<any>({
    taxaCorridaPerEntrega: 1.6,
    pisoFixo: 350.0,
    diaria_weekday: 60.0,
    diaria_saturday: 70.0,
    diaria_sunday: 80.0,
    diaria_holiday: 80.0,
    taxaSupervisao: 10.0,
    garantia_empresa: true,
    retencao_devolucao: true,
    bloquear_fatura: true,
  });

  useEffect(() => {
    if (configsRaw) {
      setRegrasForm({
        taxaCorridaPerEntrega: configsRaw.ride_fee_per_delivery ?? 1.6,
        pisoFixo: configsRaw.minimum_rides_fee_floor ?? 350.0,
        diaria_weekday: configsRaw.daily_rate_weekday ?? 60.0,
        diaria_saturday: configsRaw.daily_rate_saturday ?? 70.0,
        diaria_sunday: configsRaw.daily_rate_sunday ?? 80.0,
        diaria_holiday: configsRaw.daily_rate_holiday ?? 80.0,
        taxaSupervisao: configsRaw.taxa_supervisao ?? 10.0,
        garantia_empresa: configsRaw.guaranteed_mode_enabled ?? true,
        retencao_devolucao: configsRaw.retencao_devolucao ?? true,
        bloquear_fatura: configsRaw.bloquear_fatura ?? true,
      });
    }
  }, [configsRaw]);

  // We could fetch company metadata for primary_color but for now we just use a default state and let the save work.

  const handleSaveConfigs = async () => {
    if (!user?.machine_empresa_id) return;
    setProfileSaving(true);
    try {
      if (activeTab === "regras") {
        const res = await authFetch("/api/v1/db/configs", {
          method: "PUT",
          body: JSON.stringify({
            company_id: user?.machine_empresa_id || user?.company_id,
            ...regrasForm,
          }),
        });
        if (!res.ok) throw new Error("Erro ao salvar regras");
      } else if (activeTab === "whitelabel") {
        if (!currentCompany?.id)
          throw new Error("Empresa não encontrada localmente");
        const res = await authFetch(`/api/v1/db/companies/${currentCompany.id}`, {
          method: "PUT",
          body: JSON.stringify({ primaryColor }),
        });
        if (!res.ok) throw new Error("Erro ao salvar cor primária");
      }
      setProfileSaved(true);
      setTimeout(() => setProfileSaved(false), 3000);
      refreshConfigs();
    } catch (err: any) {
      alert(err?.message || "Falha ao salvar configurações");
    } finally {
      setProfileSaving(false);
    }
  };

  // Tabs visible per role
  // lojista: only perfil + empresa (their own store data)
  // admin: everything
  const allTabs = [
    {
      id: "perfil" as TabId,
      label: "Meu Perfil",
      icon: <User className="w-4 h-4" />,
      adminOnly: false,
    },
    {
      id: "empresa" as TabId,
      label: user?.role === "lojista" ? "Dados da Loja" : "Dados da Central",
      icon: <Building2 className="w-4 h-4" />,
      adminOnly: false,
    },
    {
      id: "whitelabel" as TabId,
      label: "White Label & Cores",
      icon: <Palette className="w-4 h-4" />,
      adminOnly: true,
    },
    {
      id: "regras" as TabId,
      label: "Regras de Negócio Padrão",
      icon: <ClipboardList className="w-4 h-4" />,
      adminOnly: true,
    },
    // { id: "notificacoes" as TabId, label: "Notificações",             icon: <Bell className="w-4 h-4" />,         adminOnly: true },
    // { id: "integracoes" as TabId,  label: "Integrações & API",        icon: <Key className="w-4 h-4" />,          adminOnly: true },
    // { id: "faturamento" as TabId,  label: "Faturamento",              icon: <CreditCard className="w-4 h-4" />,   adminOnly: true },
  ];

  const tabs = allTabs.filter((t) => isAdmin || !t.adminOnly);

  return (
    <div className="space-y-4 pb-12">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-4 rounded-xl shadow-sm ring-1 ring-zinc-950/5">
        <div>
          <h1 className="text-xl font-bold text-zinc-900 tracking-tight">
            Configurações
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            {isAdmin
              ? "Gerencie as preferências da sua conta e do sistema."
              : "Gerencie os dados da sua loja e as preferências da sua conta."}
          </p>
          {!isAdmin && (
            <span className="inline-flex items-center gap-1 mt-2 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-amber-50 text-amber-700 border border-amber-200">
              <Shield className="w-3 h-3" /> Configurações da Loja
            </span>
          )}
        </div>

        <div className="flex">
          {activeTab === "whitelabel" ? null : FUNCTIONAL_TABS.includes(activeTab) ? (
            <button
              onClick={
                activeTab === "perfil" ? handleSaveProfile : handleSaveConfigs
              }
              disabled={profileSaving}
              className="flex items-center gap-1.5 px-4 py-2 bg-zinc-900 text-white rounded-lg hover:bg-zinc-800 text-sm font-semibold shadow-sm transition-all focus:ring-2 focus:ring-zinc-900/10 disabled:opacity-50"
            >
              <Save strokeWidth={2} className="h-4 w-4" />
              {profileSaving
                ? "Salvando..."
                : profileSaved
                  ? "✓ Salvo!"
                  : "Salvar Alterações"}
            </button>
          ) : (
            <div className="flex items-center gap-2 px-4 py-2 bg-zinc-100 text-zinc-400 rounded-lg text-sm font-semibold border border-zinc-200 cursor-not-allowed">
              <Info className="h-4 w-4" /> Em desenvolvimento
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Sidebar Tabs */}
        <div className="lg:col-span-3 space-y-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
                activeTab === tab.id
                  ? "bg-zinc-100 text-zinc-900 shadow-sm border border-zinc-200/50"
                  : "text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900 transparent border border-transparent",
              )}
            >
              <span
                className={cn(
                  "p-1.5 rounded-md",
                  activeTab === tab.id
                    ? "bg-white shadow-sm border border-zinc-200/50 text-indigo-600"
                    : "text-zinc-400",
                )}
              >
                {tab.icon}
              </span>
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content Area */}
        <div className="lg:col-span-9 space-y-6">
          {activeTab === "perfil" && (
            <div className="bg-white rounded-xl shadow-sm ring-1 ring-zinc-950/5 p-6 space-y-6">
              <div>
                <h3 className="text-lg font-bold text-zinc-900 flex items-center gap-2">
                  Meu Perfil
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-200 capitalize">
                    {user?.role || "Usuário"}
                  </span>
                </h3>
                <p className="text-sm text-zinc-500">
                  Atualize suas informações pessoais e credenciais.
                </p>
              </div>
              <div className="h-px w-full bg-zinc-100" />

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">
                    Nome Completo
                  </label>
                  <input
                    type="text"
                    value={profileName}
                    onChange={(e) => setProfileName(e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-zinc-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all shadow-sm"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">
                    E-mail
                  </label>
                  <input
                    type="email"
                    defaultValue={user?.email || ""}
                    className="w-full px-3 py-2 bg-zinc-50 border border-zinc-200 rounded-lg text-sm text-zinc-500 cursor-not-allowed shadow-sm"
                    disabled
                  />
                  <p className="text-[10px] text-zinc-400 mt-1">
                    O e-mail não pode ser alterado. Contate o suporte.
                  </p>
                </div>
              </div>

              <div className="space-y-4 pt-4">
                <h4 className="text-sm font-semibold text-zinc-900 flex items-center gap-2">
                  <Shield className="w-4 h-4 text-zinc-400" />
                  Segurança da Conta
                </h4>
                <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-4 flex items-start gap-3">
                  <Info className="w-4 h-4 text-zinc-400 shrink-0 mt-0.5" />
                  <p className="text-xs text-zinc-500">
                    A alteração de senha será disponibilizada em breve. Para
                    redefinir sua senha, contate o administrador do sistema.
                  </p>
                </div>
              </div>
            </div>
          )}

          {activeTab === "empresa" && (
            <div className="bg-white rounded-xl shadow-sm ring-1 ring-zinc-950/5 p-6 space-y-6">
              <div>
                <h3 className="text-lg font-bold text-zinc-900">
                  {user?.role === "lojista"
                    ? "Dados da Loja"
                    : "Dados da Central / Operador Logístico"}
                </h3>
                <p className="text-sm text-zinc-500">
                  {user?.role === "lojista"
                    ? "Informações cadastrais da sua loja parceira."
                    : "Informações cadastrais da sua central de logística e entregas."}
                </p>
              </div>
              <div className="h-px w-full bg-zinc-100" />

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-1.5 md:col-span-2">
                  <label className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">
                    Razão Social / Nome da Operação
                  </label>
                  <input
                    type="text"
                    defaultValue={companyName || ""}
                    placeholder="Nome da empresa"
                    className="w-full px-3 py-2 bg-zinc-50 border border-zinc-200 rounded-lg text-sm text-zinc-500 cursor-not-allowed shadow-sm"
                    readOnly
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">
                    CNPJ / Documento
                  </label>
                  <input
                    type="text"
                    defaultValue={
                      currentCompany?.documento || currentCompany?.cnpj || ""
                    }
                    placeholder="Não configurado"
                    className="w-full px-3 py-2 bg-zinc-50 border border-zinc-200 rounded-lg text-sm text-zinc-500 cursor-not-allowed shadow-sm"
                    readOnly
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">
                    Telefone Comercial
                  </label>
                  <input
                    type="text"
                    defaultValue={currentCompany?.telefone || ""}
                    placeholder="Não configurado"
                    className="w-full px-3 py-2 bg-zinc-50 border border-zinc-200 rounded-lg text-sm text-zinc-500 cursor-not-allowed shadow-sm"
                    readOnly
                  />
                </div>
                <div className="space-y-1.5 md:col-span-2">
                  <label className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">
                    Endereço da Base Operacional
                  </label>
                  <input
                    type="text"
                    defaultValue={currentCompany?.endereco || ""}
                    placeholder="Não configurado"
                    className="w-full px-3 py-2 bg-zinc-50 border border-zinc-200 rounded-lg text-sm text-zinc-500 cursor-not-allowed shadow-sm"
                    readOnly
                  />
                </div>
              </div>

              <div className="space-y-4 pt-4">
                <h4 className="text-sm font-semibold text-zinc-900 flex items-center gap-2">
                  <Globe className="w-4 h-4 text-zinc-400" />
                  Regionalização
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">
                      Fuso Horário
                    </label>
                    <select
                      className="w-full px-3 py-2 bg-zinc-50 border border-zinc-200 rounded-lg text-sm text-zinc-500 cursor-not-allowed shadow-sm"
                      disabled
                    >
                      <option>Horário de Brasília (UTC-3)</option>
                    </select>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">
                      Moeda Padrão
                    </label>
                    <select
                      className="w-full px-3 py-2 bg-zinc-50 border border-zinc-200 rounded-lg text-sm text-zinc-500 cursor-not-allowed shadow-sm"
                      disabled
                    >
                      <option>Real (BRL) R$</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "whitelabel" && (
            <WhiteLabelConfigPanel />
          )}

          {activeTab === "regras" && (
            <div className="bg-white rounded-xl shadow-sm ring-1 ring-zinc-950/5 p-6 space-y-6">
              <div>
                <h3 className="text-lg font-bold text-zinc-900">
                  Regras de Negócio Padrão
                </h3>
                <p className="text-sm text-zinc-500">
                  Defina os parâmetros padrão de comissionamento e repasses
                  aplicados a novas operações.
                </p>
              </div>
              <div className="h-px w-full bg-zinc-100" />

              <div className="space-y-6">
                <div className="space-y-4">
                  <h4 className="text-sm font-semibold text-zinc-900">
                    Configuração Global de Valores
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">
                        Taxa Padrão por Corrida (Mínima)
                      </label>
                      <div className="relative">
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 text-sm font-medium">
                          R$
                        </span>
                        <input
                          type="number"
                          step="0.01"
                          value={regrasForm.taxaCorridaPerEntrega}
                          onChange={(e) =>
                            setRegrasForm({
                              ...regrasForm,
                              taxaCorridaPerEntrega: Number(e.target.value),
                            })
                          }
                          className="w-full pl-9 pr-3 py-2 bg-white border border-zinc-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all shadow-sm font-mono"
                        />
                      </div>
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">
                        Diária Base Padrão (Dias Úteis)
                      </label>
                      <div className="relative">
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 text-sm font-medium">
                          R$
                        </span>
                        <input
                          type="number"
                          step="0.01"
                          value={regrasForm.diaria_weekday}
                          onChange={(e) =>
                            setRegrasForm({
                              ...regrasForm,
                              diaria_weekday: Number(e.target.value),
                            })
                          }
                          className="w-full pl-9 pr-3 py-2 bg-white border border-zinc-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all shadow-sm font-mono"
                        />
                      </div>
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">
                        Diária Base (Fins de Semana / Feriados)
                      </label>
                      <div className="relative">
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 text-sm font-medium">
                          R$
                        </span>
                        <input
                          type="number"
                          step="0.01"
                          value={regrasForm.diaria_saturday}
                          onChange={(e) =>
                            setRegrasForm({
                              ...regrasForm,
                              diaria_saturday: Number(e.target.value),
                            })
                          }
                          className="w-full pl-9 pr-3 py-2 bg-white border border-zinc-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all shadow-sm font-mono"
                        />
                      </div>
                    </div>
                    <div className="space-y-1.5 md:col-span-2">
                      <label className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">
                        Taxa / Comissão Logística Padrão (%)
                      </label>
                      <div className="relative">
                        <input
                          type="number"
                          step="0.1"
                          value={regrasForm.taxaSupervisao}
                          onChange={(e) =>
                            setRegrasForm({
                              ...regrasForm,
                              taxaSupervisao: Number(e.target.value),
                            })
                          }
                          className="w-full pl-3 pr-9 py-2 bg-white border border-zinc-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all shadow-sm font-mono"
                        />
                        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 text-sm font-medium">
                          %
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="space-y-4 pt-4 border-t border-zinc-100">
                  <h4 className="text-sm font-semibold text-zinc-900 border-b border-transparent">
                    Regras de Exceção e Ocorrências
                  </h4>
                  <div className="grid grid-cols-1 gap-4">
                    <label className="flex items-start gap-3 p-3 bg-zinc-50/50 rounded-lg border border-zinc-200/60 cursor-pointer hover:border-indigo-200 transition-colors">
                      <div className="pt-0.5">
                        <input
                          type="checkbox"
                          checked={regrasForm.garantia_empresa}
                          onChange={(e) =>
                            setRegrasForm({
                              ...regrasForm,
                              garantia_empresa: e.target.checked,
                            })
                          }
                          className="w-4 h-4 text-indigo-600 rounded border-zinc-300 focus:ring-indigo-500 mt-1 cursor-pointer"
                        />
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[13px] font-semibold text-zinc-900">
                          Aplicar Cálculo de Piso (Garantia de Empresa)
                        </span>
                        <span className="text-[11px] font-medium text-zinc-500 mt-0.5 leading-relaxed">
                          Se as taxas de entregas de uma empresa na semana não
                          atingirem o custo operacional daquele alocamento, o
                          sistema cobra o complemento faltante da empresa
                          parceira.
                        </span>
                      </div>
                    </label>

                    <label className="flex items-start gap-3 p-3 bg-zinc-50/50 rounded-lg border border-zinc-200/60 cursor-pointer hover:border-indigo-200 transition-colors">
                      <div className="pt-0.5">
                        <input
                          type="checkbox"
                          checked={regrasForm.retencao_devolucao}
                          onChange={(e) =>
                            setRegrasForm({
                              ...regrasForm,
                              retencao_devolucao: e.target.checked,
                            })
                          }
                          className="w-4 h-4 text-indigo-600 rounded border-zinc-300 focus:ring-indigo-500 mt-1 cursor-pointer"
                        />
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[13px] font-semibold text-zinc-900">
                          Aplicar retenção em caso de devolução
                        </span>
                        <span className="text-[11px] font-medium text-zinc-500 mt-0.5">
                          Na aba de "Devoluções/Extravios", a corrida será
                          abatida do valor bruto de repasse como penalidade de
                          perda logística.
                        </span>
                      </div>
                    </label>

                    <label className="flex items-start gap-3 p-3 bg-zinc-50/50 rounded-lg border border-zinc-200/60 cursor-pointer hover:border-indigo-200 transition-colors">
                      <div className="pt-0.5">
                        <input
                          type="checkbox"
                          checked={regrasForm.bloquear_fatura}
                          onChange={(e) =>
                            setRegrasForm({
                              ...regrasForm,
                              bloquear_fatura: e.target.checked,
                            })
                          }
                          className="w-4 h-4 text-indigo-600 rounded border-zinc-300 focus:ring-indigo-500 mt-1 cursor-pointer"
                        />
                      </div>
                      <div className="flex flex-col">
                        <span className="text-sm font-semibold text-zinc-900">
                          Exigir aprovação de fechamento com dívidas
                        </span>
                        <span className="text-[11px] text-zinc-500 mt-0.5">
                          Se o entregador finalizar o dia devendo valores
                          (adiantamentos não descontados), o sistema bloqueia
                          fatura automática.
                        </span>
                      </div>
                    </label>
                  </div>
                </div>

                <div className="p-4 bg-indigo-50 rounded-lg border border-indigo-100 flex gap-3 text-indigo-800">
                  <ClipboardList className="w-5 h-5 shrink-0 mt-0.5 text-indigo-600" />
                  <div className="text-sm">
                    <p className="font-semibold text-indigo-900">
                      Essas regras são os padrões globais.
                    </p>
                    <p className="mt-1 opacity-90">
                      Eles serão usados automaticamente para novos
                      estabelecimentos cadastrados na plataforma. Você pode
                      ajustar ou sobrescrever essas regras individualmente nas
                      configurações da loja ao repassar orçamentos flexíveis.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "notificacoes" && (
            <div className="bg-white rounded-xl shadow-sm ring-1 ring-zinc-950/5 p-6 space-y-6">
              <DevBanner />
              <div>
                <h3 className="text-lg font-bold text-zinc-900">
                  Notificações e Alertas
                </h3>
                <p className="text-sm text-zinc-500">
                  Decida como e quando o sistema deve avisar sobre as operações.
                </p>
              </div>
              <div className="h-px w-full bg-zinc-100" />

              <div className="space-y-1">
                {[
                  {
                    title: "Novas Corridas na Fila",
                    desc: "Foram disparadas pelo provedor de despacho mas ainda não foram aceitas.",
                  },
                  {
                    title: "Motoboy Ocioso",
                    desc: "Avisar se um motoboy padrão na escala está off-line ou parado demais.",
                  },
                  {
                    title: "Atrasos em Coletas",
                    desc: "Quando um motoboy exceder o tempo limite até a loja parceira.",
                  },
                  {
                    title: "Fechamento Diário",
                    desc: "Receber um resumo do extrato financeiro no fim do dia.",
                  },
                ].map((item, idx) => (
                  <label
                    key={idx}
                    className="flex items-start gap-3 p-3 hover:bg-zinc-50 rounded-lg cursor-pointer transition-colors border border-transparent hover:border-zinc-200/60"
                  >
                    <div className="pt-0.5">
                      <input
                        type="checkbox"
                        defaultChecked={idx < 2}
                        className="w-4 h-4 text-indigo-600 rounded border-zinc-300 focus:ring-indigo-500 mt-1 cursor-pointer"
                      />
                    </div>
                    <div className="flex flex-col">
                      <span className="text-sm font-semibold text-zinc-900">
                        {item.title}
                      </span>
                      <span className="text-[11px] text-zinc-500">
                        {item.desc}
                      </span>
                    </div>
                  </label>
                ))}
              </div>

              <div className="p-4 bg-amber-50 rounded-lg border border-amber-200/50 flex gap-3 text-amber-800">
                <Bell className="w-5 h-5 shrink-0 mt-0.5 text-amber-600" />
                <div className="text-sm">
                  <p className="font-semibold text-amber-900">
                    Notificações via WhatsApp
                  </p>
                  <p className="mt-1 opacity-90">
                    Para receber alertas no WhatsApp, é necessário configurar a
                    integração com uma API de mensagens na aba{" "}
                    <strong className="font-bold">Integrações</strong>.
                  </p>
                </div>
              </div>
            </div>
          )}

          {activeTab === "integracoes" && (
            <div className="bg-white rounded-xl shadow-sm ring-1 ring-zinc-950/5 p-6 space-y-6">
              <div>
                <h3 className="text-lg font-bold text-zinc-900">
                  Integrações Automáticas
                </h3>
                <p className="text-sm text-zinc-500">
                  Conecte o LogiSaaS a provedores de despacho e ERPs
                  financeiros.
                </p>
              </div>
              <div className="h-px w-full bg-zinc-100" />

              <div className="space-y-4">
                {/* Taxi Machine Integration */}
                <div className="border border-zinc-200 rounded-xl p-5 relative overflow-hidden group hover:border-zinc-300 transition-colors bg-white">
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-zinc-900 text-white flex items-center justify-center font-bold text-xs ring-1 ring-black/5 shadow-sm">
                        TM
                      </div>
                      <div>
                        <h4 className="text-sm font-bold text-zinc-900">
                          Taxi Machine
                        </h4>
                        <p className="text-[11px] text-zinc-500 mt-0.5">
                          Sincronização de corridas, motoboys e rotas
                        </p>
                      </div>
                    </div>
                    <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider bg-amber-50 text-amber-700 border border-amber-200/60 shadow-sm">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                      Não configurado
                    </span>
                  </div>

                  <div className="space-y-3">
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">
                        Chave de API (Secret)
                      </label>
                      <div className="flex gap-2">
                        <input
                          type="password"
                          value=""
                          placeholder="Disponível após homologação do conector"
                          className="w-full px-3 py-2 bg-zinc-50 border border-zinc-200 rounded-lg text-sm text-zinc-500 shadow-inner focus:outline-none"
                          disabled
                        />
                        <button disabled className="px-3 py-2 bg-zinc-100 border border-zinc-200 text-zinc-400 rounded-lg text-sm font-semibold cursor-not-allowed">
                          Indisponível
                        </button>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 pt-2">
                      <Database className="w-3.5 h-3.5 text-zinc-400" />
                      <span className="text-[11px] text-zinc-500 font-medium">
                        Nenhuma sincronização realizada
                      </span>
                    </div>
                  </div>
                </div>

                {/* iFood Integration */}
                <div className="border border-zinc-200 rounded-xl p-5 relative overflow-hidden group hover:border-zinc-300 transition-colors bg-white">
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-[#EA1D2C] text-white flex items-center justify-center font-bold text-[10px] ring-1 ring-black/5 shadow-sm">
                        iFood
                      </div>
                      <div>
                        <h4 className="text-sm font-bold text-zinc-900">
                          iFood para Parceiros
                        </h4>
                        <p className="text-[11px] text-zinc-500 mt-0.5">
                          Importação de entregas via logística própria
                        </p>
                      </div>
                    </div>
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-zinc-100 text-zinc-500 border border-zinc-200/60">
                      Desconectado
                    </span>
                  </div>

                  <div className="space-y-2">
                    <button className="w-full px-4 py-2 border border-zinc-200 border-dashed rounded-lg text-sm font-semibold text-zinc-600 hover:border-zinc-300 hover:text-zinc-900 hover:bg-zinc-50 transition-all">
                      Configurar Integração
                    </button>
                  </div>
                </div>

                {/* Bling ERP Integration */}
                <div className="border border-zinc-200 rounded-xl p-5 relative overflow-hidden group hover:border-zinc-300 transition-colors bg-white">
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-emerald-600 text-white flex items-center justify-center font-bold text-[10px] ring-1 ring-black/5 shadow-sm">
                        ERP
                      </div>
                      <div>
                        <h4 className="text-sm font-bold text-zinc-900">
                          Bling ERP / NF-e
                        </h4>
                        <p className="text-[11px] text-zinc-500 mt-0.5">
                          Emissão de notas fiscais de serviço (NFS-e)
                        </p>
                      </div>
                    </div>
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-zinc-100 text-zinc-500 border border-zinc-200/60">
                      Desconectado
                    </span>
                  </div>

                  <div className="space-y-2">
                    <button className="w-full px-4 py-2 border border-zinc-200 border-dashed rounded-lg text-sm font-semibold text-zinc-600 hover:border-zinc-300 hover:text-zinc-900 hover:bg-zinc-50 transition-all">
                      Configurar Integração
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "faturamento" && (
            <div className="bg-white rounded-xl shadow-sm ring-1 ring-zinc-950/5 p-6 space-y-6">
              <DevBanner />
              <div>
                <h3 className="text-lg font-bold text-zinc-900">
                  Plano e Faturamento
                </h3>
                <p className="text-sm text-zinc-500">
                  Gerencie sua assinatura LogiSaaS e métodos de pagamento.
                </p>
              </div>
              <div className="h-px w-full bg-zinc-100" />

              <div className="bg-zinc-900 rounded-xl p-6 text-white relative overflow-hidden">
                <div className="absolute top-0 right-0 p-32 bg-indigo-500/20 blur-3xl rounded-full" />
                <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                  <div>
                    <div className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-white/10 text-white border border-white/10 mb-3">
                      Plano Atual
                    </div>
                    <h4 className="text-2xl font-bold">LogiSaaS Pro</h4>
                    <p className="text-zinc-400 text-sm mt-1">
                      Até 50 motoboys e integrações ilimitadas.
                    </p>
                  </div>
                  <div className="text-right flex flex-col items-start md:items-end w-full md:w-auto">
                    <span className="text-3xl font-bold tracking-tight">
                      R$ 299
                      <span className="text-lg text-zinc-400 font-medium">
                        /mês
                      </span>
                    </span>
                    <button className="mt-4 w-full md:w-auto px-4 py-2 bg-white text-zinc-900 rounded-lg text-sm font-bold shadow-sm hover:bg-zinc-100 transition-colors">
                      Mudar de Plano
                    </button>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="text-sm font-semibold text-zinc-900">
                  Método de Pagamento
                </h4>
                <div className="border border-zinc-200 rounded-xl p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-8 rounded bg-zinc-100 border border-zinc-200 flex items-center justify-center font-bold text-indigo-900 text-[10px]">
                      VISA
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-zinc-900">
                        •••• •••• •••• 4242
                      </p>
                      <p className="text-[11px] text-zinc-500">
                        Expira em 12/2028
                      </p>
                    </div>
                  </div>
                  <button className="text-sm font-semibold text-indigo-600 hover:text-indigo-700">
                    Atualizar
                  </button>
                </div>
              </div>

              <div className="space-y-4 pt-4">
                <h4 className="text-sm font-semibold text-zinc-900">
                  Histórico de Faturas
                </h4>
                <div className="border border-zinc-200 rounded-xl overflow-hidden">
                  <table className="w-full text-left text-sm whitespace-nowrap">
                    <thead className="bg-zinc-50 border-b border-zinc-200 text-zinc-500 font-semibold text-[10px] uppercase tracking-wider">
                      <tr>
                        <th className="px-4 py-2">Data</th>
                        <th className="px-4 py-2">Valor</th>
                        <th className="px-4 py-2">Status</th>
                        <th className="px-4 py-2 text-right">Fatura</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-100">
                      {["10 Fev 2026", "10 Jan 2026", "10 Dez 2025"].map(
                        (date, i) => (
                          <tr key={i}>
                            <td className="px-4 py-3 text-zinc-900 font-medium text-xs">
                              {date}
                            </td>
                            <td className="px-4 py-3 text-zinc-600 font-mono text-xs">
                              R$ 299,00
                            </td>
                            <td className="px-4 py-3">
                              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200/60">
                                Pago
                              </span>
                            </td>
                            <td className="px-4 py-3 text-right">
                              <button className="text-xs font-semibold text-indigo-600 hover:text-indigo-700">
                                Baixar PDF
                              </button>
                            </td>
                          </tr>
                        ),
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
