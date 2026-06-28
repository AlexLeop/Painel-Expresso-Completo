import { logger } from "@/lib/logger";
import { useState, useEffect, useMemo } from "react";
import {
  Plus,
  Search,
  Filter,
  CalendarDays,
  ArrowUpRight,
  ArrowDownRight,
  MoreVertical,
  FileText,
  Edit2,
  Trash2,
  Loader2,
} from "lucide-react";
import { motion } from "framer-motion";
import { cn, formatCurrency } from "../lib/utils";
import { LancamentoModal, LancamentoType } from "../components/LancamentoModal";
import { ConfirmModal } from "../components/ConfirmModal";
import { authFetch, getSession } from "../lib/api";

export function Lancamentos() {
  const [lancamentos, setLancamentos] = useState<LancamentoType[]>([]);
  const [motoboys, setMotoboys] = useState<{ id: string; nome: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [lancamentoToEdit, setLancamentoToEdit] =
    useState<LancamentoType | null>(null);
  const [defaultCategoria, setDefaultCategoria] = useState<
    "Crédito" | "Débito"
  >("Débito");

  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [lancamentoToDelete, setLancamentoToDelete] = useState<number | null>(
    null,
  );

  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 15;

  const session = getSession();
  const isAdmin =
    session?.user?.role === "admin" ||
    session?.user?.role === "administrador" ||
    session?.user?.role === "master";

  useEffect(() => {
    fetchLancamentos();
  }, []);

  const fetchLancamentos = async () => {
    setLoading(true);
    setError(null);
    try {
      const session = getSession();
      const companyId = session?.user?.machine_empresa_id || session?.user?.company_id || "";
      if (!companyId) {
        setError("Empresa não encontrada na sessão. Faça login novamente.");
        setLoading(false);
        return;
      }
      const [res, driversRes] = await Promise.all([
        authFetch(`/api/db/entries?company_id=${companyId}`),
        authFetch(
          `/api/db/company-drivers?company_id=${companyId}&active_only=0`,
        ),
      ]);

      if (driversRes.ok) {
        const dData = await driversRes.json();
        const rawDrivers = Array.isArray(dData) ? dData : dData.motoboys || [];
        setMotoboys(
          rawDrivers.map((d: any) => ({
            id: String(d.driverId || d.id || ""),
            nome: d.driverName || d.nome || d.name || "Sem nome",
          })),
        );
      }

      if (res.ok) {
        const data = await res.json();
        const rawList = Array.isArray(data) ? data : data.lancamentos || [];
        // Map API fields → LancamentoType shape
        const fetchedLancamentos = rawList
          .map((e: any) => ({
            id: e.id,
            motoboy: e.driverName || e.motoboy || "",
            tipo: e.type || e.tipo || "",
            categoria:
              e.type === "adiantamento" || e.categoria === "Débito"
                ? "Débito"
                : "Crédito",
            valor: Number(e.amount ?? e.valor ?? 0),
            data: e.date
              ? e.date.split("T")[0].split("-").reverse().join("/")
              : e.data || "",
            descricao: e.description || e.descricao || "",
            visibilidade: e.visibilidade || "ambos",
            entregas: e.entregas || 1,
          }))
          .filter((l: any) => isAdmin || l.visibilidade !== "motoboy");
        setLancamentos(fetchedLancamentos);
      } else {
        setError("Falha ao carregar lançamentos.");
        setLancamentos([]);
      }
    } catch (err: any) {
      logger.error("Failed to fetch lancamentos:", err);
      setError(err.message || "Erro de conexão ao buscar lançamentos.");
      setLancamentos([]);
    } finally {
      setLoading(false);
    }
  };

  const totalCreditos = lancamentos
    .filter((l) => l.categoria === "Crédito")
    .reduce((acc, curr) => acc + curr.valor, 0);
  const totalDebitos = lancamentos
    .filter((l) => l.categoria === "Débito")
    .reduce((acc, curr) => acc + curr.valor, 0);

  const handleOpenModal = (
    lancamento?: LancamentoType,
    categoria: "Crédito" | "Débito" = "Débito",
  ) => {
    setLancamentoToEdit(lancamento || null);
    setDefaultCategoria(lancamento?.categoria || categoria);
    setIsModalOpen(true);
  };

  const handleSaveLancamento = async (lancamento: LancamentoType) => {
    try {
      const session = getSession();
      const companyId = session?.user?.machine_empresa_id || session?.user?.company_id || "";
      const motoboy = Array.isArray(motoboys) ? motoboys.find((m) => m.nome === lancamento.motoboy) : undefined;

      // Map date DD/MM/YYYY -> YYYY-MM-DD
      let isoDate = lancamento.data;
      if (isoDate.includes("/")) {
        isoDate = isoDate.split("/").reverse().join("-");
      }

      const payload = {
        id: lancamento.id,
        companyId: Number(companyId),
        company_id: Number(companyId),
        driverName: lancamento.motoboy,
        driverId: motoboy ? motoboy.id : "9999",
        type:
          lancamento.categoria === "Débito"
            ? "adiantamento"
            : ["extra", "corrida_manual"].includes(lancamento.tipo)
              ? lancamento.tipo
              : "extra",
        amount: Number(lancamento.valor),
        date: isoDate,
        description:
          (lancamento.descricao ||
            lancamento.tipo ||
            (lancamento.categoria === "Débito" ? "Vale" : "Bônus")) +
          (lancamento.visibilidade && lancamento.visibilidade !== "ambos"
            ? `|vis:${lancamento.visibilidade}`
            : "") +
          (lancamento.tipo === "corrida_manual" &&
          lancamento.entregas &&
          lancamento.entregas > 1
            ? `|entregas:${lancamento.entregas}`
            : ""),
      };

      if (lancamento.id) {
        await authFetch(`/api/db/entries`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
      } else {
        await authFetch("/api/db/entries", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
      }
      fetchLancamentos();
    } catch (err) {
      logger.error("Failed to save lancamento", err);
      alert("Falha ao salvar lançamento. Verifique a conexão.");
      fetchLancamentos();
    }
    setIsModalOpen(false);
  };

  const handleDeleteLancamento = (id: number) => {
    setLancamentoToDelete(id);
    setIsConfirmOpen(true);
  };

  const confirmDelete = async () => {
    if (lancamentoToDelete !== null) {
      try {
        await authFetch(`/api/db/entries?id=${lancamentoToDelete}`, {
          method: "DELETE",
        });
        setLancamentos(lancamentos.filter((l) => l.id !== lancamentoToDelete));
      } catch (err) {
        logger.error("Failed to delete lancamento", err);
        alert("Falha ao excluir lançamento.");
        fetchLancamentos();
      } finally {
        setLancamentoToDelete(null);
        setIsConfirmOpen(false);
      }
    }
  };

  const filteredLancamentos = useMemo(() => {
    const term = searchTerm.toLowerCase().trim();
    if (!term) return lancamentos;
    return lancamentos.filter(
      (l) =>
        l.motoboy?.toLowerCase().includes(term) ||
        l.descricao?.toLowerCase().includes(term) ||
        l.categoria?.toLowerCase().includes(term),
    );
  }, [lancamentos, searchTerm]);

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

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-5 rounded-xl shadow-sm ring-1 ring-zinc-950/5">
        <div>
          <h1 className="text-xl font-bold text-zinc-900 tracking-tight">
            Lançamentos Manuais
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            Gestão de vales, bônus e adiantamentos de motoboys.
          </p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => handleOpenModal(undefined, "Débito")}
            className="flex items-center gap-1.5 px-4 py-2 bg-rose-50 text-rose-700 border border-rose-200/60 rounded-md hover:bg-rose-100 text-sm font-semibold shadow-sm transition-all focus:ring-2 focus:ring-rose-500/20"
          >
            <ArrowDownRight strokeWidth={2} className="h-4 w-4" /> Novo Débito
          </button>
          <button
            onClick={() => handleOpenModal(undefined, "Crédito")}
            className="flex items-center gap-1.5 px-4 py-2 bg-emerald-50 text-emerald-700 border border-emerald-200/60 rounded-md hover:bg-emerald-100 text-sm font-semibold shadow-sm transition-all focus:ring-2 focus:ring-emerald-500/20"
          >
            <ArrowUpRight strokeWidth={2} className="h-4 w-4" /> Novo Crédito
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-zinc-200 p-5">
          <div className="flex items-center gap-3 text-emerald-600 mb-2">
            <div className="p-2 bg-emerald-50 rounded-lg">
              <ArrowUpRight strokeWidth={2} className="h-4 w-4" />
            </div>
            <span className="font-semibold text-sm">Total Créditos (Mês)</span>
          </div>
          <h3 className="text-2xl font-bold text-zinc-900 tracking-tight pl-11">
            {formatCurrency(totalCreditos)}
          </h3>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-zinc-200 p-5">
          <div className="flex items-center gap-3 text-rose-600 mb-2">
            <div className="p-2 bg-rose-50 rounded-lg">
              <ArrowDownRight strokeWidth={2} className="h-4 w-4" />
            </div>
            <span className="font-semibold text-sm">Total Débitos (Mês)</span>
          </div>
          <h3 className="text-2xl font-bold text-zinc-900 tracking-tight pl-11">
            {formatCurrency(totalDebitos)}
          </h3>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-zinc-200 p-5">
          <div className="flex items-center gap-3 text-indigo-600 mb-2">
            <div className="p-2 bg-indigo-50 rounded-lg">
              <FileText strokeWidth={2} className="h-4 w-4" />
            </div>
            <span className="font-semibold text-sm">Lançamentos Pendentes</span>
          </div>
          <h3 className="text-2xl font-bold text-zinc-900 tracking-tight pl-11">
            {lancamentos.length}
          </h3>
        </div>
      </div>

      <div className="bg-white p-4 rounded-xl shadow-sm border border-zinc-200 flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="relative w-full max-w-sm group">
          <Search
            strokeWidth={1.5}
            className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400 group-focus-within:text-zinc-600 transition-colors"
          />
          <input
            type="text"
            placeholder="Buscar por motoboy ou descrição..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all placeholder:text-zinc-400 shadow-sm"
          />
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-[0_1px_3px_0_rgba(0,0,0,0.05),_0_0_0_1px_rgba(0,0,0,0.05)] overflow-hidden flex flex-col">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-zinc-50 border-b border-zinc-200 text-zinc-500 font-semibold text-[10px] uppercase tracking-wider">
              <tr>
                <th className="px-4 py-2">Data</th>
                <th className="px-4 py-2">Motoboy</th>
                <th className="px-4 py-2">Categoria/Tipo</th>
                <th className="px-4 py-2">Descrição</th>
                <th className="px-4 py-2 text-right">Valor</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {error && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-8 text-center text-red-500 bg-red-50/50"
                  >
                    <span className="font-bold">Erro:</span> {error}
                  </td>
                </tr>
              )}
              {filteredLancamentos.length === 0 && !error && !loading && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-8 text-center text-zinc-500"
                  >
                    {searchTerm
                      ? "Nenhum lançamento encontrado para a busca."
                      : "Nenhum lançamento encontrado."}
                  </td>
                </tr>
              )}
              {filteredLancamentos
                .slice(
                  (currentPage - 1) * itemsPerPage,
                  currentPage * itemsPerPage,
                )
                .map((lancamento) => (
                  <motion.tr
                    key={lancamento.id}
                    variants={itemVariants}
                    className="hover:bg-zinc-50/50 transition-colors group"
                  >
                    <td className="px-4 py-2">
                      <span className="font-mono text-[11px] text-zinc-600">
                        {lancamento.data}
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      <span className="font-semibold text-zinc-900 text-xs">
                        {lancamento.motoboy}
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex items-center gap-2">
                        <span
                          className={cn(
                            "inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider border",
                            lancamento.categoria === "Crédito"
                              ? "bg-emerald-50 text-emerald-700 border-emerald-200/60"
                              : "bg-rose-50 text-rose-700 border-rose-200/60",
                          )}
                        >
                          {lancamento.categoria}
                        </span>
                        <span className="text-zinc-500 text-[11px] font-medium">
                          {lancamento.tipo}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-2 text-zinc-600">
                      <span className="truncate max-w-[200px] block text-xs">
                        {lancamento.descricao}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-right">
                      <span
                        className={cn(
                          "font-mono font-bold text-xs tracking-tight",
                          lancamento.categoria === "Crédito"
                            ? "text-emerald-600"
                            : "text-rose-600",
                        )}
                      >
                        {lancamento.categoria === "Crédito" ? "+" : "-"}
                        {formatCurrency(lancamento.valor)}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-right">
                      <div className="flex justify-end gap-1">
                        <button
                          onClick={() => handleOpenModal(lancamento)}
                          className="p-1 px-1.5 text-zinc-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-md transition-colors"
                          title="Editar"
                        >
                          <Edit2 strokeWidth={1.5} className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={() =>
                            lancamento.id &&
                            handleDeleteLancamento(lancamento.id)
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

        <div className="px-4 py-3 border-t border-zinc-200 bg-zinc-50 flex flex-col sm:flex-row items-center justify-between gap-4">
          <span className="text-[10px] font-medium text-zinc-500 uppercase tracking-wider">
            Mostrando {(currentPage - 1) * itemsPerPage + 1} -{" "}
            {Math.min(currentPage * itemsPerPage, filteredLancamentos.length)}{" "}
            de {filteredLancamentos.length} registros
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1.5 border border-zinc-200 rounded-lg bg-white text-zinc-700 hover:bg-zinc-50 disabled:opacity-50 disabled:text-zinc-400 text-[10px] font-bold uppercase tracking-wider shadow-sm transition-all"
            >
              Anterior
            </button>
            <button
              onClick={() => setCurrentPage((prev) => prev + 1)}
              disabled={
                currentPage * itemsPerPage >= filteredLancamentos.length
              }
              className="px-3 py-1.5 border border-zinc-200 rounded-lg bg-white text-zinc-700 hover:bg-zinc-50 disabled:opacity-50 disabled:text-zinc-400 text-[10px] font-bold uppercase tracking-wider shadow-sm transition-all"
            >
              Próxima
            </button>
          </div>
        </div>
      </div>

      <LancamentoModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        lancamento={lancamentoToEdit}
        onSave={handleSaveLancamento}
        defaultCategoria={defaultCategoria}
        motoboys={motoboys}
        isAdmin={isAdmin}
      />

      <ConfirmModal
        isOpen={isConfirmOpen}
        title="Excluir Lançamento"
        message="Tem certeza que deseja excluir este lançamento? O saldo associado também será revertido."
        onConfirm={confirmDelete}
        onCancel={() => {
          setIsConfirmOpen(false);
          setLancamentoToDelete(null);
        }}
      />
    </div>
  );
}
