import { logger } from "@/lib/logger";
import { useState, useEffect, useMemo } from "react";
import {
  Search,
  Plus,
  Filter,
  Store,
  MapPin,
  Phone,
  MoreVertical,
  Edit2,
  Trash2,
  X,
  Upload,
  Save,
  Building2,
  ClipboardList,
  Wallet,
  Image as ImageIcon,
  Power,
  PowerOff,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn, formatCurrency } from "../lib/utils";
import { EmpresaModal, EmpresaType } from "../components/EmpresaModal";
import { ConfirmModal } from "../components/ConfirmModal";
import { authFetch, getSession } from "../lib/api";

export function Empresas() {
  const session = getSession();
  const companyId = session?.user?.machine_empresa_id || session?.user?.company_id;

  const [empresas, setEmpresas] = useState<EmpresaType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [empresaToEdit, setEmpresaToEdit] = useState<EmpresaType | null>(null);

  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [empresaToDelete, setEmpresaToDelete] = useState<number | null>(null);

  useEffect(() => {
    fetchEmpresas();
  }, []);

  const fetchEmpresas = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await authFetch("/api/v1/db/companies");
      if (res.ok) {
        const data = await res.json();
        const rawList = Array.isArray(data) ? data : data.empresas || [];
        const parseNum = (value: unknown, fallback: number) => {
          if (value === null || value === undefined || value === "")
            return fallback;
          if (typeof value === "number")
            return Number.isFinite(value) ? value : fallback;
          if (typeof value === "string") {
            const normalized = value.replace(",", ".");
            const n = Number(normalized);
            return Number.isFinite(n) ? n : fallback;
          }
          const n = Number(value as any);
          return Number.isFinite(n) ? n : fallback;
        };
        // Map API fields (name, machineEmpresaId, active) → EmpresaType shape
        const fetchedEmpresas = rawList.map((c: any) => {
          const cfg = Array.isArray(c.company_configs)
            ? c.company_configs[0]
            : c.company_configs || {};

          const rideFeePerDeliveryRaw =
            c.ride_fee_per_delivery ??
            cfg.ride_fee_per_delivery ??
            c.rideFeePerDelivery ??
            c.ride_fee ??
            null;
          const minimumRidesFeeFloorRaw =
            c.minimum_rides_fee_floor ??
            cfg.minimum_rides_fee_floor ??
            c.minimumRidesFeeFloor ??
            null;
          const minimumFloorPercentRaw =
            c.minimum_floor_percent ??
            cfg.minimum_floor_percent ??
            c.minimumFloorPercent ??
            null;
          const taxaSupervisaoRaw =
            c.taxa_supervisao ??
            cfg.taxa_supervisao ??
            c.taxaSupervisao ??
            null;
          const debitoPendenteRaw =
            c.debito_pendente ??
            cfg.debito_pendente ??
            c.debitoPendente ??
            null;

          const dailyRateWeekdayRaw =
            c.daily_rate_weekday ??
            cfg.daily_rate_weekday ??
            c.diaria_weekday ??
            null;
          const dailyRateSaturdayRaw =
            c.daily_rate_saturday ??
            cfg.daily_rate_saturday ??
            c.diaria_saturday ??
            null;
          const dailyRateSundayRaw =
            c.daily_rate_sunday ??
            cfg.daily_rate_sunday ??
            c.diaria_sunday ??
            null;
          const dailyRateHolidayRaw =
            c.daily_rate_holiday ??
            cfg.daily_rate_holiday ??
            c.diaria_holiday ??
            null;

          const extraKmModeRaw =
            c.extra_km_mode ?? cfg.extra_km_mode ?? c.extraKmMode ?? null;
          const extraKmMinDistanceRaw =
            c.extra_km_min_distance ??
            cfg.extra_km_min_distance ??
            c.extraKmMinDistance ??
            null;
          const extraKmFixedAmountRaw =
            c.extra_km_fixed_amount ??
            cfg.extra_km_fixed_amount ??
            c.extraKmFixedAmount ??
            null;
          const reportTypeRaw =
            c.report_type ?? cfg.report_type ?? c.reportType ?? null;
          const turnosRaw =
            c.turnos_config ?? cfg.turnos_config ?? (c.turnos || []);
          const faixasHorasRaw =
            c.faixas_horas_config ??
            cfg.faixas_horas_config ??
            (c.faixasHoras || []);

          return {
            id: c.id,
            nome: c.name || c.nome || "Empresa sem nome",
            endereco: c.address || c.endereco || "",
            telefone: c.telefone || c.phone || "",
            status: c.active === true ? "Ativo" : "Inativo",
            // Regras Financeiras
            taxaCorridaPerEntrega: parseNum(rideFeePerDeliveryRaw, 1.6),
            pisoFixo: parseNum(minimumRidesFeeFloorRaw, 350),
            pisoPercentual: parseNum(minimumFloorPercentRaw, 0),
            taxaSupervisao: parseNum(taxaSupervisaoRaw, 0),
            debitoPendente: parseNum(debitoPendenteRaw, 0),
            // Diárias
            diaria_weekday: parseNum(dailyRateWeekdayRaw, 60),
            diaria_saturday: parseNum(dailyRateSaturdayRaw, 70),
            diaria_sunday: parseNum(dailyRateSundayRaw, 80),
            diaria_holiday: parseNum(dailyRateHolidayRaw, 80),
            // Configurações
            reportType: reportTypeRaw || "producao",
            turnos: Array.isArray(turnosRaw) ? turnosRaw : [],
            faixasHoras: Array.isArray(faixasHorasRaw) ? faixasHorasRaw : [],
            extraKmMode: extraKmModeRaw || "disabled",
            extraKmMinDistance: parseNum(extraKmMinDistanceRaw, 6),
            extraKmFixedAmount: parseNum(extraKmFixedAmountRaw, 3),
            machineEmpresaId: c.machine_empresa_id || c.machineEmpresaId || "",
          };
        });
        setEmpresas(fetchedEmpresas);
      } else {
        setError("Falha ao carregar empresas.");
        setEmpresas([]);
      }
    } catch (err: any) {
      logger.error("Failed to fetch empresas:", err);
      setError(err.message || "Erro de conexão ao buscar empresas.");
      setEmpresas([]);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleStatus = async (id: any) => {
    const empresa = empresas.find((e) => e.id === id);
    if (!empresa) return;
    const previousEmpresas = empresas;
    const newStatus = empresa.status === "Ativo" ? "Inativo" : "Ativo";

    try {
      setEmpresas(
        empresas.map((e) => (e.id === id ? { ...e, status: newStatus } : e)),
      );

      const response = await authFetch(`/api/v1/db/companies/${id}`, {
        method: "PUT",
        body: JSON.stringify({ ...empresa, status: newStatus }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || "Erro ao atualizar status");
      }

      await fetchEmpresas();
    } catch (err) {
      logger.error(err);
      setEmpresas(previousEmpresas);
      alert(
        `Falha ao atualizar status: ${err instanceof Error ? err.message : "Erro desconhecido"}`,
      );
    }
  };

  const handleOpenModal = (empresa?: EmpresaType) => {
    setEmpresaToEdit(empresa || null);
    setIsModalOpen(true);
  };

  const handleSaveEmpresa = async (empresa: EmpresaType) => {
    try {
      if (empresa.id) {
        const previousEmpresas = empresas;
        setEmpresas(empresas.map((e) => (e.id === empresa.id ? empresa : e)));

        const response = await authFetch(`/api/v1/db/companies/${empresa.id}`, {
          method: "PUT",
          body: JSON.stringify(empresa),
        });
        
        const data = await response.json().catch(() => ({}));

        if (!response.ok || data.error || data.success === false) {
          setEmpresas(previousEmpresas);
          throw new Error(data.error || "Erro ao atualizar empresa");
        }
        await fetchEmpresas();
      } else {
        const response = await authFetch("/api/v1/db/companies", {
          method: "POST",
          body: JSON.stringify({
            companyId,
            name: empresa.nome,
            documento: empresa.documento || "",
            lat: empresa.lat,
            lng: empresa.lng,
            averagePrepTimeMinutes: empresa.averagePrepTimeMinutes || 15
          }),
        });
        
        const data = await response.json().catch(() => ({}));

        if (!response.ok || data.error || data.success === false) {
          throw new Error(data.error || "Erro ao criar empresa");
        }

        alert("Empresa criada com sucesso!");
        await fetchEmpresas();
      }
      setIsModalOpen(false);
    } catch (err: any) {
      logger.error("Failed to save empresa:", err);
      alert(`Falha ao salvar empresa: ${err.message}`);
      fetchEmpresas();
    }
  };

  const handleDeleteEmpresa = (id: any) => {
    setEmpresaToDelete(id);
    setIsConfirmOpen(true);
  };

  const confirmDelete = async () => {
    if (empresaToDelete !== null) {
      try {
        const response = await authFetch(
          `/api/v1/db/companies/${empresaToDelete}`,
          {
            method: "DELETE",
          },
        );

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.error || "Erro ao excluir empresa");
        }

        setEmpresas(empresas.filter((e) => e.id !== empresaToDelete));
      } catch (err: any) {
        logger.error("Failed to delete", err);
        alert(`Falha ao excluir empresa: ${err.message}`);
        fetchEmpresas();
      } finally {
        setEmpresaToDelete(null);
        setIsConfirmOpen(false);
      }
    }
  };

  const filteredEmpresas = useMemo(() => {
    const term = searchTerm.toLowerCase().trim();
    if (!term) return empresas;
    return empresas.filter(
      (e) =>
        e.nome?.toLowerCase().includes(term) ||
        e.endereco?.toLowerCase().includes(term) ||
        e.telefone?.toLowerCase().includes(term),
    );
  }, [empresas, searchTerm]);

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
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 py-2">
        <div>
          <h1 className="text-xl font-bold text-zinc-900 tracking-tight">
            Empresas
          </h1>
          <p className="text-[13px] font-medium text-zinc-500 mt-1">
            Gestão de regras financeiras para lojas sincronizadas da Machine
            API.
          </p>
        </div>
      </div>

      <div className="glass-panel overflow-hidden flex flex-col">
        <div className="p-4 border-b border-zinc-100 flex flex-col sm:flex-row gap-3 items-center justify-between bg-zinc-50/30">
          <div className="relative w-full sm:max-w-md group">
            <Search
              strokeWidth={2}
              className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-zinc-400 group-focus-within:text-zinc-600 transition-colors"
            />
            <input
              type="text"
              placeholder="Buscar por nome, endereço ou telefone..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-1.5 text-[13px] font-medium bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0a0a0a]/10 focus:border-zinc-300 transition-all placeholder:text-zinc-400 shadow-sm"
            />
          </div>
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <button
              onClick={fetchEmpresas}
              disabled={loading}
              className="flex items-center gap-2 px-3 py-1.5 bg-white border border-zinc-200 text-zinc-700 rounded-lg hover:bg-zinc-50 text-[13px] font-semibold shadow-sm transition-all flex-1 sm:flex-none justify-center disabled:opacity-50"
            >
              <RefreshCw
                strokeWidth={1.5}
                className={cn("h-4 w-4", loading && "animate-spin")}
              />
              {loading ? "Sincronizando..." : "Sincronizar"}
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-zinc-50 border-b border-zinc-200 text-zinc-500 font-semibold text-[10px] uppercase tracking-wider">
              <tr>
                <th className="px-4 py-2">Empresa</th>
                <th className="px-4 py-2">Endereço / Contato</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2 text-right">Taxa/Entr.</th>
                <th className="px-4 py-2 text-right">Taxa Adm</th>
                <th className="px-4 py-2 text-right">Extra KM</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {error && (
                <tr>
                  <td
                    colSpan={7}
                    className="px-4 py-8 text-center text-red-500 bg-red-50/50"
                  >
                    <span className="font-bold">Erro:</span> {error}
                  </td>
                </tr>
              )}
              {filteredEmpresas.length === 0 && !error && !loading && (
                <tr>
                  <td
                    colSpan={7}
                    className="px-4 py-8 text-center text-zinc-500"
                  >
                    {searchTerm
                      ? "Nenhuma empresa encontrada para a busca."
                      : "Nenhuma empresa encontrada."}
                  </td>
                </tr>
              )}
              {filteredEmpresas.map((empresa) => (
                <motion.tr
                  variants={itemVariants}
                  key={empresa.id}
                  className="hover:bg-zinc-50/80 transition-colors group"
                >
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-3">
                      <div className="h-8 w-8 rounded-lg bg-zinc-100 flex items-center justify-center text-zinc-900 border border-zinc-200 shadow-sm shrink-0">
                        <Store strokeWidth={1.5} className="h-4 w-4" />
                      </div>
                      <span className="font-semibold text-zinc-900 block">
                        {empresa.nome}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex flex-col">
                      <div className="flex items-center gap-1.5 text-xs text-zinc-600">
                        <MapPin
                          strokeWidth={1.5}
                          className="h-3 w-3 text-zinc-400"
                        />
                        <span className="truncate max-w-[200px]">
                          {empresa.endereco}
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5 text-[11px] text-zinc-500 mt-0.5">
                        <Phone
                          strokeWidth={1.5}
                          className="h-3 w-3 text-zinc-400"
                        />
                        {empresa.telefone}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-2">
                    <span
                      className={cn(
                        "inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider",
                        empresa.status === "Ativo"
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200/60"
                          : "bg-red-50 text-red-700 border border-red-200/60",
                      )}
                    >
                      {empresa.status}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right">
                    <span className="font-mono text-xs text-zinc-700 font-medium">
                      {formatCurrency(empresa.taxaCorridaPerEntrega)}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right">
                    <div className="flex flex-col items-end">
                      <span className="font-mono text-xs text-emerald-600 font-bold">
                        {formatCurrency(empresa.pisoFixo)}
                      </span>
                      {empresa.pisoPercentual > 0 && (
                        <span className="text-[9px] text-zinc-400 font-medium">
                          ou {empresa.pisoPercentual}%
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-2 text-right">
                    <div className="flex flex-col items-end">
                      <span className="font-mono text-xs text-zinc-900 font-bold">
                        {empresa.extraKmMode === "disabled"
                          ? "—"
                          : empresa.extraKmMode === "fixed"
                            ? formatCurrency(empresa.extraKmFixedAmount)
                            : "Taxa"}
                      </span>
                      {empresa.extraKmMode !== "disabled" && (
                        <span className="text-[9px] text-zinc-400 font-medium">
                          &gt; {empresa.extraKmMinDistance}km
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-2 text-right">
                    <div className="flex justify-end gap-1">
                      <button
                        onClick={() => handleToggleStatus(empresa.id)}
                        className={cn(
                          "p-1 px-1.5 rounded-md transition-colors",
                          empresa.status === "Ativo"
                            ? "text-zinc-400 hover:text-amber-600 hover:bg-amber-50"
                            : "text-zinc-400 hover:text-emerald-600 hover:bg-emerald-50",
                        )}
                        title={
                          empresa.status === "Ativo" ? "Desativar" : "Ativar"
                        }
                      >
                        {empresa.status === "Ativo" ? (
                          <PowerOff strokeWidth={1.5} className="h-3.5 w-3.5" />
                        ) : (
                          <Power strokeWidth={1.5} className="h-3.5 w-3.5" />
                        )}
                      </button>
                      <button
                        onClick={() => handleOpenModal(empresa)}
                        className="p-1 px-1.5 text-zinc-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-md transition-colors"
                        title="Configurações da Empresa"
                      >
                        <Edit2 strokeWidth={1.5} className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() =>
                          empresa.id && handleDeleteEmpresa(empresa.id)
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
            Mostrando {filteredEmpresas.length} de {empresas.length} empresas
          </span>
        </div>
      </div>

      <EmpresaModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        empresa={empresaToEdit}
        onSave={handleSaveEmpresa}
      />

      <ConfirmModal
        isOpen={isConfirmOpen}
        title="Excluir Empresa"
        message="Tem certeza que deseja excluir esta empresa? Essa ação não pode ser desfeita."
        onConfirm={confirmDelete}
        onCancel={() => {
          setIsConfirmOpen(false);
          setEmpresaToDelete(null);
        }}
      />
    </div>
  );
}
