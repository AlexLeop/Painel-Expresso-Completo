import { useState, useEffect } from "react";
import {
  Search,
  Filter,
  Lock,
  Unlock,
  FileText,
  CheckCircle2,
  Eye,
  Calendar,
  Building2,
  Download,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import { cn, formatCurrency } from "../lib/utils";
import { authFetch, getSession } from "../lib/api";

interface Snapshot {
  id: string;
  companyId: number;
  weekStart: string;
  weekEnd: string;
  weekLabel: string;
  status: string;
  totalGeral: number;
  drivers: Array<{
    driverId: string;
    driverName: string;
    totalLiquido: number;
  }>;
  createdAt: string;
  notes?: string;
}

export function Snapshots() {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    const fetchSnapshots = async () => {
      setLoading(true);
      setError(null);
      try {
        const session = getSession();
        const companyId = session?.user?.machine_empresa_id;
        if (!companyId) {
          setError("Empresa não encontrada na sessão. Faça login novamente.");
          setLoading(false);
          return;
        }
        const res = await authFetch(
          `/api/db/snapshots?company_id=${companyId}`,
        );
        if (res.ok) {
          const data = await res.json();
          setSnapshots(Array.isArray(data) ? data : []);
        } else {
          setError("Falha ao carregar snapshots.");
        }
      } catch (err: any) {
        setError(err.message || "Erro de conexão ao buscar snapshots.");
      } finally {
        setLoading(false);
      }
    };
    fetchSnapshots();
  }, []);

  const filtered = snapshots.filter((s) =>
    (s.weekLabel || s.weekStart || s.id)
      .toLowerCase()
      .includes(searchTerm.toLowerCase()),
  );

  const countRascunho = snapshots.filter(
    (s) => s.status === "draft" || s.status === "rascunho",
  ).length;
  const countFinalizado = snapshots.filter(
    (s) => s.status === "finalized" || s.status === "finalizado",
  ).length;
  const countBloqueado = snapshots.filter(
    (s) => s.status === "locked" || s.status === "bloqueado",
  ).length;

  const getStatusLabel = (status: string) => {
    const map: Record<string, string> = {
      draft: "Rascunho",
      rascunho: "Rascunho",
      finalized: "Finalizado",
      finalizado: "Finalizado",
      locked: "Bloqueado",
      bloqueado: "Bloqueado",
    };
    return map[status] || status;
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 py-2">
        <div>
          <h1 className="text-xl font-bold text-zinc-900 tracking-tight">
            Snapshots de Fechamento
          </h1>
          <p className="text-[13px] font-medium text-zinc-500 mt-1 max-w-xl">
            Cópias permanentes de cálculos, motoristas e corridas. Audite e
            trave faturamentos para pagamento.
          </p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-zinc-900 text-white rounded-lg hover:bg-zinc-800 text-[13px] font-semibold transition-all shadow-[0_1px_2px_rgba(0,0,0,0.1)]">
          Gerar Novo Snapshot
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="glass-panel p-5 border-l-4 border-l-amber-500">
          <div className="flex flex-col">
            <h3 className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5" /> Rascunho
            </h3>
            <p className="text-2xl font-bold text-zinc-900 mt-2 tracking-tight">
              {loading ? "–" : countRascunho}
            </p>
            <p className="text-[11px] text-zinc-500 mt-1 font-medium">
              Permite edições e ajustes de valores (Override)
            </p>
          </div>
        </div>
        <div className="glass-panel p-5 border-l-4 border-l-emerald-500">
          <div className="flex flex-col">
            <h3 className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" /> Finalizado
            </h3>
            <p className="text-2xl font-bold text-zinc-900 mt-2 tracking-tight">
              {loading ? "–" : countFinalizado}
            </p>
            <p className="text-[11px] text-zinc-500 mt-1 font-medium">
              Configuração pronta, sem acesso a edição básica
            </p>
          </div>
        </div>
        <div className="glass-panel p-5 border-l-4 border-l-zinc-900">
          <div className="flex flex-col">
            <h3 className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5" /> Bloqueado
            </h3>
            <p className="text-2xl font-bold text-zinc-900 mt-2 tracking-tight">
              {loading ? "–" : countBloqueado}
            </p>
            <p className="text-[11px] text-zinc-500 mt-1 font-medium">
              Imutável. Documento oficial auditável
            </p>
          </div>
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
              placeholder="Buscar snapshot por período..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-1.5 text-[13px] font-medium bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0a0a0a]/10 focus:border-zinc-300 transition-all placeholder:text-zinc-400 shadow-sm"
            />
          </div>
          <button className="flex items-center gap-2 px-3 py-1.5 bg-white border border-zinc-200 text-zinc-700 rounded-lg hover:bg-zinc-50 text-[13px] font-semibold shadow-sm transition-all w-full sm:w-auto justify-center">
            <Filter strokeWidth={1.5} className="h-4 w-4" /> Filtros
          </button>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-16 gap-2 text-zinc-400">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span className="text-sm font-medium">Carregando snapshots...</span>
          </div>
        )}

        {error && !loading && (
          <div className="flex items-center justify-center py-16 gap-2 text-red-500">
            <AlertTriangle className="h-5 w-5" />
            <span className="text-sm font-medium">{error}</span>
          </div>
        )}

        {!loading && !error && (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-zinc-50/50 border-b border-zinc-100">
                  <th className="px-5 py-3 text-[10px] font-bold text-zinc-500 uppercase tracking-widest">
                    Período
                  </th>
                  <th className="px-5 py-3 text-[10px] font-bold text-zinc-500 uppercase tracking-widest text-center">
                    Status
                  </th>
                  <th className="px-5 py-3 text-[10px] font-bold text-zinc-500 uppercase tracking-widest text-center">
                    Entregadores
                  </th>
                  <th className="px-5 py-3 text-[10px] font-bold text-zinc-500 uppercase tracking-widest text-right">
                    Total Líquido
                  </th>
                  <th className="px-5 py-3 text-[10px] font-bold text-zinc-500 uppercase tracking-widest text-center">
                    Ações
                  </th>
                </tr>
              </thead>
              <tbody className="text-sm divide-y divide-zinc-100">
                {filtered.length === 0 ? (
                  <tr>
                    <td
                      colSpan={5}
                      className="px-5 py-12 text-center text-zinc-400 text-[13px] font-medium"
                    >
                      Nenhum snapshot encontrado.
                    </td>
                  </tr>
                ) : (
                  filtered.map((snap) => {
                    const label = getStatusLabel(snap.status);
                    return (
                      <tr
                        key={snap.id}
                        className="hover:bg-zinc-50/50 transition-colors group"
                      >
                        <td className="px-5 py-3.5 font-medium text-zinc-700">
                          <div className="flex items-center gap-1.5 text-[13px]">
                            <Calendar className="w-3.5 h-3.5 text-zinc-400" />
                            {snap.weekLabel ||
                              `${snap.weekStart} – ${snap.weekEnd}`}
                          </div>
                        </td>
                        <td className="px-5 py-3.5">
                          <div className="flex justify-center">
                            <span
                              className={cn(
                                "inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider rounded-md border shadow-sm",
                                label === "Rascunho"
                                  ? "bg-amber-50 text-amber-700 border-amber-200"
                                  : label === "Finalizado"
                                    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                    : "bg-zinc-900 text-white border-zinc-700",
                              )}
                            >
                              {label === "Rascunho" ? (
                                <Unlock strokeWidth={2.5} className="w-3 h-3" />
                              ) : label === "Finalizado" ? (
                                <CheckCircle2
                                  strokeWidth={2.5}
                                  className="w-3 h-3"
                                />
                              ) : (
                                <Lock strokeWidth={2.5} className="w-3 h-3" />
                              )}
                              {label}
                            </span>
                          </div>
                        </td>
                        <td className="px-5 py-3.5">
                          <div className="flex justify-center items-center gap-1 text-zinc-600 text-[13px] font-medium">
                            <Building2 className="w-3.5 h-3.5 text-zinc-400" />
                            {snap.drivers?.length ?? 0}
                          </div>
                        </td>
                        <td className="px-5 py-3.5 text-right font-mono text-sm font-bold text-zinc-900">
                          {formatCurrency(snap.totalGeral)}
                        </td>
                        <td className="px-5 py-3.5">
                          <div className="flex justify-center items-center gap-1">
                            <button
                              className="p-1.5 text-zinc-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-md transition-colors"
                              title="Visualizar"
                            >
                              <Eye strokeWidth={2} className="h-4 w-4" />
                            </button>
                            <button
                              className="p-1.5 text-zinc-400 hover:text-zinc-900 hover:bg-zinc-100 rounded-md transition-colors"
                              title="Exportar"
                            >
                              <Download strokeWidth={2} className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
