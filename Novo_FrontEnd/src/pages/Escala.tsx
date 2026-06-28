import { logger } from "@/lib/logger";
import { useCallback, useEffect, useMemo, useState, memo } from "react";
import {
  Plus,
  ChevronLeft,
  ChevronRight,
  Send,
  RefreshCw,
  Check,
  Clock,
  AlertCircle,
  User,
  MessageSquare,
  PhoneCall,
} from "lucide-react";
import {
  cn,
  formatCurrency,
  isBrazilianHoliday,
  getBrazilianHolidayName,
} from "../lib/utils";
import {
  EscalaModal,
  type CompanyEscalaConfig,
  type DriverOption,
  type EditingEntry,
  type EscalaSavePayload,
  type WeekDate,
} from "../components/EscalaModal";
import { ConfirmModal } from "../components/ConfirmModal";
import { authFetch } from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

function toLocalISO(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function getWeekStart(d: Date) {
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  const s = new Date(d);
  s.setDate(diff);
  return toLocalISO(s);
}

function parseVal(val: any, fallback: number): number {
  if (val === null || val === undefined || val === "") return fallback;
  const n = Number(val);
  return Number.isFinite(n) ? n : fallback;
}

function resolveDiariaObj(
  diariaVal: any,
  dateISO: string,
  fallback: number,
): number {
  if (diariaVal == null) return fallback;
  if (typeof diariaVal === "number")
    return Number.isFinite(diariaVal) ? diariaVal : fallback;
  if (typeof diariaVal === "string") {
    if (diariaVal.trim() === "") return fallback;
    const n = Number(diariaVal);
    return Number.isFinite(n) ? n : fallback;
  }
  if (typeof diariaVal === "object") {
    const dow = new Date(dateISO + "T12:00:00").getDay();
    if (dow === 0)
      return parseVal(diariaVal.sunday, parseVal(diariaVal.weekday, fallback));
    if (dow === 6)
      return parseVal(
        diariaVal.saturday,
        parseVal(diariaVal.weekday, fallback),
      );
    return parseVal(diariaVal.weekday, fallback);
  }
  return fallback;
}

type ScheduleEntryLike = {
  daily_rate?: number;
  status?: string;
};

const EscalaRow = memo(function EscalaRow({
  driverUUID,
  driver,
  byDate,
  weekDates,
  todayISO,
  companyConfig,
  onAddForDriverDate,
  onEditEntry,
  onDeleteEntry,
}: {
  driverUUID: string;
  driver: any;
  byDate: Map<string, any[]>;
  weekDates: any[];
  todayISO: string;
  companyConfig: any;
  onAddForDriverDate: (driverUUID: string, dateISO: string) => void;
  onEditEntry: (entry: any) => void;
  onDeleteEntry: (entryId: string) => void;
}) {
  const shiftList = Array.from(byDate.values()).flat() as ScheduleEntryLike[];
  const weekTotal = shiftList.reduce(
    (s, e) => s + Number(e.daily_rate || 0),
    0,
  );

  const statusCell = (
    entriesForDay: any[],
    driverUUID: string,
    dateISO: string,
  ) => {
    if (!entriesForDay || entriesForDay.length === 0)
      return (
        <button
          type="button"
          onClick={() => onAddForDriverDate(driverUUID, dateISO)}
          className="w-full py-1 text-[10px] font-bold text-zinc-300 hover:text-blue-600 hover:bg-blue-50/60 rounded-md border border-dashed border-zinc-200 hover:border-blue-300 transition-all opacity-0 group-hover:opacity-100"
          title="Alocar neste dia"
        >
          + Alocar
        </button>
      );
    return (
      <div className="w-full flex flex-col gap-1.5 items-center">
        {entriesForDay.map((entry: any) => {
          const s = entry.status;
          const cls =
            s === "confirmed"
              ? "bg-emerald-100 text-emerald-700 border-emerald-200"
              : s === "no_show"
                ? "bg-rose-100 text-rose-700 border-rose-200"
                : s === "sent"
                  ? "bg-blue-100 text-blue-700 border-blue-200"
                  : "bg-amber-100 text-amber-700 border-amber-200";
          const label =
            s === "confirmed"
              ? "✓ Conf."
              : s === "no_show"
                ? "✗ Falta"
                : s === "sent"
                  ? "Enviado"
                  : "Pendente";
          let garantidoMinimo = 0;
          if (
            entry.min_guaranteed_override != null &&
            Number.isFinite(Number(entry.min_guaranteed_override))
          ) {
            garantidoMinimo = Number(entry.min_guaranteed_override);
          } else if (
            companyConfig?.report_type === "garantida_horas" &&
            companyConfig?.faixas_horas_config?.length > 0
          ) {
            const [sh, sm] = (entry.shift_start || "08:00")
              .split(":")
              .map(Number);
            const [eh, em] = (entry.shift_end || "18:00")
              .split(":")
              .map(Number);
            let diff = eh + em / 60 - (sh + sm / 60);
            if (diff < 0) diff += 24;
            const sortedFaixas = [...companyConfig.faixas_horas_config].sort(
              (a: any, b: any) =>
                Number(a.horasMaximas) - Number(b.horasMaximas),
            );
            const faixa =
              sortedFaixas.find(
                (f: any) =>
                  diff >= Number(f.horasMinimas) &&
                  diff <= Number(f.horasMaximas),
              ) || sortedFaixas[sortedFaixas.length - 1];
            if (faixa) garantidoMinimo = Number(faixa.valor) || 0;
          } else if (companyConfig?.report_type === "garantida") {
            garantidoMinimo = Number(companyConfig.daily_rate_weekday || 0);
          }
          return (
            <div
              key={entry.id}
              className={cn(
                "relative group/entry w-full flex flex-col gap-0.5 px-2 py-1 rounded-lg text-[9px] font-bold border transition-all shadow-xs",
                cls,
              )}
            >
              <div className="flex items-center justify-between font-extrabold text-[10px]">
                <span className="truncate max-w-[70px]">
                  {entry.shift_label || "Integral"}
                </span>
                <span className="font-mono text-[9px] opacity-75">
                  {entry.shift_start} às {entry.shift_end}
                </span>
              </div>
              <div className="flex items-center justify-between pt-1 border-t border-current/15 mt-1 font-semibold text-[9px]">
                <span>{label}</span>
                <div className="flex flex-col items-end font-mono">
                  <span>
                    Diária: {formatCurrency(Number(entry.daily_rate || 0))}
                  </span>
                  {garantidoMinimo > 0 && (
                    <span className="text-[8px] opacity-85">
                      Gar.: {formatCurrency(garantidoMinimo)}
                    </span>
                  )}
                </div>
              </div>
              <div className="absolute -top-1.5 -right-1.5 opacity-0 group-hover/entry:opacity-100 transition-opacity bg-zinc-900 text-white rounded-md shadow-md flex gap-1 p-1 z-20">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onEditEntry(entry);
                  }}
                  title="Editar"
                  className="hover:text-indigo-400"
                >
                  <svg
                    className="h-3 w-3"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
                    <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
                  </svg>
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteEntry(entry.id);
                  }}
                  title="Remover"
                  className="hover:text-rose-400"
                >
                  <svg
                    className="h-3 w-3"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6l-1 14H6L5 6" />
                    <path d="M10 11v6M14 11v6" />
                    <path d="M9 6V4h6v2" />
                  </svg>
                </button>
              </div>
            </div>
          );
        })}
        <button
          type="button"
          onClick={() => onAddForDriverDate(driverUUID, dateISO)}
          className="w-full py-0.5 text-[9px] font-bold text-zinc-300 hover:text-blue-600 hover:bg-blue-50/60 rounded border border-dashed border-zinc-200 hover:border-blue-300 transition-all opacity-0 group-hover:opacity-100 mt-0.5"
          title="Adicionar outro turno neste dia"
        >
          + Turno
        </button>
      </div>
    );
  };

  return (
    <tr className="hover:bg-zinc-50/50 transition-colors group">
      <td className="px-4 py-2.5 sticky left-0 bg-white group-hover:bg-zinc-50 z-10 border-r border-zinc-100">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-full bg-zinc-900 flex items-center justify-center text-white font-bold text-[10px] shrink-0">
            {(driver?.name || "M").charAt(0)}
          </div>
          <span className="font-semibold text-zinc-900 text-xs">
            {driver?.name || "Motoboy"}
          </span>
        </div>
      </td>
      {weekDates.map((d) => {
        const entriesForDay = byDate.get(d.iso) || [];
        const isToday = d.iso === todayISO;
        return (
          <td
            key={d.iso}
            className={cn(
              "px-1.5 py-1.5 text-center align-middle",
              isToday && "bg-blue-50/30",
            )}
          >
            <div className="flex flex-col items-center gap-1">
              {statusCell(entriesForDay, driverUUID, d.iso)}
            </div>
          </td>
        );
      })}
      <td className="px-4 py-2.5 text-right font-mono font-bold text-zinc-700 text-xs">
        {weekTotal > 0 ? formatCurrency(weekTotal) : "—"}
      </td>
    </tr>
  );
});

