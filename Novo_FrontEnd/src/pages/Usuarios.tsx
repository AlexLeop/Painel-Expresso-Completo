import { logger } from "@/lib/logger";
import { useState, useEffect, useMemo } from "react";
import {
  Search,
  Plus,
  Filter,
  UserCog,
  User,
  Phone,
  MoreVertical,
  Edit2,
  Trash2,
  Power,
  PowerOff,
  Loader2,
} from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "../lib/utils";
import { UserModal, UserType } from "../components/UserModal";
import { ConfirmModal } from "../components/ConfirmModal";
import { authFetch } from "../lib/api";

export function Usuarios() {
  const [usuarios, setUsuarios] = useState<UserType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<UserType | null>(null);

  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [usuarioToDelete, setUsuarioToDelete] = useState<string | null>(null);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await authFetch("/api/v1/db/users");
      if (res.ok) {
        const data = await res.json();
        const rawList = Array.isArray(data) ? data : data.users || [];
        // Map API fields (fullName, role, companies) → UserType shape
        const ROLE_LABEL: Record<string, string> = {
          admin: "Administrador",
          manager: "Gestor",
          supervisor: "Supervisor",
          coordinator: "Coordenador",
          operator: "Operador",
          viewer: "Visualizador",
        };
        const fetchedUsers = rawList.map((u: any) => ({
          id: u.id,
          nome: u.fullName || u.nome || u.email?.split("@")[0] || "Sem nome",
          email: u.email || "",
          telefone: u.telefone || u.phone || "",
          cargo: ROLE_LABEL[u.role] || u.cargo || u.role || "Operador",
          status: u.active === false ? "Inativo" : "Ativo",
          empresas: Array.isArray(u.companies)
            ? u.companies.map((c: any) => c.id || c)
            : u.empresas || [],
        }));
        setUsuarios(fetchedUsers);
      } else {
        setError("Falha ao carregar usuários.");
        setUsuarios([]);
      }
    } catch (err: any) {
      logger.error("Failed to fetch users:", err);
      setError(err.message || "Erro de conexão ao buscar usuários.");
      setUsuarios([]);
    } finally {
      setLoading(false);
    }
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.05 },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 10 },
    show: { opacity: 1, y: 0 },
  };

  const handleOpenModal = (user?: UserType) => {
    setSelectedUser(user || null);
    setIsModalOpen(true);
  };

  const handleSaveUser = async (user: UserType) => {
    try {
      const ROLE_TO_API: Record<string, string> = {
        Administrador: "admin",
        Gestor: "manager",
        Supervisor: "supervisor",
        Coordenador: "coordinator",
        Operador: "operator",
        Visualizador: "viewer",
      };
      const apiRole = ROLE_TO_API[user.cargo] || "operator";

      const previousUsuarios = usuarios;
      if (user.id) {
        setUsuarios(usuarios.map((u) => (u.id === user.id ? user : u)));
        const res = await authFetch("/api/v1/db/users", {
          method: "PUT",
          body: JSON.stringify({
            id: user.id,
            fullName: user.nome,
            role: apiRole,
            companyIds: user.empresas,
          }),
        });
        if (!res.ok) {
          setUsuarios(previousUsuarios);
          const d = await res.json().catch(() => ({}));
          throw new Error(d.error || "Erro ao atualizar usuário");
        }
      } else {
        const payload = {
          email: user.email,
          password: user.password || "Mudar@123",
          fullName: user.nome,
          role: apiRole,
          companyIds: user.empresas,
        };
        const response = await authFetch("/api/v1/db/users", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        const savedData = await response.json();
        if (savedData.error) {
          alert(`Erro: ${savedData.error}`);
          return;
        }
      }
      fetchUsers();
    } catch (error) {
      logger.error("Failed to save user", error);
      alert("Falha ao salvar usuário. Verifique a conexão.");
      fetchUsers();
    }
    setIsModalOpen(false);
  };

  const handleDeleteUser = (id: string) => {
    setUsuarioToDelete(id);
    setIsConfirmOpen(true);
  };

  const confirmDelete = async () => {
    if (usuarioToDelete !== null) {
      try {
        await authFetch(`/api/v1/db/users?id=${usuarioToDelete}`, {
          method: "DELETE",
        });
        setUsuarios(usuarios.filter((u) => u.id !== usuarioToDelete));
      } catch (err) {
        logger.error("Failed to delete user", err);
        alert("Falha ao excluir usuário.");
        fetchUsers();
      } finally {
        setUsuarioToDelete(null);
        setIsConfirmOpen(false);
      }
    }
  };

  const handleToggleStatus = async (id: string) => {
    const user = usuarios.find((u) => u.id === id);
    if (!user) return;
    const newStatus = user.status === "Ativo" ? "Inativo" : "Ativo";
    const previousUsuarios = usuarios;
    setUsuarios(
      usuarios.map((u) => (u.id === id ? { ...u, status: newStatus } : u)),
    );
    try {
      const res = await authFetch("/api/v1/db/users", {
        method: "PUT",
        body: JSON.stringify({ id, active: newStatus === "Ativo" }),
      });
      if (!res.ok) {
        setUsuarios(previousUsuarios);
        alert("Falha ao alterar status do usuário.");
      }
    } catch (err) {
      logger.error("Failed to toggle user status:", err);
      setUsuarios(previousUsuarios);
      alert("Falha ao alterar status do usuário.");
    }
  };

  const filteredUsuarios = useMemo(() => {
    const term = searchTerm.toLowerCase().trim();
    if (!term) return usuarios;
    return usuarios.filter(
      (u) =>
        u.nome?.toLowerCase().includes(term) ||
        u.email?.toLowerCase().includes(term) ||
        u.cargo?.toLowerCase().includes(term),
    );
  }, [usuarios, searchTerm]);

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-4 rounded-xl shadow-sm ring-1 ring-zinc-950/5">
        <div>
          <h1 className="text-xl font-bold text-zinc-900 tracking-tight">
            Usuários
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            Gerencie os acessos ao painel Administrativo do sistema.
          </p>
        </div>

        <div className="flex bg-zinc-100 p-1 rounded-lg">
          <button
            onClick={() => handleOpenModal()}
            className="flex items-center gap-1.5 px-4 py-2 bg-zinc-900 text-white rounded-md hover:bg-zinc-800 text-sm font-semibold shadow-sm transition-all focus:ring-2 focus:ring-zinc-900/10"
          >
            <Plus strokeWidth={2} className="h-4 w-4" /> Novo Usuário
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-[0_1px_3px_0_rgba(0,0,0,0.05),_0_0_0_1px_rgba(0,0,0,0.05)] overflow-hidden flex flex-col">
        <div className="p-3 border-b border-zinc-200 flex flex-col sm:flex-row gap-3 items-center justify-between bg-zinc-50/50">
          <div className="relative w-full sm:max-w-md group">
            <Search
              strokeWidth={1.5}
              className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400 group-focus-within:text-zinc-600 transition-colors"
            />
            <input
              type="text"
              placeholder="Buscar por nome, e-mail ou cargo..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all placeholder:text-zinc-400 shadow-sm"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-zinc-50 border-b border-zinc-200 text-zinc-500 font-semibold text-[10px] uppercase tracking-wider">
              <tr>
                <th className="px-4 py-2">Usuário</th>
                <th className="px-4 py-2">Cargo</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Empresas</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {error && (
                <tr>
                  <td
                    colSpan={5}
                    className="px-4 py-8 text-center text-red-500 bg-red-50/50"
                  >
                    <span className="font-bold">Erro:</span> {error}
                  </td>
                </tr>
              )}
              {filteredUsuarios.length === 0 && !error && !loading && (
                <tr>
                  <td
                    colSpan={5}
                    className="px-4 py-8 text-center text-zinc-500"
                  >
                    {searchTerm
                      ? "Nenhum usuário encontrado para a busca."
                      : "Nenhum usuário encontrado."}
                  </td>
                </tr>
              )}
              {filteredUsuarios.map((usuario) => (
                <motion.tr
                  variants={itemVariants}
                  key={usuario.id}
                  className="hover:bg-zinc-50/80 transition-colors group"
                >
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-3">
                      <div className="h-8 w-8 rounded-full bg-zinc-100 border border-zinc-200 flex items-center justify-center text-zinc-800 font-bold text-xs shrink-0">
                        {(usuario.nome || "?")
                          .split(" ")
                          .map((n: string) => n[0])
                          .slice(0, 2)
                          .join("")}
                      </div>
                      <div className="flex flex-col">
                        <span className="font-semibold text-zinc-900 block text-sm">
                          {usuario.nome}
                        </span>
                        <div className="flex items-center gap-1.5 text-[11px] text-zinc-500 mt-0.5">
                          {usuario.email}
                          <span className="text-zinc-300">•</span>
                          {usuario.telefone}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-1.5 text-xs text-zinc-700 font-medium">
                      <UserCog
                        strokeWidth={1.5}
                        className="h-3.5 w-3.5 text-zinc-400"
                      />
                      {usuario.cargo}
                    </div>
                  </td>
                  <td className="px-4 py-2">
                    <span
                      className={cn(
                        "inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider",
                        usuario.status === "Ativo"
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200/60"
                          : "bg-zinc-100 text-zinc-600 border border-zinc-200/60",
                      )}
                    >
                      {usuario.status}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-zinc-500 text-xs">
                    {(usuario.empresas || []).length}{" "}
                    {(usuario.empresas || []).length === 1
                      ? "empresa"
                      : "empresas"}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <div className="flex justify-end gap-1">
                      <button
                        onClick={() =>
                          usuario.id && handleToggleStatus(usuario.id)
                        }
                        className={cn(
                          "p-1 px-1.5 rounded-md transition-colors",
                          usuario.status === "Ativo"
                            ? "text-zinc-400 hover:text-amber-600 hover:bg-amber-50"
                            : "text-zinc-400 hover:text-emerald-600 hover:bg-emerald-50",
                        )}
                        title={
                          usuario.status === "Ativo" ? "Desativar" : "Ativar"
                        }
                      >
                        {usuario.status === "Ativo" ? (
                          <PowerOff strokeWidth={1.5} className="h-3.5 w-3.5" />
                        ) : (
                          <Power strokeWidth={1.5} className="h-3.5 w-3.5" />
                        )}
                      </button>
                      <button
                        onClick={() => handleOpenModal(usuario)}
                        className="p-1 px-1.5 text-zinc-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-md transition-colors"
                        title="Editar"
                      >
                        <Edit2 strokeWidth={1.5} className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() =>
                          usuario.id && handleDeleteUser(usuario.id)
                        }
                        className="p-1 px-1.5 text-zinc-400 hover:text-rose-600 hover:bg-rose-50 rounded-md transition-colors"
                        title="Excluir"
                      >
                        <Trash2 strokeWidth={1.5} className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="px-4 py-3 border-t border-zinc-200 bg-zinc-50 flex items-center justify-center">
          <span className="text-[10px] font-medium text-zinc-500 uppercase tracking-wider">
            Mostrando {filteredUsuarios.length} de {usuarios.length} usuários
          </span>
        </div>
      </div>

      <UserModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        user={selectedUser}
        onSave={handleSaveUser}
      />

      <ConfirmModal
        isOpen={isConfirmOpen}
        title="Excluir Usuário"
        message="Tem certeza que deseja excluir este usuário? O acesso dele ao sistema será revogado imediatamente."
        onConfirm={confirmDelete}
        onCancel={() => {
          setIsConfirmOpen(false);
          setUsuarioToDelete(null);
        }}
      />
    </div>
  );
}
