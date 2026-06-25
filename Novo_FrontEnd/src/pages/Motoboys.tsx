import { logger } from '@/lib/logger';
import { Search, Phone, Star, Edit2, Power, PowerOff } from "lucide-react";
import { motion } from "framer-motion";
import { cn, formatCurrency } from "../lib/utils";
import { useState, useMemo } from "react";
import { MotoboyModal, MotoboyType } from "../components/MotoboyModal";
import { authFetch, getSession } from "../lib/api";
import { useApiQuery, mutateCache } from "../lib/useApiQuery";


export function Motoboys() {
  const session = getSession();
  const companyId = session?.user?.machine_empresa_id;

  const dbKey = companyId ? `/api/db/company-drivers?company_id=${companyId}&active_only=0` : null;
  const machineKey = `/api/machine/drivers`;

  const { data: dbRaw, isLoading: loadingDb, error: errorDb, refresh } = useApiQuery<any[]>(dbKey, { refreshInterval: 60_000 });
  const { data: machineRaw, isLoading: loadingMachine } = useApiQuery<any>(machineKey, { refreshInterval: 60_000 });

  // Get current month dates to fetch entries
  const { startISO, endISO } = useMemo(() => {
    const now = new Date();
    const start = new Date(now.getFullYear(), now.getMonth(), 1);
    const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    const formatDate = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    return { startISO: formatDate(start), endISO: formatDate(end) };
  }, []);

  const entriesKey = companyId ? `/api/db/entries?company_id=${companyId}&start=${startISO}&end=${endISO}` : null;
  const { data: entriesRaw, isLoading: loadingEntries } = useApiQuery<any[]>(entriesKey, { refreshInterval: 60_000 });

  const loading = loadingDb || loadingMachine || loadingEntries;
  const error = errorDb;

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedMotoboy, setSelectedMotoboy] = useState<MotoboyType | null>(null);
  const [currentPage] = useState(1);
  const itemsPerPage = 10;
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("Todos");

  const motoboys: MotoboyType[] = useMemo(() => {
    const dbList: any[] = Array.isArray(dbRaw) ? dbRaw : (dbRaw as any)?.motoboys || [];
    const machineDrivers: any[] = Array.isArray(machineRaw?.drivers) ? machineRaw.drivers : [];
    const entries: any[] = Array.isArray(entriesRaw) ? entriesRaw : [];

    const machineMap = new Map<string, any>();
    machineDrivers.forEach((d: any) => { if (d?.id != null) machineMap.set(String(d.id), d); });

    // Group entries by driver
    const driverStats = new Map<string, { faturamento: number; corridas: number }>();
    entries.forEach((e: any) => {
      const dId = String(e.driverId || '');
      if (!dId) return;
      if (!driverStats.has(dId)) driverStats.set(dId, { faturamento: 0, corridas: 0 });
      const stats = driverStats.get(dId)!;
      if (e.type === 'diaria' || e.type === 'extra') {
        stats.faturamento += (Number(e.amount) || 0);
        stats.corridas += 1;
      } else if (e.type === 'adiantamento') {
        stats.faturamento -= (Number(e.amount) || 0);
      }
    });

    return dbList.map((d: any) => {
      const dId = String(d.driverId || d.id || '');
      const stats = driverStats.get(dId) || { faturamento: 0, corridas: 0 };
      
      return {
        id: dId,
        nome: (machineMap.get(dId)?.nome) || d.driverName || d.nome || d.name || 'Sem nome',
        telefone: (machineMap.get(dId)?.telefone) || d.driverPhone || d.telefone || d.phone || '',
        placa: d.placa || d.plate || '',
        modelo: d.modelo || d.vehicle || '',
        status: formatCadastroStatus(machineMap.get(dId)?.status) || formatDriverStatus(d.driverStatus || d.status || ''),
        avaliacao: d.avaliacao || d.rating || 5.0,
        corridas: stats.corridas,
        faturamento: stats.faturamento,
        ativo: d.active !== false,
      };
    });
  }, [dbRaw, machineRaw, entriesRaw]);

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { staggerChildren: 0.05 } }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: { opacity: 1, y: 0 }
  };

  const filteredMotoboys = useMemo(() => {
    let list = motoboys;
    const term = searchTerm.toLowerCase().trim();
    if (term) {
      list = list.filter(m =>
        m.nome?.toLowerCase().includes(term) ||
        m.placa?.toLowerCase().includes(term) ||
        m.telefone?.toLowerCase().includes(term)
      );
    }
    if (statusFilter === "Ativo") list = list.filter(m => m.ativo !== false);
    else if (statusFilter === "Inativo") list = list.filter(m => m.ativo === false);
    return list;
  }, [motoboys, searchTerm, statusFilter]);

  const handleOpenModal = (motoboy?: MotoboyType) => {
    setSelectedMotoboy(motoboy || null);
    setIsModalOpen(true);
  };

  const handleToggleActive = async (motoboyId: string, nextActive: boolean) => {
    try {
      if (!companyId) return;

      // Atualização Otimista: atualiza o cache imediatamente antes da confirmação da API
      if (dbKey) {
        mutateCache<any[]>(dbKey, (prev) =>
          (prev || []).map((d: any) => {
            const id = String(d.driverId || d.id || '');
            return id === motoboyId ? { ...d, active: nextActive } : d;
          })
        );
      }

      const res = await authFetch(`/api/db/company-drivers`, {
        method: 'PATCH',
        body: JSON.stringify({ companyId, driverId: motoboyId, active: nextActive }),
      });

      if (!res.ok) {
        // Reverte o cache em caso de erro
        if (dbKey) {
          mutateCache<any[]>(dbKey, (prev) =>
            (prev || []).map((d: any) => {
              const id = String(d.driverId || d.id || '');
              return id === motoboyId ? { ...d, active: !nextActive } : d;
            })
          );
        }
        alert("Falha ao alterar cadastro do motoboy.");
      }
    } catch (err) {
      logger.error('Failed to toggle status', err);
      if (dbKey) {
        mutateCache<any[]>(dbKey, (prev) =>
          (prev || []).map((d: any) => {
            const id = String(d.driverId || d.id || '');
            return id === motoboyId ? { ...d, active: !nextActive } : d;
          })
        );
      }
      alert("Falha ao alterar cadastro do motoboy.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 py-2">
        <div>
          <h1 className="text-xl font-bold text-zinc-900 tracking-tight">Motoboys</h1>
          <p className="text-[13px] font-medium text-zinc-500 mt-1">Gerencie a frota de entregadores, contratos e disponibilidade.</p>
        </div>
      </div>

      <div className="glass-panel overflow-hidden flex flex-col">
        <div className="p-4 border-b border-zinc-100 flex flex-col sm:flex-row gap-3 items-center justify-between bg-zinc-50/30">
          <div className="relative w-full sm:max-w-md group">
            <Search strokeWidth={2} className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-zinc-400 group-focus-within:text-zinc-600 transition-colors" />
            <input 
              type="text" 
              placeholder="Buscar motoboy por nome, placa ou telefone..." 
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-1.5 text-[13px] font-medium bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0a0a0a]/10 focus:border-zinc-300 transition-all placeholder:text-zinc-400 shadow-sm"
            />
          </div>
          <div className="flex gap-2 w-full sm:w-auto">
            <select 
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              className="flex-1 sm:w-auto px-3 py-2 text-sm border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 bg-white text-zinc-700 font-medium shadow-sm transition-all appearance-none cursor-pointer"
            >
              <option value="Todos">Todos os Status</option>
              <option value="Ativo">Ativo</option>
              <option value="Inativo">Inativo</option>
            </select>
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-zinc-50 border-b border-zinc-200 text-zinc-500 font-semibold text-[10px] uppercase tracking-wider">
              <tr>
                <th className="px-4 py-2">Motoboy</th>
                <th className="px-4 py-2">Veículo / Placa</th>
                <th className="px-4 py-2 text-center">Avaliação</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2 text-right" title="Número de lançamentos no mês">Lançamentos</th>
                <th className="px-4 py-2 text-right" title="Faturamento no mês">Faturamento Mês</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {error && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-red-500 bg-red-50/50">
                    <span className="font-bold">Erro:</span> {error}
                  </td>
                </tr>
              )}
              {filteredMotoboys.length === 0 && !error && !loading && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-zinc-500">
                    {searchTerm || statusFilter !== 'Todos' ? 'Nenhum motoboy encontrado para os filtros aplicados.' : 'Nenhum motoboy encontrado.'}
                  </td>
                </tr>
              )}
              {filteredMotoboys.map((motoboy) => (
                <motion.tr variants={itemVariants} key={motoboy.id} className={cn("hover:bg-zinc-50/80 transition-colors group", motoboy.ativo === false && "opacity-50 grayscale")}>
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-3">
                      <div className="h-8 w-8 rounded-full bg-zinc-100 border border-zinc-200 flex items-center justify-center text-zinc-800 font-bold text-xs">
                        {motoboy.nome.split(' ').map(n => n[0]).join('')}
                      </div>
                      <div>
                        <span className="font-semibold text-zinc-900 block">{motoboy.nome}</span>
                        <div className="flex items-center gap-1 mt-0.5 text-[11px] text-zinc-500">
                           <Phone strokeWidth={1.5} className="h-3 w-3" />
                           {motoboy.telefone}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex flex-col">
                      <span className="font-medium text-zinc-700 text-xs">{motoboy.modelo}</span>
                      <span className="font-mono text-zinc-500 text-[11px] uppercase">{motoboy.placa}</span>
                    </div>
                  </td>
                  <td className="px-4 py-2 text-center">
                    <div className="flex items-center justify-center gap-1 font-semibold text-zinc-700 text-xs text-center border border-zinc-200 w-fit mx-auto px-1.5 py-0.5 rounded-md bg-white">
                      <Star className="h-3.5 w-3.5 text-amber-500 fill-amber-500" />
                      {motoboy.avaliacao}
                    </div>
                  </td>
                  <td className="px-4 py-2">
                    <span className={cn(
                      "inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border",
                      motoboy.status === 'Ativo' ? 'bg-emerald-50 text-emerald-700 border-emerald-200/60' :
                      motoboy.status === 'Inativo' ? 'bg-zinc-100 text-zinc-600 border-zinc-200' :
                      motoboy.status === 'Suspenso' ? 'bg-rose-50 text-rose-700 border-rose-200/60' :
                      'bg-amber-50 text-amber-700 border-amber-200/60'
                    )}>
                      <span className={cn(
                        "h-1.5 w-1.5 rounded-full",
                        motoboy.status === 'Ativo' ? 'bg-emerald-500' :
                        motoboy.status === 'Inativo' ? 'bg-zinc-400' :
                        motoboy.status === 'Suspenso' ? 'bg-rose-500' :
                        'bg-amber-500'
                      )}></span>
                      {motoboy.status}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right">
                    <span className="font-mono font-medium text-zinc-900 text-xs">
                      {motoboy.corridas}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right">
                    <span className="font-mono font-bold text-emerald-600 text-xs">
                      {formatCurrency(motoboy.faturamento)}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right">
                    <div className="flex justify-end gap-1">
                      <button 
                        onClick={() => handleToggleActive(motoboy.id, !motoboy.ativo)}
                        className={cn(
                          "p-1 px-1.5 rounded-md transition-colors",
                          motoboy.ativo !== false 
                            ? "text-zinc-400 hover:text-amber-600 hover:bg-amber-50" 
                            : "text-zinc-400 hover:text-emerald-600 hover:bg-emerald-50"
                        )}
                        title={motoboy.ativo !== false ? "Desativar" : "Ativar"}
                      >
                        {motoboy.ativo !== false ? <PowerOff strokeWidth={1.5} className="h-3.5 w-3.5" /> : <Power strokeWidth={1.5} className="h-3.5 w-3.5" />}
                      </button>
                      <button 
                        onClick={() => handleOpenModal(motoboy)}
                        className="p-1 px-1.5 text-zinc-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-md transition-colors" 
                        title="Detalhes"
                      >
                        <Edit2 strokeWidth={1.5} className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="px-4 py-3 border-t border-zinc-200 bg-zinc-50 flex items-center justify-center">
          <span className="text-[10px] font-medium text-zinc-500 uppercase tracking-wider">Mostrando {filteredMotoboys.length} de {motoboys.length} motoboys</span>
        </div>
      </div>
      
      <MotoboyModal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)} 
        motoboy={selectedMotoboy}
        onToggleActive={handleToggleActive}
      />
    </div>
  );
}

function formatDriverStatus(raw: string) {
  const v = String(raw || '').trim().toLowerCase();
  if (!v) return '—';
  if (v === 'active') return 'Ativo';
  if (v === 'inactive') return 'Inativo';
  if (v === 'blocked') return 'Suspenso';
  return raw;
}

function formatCadastroStatus(raw: unknown) {
  const v = String(raw || '').trim().toLowerCase();
  if (!v) return '';
  if (v.includes('analise') || v.includes('análise')) return 'Em análise';
  if (v.includes('excl')) return 'Excluído';
  if (v.includes('susp')) return 'Suspenso';
  if (v.includes('inativ')) return 'Inativo';
  if (v.includes('ativ')) return 'Ativo';
  return String(raw);
}