export function Escala() {
  const { session } = useAuth();
  const user = session?.user;
  const machineCompanyId = user?.machine_empresa_id || user?.company_id || "";
  const currentCompany = user?.companies?.find(
    (c) => Number(c.id) === Number(machineCompanyId),
  );
  const companyName = currentCompany?.nome || "Empresa";

  const [activeTab, setActiveTab] = useState<"Escalas" | "Produção" | "Equipe">(
    "Escalas",
  );
  const [weekStart, setWeekStart] = useState(() => getWeekStart(new Date()));
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [whatsappState, setWhatsappState] = useState<
    "connected" | "connecting" | "disconnected"
  >("disconnected");
  const [whatsappDetails, setWhatsappDetails] = useState<string>("");
  const [notificationStatus, setNotificationStatus] = useState<{
    type: "success" | "error" | "info";
    message: string;
  } | null>(null);

  const [companyUUID, setCompanyUUID] = useState<string | null>(null);
  const [companyConfig, setCompanyConfig] =
    useState<CompanyEscalaConfig | null>(null);
  const [drivers, setDrivers] = useState<DriverOption[]>([]);
  const [schedule, setSchedule] = useState<any | null>(null);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingEntry, setEditingEntry] = useState<EditingEntry | null>(null);
  const [defaultSelectedDate, setDefaultSelectedDate] = useState<string>("");
  const [defaultDriverUUID, setDefaultDriverUUID] = useState<string>("");
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [entryToDelete, setEntryToDelete] = useState<string | null>(null);

  const [isFreelancerModalOpen, setIsFreelancerModalOpen] = useState(false);
  const [freelancerData, setFreelancerData] = useState({ name: "", phone: "" });

  const handleOpenNewModal = (dUUID?: string) => {
    setEditingEntry(null);
    setDefaultDriverUUID(dUUID || "");
    setDefaultSelectedDate(weekDates[0]?.iso || toLocalISO(new Date()));
    setIsModalOpen(true);
  };

  const handleAddForDriverDate = (driverUUID: string, dateISO: string) => {
    setEditingEntry(null);
    setDefaultDriverUUID(driverUUID);
    setDefaultSelectedDate(dateISO);
    setIsModalOpen(true);
  };

  const weekEnd = useMemo(() => {
    const d = new Date(weekStart + "T12:00:00");
    d.setDate(d.getDate() + 6);
    return toLocalISO(d);
  }, [weekStart]);

  const weekDates: WeekDate[] = useMemo(() => {
    const start = new Date(weekStart + "T12:00:00");
    const names = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];
    return Array.from({ length: 7 }, (_, i) => {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      return {
        iso: toLocalISO(d),
        label: d.toLocaleDateString("pt-BR", {
          day: "2-digit",
          month: "2-digit",
        }),
        dayName: names[i],
      };
    });
  }, [weekStart]);

  const prevWeek = () => {
    const d = new Date(weekStart + "T12:00:00");
    d.setDate(d.getDate() - 7);
    setWeekStart(toLocalISO(d));
  };
  const nextWeek = () => {
    const d = new Date(weekStart + "T12:00:00");
    d.setDate(d.getDate() + 7);
    setWeekStart(toLocalISO(d));
  };
  const goToday = () => setWeekStart(getWeekStart(new Date()));

  const getDailyRateForDate = useCallback(
    (dateISO: string) => {
      const cfg = companyConfig;
      if (!cfg) return 60;
      if (isBrazilianHoliday(dateISO)) {
        return cfg.daily_rate_holiday;
      }
      const dow = new Date(dateISO + "T12:00:00").getDay();
      if (dow === 0) return cfg.daily_rate_sunday;
      if (dow === 6) return cfg.daily_rate_saturday;
      return cfg.daily_rate_weekday;
    },
    [companyConfig],
  );

  const computeDailyRate = useCallback(
    (dateISO: string, payload: EscalaSavePayload) => {
      const cfg = companyConfig;
      if (!cfg) return payload.dailyRateOverride ?? 60;
      if (payload.dailyRateOverride != null) return payload.dailyRateOverride;
      const defaultRate = getDailyRateForDate(dateISO);
      if (cfg.turnos_config?.length > 0) {
        const turno =
          cfg.turnos_config.find(
            (t) => (t.nome || t.label) === payload.shiftLabel,
          ) ||
          cfg.turnos_config.find(
            (t) =>
              (t.startTime || t.inicio) === payload.shiftStart &&
              (t.endTime || t.fim) === payload.shiftEnd,
          );
        if (turno && turno.diaria != null) {
          return resolveDiariaObj(turno.diaria, dateISO, defaultRate);
        }
      }
      return defaultRate;
    },
    [companyConfig, getDailyRateForDate],
  );

  const loadData = useCallback(
    async (isRefresh = false) => {
      if (!machineCompanyId) return;
      if (!isRefresh) setLoading(true);
      setError(null);
      try {
        const companyNameParam = companyName
          ? `&company_name=${encodeURIComponent(companyName)}`
          : "";
        const cfgRes = await authFetch(
          `/api/v1/db/configs?company_id=${machineCompanyId}${companyNameParam}`,
        );
        if (!cfgRes.ok) throw new Error("Falha ao carregar configuração");
        const cfg = await cfgRes.json();
        setCompanyUUID(cfg.company_id || null);
        setCompanyConfig({
          report_type: cfg.report_type || "producao",
          daily_rate_weekday: parseVal(cfg.daily_rate_weekday, 60),
          daily_rate_saturday: parseVal(cfg.daily_rate_saturday, 70),
          daily_rate_sunday: parseVal(cfg.daily_rate_sunday, 80),
          daily_rate_holiday: parseVal(cfg.daily_rate_holiday, 80),
          turnos_config: Array.isArray(cfg.turnos_config)
            ? cfg.turnos_config
            : [],
          faixas_horas_config: Array.isArray(cfg.faixas_horas_config)
            ? cfg.faixas_horas_config
            : [],
        });

        const params = new URLSearchParams({
          empresa_id: String(machineCompanyId),
          limite: "500",
          status_solicitacao: "F",
          data_hora_solicitacao_min: `${weekStart} 00:00:00`,
          data_hora_solicitacao_max: `${weekEnd} 23:59:59`,
        });

        const [driversRes, schedRes] = await Promise.all([
          authFetch(
            `/api/v1/db/company-drivers?company_id=${machineCompanyId}&active_only=0`,
          ),
          cfg.company_id
            ? authFetch(
                `/api/schedules?company_id=${encodeURIComponent(cfg.company_id)}&week_start=${encodeURIComponent(weekStart)}`,
              )
            : Promise.resolve(null),
        ]);

        const driversRaw = driversRes.ok ? await driversRes.json() : [];
        const cdList = (Array.isArray(driversRaw) ? driversRaw : [])
          .map((d: any) => ({
            driverUUID: String(d.driverUUID || ""),
            driverId: d.driverId ? String(d.driverId) : undefined,
            driverName: String(d.driverName || ""),
            driverPhone: d.driverPhone || null,
            isPrimary: Boolean(d.isPrimary),
          }))
          .filter((d: any) => Boolean(d.driverUUID));

        let scheduleObj: any = null;
        let scheduleEntriesSet = new Set<string>();
        if (schedRes && schedRes.ok) {
          const schedData = await schedRes.json();
          scheduleObj = schedData?.schedules?.[0] || null;
          setSchedule(scheduleObj);
          if (scheduleObj?.schedule_entries) {
            scheduleEntriesSet = new Set(
              scheduleObj.schedule_entries.map((e: any) => String(e.driver_id)),
            );
          }
        } else {
          setSchedule(null);
        }

        // Renderização inicial super rápida (Supabase only)
        const initialRelevant = cdList.filter(
          (d: any) =>
            scheduleEntriesSet.has(d.driverUUID) ||
            d.isPrimary ||
            (d.driverId && String(d.driverId).startsWith("FREE-")),
        );
        setDrivers(initialRelevant);
        if (!isRefresh) setLoading(false);

        // Async fetch for Machine Rides so we don't block the UI
        const fetchMachineAsync = async () => {
          try {
            const res = await authFetch(
              `/api/machine/rides?${params.toString()}`,
            );
            const data = res.ok ? await res.json() : {};
            const ridesList = Array.isArray(data.rides) ? data.rides : [];

            const machineDriversMap = new Map<
              string,
              { id: string; name: string; phone?: string }
            >();
            ridesList.forEach((r: any) => {
              const dId = String(r?.condutor_id ?? r?.taxista_id ?? "");
              if (dId && !machineDriversMap.has(dId)) {
                machineDriversMap.set(dId, {
                  id: dId,
                  name: String(r?.nome_condutor || `Condutor ${dId}`),
                  phone: r?.telefone_condutor || undefined,
                });
              }
            });

            const relevantDrivers: any[] = [];
            for (const d of cdList) {
              const isRelevant = Boolean(
                (d.driverId && machineDriversMap.has(d.driverId)) ||
                scheduleEntriesSet.has(d.driverUUID) ||
                d.isPrimary ||
                (d.driverId && String(d.driverId).startsWith("FREE-")),
              );
              if (isRelevant) {
                relevantDrivers.push(d);
              } else if (d.driverId) {
                authFetch(
                  `/api/v1/db/company-drivers?company_id=${machineCompanyId}&driver_id=${d.driverId}`,
                  { method: "DELETE" },
                ).catch(() => {});
              }
            }

            const finalDrivers = [...relevantDrivers];
            const existingIds = new Set(
              relevantDrivers.map((d) => String(d.driverId)),
            );

            for (const [mId, mInfo] of machineDriversMap.entries()) {
              if (!existingIds.has(mId)) {
                try {
                  const syncRes = await authFetch(`/api/v1/db/company-drivers`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      companyId: machineCompanyId,
                      driverId: mId,
                      driverName: mInfo.name,
                      isPrimary: false,
                    }),
                  });
                  if (syncRes.ok) {
                    const syncData = await syncRes.json();
                    if (syncData?.driver_id) {
                      finalDrivers.push({
                        driverUUID: String(syncData.driver_id),
                        driverId: mId,
                        driverName: mInfo.name,
                        driverPhone: mInfo.phone || null,
                        isPrimary: false,
                      });
                      existingIds.add(mId);
                    }
                  }
                } catch (err) {
                  logger.error("Erro sincronizando motoboy da machine:", err);
                }
              }
            }

            setDrivers(finalDrivers);
          } catch (err) {
            logger.error("Erro buscando corridas async:", err);
          }
        };

        fetchMachineAsync();
      } catch (err: any) {
        setError(err?.message || "Erro ao carregar escala");
      } finally {
        if (!isRefresh) setLoading(false);
      }
    },
    [machineCompanyId, companyName, weekStart],
  );

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    async function checkWhatsApp() {
      try {
        const res = await authFetch("/api/schedules/whatsapp-status");
        if (res.ok) {
          const data = await res.json();
          setWhatsappState(data.state || "disconnected");
          setWhatsappDetails(data.details || "");
        } else {
          setWhatsappState("disconnected");
        }
      } catch (err) {
        setWhatsappState("disconnected");
      }
    }
    if (machineCompanyId) {
      checkWhatsApp();
    }
  }, [machineCompanyId]);

  // Build driver → date → entry map
  const entries: any[] = useMemo(
    () => schedule?.schedule_entries || [],
    [schedule],
  );

  const driverMap = useMemo(() => {
    const map = new Map<string, { driver: any; byDate: Map<string, any[]> }>();
    for (const e of entries) {
      if (!map.has(e.driver_id))
        map.set(e.driver_id, { driver: e.driver, byDate: new Map() });
      const list = map.get(e.driver_id)!.byDate.get(e.entry_date) || [];
      list.push(e);
      map.get(e.driver_id)!.byDate.set(e.entry_date, list);
    }
    // Add drivers in the roster that have no entries
    for (const d of drivers) {
      if (!map.has(d.driverUUID))
        map.set(d.driverUUID, {
          driver: {
            id: d.driverUUID,
            name: d.driverName,
            phone: d.driverPhone,
          },
          byDate: new Map(),
        });
    }
    return map;
  }, [entries, drivers]);

  const sortedDrivers = useMemo(
    () =>
      Array.from(driverMap.entries()).sort((a, b) =>
        (a[1].driver?.name || "").localeCompare(b[1].driver?.name || ""),
      ),
    [driverMap],
  );

  // Stats
  const todayISO = toLocalISO(new Date());
  const stats = useMemo(() => {
    const todayEntries = entries.filter((e) => e.entry_date === todayISO);
    return {
      totalWeek: entries.length,
      confirmedWeek: entries.filter((e) => e.status === "confirmed").length,
      pendingWeek: entries.filter(
        (e) => e.status === "pending" || e.status === "sent",
      ).length,
      noShowWeek: entries.filter((e) => e.status === "no_show").length,
      totalToday: todayEntries.length,
      confirmedToday: todayEntries.filter((e) => e.status === "confirmed")
        .length,
    };
  }, [entries, todayISO]);

  const weekLabel = `${weekDates[0]?.label} — ${weekDates[6]?.label}`;

  const handleDeleteEntry = useCallback((entryId: string) => {
    setEntryToDelete(entryId);
    setIsConfirmOpen(true);
  }, []);

  const handleSendSchedule = async () => {
    if (!schedule?.id) return;
    setSending(true);
    setNotificationStatus({
      type: "info",
      message: "Disparando notificações via WhatsApp...",
    });
    try {
      const res = await authFetch(`/api/schedules/${schedule.id}/send`, {
        method: "POST",
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      setNotificationStatus({
        type: "success",
        message: `Disparo concluído: ${data.sent} motoboy(s) notificado(s) no WhatsApp via Evolution API.${data.failed > 0 ? ` | Falhas: ${data.failed}` : ""}`,
      });
      await loadData(true);
    } catch (err: any) {
      setNotificationStatus({
        type: "error",
        message: err?.message || "Erro ao enviar escala via WhatsApp.",
      });
    } finally {
      setSending(false);
    }
  };

  const handleSaveEscala = async (payload: EscalaSavePayload) => {
    if (!companyUUID) {
      setNotificationStatus({
        type: "error",
        message: "Empresa não resolvida. Recarregue a página.",
      });
      return;
    }
    try {
      if (payload.entryId) {
        if (!schedule?.id) throw new Error("Nenhuma escala carregada");
        const dateISO = payload.selectedDates[0] || weekStart;
        const res = await authFetch(`/api/schedules/${schedule.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            entry_updates: [
              {
                id: payload.entryId,
                shift_label: payload.shiftLabel || "Integral",
                shift_start: payload.shiftStart || "08:00",
                shift_end: payload.shiftEnd || "18:00",
                daily_rate: computeDailyRate(dateISO, payload),
                min_guaranteed_override: payload.minGuaranteedOverride ?? null,
                notes: payload.notes || null,
              },
            ],
          }),
        });
        if (!res.ok) {
          const d = await res.json().catch(() => ({}));
          throw new Error(d.error || "Erro ao ajustar");
        }
        setNotificationStatus({
          type: "success",
          message: "Alocação alterada com sucesso.",
        });
      } else {
        const entriesToAdd = payload.selectedDates.map((dateISO) => ({
          driver_id: payload.driverUUID,
          entry_date: dateISO,
          shift_label: payload.shiftLabel || "Integral",
          shift_start: payload.shiftStart || "08:00",
          shift_end: payload.shiftEnd || "18:00",
          daily_rate: computeDailyRate(dateISO, payload),
          min_guaranteed_override: payload.minGuaranteedOverride ?? null,
          notes: payload.notes || null,
        }));
        if (!schedule?.id) {
          const res = await authFetch("/api/schedules", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              company_id: companyUUID,
              week_start: weekStart,
              week_end: weekEnd,
              created_by_name: user?.name || "Sistema",
              entries: entriesToAdd,
            }),
          });
          if (!res.ok) {
            const d = await res.json().catch(() => ({}));
            throw new Error(d.error || "Erro ao criar escala");
          }
          setNotificationStatus({
            type: "success",
            message: "Nova escala criada e motoboy alocado.",
          });
        } else {
          const res = await authFetch(`/api/schedules/${schedule.id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ entries_to_add: entriesToAdd }),
          });
          if (!res.ok) {
            const d = await res.json().catch(() => ({}));
            throw new Error(d.error || "Erro ao atualizar");
          }
          setNotificationStatus({
            type: "success",
            message: "Motoboy alocado com sucesso.",
          });
        }
      }
      setIsModalOpen(false);
      setEditingEntry(null);
      loadData(true);
    } catch (err) {
      setNotificationStatus({
        type: "error",
        message: err instanceof Error ? err.message : "Falha ao salvar escala.",
      });
    }
  };

  const handleEditEntry = (entry: any) => {
    if (!entry?.id) return;
    setEditingEntry({
      id: String(entry.id),
      driverUUID: String(entry.driver_id || ""),
      entryDate: String(entry.entry_date || weekStart),
      shiftLabel: String(entry.shift_label || "Integral"),
      shiftStart: String(entry.shift_start || "08:00"),
      shiftEnd: String(entry.shift_end || "18:00"),
      dailyRate: Number(entry.daily_rate || 0),
      minGuaranteedOverride:
        entry.min_guaranteed_override != null
          ? Number(entry.min_guaranteed_override)
          : null,
      notes: entry.notes ?? "",
    });
    setIsModalOpen(true);
  };

  const confirmDelete = async () => {
    if (!schedule?.id || !entryToDelete) {
      setIsConfirmOpen(false);
      setEntryToDelete(null);
      return;
    }
    try {
      const res = await authFetch(`/api/schedules/${schedule.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ entries_to_remove: [entryToDelete] }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.error || "Erro ao remover");
      }
      setNotificationStatus({
        type: "success",
        message:
          "Alocação removida com sucesso. Livro caixa correspondente foi limpo.",
      });
    } catch (err) {
      setNotificationStatus({
        type: "error",
        message: err instanceof Error ? err.message : "Falha ao remover.",
      });
    }
    setIsConfirmOpen(false);
    setEntryToDelete(null);
    loadData(true);
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 bg-[#F9F9FA] space-y-5 pb-20">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-black text-zinc-900 tracking-tight">
            Escala de Trabalho
          </h1>
          <p className="text-sm text-zinc-500 mt-0.5">
            {companyName} · {weekLabel}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          {whatsappState === "connected" ? (
            <div
              className="hidden sm:flex items-center gap-1.5 px-3 py-2 bg-emerald-50 border border-emerald-200/80 text-emerald-700 rounded-xl text-xs font-semibold shadow-sm"
              title={
                whatsappDetails ||
                "Instância do WhatsApp conectada com sucesso."
              }
            >
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              WhatsApp Online
            </div>
          ) : whatsappState === "connecting" ? (
            <div
              className="hidden sm:flex items-center gap-1.5 px-3 py-2 bg-amber-50 border border-amber-200/80 text-amber-700 rounded-xl text-xs font-semibold shadow-sm animate-pulse"
              title={whatsappDetails || "WhatsApp conectando..."}
            >
              <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
              WhatsApp Conectando...
            </div>
          ) : (
            <div
              className="hidden sm:flex items-center gap-1.5 px-3 py-2 bg-rose-50 border border-rose-200/80 text-rose-700 rounded-xl text-xs font-semibold shadow-sm"
              title={
                whatsappDetails ||
                "Sem conexão com o gateway do WhatsApp. QR code pode ser necessário."
              }
            >
              <div className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
              WhatsApp Offline
            </div>
          )}
          {schedule?.id && (
            <button
              onClick={handleSendSchedule}
              disabled={sending}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl transition-colors disabled:opacity-50 shadow-sm"
            >
              {sending ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              Enviar Notificações
            </button>
          )}
          <button
            onClick={() => handleOpenNewModal()}
            className="flex items-center gap-2 px-4 py-2 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold rounded-xl transition-colors shadow-sm"
          >
            <Plus className="h-4 w-4" /> Alocar Motoboy
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          {
            label: "Na Semana",
            value: stats.totalWeek,
            icon: <User className="h-4 w-4" />,
            color: "text-zinc-700",
            bg: "bg-zinc-100",
          },
          {
            label: "Confirmados",
            value: stats.confirmedWeek,
            icon: <Check className="h-4 w-4" />,
            color: "text-emerald-700",
            bg: "bg-emerald-100",
          },
          {
            label: "Pendentes",
            value: stats.pendingWeek,
            icon: <Clock className="h-4 w-4" />,
            color: "text-amber-700",
            bg: "bg-amber-100",
          },
          {
            label: "Faltas",
            value: stats.noShowWeek,
            icon: <AlertCircle className="h-4 w-4" />,
            color: "text-rose-700",
            bg: "bg-rose-100",
          },
        ].map((s, i) => (
          <div
            key={i}
            className="bg-white rounded-xl p-4 shadow-sm ring-1 ring-zinc-200/60 flex items-center gap-3"
          >
            <div className={cn("p-2 rounded-lg", s.bg, s.color)}>{s.icon}</div>
            <div>
              <p className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">
                {s.label}
              </p>
              <p className={cn("text-2xl font-black tracking-tight", s.color)}>
                {s.value}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Tabs Navigation */}
      <div className="border border-zinc-200/80 bg-white p-1.5 rounded-xl shadow-sm flex items-center gap-1 w-fit">
        <button
          onClick={() => setActiveTab("Escalas")}
          className={cn(
            "px-4 py-2 rounded-lg text-xs font-bold transition-all",
            activeTab === "Escalas"
              ? "bg-zinc-900 text-white shadow-sm"
              : "text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100",
          )}
        >
          Escalas da Semana
        </button>
        <button
          onClick={() => setActiveTab("Produção")}
          className={cn(
            "px-4 py-2 rounded-lg text-xs font-bold transition-all",
            activeTab === "Produção"
              ? "bg-zinc-900 text-white shadow-sm"
              : "text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100",
          )}
        >
          Resumo de Produção
        </button>
        <button
          onClick={() => setActiveTab("Equipe")}
          className={cn(
            "px-4 py-2 rounded-lg text-xs font-bold transition-all",
            activeTab === "Equipe"
              ? "bg-zinc-900 text-white shadow-sm"
              : "text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100",
          )}
        >
          Equipe Ativa ({drivers.length})
        </button>
      </div>

      {/* Tab 1: Escalas */}
      {activeTab === "Escalas" && (
        <div className="space-y-4">
          {/* Week Navigation */}
          <div className="flex items-center justify-between bg-white px-4 py-3 rounded-xl shadow-sm ring-1 ring-zinc-200/60">
            <button
              onClick={prevWeek}
              className="p-2 hover:bg-zinc-100 rounded-lg transition-colors text-zinc-500 hover:text-zinc-900"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>
            <div className="flex items-center gap-3">
              <span className="text-sm font-bold text-zinc-700">
                {weekLabel}
              </span>
              <button
                onClick={goToday}
                className="text-[10px] font-bold text-blue-600 hover:text-blue-800 uppercase tracking-wider"
              >
                Hoje
              </button>
            </div>
            <button
              onClick={nextWeek}
              className="p-2 hover:bg-zinc-100 rounded-lg transition-colors text-zinc-500 hover:text-zinc-900"
            >
              <ChevronRight className="h-5 w-5" />
            </button>
          </div>

          {/* Weekly Grid Table */}
          <div className="bg-white rounded-2xl shadow-sm ring-1 ring-zinc-200/60 overflow-hidden">
            {error && (
              <div className="p-4 text-sm text-red-600 bg-red-50 border-b border-red-100">
                {error}
              </div>
            )}
            {loading ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs whitespace-nowrap">
                  <thead className="bg-zinc-50 border-b border-zinc-200 text-zinc-500 font-bold text-[10px] uppercase tracking-wider animate-pulse">
                    <tr>
                      <th className="px-4 py-3 sticky left-0 bg-zinc-50 z-10 border-r border-zinc-100 min-w-[160px]">
                        Motoboy
                      </th>
                      {weekDates.map((d) => (
                        <th
                          key={d.iso}
                          className="px-2 py-3 text-center min-w-[90px]"
                        >
                          {d.dayName}
                        </th>
                      ))}
                      <th className="px-4 py-3 text-right">Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-100">
                    {Array.from({ length: 5 }).map((_, rowIndex) => (
                      <tr key={rowIndex} className="animate-pulse">
                        <td className="px-4 py-3 sticky left-0 bg-white z-10 border-r border-zinc-100">
                          <div className="flex items-center gap-2.5">
                            <div className="w-7 h-7 rounded-full bg-zinc-200 shrink-0" />
                            <div className="h-4 bg-zinc-200 rounded-md w-28" />
                          </div>
                        </td>
                        {Array.from({ length: 7 }).map((_, colIndex) => (
                          <td key={colIndex} className="px-1.5 py-3">
                            <div className="h-10 bg-zinc-100/80 rounded-lg w-full flex items-center justify-center border border-dashed border-zinc-200" />
                          </td>
                        ))}
                        <td className="px-4 py-3 text-right">
                          <div className="h-4 bg-zinc-200 rounded-md w-16 ml-auto" />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs whitespace-nowrap">
                  <thead className="bg-zinc-50 border-b border-zinc-200 text-zinc-500 font-bold text-[10px] uppercase tracking-wider">
                    <tr>
                      <th className="px-4 py-3 sticky left-0 bg-zinc-50 z-10 border-r border-zinc-100 min-w-[160px]">
                        Motoboy
                      </th>
                      {weekDates.map((d) => {
                        const isToday = d.iso === todayISO;
                        const holidayName = getBrazilianHolidayName(d.iso);
                        return (
                          <th
                            key={d.iso}
                            className={cn(
                              "px-2 py-3 text-center min-w-[90px] relative group",
                              isToday && "bg-blue-50/60 text-blue-600",
                              holidayName &&
                                "bg-amber-50/40 text-amber-900 border-amber-200/50",
                            )}
                          >
                            <div className="flex flex-col items-center justify-center">
                              <span className="flex items-center gap-0.5 font-bold">
                                {d.dayName}
                                {holidayName && (
                                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
                                )}
                              </span>
                              <span className="text-[9px] font-medium opacity-60">
                                {d.label}
                              </span>
                            </div>
                            {holidayName && (
                              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block bg-zinc-950 text-white text-[9px] px-2.5 py-1.5 rounded-lg shadow-xl border border-white/10 z-30 whitespace-nowrap backdrop-blur-md">
                                🇧🇷 {holidayName}
                              </div>
                            )}
                          </th>
                        );
                      })}
                      <th className="px-4 py-3 text-right">Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-100">
                    {sortedDrivers.length === 0 && (
                      <tr>
                        <td
                          colSpan={9}
                          className="px-4 py-10 text-center text-zinc-400"
                        >
                          Nenhum motoboy na equipe. Adicione motoboys na página
                          de Motoboys primeiro.
                        </td>
                      </tr>
                    )}
                    {sortedDrivers.map(([driverUUID, { driver, byDate }]) => (
                      <EscalaRow
                        key={driverUUID}
                        driverUUID={driverUUID}
                        driver={driver}
                        byDate={byDate}
                        weekDates={weekDates}
                        todayISO={todayISO}
                        companyConfig={companyConfig}
                        onAddForDriverDate={handleAddForDriverDate}
                        onEditEntry={handleEditEntry}
                        onDeleteEntry={handleDeleteEntry}
                      />
                    ))}
                  </tbody>
                  {sortedDrivers.length > 0 && (
                    <tfoot className="bg-zinc-900 text-white border-t-2 border-zinc-800">
                      <tr>
                        <td className="px-4 py-2.5 sticky left-0 bg-zinc-900 z-10 text-[10px] font-black uppercase tracking-widest border-r border-zinc-800">
                          Total Diárias
                        </td>
                        {weekDates.map((d) => {
                          const dayTotal = Array.from(
                            driverMap.values(),
                          ).reduce<number>((s, { byDate }) => {
                            const list = (byDate.get(d.iso) ||
                              []) as ScheduleEntryLike[];
                            return (
                              s +
                              list.reduce<number>(
                                (ss, e) => ss + Number(e.daily_rate || 0),
                                0,
                              )
                            );
                          }, 0);
                          return (
                            <td
                              key={d.iso}
                              className="px-2 py-2.5 text-center font-mono text-xs"
                            >
                              {dayTotal > 0 ? formatCurrency(dayTotal) : "—"}
                            </td>
                          );
                        })}
                        <td className="px-4 py-2.5 text-right font-mono font-black text-sm">
                          {formatCurrency(
                            Array.from(driverMap.values()).reduce<number>(
                              (s, { byDate }) =>
                                s +
                                (
                                  Array.from(
                                    byDate.values(),
                                  ).flat() as ScheduleEntryLike[]
                                ).reduce<number>(
                                  (ss, e) => ss + Number(e.daily_rate || 0),
                                  0,
                                ),
                              0,
                            ),
                          )}
                        </td>
                      </tr>
                    </tfoot>
                  )}
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Produção */}
      {activeTab === "Produção" && (
        <div className="bg-white rounded-2xl shadow-sm ring-1 ring-zinc-200/60 overflow-hidden p-6 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-zinc-100 gap-4">
            <div>
              <h2 className="text-lg font-bold text-zinc-900 tracking-tight">
                Resumo de Produção Semanal
              </h2>
              <p className="text-xs text-zinc-500">
                Métricas de ganhos acumulados e produtividade por motoboy em{" "}
                {weekLabel}
              </p>
            </div>
            <div className="sm:text-right bg-zinc-50 p-3 rounded-xl border border-zinc-200/60">
              <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-0.5">
                Faturamento Total Estimado
              </span>
              <span className="text-2xl font-black text-emerald-600 font-mono">
                {formatCurrency(
                  Array.from(driverMap.values()).reduce<number>(
                    (s, { byDate }) =>
                      s +
                      (
                        Array.from(
                          byDate.values(),
                        ).flat() as ScheduleEntryLike[]
                      ).reduce<number>(
                        (ss, e) => ss + Number(e.daily_rate || 0),
                        0,
                      ),
                    0,
                  ),
                )}
              </span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs whitespace-nowrap">
              <thead className="bg-zinc-50 border-b border-zinc-200 text-zinc-500 font-bold text-[10px] uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3 min-w-[200px]">Motoboy</th>
                  <th className="px-4 py-3 text-center">Turnos Realizados</th>
                  <th className="px-4 py-3 text-center">Faltas / No Show</th>
                  <th className="px-4 py-3 text-right">Média por Turno</th>
                  <th className="px-4 py-3 text-right">Ganhos Totais</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {sortedDrivers.map(([driverUUID, { driver, byDate }]) => {
                  const shiftList = Array.from(
                    byDate.values(),
                  ).flat() as ScheduleEntryLike[];
                  const confirmedShifts = shiftList.filter(
                    (e) => e.status === "confirmed",
                  );
                  const noShowShifts = shiftList.filter(
                    (e) => e.status === "no_show",
                  );
                  const total = shiftList.reduce(
                    (s, e) => s + Number(e.daily_rate || 0),
                    0,
                  );
                  const avg =
                    confirmedShifts.length > 0
                      ? total / confirmedShifts.length
                      : shiftList.length > 0
                        ? total / shiftList.length
                        : 0;
                  return (
                    <tr
                      key={driverUUID}
                      className="hover:bg-zinc-50/50 transition-colors font-medium"
                    >
                      <td className="px-4 py-3 text-zinc-900 flex items-center gap-3 font-bold">
                        <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-black text-xs shrink-0">
                          {(driver?.name || "M").charAt(0)}
                        </div>
                        <div>
                          <div>{driver?.name || "Motoboy"}</div>
                          <div className="text-[10px] font-normal text-zinc-400 font-mono">
                            {driver?.phone || "Sem contato"}
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center font-bold text-zinc-700">
                        <span className="px-2 py-0.5 bg-zinc-100 text-zinc-800 rounded-full text-xs">
                          {confirmedShifts.length}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center font-bold">
                        {noShowShifts.length > 0 ? (
                          <span className="px-2 py-0.5 bg-rose-100 text-rose-700 rounded-full text-xs">
                            {noShowShifts.length}
                          </span>
                        ) : (
                          <span className="text-zinc-300">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-zinc-600">
                        {formatCurrency(avg)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono font-bold text-emerald-600 text-sm">
                        {formatCurrency(total)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: Equipe */}
      {activeTab === "Equipe" && (
        <div className="bg-white rounded-2xl shadow-sm ring-1 ring-zinc-200/60 overflow-hidden p-6 space-y-6">
          <div className="flex items-center justify-between pb-4 border-b border-zinc-100">
            <div>
              <h2 className="text-lg font-bold text-zinc-900 tracking-tight">
                Equipe de Motoboys ({drivers.length})
              </h2>
              <p className="text-xs text-zinc-500">
                Gestão e contatos da equipe ativa alocada na loja
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsFreelancerModalOpen(true)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold transition-colors flex items-center gap-2 shadow-sm"
              >
                <User className="w-4 h-4" /> Adicionar Freelancer
              </button>
              <button
                onClick={() => handleOpenNewModal()}
                className="px-4 py-2 bg-zinc-900 hover:bg-zinc-800 text-white rounded-xl text-xs font-bold transition-colors flex items-center gap-2 shadow-sm"
              >
                <Plus className="w-4 h-4" /> Alocar na Escala
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {drivers.map((d) => (
              <div
                key={d.driverUUID}
                className="bg-zinc-50 p-4 rounded-xl border border-zinc-200/80 flex items-center justify-between gap-3 shadow-sm hover:border-zinc-300 transition-all"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-zinc-900 text-white flex items-center justify-center font-bold text-sm shrink-0">
                    {(d.driverName || "M").charAt(0)}
                  </div>
                  <div>
                    <h3 className="font-bold text-zinc-900 text-sm truncate max-w-[150px]">
                      {d.driverName}
                    </h3>
                    <p className="text-xs text-zinc-500 font-mono flex items-center gap-1 mt-0.5">
                      <PhoneCall className="w-3 h-3 text-zinc-400" />
                      {d.driverPhone || "Sem telefone"}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => handleOpenNewModal(d.driverUUID)}
                    className="p-2 text-indigo-600 hover:bg-indigo-100 bg-white rounded-xl shadow-sm border border-zinc-200 transition-colors"
                    title="Alocar na escala"
                  >
                    <Plus className="w-4 h-4" />
                  </button>
                  {d.driverPhone && (
                    <a
                      href={`https://wa.me/${d.driverPhone.replace(/\D/g, "")}`}
                      target="_blank"
                      rel="noreferrer"
                      className="p-2 text-emerald-600 hover:bg-emerald-100 bg-white rounded-xl shadow-sm border border-zinc-200 transition-colors flex items-center justify-center"
                      title="Conversar no WhatsApp"
                    >
                      <MessageSquare className="w-4 h-4" />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <EscalaModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setEditingEntry(null);
        }}
        onSave={handleSaveEscala}
        weekDates={weekDates}
        drivers={drivers}
        companyName={companyName}
        config={companyConfig}
        defaultSelectedDate={
          defaultSelectedDate || weekDates[0]?.iso || toLocalISO(new Date())
        }
        defaultDriverUUID={defaultDriverUUID}
        editingEntry={editingEntry}
      />

      <ConfirmModal
        isOpen={isConfirmOpen}
        title="Remover Alocação"
        message="Tem certeza que deseja remover esta alocação da escala?"
        onConfirm={confirmDelete}
        onCancel={() => {
          setIsConfirmOpen(false);
          setEntryToDelete(null);
        }}
      />

      {/* Freelancer Modal */}
      {isFreelancerModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-zinc-900/40 backdrop-blur-sm">
          <div className="bg-white rounded-2xl w-full max-w-sm shadow-xl flex flex-col overflow-hidden">
            <div className="px-5 py-4 border-b border-zinc-100 flex items-center justify-between bg-zinc-50/50">
              <h3 className="font-bold text-zinc-900">
                Adicionar Motoboy Manual
              </h3>
              <button
                onClick={() => setIsFreelancerModalOpen(false)}
                className="text-zinc-400 hover:text-zinc-700 text-sm font-bold"
              >
                ✕
              </button>
            </div>
            <div className="p-5 space-y-4">
              <p className="text-xs text-zinc-500 leading-relaxed">
                Adicione um motoboy que não esteja na base da Machine para que
                ele receba alocações e apareça nos relatórios com lançamentos
                manuais.
              </p>
              <div>
                <label className="block text-xs font-bold text-zinc-700 mb-1">
                  Nome do Motoboy *
                </label>
                <input
                  type="text"
                  placeholder="Ex: João Silva"
                  className="w-full text-sm font-medium border border-zinc-200 rounded-lg px-3 py-2 bg-white outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                  value={freelancerData.name}
                  onChange={(e) =>
                    setFreelancerData((prev) => ({
                      ...prev,
                      name: e.target.value,
                    }))
                  }
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-zinc-700 mb-1">
                  Telefone (Opcional)
                </label>
                <input
                  type="text"
                  placeholder="Ex: 11999999999"
                  className="w-full text-sm font-medium border border-zinc-200 rounded-lg px-3 py-2 bg-white outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                  value={freelancerData.phone}
                  onChange={(e) =>
                    setFreelancerData((prev) => ({
                      ...prev,
                      phone: e.target.value,
                    }))
                  }
                />
              </div>
            </div>
            <div className="p-4 bg-zinc-50 border-t border-zinc-100 flex justify-end gap-2">
              <button
                onClick={() => setIsFreelancerModalOpen(false)}
                className="px-4 py-2 text-xs font-bold text-zinc-600 hover:text-zinc-900 hover:bg-zinc-200/50 rounded-xl transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={async () => {
                  if (!freelancerData.name) {
                    setNotificationStatus({
                      type: "error",
                      message: "Nome do motoboy é obrigatório.",
                    });
                    return;
                  }
                  try {
                    setLoading(true);
                    const res = await authFetch("/api/v1/db/company-drivers", {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({
                        companyId: machineCompanyId,
                        driverId: `FREE-${Date.now()}`,
                        driverName: freelancerData.name,
                        driverPhone: freelancerData.phone,
                        isPrimary: false,
                      }),
                    });
                    if (!res.ok)
                      throw new Error("Erro ao adicionar motoboy manual.");
                    setNotificationStatus({
                      type: "success",
                      message: "Motoboy manual adicionado à equipe!",
                    });
                    setIsFreelancerModalOpen(false);
                    setFreelancerData({ name: "", phone: "" });
                    // @ts-ignore
                    loadData();
                  } catch (err: any) {
                    setNotificationStatus({
                      type: "error",
                      message: err.message,
                    });
                  } finally {
                    setLoading(false);
                  }
                }}
                className="px-4 py-2 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold rounded-xl transition-colors shadow-sm"
              >
                Adicionar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Glassmorphic Toast Notification */}
      {notificationStatus && (
        <div
          className={cn(
            "fixed bottom-5 right-5 max-w-sm p-4 rounded-xl shadow-xl border flex gap-3 items-start z-50 backdrop-blur-md transition-all duration-300 transform translate-y-0 scale-100",
            notificationStatus.type === "success"
              ? "bg-emerald-50/95 border-emerald-200/80 text-emerald-800"
              : notificationStatus.type === "error"
                ? "bg-rose-50/95 border-rose-200/80 text-rose-800"
                : "bg-blue-50/95 border-blue-200/80 text-blue-800",
          )}
        >
          {notificationStatus.type === "success" ? (
            <Check className="h-5 w-5 text-emerald-600 shrink-0 mt-0.5" />
          ) : notificationStatus.type === "error" ? (
            <AlertCircle className="h-5 w-5 text-rose-600 shrink-0 mt-0.5" />
          ) : (
            <Clock className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />
          )}
          <div className="flex-1">
            <h4 className="text-xs font-black uppercase tracking-wider">
              {notificationStatus.type === "success"
                ? "Sucesso"
                : notificationStatus.type === "error"
                  ? "Erro"
                  : "WhatsApp"}
            </h4>
            <p className="text-xs mt-1 font-semibold leading-relaxed">
              {notificationStatus.message}
            </p>
          </div>
          <button
            onClick={() => setNotificationStatus(null)}
            className="text-current/50 hover:text-current font-bold text-xs shrink-0 self-start p-0.5"
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
}
