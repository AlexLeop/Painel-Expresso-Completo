import React, { useState, useEffect } from "react";
import {
  LayoutDashboard,
  Bike,
  Store,
  CalendarDays,
  FileSpreadsheet,
  Wallet,
  BarChart3,
  Camera,
  RefreshCcw,
  Users,
  Settings,
  Menu,
  Bell,
  Search,
  MapPin,
  ChevronDown,
  LogOut,
  ChevronLeft,
  ChevronRight,
  X,
  Activity,
  History,
} from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { cn } from "../../lib/utils";
import { useAuth } from "../../contexts/AuthContext";

// ─── Roles (matching old frontend) ────────────────────────────
// admin      → acessa tudo
// lojista    → acessa tudo EXCETO: motoboys, empresas, sync, usuarios, snapshots
// supervisor → acessa APENAS: /escala
// coordinator→ acessa APENAS: /escala

const ADMIN_ONLY_ROUTES = [
  "/motoboys",
  "/empresas",
  "/sync",
  "/usuarios",
  "/snapshots",
  "/financeiro",
];
const SUPERVISOR_ONLY_ROUTE = "/escala";
const SUPERVISOR_ROLES = ["supervisor", "coordinator"];

const navigationGroups = [
  {
    title: "Operacional",
    items: [
      {
        name: "Dashboard",
        href: "/",
        icon: LayoutDashboard,
        roles: ["admin", "lojista"],
      },
      {
        name: "Corridas",
        href: "/corridas",
        icon: MapPin,
        roles: ["admin", "lojista"],
      },
      {
        name: "Escala",
        href: "/escala",
        icon: CalendarDays,
        roles: ["admin", "supervisor", "coordinator"],
      },
    ],
  },
  {
    title: "Gestão",
    items: [
      { name: "Motoboys", href: "/motoboys", icon: Bike, roles: ["admin"] },
      { name: "Empresas", href: "/empresas", icon: Store, roles: ["admin"] },
      { name: "Usuários", href: "/usuarios", icon: Users, roles: ["admin"] },
    ],
  },
  {
    title: "Financeiro & Dados",
    items: [
      {
        name: "Lançamentos",
        href: "/lancamentos",
        icon: FileSpreadsheet,
        roles: ["admin", "lojista"],
      },
      {
        name: "Financeiro",
        href: "/financeiro",
        icon: Wallet,
        roles: ["admin"],
      },
      {
        name: "Relatórios",
        href: "/relatorios",
        icon: BarChart3,
        roles: ["admin", "lojista"],
      },
      {
        name: "Histórico",
        href: "/historico",
        icon: History,
        roles: ["admin", "lojista"],
      },
      {
        name: "Gerencial",
        href: "/gerencial",
        icon: Activity,
        roles: ["admin"],
      },
    ],
  },
  {
    title: "Sistema",
    items: [
      {
        name: "Configurações",
        href: "/configuracoes",
        icon: Settings,
        roles: ["admin", "lojista"],
      },
      { name: "Snapshots", href: "/snapshots", icon: Camera, roles: ["admin"] },
      { name: "Sync", href: "/sync", icon: RefreshCcw, roles: ["admin"] },
    ],
  },
];

const navigation = navigationGroups.flatMap((g) => g.items);

