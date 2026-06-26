import { logger } from "@/lib/logger";
/**
 * CreditQueuePanel — Real-time view of the credit_queue.
 *
 * Shows pending, processing, failed, and dead items.
 * Subscribes to Supabase Realtime for live updates.
 * Allows admin to manually retry dead items.
 */

import { useState, useEffect, useCallback } from "react";
import { authFetch } from "../lib/api";
import { cn, formatCurrency } from "../lib/utils";
import {
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Clock,
  XCircle,
  Play,
} from "lucide-react";

interface QueueItem {
  id: string;
  company_id: string;
  driver_id: string;
  machine_condutor_id: string;
  net_amount: number;
  description: string;
  status: "pending" | "processing" | "completed" | "failed" | "dead";
  attempt_count: number;
  max_attempts: number;
  last_error: string | null;
  next_retry_at: string;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  // Joined
  driver_name?: string;
  company_name?: string;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "agora";
  if (mins < 60) return `${mins}m atrás`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h atrás`;
  const days = Math.floor(hrs / 24);
  return `${days}d atrás`;
}

function nextRetryLabel(dateStr: string): string {
  const diff = new Date(dateStr).getTime() - Date.now();
  if (diff <= 0) return "Agora (na próxima execução)";
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `em ${mins}min`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `em ${hrs}h`;
  const days = Math.floor(hrs / 24);
  return `em ${days}d`;
}

const STATUS_CONFIG: Record<
  string,
  { label: string; colorClass: string; bgClass: string; icon: any }
> = {
  pending: {
    label: "Pendente",
    colorClass: "text-amber-600",
    bgClass: "bg-amber-50",
    icon: Clock,
  },
  processing: {
    label: "Processando",
    colorClass: "text-blue-600",
    bgClass: "bg-blue-50",
    icon: RefreshCw,
  },
  completed: {
    label: "Concluído",
    colorClass: "text-emerald-600",
    bgClass: "bg-emerald-50",
    icon: CheckCircle2,
  },
  failed: {
    label: "Falhou",
    colorClass: "text-orange-600",
    bgClass: "bg-orange-50",
    icon: AlertCircle,
  },
  dead: {
    label: "DLQ",
    colorClass: "text-rose-600",
    bgClass: "bg-rose-50",
    icon: XCircle,
  },
};

interface CreditQueuePanelProps {
  companyId?: string;
}

export default function CreditQueuePanel({ companyId }: CreditQueuePanelProps) {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("active"); // 'active' | 'all' | 'dead'

  const loadQueue = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (companyId) params.set("company_id", companyId);
      if (filter === "active")
        params.set("status", "pending,processing,failed");
      else if (filter === "dead") params.set("status", "dead");

      const res = await authFetch(`/api/db/credit-queue?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setItems(data.items || []);
      }
    } catch (err) {
      logger.error("[CreditQueuePanel] Load failed:", err);
    } finally {
      setLoading(false);
    }
  }, [companyId, filter]);

  useEffect(() => {
    loadQueue();

    // Auto-refresh every 1 min as fallback for realtime
    const interval = setInterval(loadQueue, 60000);
    return () => clearInterval(interval);
  }, [loadQueue]);

  const handleRetry = async (queueId: string) => {
    setRetrying(queueId);
    try {
      const res = await authFetch("/api/db/credit-queue/retry", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ queue_ids: [queueId] }),
      });
      if (res.ok) {
        await loadQueue();
      }
    } catch (err) {
      logger.error("[CreditQueuePanel] Retry failed:", err);
    } finally {
      setRetrying(null);
    }
  };

  const handleRetryAll = async () => {
    setRetrying("all");
    try {
      const res = await authFetch("/api/db/credit-queue/retry", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ retry_all: true }),
      });
      if (res.ok) {
        await loadQueue();
      }
    } catch (err) {
      logger.error("[CreditQueuePanel] Retry all failed:", err);
    } finally {
      setRetrying(null);
    }
  };

  // Stats
  const queueStats = {
    pending: items.filter((i) => i.status === "pending").length,
    processing: items.filter((i) => i.status === "processing").length,
    failed: items.filter((i) => i.status === "failed").length,
    dead: items.filter((i) => i.status === "dead").length,
    totalAmount: items
      .filter((i) => i.status !== "completed")
      .reduce((sum, i) => sum + Number(i.net_amount), 0),
  };

  const hasAlerts = queueStats.dead > 0 || queueStats.failed > 0;

  return (
    <div className="bg-white rounded-xl shadow-sm ring-1 ring-zinc-950/5 overflow-hidden">
      <div className="px-6 py-4 border-b border-zinc-100 flex items-center justify-between bg-zinc-50/30">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-bold text-zinc-900 uppercase tracking-wider">
            Fila de Créditos
          </h2>
          {hasAlerts && (
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-orange-500 text-[10px] font-bold text-white animate-pulse">
              {queueStats.dead + queueStats.failed}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className="flex bg-zinc-100 p-0.5 rounded-lg">
            {[
              { key: "active", label: "Ativos" },
              { key: "dead", label: "DLQ" },
              { key: "all", label: "Todos" },
            ].map((f) => (
              <button
                key={f.key}
                onClick={() => setFilter(f.key)}
                className={cn(
                  "px-3 py-1 text-[10px] font-bold uppercase tracking-wider rounded-md transition-all",
                  filter === f.key
                    ? "bg-white text-zinc-900 shadow-sm"
                    : "text-zinc-500 hover:text-zinc-700",
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
          <button
            onClick={loadQueue}
            className="p-1.5 text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 rounded-md transition-all"
            title="Atualizar"
          >
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
          </button>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="px-6 py-3 bg-zinc-50/50 border-b border-zinc-100 grid grid-cols-2 sm:flex items-center gap-4">
        {Object.entries(STATUS_CONFIG)
          .filter(([key]) => key !== "completed")
          .map(([key, cfg]) => {
            const count =
              key === "pending"
                ? queueStats.pending
                : key === "processing"
                  ? queueStats.processing
                  : key === "failed"
                    ? queueStats.failed
                    : queueStats.dead;
            return (
              <div key={key} className="flex items-center gap-2">
                <cfg.icon className={cn("h-3.5 w-3.5", cfg.colorClass)} />
                <span className="text-xs font-bold text-zinc-900">{count}</span>
                <span className="text-[10px] text-zinc-500 uppercase font-medium">
                  {cfg.label}
                </span>
              </div>
            );
          })}
        {queueStats.totalAmount > 0 && (
          <div className="col-span-2 sm:ml-auto flex items-center gap-2 border-t sm:border-t-0 pt-2 sm:pt-0">
            <span className="text-[10px] text-zinc-400 uppercase font-bold tracking-wider">
              Total na fila:
            </span>
            <span className="text-sm font-bold text-zinc-900">
              {formatCurrency(queueStats.totalAmount)}
            </span>
          </div>
        )}
      </div>

      {/* Dead Letter Alert */}
      {queueStats.dead > 0 && (
        <div className="m-6 p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-4">
          <div className="h-10 w-10 rounded-full bg-rose-100 flex items-center justify-center text-rose-600 shrink-0">
            <XCircle className="h-6 w-6" />
          </div>
          <div className="flex-1">
            <h3 className="text-sm font-bold text-rose-900">
              {queueStats.dead} pagamento{queueStats.dead > 1 ? "s" : ""} na
              Dead Letter Queue
            </h3>
            <p className="text-xs text-rose-700 mt-0.5">
              Estes pagamentos falharam repetidamente e requerem intervenção
              manual.
            </p>
          </div>
          <button
            onClick={handleRetryAll}
            disabled={!!retrying}
            className="px-4 py-2 bg-rose-600 text-white text-xs font-bold uppercase tracking-wider rounded-lg hover:bg-rose-700 transition-all shadow-sm disabled:opacity-50"
          >
            {retrying === "all" ? "Processando..." : "Reprocessar Todos"}
          </button>
        </div>
      )}

      {/* Items Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left whitespace-nowrap text-xs">
          <thead className="bg-zinc-50/80 border-b border-zinc-200 text-zinc-500 text-[10px] font-bold uppercase tracking-wider">
            <tr>
              <th className="px-6 py-3">Motoboy</th>
              <th className="px-4 py-3">Valor</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-center">Tentativas</th>
              <th className="px-4 py-3">Próximo Retry</th>
              <th className="px-4 py-3">Último Erro</th>
              <th className="px-6 py-3 text-right">Ação</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100">
            {items.map((item) => {
              const cfg = STATUS_CONFIG[item.status] || STATUS_CONFIG.pending;
              return (
                <tr
                  key={item.id}
                  className="hover:bg-zinc-50/50 transition-colors"
                >
                  <td className="px-6 py-3.5">
                    <div className="font-bold text-zinc-900">
                      {item.driver_name || item.machine_condutor_id}
                    </div>
                    <div
                      className="text-[10px] text-zinc-500 mt-0.5 max-w-[200px] truncate"
                      title={item.description}
                    >
                      {item.description || "Sem descrição"}
                    </div>
                  </td>
                  <td className="px-4 py-3.5">
                    <span className="font-mono font-bold text-zinc-900">
                      {formatCurrency(Number(item.net_amount))}
                    </span>
                  </td>
                  <td className="px-4 py-3.5">
                    <div
                      className={cn(
                        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[10px] font-bold uppercase tracking-wider",
                        cfg.bgClass,
                        cfg.colorClass,
                        "border-current/10",
                      )}
                    >
                      <cfg.icon className="h-3 w-3" />
                      {cfg.label}
                    </div>
                  </td>
                  <td className="px-4 py-3.5 text-center font-mono font-bold text-zinc-600">
                    {item.attempt_count}/{item.max_attempts}
                  </td>
                  <td className="px-4 py-3.5 text-zinc-500">
                    {item.status === "failed" && item.next_retry_at
                      ? nextRetryLabel(item.next_retry_at)
                      : item.status === "dead"
                        ? "Manual"
                        : "—"}
                  </td>
                  <td className="px-4 py-3.5">
                    {item.last_error && (
                      <div
                        className="text-rose-500 max-w-[150px] truncate text-[10px]"
                        title={item.last_error}
                      >
                        {item.last_error}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-3.5 text-right">
                    {(item.status === "dead" || item.status === "failed") && (
                      <button
                        onClick={() => handleRetry(item.id)}
                        disabled={retrying === item.id}
                        className="p-1.5 text-zinc-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-md transition-all"
                        title="Tentar novamente"
                      >
                        <Play
                          className={cn(
                            "h-4 w-4",
                            retrying === item.id && "animate-pulse",
                          )}
                        />
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {items.length === 0 && !loading && (
          <div className="py-12 flex flex-col items-center justify-center text-zinc-400">
            <CheckCircle2 className="h-10 w-10 mb-3 opacity-20" />
            <p className="text-sm font-medium">Nenhum item na fila</p>
          </div>
        )}
      </div>
    </div>
  );
}