export function AppLayout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem("nevesgo:sidebarCollapsed") === "1";
    } catch {
      return false;
    }
  });

  const { session, logout, changeTenant, globalSearch, setGlobalSearch } =
    useAuth();
  const user = session?.user;
  const rawRole = user?.role || "lojista";
  const role = rawRole === "administrador" ? "admin" : rawRole;
  const isSupervisor = SUPERVISOR_ROLES.includes(role);
  const isMobileOpen = sidebarOpen;

  // Shortcut ⌘K / Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        const input = document.getElementById("global-search-input");
        input?.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(
        "nevesgo:sidebarCollapsed",
        sidebarCollapsed ? "1" : "0",
      );
    } catch {
      return;
    }
  }, [sidebarCollapsed]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setUserDropdownOpen(false);
        setSidebarOpen(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      const target = e.target as HTMLElement | null;
      if (!target) return;
      if (target.closest('[data-user-menu-root="1"]')) return;
      setUserDropdownOpen(false);
    }
    if (!userDropdownOpen) return;
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [userDropdownOpen]);

  // Route guard — mirrors old frontend AppContext.tsx
  useEffect(() => {
    if (!role) return;
    // Supervisors can only access /escala
    if (isSupervisor && location.pathname !== SUPERVISOR_ONLY_ROUTE) {
      navigate(SUPERVISOR_ONLY_ROUTE, { replace: true });
      return;
    }
    // Lojistas cannot access admin-only routes
    if (role === "lojista" && ADMIN_ONLY_ROUTES.includes(location.pathname)) {
      navigate("/", { replace: true });
    }
  }, [location.pathname, role, isSupervisor, navigate]);

  // Supervisors get a minimal layout (just the page, no sidebar)
  if (isSupervisor) {
    return (
      <div className="h-screen flex flex-col bg-[#F9F9FA] overflow-hidden">
        <header className="h-14 bg-white border-b border-zinc-200 flex items-center justify-between px-6 shrink-0">
          <div className="flex items-center gap-2">
            <Bike strokeWidth={2.5} className="h-5 w-5 text-zinc-900" />
            <span className="text-sm font-bold text-zinc-900">
              Escala — {user?.name}
            </span>
          </div>
          <button
            onClick={logout}
            className="flex items-center gap-2 text-xs text-zinc-500 hover:text-zinc-900 transition-colors"
          >
            <LogOut className="h-4 w-4" /> Sair
          </button>
        </header>
        <main className="flex-1 overflow-hidden">{children}</main>
      </div>
    );
  }

  return (
    <div className="h-screen bg-[#F9F9FA] flex overflow-hidden">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-[#0a0a0a]/40 backdrop-blur-sm lg:hidden transition-opacity"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        aria-label="Menu lateral"
        className={cn(
          "fixed inset-y-0 left-0 z-50 bg-[#0a0a0a] text-zinc-300 transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static flex flex-col border-r border-[#1a1a1a]",
          sidebarCollapsed ? "w-[72px]" : "w-[240px]",
          sidebarOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div
          className={cn(
            "h-14 flex items-center border-b border-[#1a1a1a] shrink-0",
            sidebarCollapsed ? "px-2" : "px-5",
          )}
        >
          <div
            className={cn(
              "flex items-center gap-2 min-w-0",
              sidebarCollapsed && "w-full justify-center",
            )}
          >
            <div className="bg-white p-1 rounded-md min-w-[28px] h-[28px] flex items-center justify-center">
              <img
                src="/favicon.ico"
                alt="Expresso Neves"
                className="h-5 w-5 object-contain"
              />
            </div>
            {!sidebarCollapsed && (
              <div className="min-w-0">
                <div className="text-[13px] font-extrabold tracking-tight text-white leading-tight truncate">
                  Expresso Neves
                </div>
                <div className="text-[10px] font-semibold tracking-[0.18em] uppercase text-zinc-500 truncate">
                  Portal Logístico
                </div>
              </div>
            )}
          </div>

          <div
            className={cn(
              "ml-auto flex items-center gap-1",
              sidebarCollapsed && "hidden lg:flex",
            )}
          >
            <button
              type="button"
              onClick={() => setSidebarCollapsed((v) => !v)}
              className={cn(
                "hidden lg:inline-flex items-center justify-center h-9 w-9 rounded-lg text-zinc-400 hover:text-white hover:bg-[#151515] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#E55C00] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0a0a0a] transition-colors",
                sidebarCollapsed && "h-10 w-10",
              )}
              aria-label={sidebarCollapsed ? "Expandir menu" : "Recolher menu"}
            >
              {sidebarCollapsed ? (
                <ChevronRight className="h-4 w-4" />
              ) : (
                <ChevronLeft className="h-4 w-4" />
              )}
            </button>
          </div>

          <button
            type="button"
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden ml-auto inline-flex items-center justify-center h-10 w-10 rounded-lg text-zinc-300 hover:text-white hover:bg-[#151515] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#E55C00] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0a0a0a]"
            aria-label="Fechar menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div
          className={cn(
            "py-4 flex-1 overflow-y-auto min-h-0 space-y-6",
            sidebarCollapsed ? "px-2" : "px-3",
          )}
        >
          {navigationGroups.map((group) => {
            const visibleItems = group.items.filter((item) =>
              item.roles.includes(role),
            );
            if (visibleItems.length === 0) return null;

            return (
              <div key={group.title} className="space-y-1">
                {!sidebarCollapsed && (
                  <div className="text-[10px] font-bold text-zinc-500 tracking-widest uppercase mb-2 px-3">
                    {group.title}
                  </div>
                )}
                <nav
                  className="space-y-0.5"
                  aria-label={`Navegação ${group.title}`}
                >
                  {visibleItems.map((item) => {
                    const isActive =
                      location.pathname === item.href ||
                      (item.href !== "/" &&
                        location.pathname.startsWith(item.href));
                    return (
                      <Link
                        key={item.name}
                        to={item.href}
                        onClick={() => setSidebarOpen(false)}
                        aria-current={isActive ? "page" : undefined}
                        aria-label={sidebarCollapsed ? item.name : undefined}
                        className={cn(
                          "flex items-center gap-3 rounded-xl text-[13px] transition-all duration-200 group focus:outline-none focus-visible:ring-2 focus-visible:ring-[#E55C00] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0a0a0a]",
                          sidebarCollapsed
                            ? "px-3 py-2.5 justify-center"
                            : "px-3 py-2",
                          isActive
                            ? "bg-[#141414] text-white font-semibold ring-1 ring-[#E55C00]/30 shadow-[0_10px_30px_-20px_rgba(229,92,0,0.55)]"
                            : "text-zinc-400 hover:text-white hover:bg-[#151515]",
                        )}
                      >
                        <item.icon
                          strokeWidth={isActive ? 2.5 : 2}
                          className={cn(
                            "h-4 w-4 transition-colors",
                            isActive
                              ? "text-[#E55C00]"
                              : "text-zinc-500 group-hover:text-zinc-300",
                          )}
                        />
                        {!sidebarCollapsed ? (
                          <span className="truncate">{item.name}</span>
                        ) : (
                          <span className="sr-only">{item.name}</span>
                        )}
                        {isActive && !sidebarCollapsed && (
                          <span
                            className="ml-auto h-2 w-2 rounded-full bg-[#E55C00] shadow-[0_0_0_3px_rgba(229,92,0,0.18)]"
                            aria-hidden="true"
                          />
                        )}
                      </Link>
                    );
                  })}
                </nav>
              </div>
            );
          })}
        </div>

        <div
          className={cn(
            "border-t border-[#1a1a1a] shrink-0 bg-[#0a0a0a] relative",
            sidebarCollapsed ? "p-2" : "p-3",
          )}
          data-user-menu-root="1"
        >
          <button
            onClick={() => setUserDropdownOpen(!userDropdownOpen)}
            className={cn(
              "flex items-center w-full gap-3 rounded-xl text-sm hover:bg-[#151515] transition-colors group focus:outline-none focus-visible:ring-2 focus-visible:ring-[#E55C00] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0a0a0a]",
              sidebarCollapsed ? "px-3 py-2.5 justify-center" : "px-3 py-2.5",
            )}
            aria-haspopup="menu"
            aria-expanded={userDropdownOpen}
            aria-label="Menu do usuário"
          >
            <div className="h-8 w-8 rounded-md bg-linear-to-tr from-zinc-800 to-zinc-700 flex items-center justify-center text-white text-xs font-semibold shadow-inner ring-1 ring-white/5 uppercase">
              {user?.name?.substring(0, 2) || "U"}
            </div>
            {!sidebarCollapsed && (
              <>
                <div className="flex-1 text-left min-w-0">
                  <p className="text-[13px] font-semibold text-zinc-100 truncate group-hover:text-white transition-colors">
                    {user?.name || "Usuário"}
                  </p>
                  <p className="text-[11px] text-zinc-500 truncate mt-0.5 capitalize">
                    {user?.role || "Lojista"}
                  </p>
                </div>
                <ChevronDown
                  strokeWidth={2}
                  className={cn(
                    "h-4 w-4 text-zinc-600 group-hover:text-zinc-400 transition-all",
                    userDropdownOpen && "rotate-180",
                  )}
                />
              </>
            )}
          </button>

          {userDropdownOpen && (
            <div
              role="menu"
              aria-label="Ações do usuário"
              className={cn(
                "absolute bottom-full mb-2 bg-[#111111] border border-[#2a2a2a] rounded-xl shadow-xl overflow-hidden py-1 z-50",
                sidebarCollapsed ? "left-2 right-2" : "left-3 right-3",
              )}
            >
              <button
                onClick={() => {
                  logout();
                  setUserDropdownOpen(false);
                }}
                role="menuitem"
                className="w-full flex items-center gap-2 px-3 py-2 text-[13px] text-zinc-200 hover:text-white hover:bg-[#1a1a1a] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#E55C00] focus-visible:ring-inset"
              >
                <LogOut className="h-4 w-4" /> Sair da conta
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top header */}
        <header className="h-14 bg-white/80 backdrop-blur-md border-b border-zinc-200/80 flex items-center justify-between px-4 sm:px-6 z-10 shrink-0 shadow-[0_1px_2px_0_rgba(0,0,0,0.02)]">
          <div className="flex items-center gap-4 lg:hidden">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 -ml-2 text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100 rounded-md transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#E55C00]"
              aria-label="Abrir menu"
              aria-expanded={isMobileOpen}
            >
              <Menu strokeWidth={2} className="h-5 w-5" />
            </button>
          </div>

          <div className="flex-1 flex justify-between items-center gap-4">
            <div className="flex items-center gap-2 text-[13px] text-zinc-500 font-medium">
              <span className="hidden sm:inline-block">Plataforma</span>
              <span className="hidden sm:inline-block text-zinc-300 px-1">
                /
              </span>
              <span className="font-semibold text-zinc-900">
                {navigation.find(
                  (n) =>
                    n.href === location.pathname ||
                    (n.href !== "/" && location.pathname.startsWith(n.href)),
                )?.name || "Página"}
              </span>
            </div>

            <div className="flex items-center gap-4">
              {user?.companies && user.companies.length > 1 && (
                <div className="relative mr-2">
                  <Store
                    strokeWidth={2}
                    className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400"
                  />
                  <select
                    value={user.machine_empresa_id}
                    onChange={(e) => changeTenant(e.target.value)}
                    className="pl-9 pr-8 py-1.5 text-[12px] font-medium bg-[#F5F5F7] border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0a0a0a]/10 focus:border-zinc-300 transition-all appearance-none cursor-pointer max-w-[200px] truncate"
                  >
                    {user.companies.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.nome}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3 w-3 text-zinc-400 pointer-events-none" />
                </div>
              )}

              <div className="relative hidden md:block w-72 group">
                <Search
                  strokeWidth={2}
                  className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-zinc-400 group-focus-within:text-zinc-900 transition-colors"
                />
                <input
                  id="global-search-input"
                  type="text"
                  value={globalSearch}
                  onChange={(e) => setGlobalSearch(e.target.value)}
                  placeholder="Buscar comando, id, cliente..."
                  className="w-full pl-9 pr-4 py-1.5 text-[13px] font-medium bg-[#F5F5F7] border border-transparent rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0a0a0a]/10 focus:border-zinc-300 focus:bg-white transition-all placeholder:text-zinc-400"
                />
                <div className="absolute right-2 top-1/2 -translate-y-1/2 hidden lg:flex items-center">
                  <span className="text-[10px] font-mono text-zinc-400 border border-zinc-200 rounded px-1.5 py-0.5 bg-white">
                    ⌘K
                  </span>
                </div>
              </div>

              <div className="h-6 w-px bg-zinc-200 hidden sm:block mx-1"></div>

              <button
                className="p-2 text-zinc-400 hover:text-zinc-900 hover:bg-zinc-100 rounded-lg relative transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#E55C00]"
                aria-label="Notificações"
              >
                <span className="absolute top-2 right-2.5 h-1.5 w-1.5 rounded-full bg-rose-500 ring-2 ring-white"></span>
                <Bell strokeWidth={2} className="h-4 w-4" />
              </button>
            </div>
          </div>
        </header>

        <main
          className={cn(
            "flex-1 w-full",
            location.pathname === "/corridas"
              ? "overflow-hidden"
              : "overflow-y-auto overflow-x-hidden",
          )}
        >
          <div
            className={cn(
              "animate-in fade-in duration-300 slide-in-from-bottom-2",
              location.pathname === "/corridas" &&
                "h-full flex flex-col min-h-0",
              location.pathname !== "/corridas" && "p-4 sm:p-6",
            )}
          >
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
