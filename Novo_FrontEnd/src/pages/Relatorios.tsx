import { logger } from "@/lib/logger";
import { useState, useEffect, useMemo, useCallback } from "react";
import {
  Download,
  FileText,
  Calendar,
  RefreshCw,
  BarChart3,
  Calculator,
  TrendingUp,
  DollarSign,
  Bike,
  ShieldCheck,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { formatCurrency, cn } from "../lib/utils";
import { useAuth } from "../contexts/AuthContext";
import {
  getCompanyConfig,
  pullConfigFromSupabase,
} from "../services/company-config";
import { exportToCSV } from "../services/export-csv";
import { exportToPDF } from "../services/export-pdf";
import {
  getDailyEntriesForWeek,
  getManualEntriesForWeek,
  pullEntriesFromSupabase,
  getDriverDayAggregation,
} from "../services/entries-store";
import { authFetch } from "../lib/api";

export function Relatorios() {
  const { session } = useAuth();
  const user = session?.user;
  const companyId = user?.machine_empresa_id || user?.company_id || "";
  const currentCompany = user?.companies?.find(
    (c: any) => String(c.id) === String(companyId),
  );
  const companyName = currentCompany?.nome || "Empresa";

  const [loading, setLoading] = useState(false);
  const [syncVersion, setSyncVersion] = useState(0);
  const [machineRides, setMachineRides] = useState<any[]>([]);
  const [ridesWarning, setRidesWarning] = useState<string | null>(null);
  const [storeConfig, setStoreConfig] = useState(() =>
    companyId ? getCompanyConfig(companyId, companyName) : null,
  );
  const [scheduleDailyByDriver, setScheduleDailyByDriver] = useState<
    Record<string, Record<string, number>>
  >({});
  const [scheduleShiftsByDriver, setScheduleShiftsByDriver] = useState<
    Record<
      string,
      Record<
        string,
        Array<{
          start: string;
          end: string;
          dailyRate?: number;
          label?: string;
          minGuaranteedOverride?: number | null;
        }>
      >
    >
  >({});

  const isAdmin =
    user?.role === "admin" ||
    user?.role === "administrador" ||
    user?.role === "master";
  const [viewMode, setViewMode] = useState<"loja" | "motoboy">("loja");

  // Período da semana
  const [currentWeekOffset, setCurrentWeekOffset] = useState(0);

  const weekPeriod = useMemo(() => {
    const now = new Date();
    now.setDate(now.getDate() + currentWeekOffset * 7);
    const day = now.getDay();
    const diff = now.getDate() - day + (day === 0 ? -6 : 1);
    const start = new Date(now.setDate(diff));
    start.setHours(0, 0, 0, 0);
    const end = new Date(start);
    end.setDate(start.getDate() + 6);
    end.setHours(23, 59, 59, 999);

    return {
      start: formatDateISO(start),
      end: formatDateISO(end),
      label: `${start.toLocaleDateString("pt-BR")} a ${end.toLocaleDateString("pt-BR")}`,
      dates: Array.from({ length: 7 }, (_, i) => {
        const d = new Date(start);
        d.setDate(start.getDate() + i);
        return {
          iso: formatDateISO(d),
          label: d
            .toLocaleDateString("pt-BR", { weekday: "short" })
            .toUpperCase()
            .replace(".", ""),
          fullLabel: d.toLocaleDateString("pt-BR", {
            day: "2-digit",
            month: "2-digit",
          }),
        };
      }),
    };
  }, [currentWeekOffset]);

  const loadData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    setRidesWarning(null);

    try {
      const freshConfig = await pullConfigFromSupabase(companyId, companyName);
      setStoreConfig(freshConfig || getCompanyConfig(companyId, companyName));

      await pullEntriesFromSupabase(
        companyId,
        weekPeriod.start,
        weekPeriod.end,
      );

      try {
        // A Machine API não suporta filtros de data — buscamos um lote grande
        // e filtramos no cliente, igual ao frontend antigo.
        const expandedStart = addDaysISO(weekPeriod.start, -1);
        const expandedEnd = addDaysISO(weekPeriod.end, 1);

        const allRides: any[] = [];
        const limit = 500;
        const maxPages = 10;
        let reachedCap = false;

        for (let page = 1; page <= maxPages; page++) {
          const params = new URLSearchParams({
            empresa_id: String(companyId),
            limite: String(limit),
            pagina: String(page),
            status_solicitacao: "F",
          });

          const res = await authFetch(
            `/api/machine/rides?${params.toString()}`,
          );
          if (!res.ok) {
            logger.error("Erro ao buscar corridas:", res.status);
            break;
          }
          const data = await res.json();
          const ridesPage = Array.isArray(data.rides) ? data.rides : [];
          allRides.push(...ridesPage);

          // Parar de paginar assim que encontrarmos corridas mais antigas que o período
          // (a API retorna em ordem decrescente)
          const oldestInPage = ridesPage[ridesPage.length - 1];
          if (oldestInPage) {
            const dateRaw = String(oldestInPage?.data_hora_solicitacao || "");
            const { dateISO } = parseDateTime(dateRaw);
            if (dateISO && dateISO < expandedStart) break; // Passamos do período
          }

          if (ridesPage.length < limit) break; // Última página
          if (page === maxPages) reachedCap = true;
        }

        // Filtragem no cliente
        const filtered = allRides.filter((ride: any) => {
          const dateRaw = String(
            ride?.data_hora_solicitacao || ride?.data_hora_finalizacao || "",
          );
          const { dateISO } = parseDateTime(dateRaw);
          if (!dateISO) return false;
          return dateISO >= expandedStart && dateISO <= expandedEnd;
        });

        setMachineRides(filtered);
        if (reachedCap) {
          setRidesWarning(
            `Atenção: a busca atingiu o limite máximo de páginas. O relatório pode estar incompleto.`,
          );
        }
      } catch (err) {
        logger.error("Erro ao buscar corridas da Machine:", err);
        setMachineRides([]);
        setRidesWarning(
          "Erro ao buscar corridas da Machine. Verifique a integração e tente novamente.",
        );
      }

      try {
        const cfgRes = await authFetch(
          `/api/db/configs?company_id=${companyId}`,
        );
        const cfgData = cfgRes.ok ? await cfgRes.json() : null;
        const companyUUID = cfgData?.company_id
          ? String(cfgData.company_id)
          : null;

        const cdRes = await authFetch(
          `/api/db/company-drivers?company_id=${companyId}&active_only=0`,
        );
        const cdRaw = cdRes.ok ? await cdRes.json() : [];
        const cdList: Array<{ driverUUID: string; driverId: string }> = (
          Array.isArray(cdRaw) ? cdRaw : []
        )
          .map((d: any) => ({
            driverUUID: String(d.driverUUID || ""),
            driverId: String(d.driverId || ""),
          }))
          .filter((d) => d.driverUUID && d.driverId);

        const uuidToMachine = new Map<string, string>();
        cdList.forEach((d) => uuidToMachine.set(d.driverUUID, d.driverId));

        if (companyUUID) {
          const schedRes = await authFetch(
            `/api/schedules?company_id=${encodeURIComponent(companyUUID)}&week_start=${encodeURIComponent(weekPeriod.start)}`,
          );
          const schedData = schedRes.ok ? await schedRes.json() : null;
          const schedules = Array.isArray(schedData?.schedules)
            ? schedData.schedules
            : [];
          const entries = schedules.flatMap((s: any) =>
            Array.isArray(s?.schedule_entries) ? s.schedule_entries : [],
          );

          const map: Record<string, Record<string, number>> = {};
          const shifts: Record<
            string,
            Record<
              string,
              Array<{
                start: string;
                end: string;
                dailyRate?: number;
                label?: string;
                minGuaranteedOverride?: number | null;
              }>
            >
          > = {};
          for (const e of entries) {
            const driverUUID = String(e.driver_id || "");
            const machineId = String(
              (e?.driver as any)?.machine_condutor_id ||
                uuidToMachine.get(driverUUID) ||
                "",
            );
            if (!machineId) continue;
            const date = String(e.entry_date || "");
            if (!date) continue;
            const val = Number(e.daily_rate || 0);
            if (!map[machineId]) map[machineId] = {};
            map[machineId][date] =
              (map[machineId][date] || 0) + (Number.isFinite(val) ? val : 0);

            const shiftStart = String(e.shift_start || "");
            const shiftEnd = String(e.shift_end || "");
            if (shiftStart && shiftEnd) {
              if (!shifts[machineId]) shifts[machineId] = {};
              if (!shifts[machineId][date]) shifts[machineId][date] = [];
              shifts[machineId][date].push({
                start: shiftStart,
                end: shiftEnd,
                dailyRate: val,
                label: String(e.shift_label || ""),
                minGuaranteedOverride:
                  e.min_guaranteed_override != null
                    ? Number(e.min_guaranteed_override)
                    : null,
              });
            }
          }
          setScheduleDailyByDriver(map);
          setScheduleShiftsByDriver(shifts);
        } else {
          setScheduleDailyByDriver({});
          setScheduleShiftsByDriver({});
        }
      } catch {
        setScheduleDailyByDriver({});
        setScheduleShiftsByDriver({});
      }

      setSyncVersion((v) => v + 1);
    } finally {
      setLoading(false);
    }
  }, [companyId, companyName, weekPeriod]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const getGarantidoDiarioConfig = useCallback(
    (cfg: any, dateIso: string): number => {
      if (!cfg) return 0;
      const faixas = Array.isArray(cfg.faixasHoras)
        ? cfg.faixasHoras
        : Array.isArray(cfg.faixas_horas_config)
          ? cfg.faixas_horas_config
          : [];
      const gdObj = faixas.find((f: any) => f.id === "garantido_diario");
      if (gdObj) {
        const dObj = new Date(dateIso + "T12:00:00");
        const dow = dObj.getDay();
        if (dow === 0) return Number(gdObj.sunday) || 0;
        if (dow === 6) return Number(gdObj.saturday) || 0;
        return Number(gdObj.weekday) || 0;
      }
      return Number(cfg.pisoFixo || cfg.diaria?.weekday || 0);
    },
    [],
  );

  // Processamento do Relatório Dinâmico
  const reportData = useMemo(() => {
    if (!companyId || !storeConfig) return null;

    const dailies = getDailyEntriesForWeek(
      companyId,
      weekPeriod.start,
      weekPeriod.end,
    );
    const manuals = getManualEntriesForWeek(
      companyId,
      weekPeriod.start,
      weekPeriod.end,
    );

    const reportType = storeConfig.report?.reportType || "producao";
    const includeTaxaCorridas = storeConfig.report?.includeTaxaCorridas ?? true;
    const showDiaria = storeConfig.report?.showDiaria ?? true;
    const showTxCorridas = storeConfig.report?.showTxCorridas ?? true;
    const showEntregas = storeConfig.report?.showEntregas ?? true;
    const cutoffHour = storeConfig.autoCredit?.cutoffHour ?? 6;
    const cutoffMinute = storeConfig.autoCredit?.cutoffMinute ?? 0;
    const cutoffHHmm = `${String(cutoffHour).padStart(2, "0")}:${String(cutoffMinute).padStart(2, "0")}`;

    const showTxCol =
      viewMode === "motoboy"
        ? false
        : reportType === "producao"
          ? includeTaxaCorridas
          : includeTaxaCorridas && showTxCorridas;

    const driverNames = new Map<string, string>();
    dailies.forEach((d) => driverNames.set(String(d.driverId), d.driverName));
    manuals.forEach((m) => driverNames.set(String(m.driverId), m.driverName));

    const perDriverPerDay: Record<
      string,
      Record<
        string,
        {
          productionValue: number;
          deliveries: number;
          rides: Array<{
            timeHHmm: string;
            fareValue: number;
            numDeliveries: number;
          }>;
        }
      >
    > = {};
    const manualRidesToInject = manuals
      .filter((m) => {
        const isInjectable =
          m.type === "corrida_manual" ||
          (m.type === "extra" &&
            (m.description || "").match(
              /^(\d+)\s*(?:entrega|corrida)s?\s*-\s*/i,
            ));
        if (!isInjectable) return false;
        let vis = (m as any).visibilidade;
        if (!vis && m.description) {
          const visMatch = m.description.match(/\|vis:(loja|motoboy|ambos)/);
          if (visMatch) vis = visMatch[1];
        }
        vis = vis || "ambos";
        if (vis !== "ambos" && vis !== viewMode) return false;
        return true;
      })
      .map((m) => {
        let numDeliveries = (m as any).entregas || 1;
        if (numDeliveries === 1) {
          const match =
            (m.description || "").match(
              /^(\d+)\s*(?:entrega|corrida)s?\s*-\s*/i,
            ) || (m.description || "").match(/(\d+)\s*(?:entrega|corrida)/i);
          if (match) numDeliveries = parseInt(match[1], 10) || 1;
        }
        if (numDeliveries === 1 && m.description) {
          const extraMatch = m.description.match(/\|entregas:(\d+)/);
          if (extraMatch) numDeliveries = parseInt(extraMatch[1], 10) || 1;
        }

        let timeStr = "12:00:00";
        const timeMatch = (m.description || "").match(/(\d{2}:\d{2})/);
        if (timeMatch) timeStr = timeMatch[1] + ":00";

        return {
          condutor_id: m.driverId,
          nome_condutor: m.driverName,
          status_solicitacao: "FINALIZADA_MANUAL",
          valor_corrida: m.amount,
          valor: m.amount,
          data: `${m.date}T${timeStr}Z`,
          paradas: Array(numDeliveries).fill({}),
          manual_id: m.id,
        };
      });

    const combinedRides = [...machineRides, ...manualRidesToInject];

    for (const ride of combinedRides) {
      const condIdRaw = ride?.condutor_id ?? ride?.taxista_id;
      const driverId = String(condIdRaw || "");
      if (!driverId) continue;

      const status = String(ride?.status_solicitacao || "")
        .toUpperCase()
        .trim();
      if (status !== "F" && !status.startsWith("FINALIZ")) continue;

      const dateRaw = String(
        ride?.data_hora_solicitacao ||
          ride?.data_hora_finalizacao ||
          ride?.data ||
          "",
      );
      const parsed = parseDateTime(dateRaw);
      if (!parsed.dateISO) continue;
      const dateKey = resolveBusinessDateISO({
        driverId,
        rideDateISO: parsed.dateISO,
        rideTimeHHmm: parsed.timeHHmm,
        shiftsByDriver: scheduleShiftsByDriver,
        cutoffHHmm,
      });
      if (!dateKey || dateKey < weekPeriod.start || dateKey > weekPeriod.end)
        continue;

      const rawFare = ride?.valor_corrida ?? ride?.valor ?? 0;
      const fareValue =
        typeof rawFare === "string"
          ? parseFloat(rawFare.replace(",", "."))
          : Number(rawFare || 0);
      const numDeliveries = Array.isArray(ride?.paradas)
        ? ride.paradas.length
        : 1;

      if (!perDriverPerDay[driverId]) perDriverPerDay[driverId] = {};
      if (!perDriverPerDay[driverId][dateKey])
        perDriverPerDay[driverId][dateKey] = {
          productionValue: 0,
          deliveries: 0,
          rides: [],
        };
      const validFare = Number.isFinite(fareValue) ? fareValue : 0;
      perDriverPerDay[driverId][dateKey].productionValue += validFare;
      perDriverPerDay[driverId][dateKey].deliveries += numDeliveries;
      perDriverPerDay[driverId][dateKey].rides.push({
        timeHHmm: parsed.timeHHmm,
        fareValue: validFare,
        numDeliveries,
      });

      if (!driverNames.has(driverId)) {
        driverNames.set(
          driverId,
          String(ride?.nome_condutor || `Condutor ${driverId}`),
        );
      }
    }

    const allDriverIds = new Set<string>([
      ...Object.keys(perDriverPerDay),
      ...dailies.map((d) => String(d.driverId)),
      ...manuals.map((m) => String(m.driverId)),
    ]);

    const faixaHoras = Array.isArray(storeConfig.faixasHoras)
      ? storeConfig.faixasHoras
      : [];

    function pickGarantidoPorHoras(driverId: string, dateISO: string) {
      const shifts = scheduleShiftsByDriver[driverId]?.[dateISO] || [];
      if (shifts.length === 0 || faixaHoras.length === 0) return 0;

      const intervals: Array<{ start: number; end: number }> = shifts
        .map((s) => {
          const startM = timeToMinutes(s.start);
          const endM0 = timeToMinutes(s.end);
          const endM = endM0 >= startM ? endM0 : endM0 + 24 * 60;
          return { start: startM, end: endM };
        })
        .filter(
          (i) =>
            Number.isFinite(i.start) &&
            Number.isFinite(i.end) &&
            i.end > i.start,
        );

      intervals.sort((a, b) => a.start - b.start);
      const merged: Array<{ start: number; end: number }> = [];
      for (const it of intervals) {
        const last = merged[merged.length - 1];
        if (!last || it.start > last.end) merged.push({ ...it });
        else last.end = Math.max(last.end, it.end);
      }

      const totalMin = merged.reduce((s, i) => s + (i.end - i.start), 0);
      const hours = totalMin / 60;
      const sortedFaixas = [...faixaHoras].sort(
        (a, b) => Number(a.horasMaximas) - Number(b.horasMaximas),
      );
      const faixa = sortedFaixas.find(
        (f) =>
          hours >= Number(f.horasMinimas) && hours <= Number(f.horasMaximas),
      );
      return faixa ? Number(faixa.valor) || 0 : 0;
    }

    function pickGarantidoForShift(startStr: string, endStr: string) {
      if (!startStr || !endStr || faixaHoras.length === 0) return 0;
      const startM = timeToMinutes(startStr);
      const endM0 = timeToMinutes(endStr);
      let diffM = endM0 - startM;
      if (diffM < 0) diffM += 24 * 60;
      const hours = diffM / 60;
      const sortedFaixas = [...faixaHoras].sort(
        (a, b) => Number(a.horasMaximas) - Number(b.horasMaximas),
      );
      const faixa =
        sortedFaixas.find(
          (f) =>
            hours >= Number(f.horasMinimas) && hours <= Number(f.horasMaximas),
        ) || sortedFaixas[sortedFaixas.length - 1];
      return faixa ? Number(faixa.valor) || 0 : 0;
    }

    function resolveDiariaValue(diariaObj: any, dateStr: string): number {
      if (!diariaObj) return 0;
      const d = new Date(dateStr + "T12:00:00");
      const dayOfWeek = d.getDay();
      if (dayOfWeek === 0)
        return diariaObj.sunday !== undefined && diariaObj.sunday !== null
          ? Number(diariaObj.sunday)
          : diariaObj.weekday !== undefined && diariaObj.weekday !== null
            ? Number(diariaObj.weekday)
            : 0;
      if (dayOfWeek === 6)
        return diariaObj.saturday !== undefined && diariaObj.saturday !== null
          ? Number(diariaObj.saturday)
          : diariaObj.weekday !== undefined && diariaObj.weekday !== null
            ? Number(diariaObj.weekday)
            : 0;
      return diariaObj.weekday !== undefined && diariaObj.weekday !== null
        ? Number(diariaObj.weekday)
        : 0;
    }

    const rows = Array.from(allDriverIds)
      .map((driverId) => {
        const name = driverNames.get(driverId) || `Condutor ${driverId}`;
        const days: Record<string, any> = {};
        const shiftsSummary: Record<
          string,
          {
            producaoReal: number;
            diaria: number;
            garantidoMinimo: number;
            ridesFee: number;
          }
        > = {};

        let totalDiaria = 0;
        let totalGarantido = 0;
        let totalProducaoReal = 0;
        let totalEntregas = 0;
        let totalRidesFee = 0;
        let totalAdiantamentos = 0;
        let totalLiquido = 0;

        for (const d of weekPeriod.dates) {
          const dayRides = perDriverPerDay[driverId]?.[d.iso];
          const productionValue = dayRides?.productionValue || 0;
          const deliveries = dayRides?.deliveries || 0;
          const ridesFee =
            deliveries * (storeConfig.taxaCorridaPerEntrega || 1.6);

          const agg = getDriverDayAggregation(
            companyId,
            driverId,
            d.iso,
            undefined,
            viewMode,
          );
          const diariaFromEntries = agg.diaria;
          const extras = agg.extras;
          const advances = agg.adiantamentos;

          const producaoDia = productionValue + extras;

          let dayDiariaFixa = 0;
          let dayGarantidoMinimo = 0;
          let netSelected = 0;
          const shiftsBreakdown: Array<{
            name: string;
            producaoReal: number;
            entregas: number;
            diaria: number;
            garantidoMinimo: number;
            ridesFee: number;
          }> = [];

          if (reportType === "garantida_horas" || reportType === "garantida") {
            const workedShifts =
              scheduleShiftsByDriver[driverId]?.[d.iso] || [];
            const configuredTurnos: any[] =
              Array.isArray(storeConfig.turnos) && storeConfig.turnos.length > 0
                ? storeConfig.turnos
                : [
                    {
                      id: "t1",
                      nome: "T1",
                      startTime: "08:00",
                      endTime: "15:59",
                    },
                    {
                      id: "t2",
                      nome: "T2",
                      startTime: "16:00",
                      endTime: "23:59",
                    },
                  ];
            const dayRidesList = dayRides?.rides || [];

            let dayPayout = 0;

            if (reportType === "garantida_horas") {
              for (let idx = 0; idx < configuredTurnos.length; idx++) {
                const ct = configuredTurnos[idx];
                const baseName =
                  ct.nome ||
                  ct.label ||
                  (idx === 0 ? "T1" : idx === 1 ? "T2" : `T${idx + 1}`);
                const shiftName =
                  baseName.length > 3 &&
                  (baseName.toLowerCase().includes("almo") ||
                    baseName.toLowerCase().includes("t1") ||
                    baseName.toLowerCase().includes("turno 1"))
                    ? "T1"
                    : baseName.length > 3 &&
                        (baseName.toLowerCase().includes("jan") ||
                          baseName.toLowerCase().includes("t2") ||
                          baseName.toLowerCase().includes("turno 2"))
                      ? "T2"
                      : baseName;
                const csm = timeToMinutes(ct.startTime);
                const cem = timeToMinutes(ct.endTime);

                const matchedWorked = workedShifts.find((w) => {
                  if (
                    w.label &&
                    w.label.toLowerCase() === baseName.toLowerCase()
                  )
                    return true;
                  const startM = timeToMinutes(w.start);
                  if (Math.abs(startM - csm) <= 120) return true;
                  if (cem >= csm) {
                    return startM >= csm && startM <= cem;
                  } else {
                    return startM >= csm || startM <= cem;
                  }
                });

                const shiftStart = matchedWorked
                  ? matchedWorked.start
                  : ct.startTime;
                const shiftEnd = matchedWorked ? matchedWorked.end : ct.endTime;

                let shiftRides: any[] = [];
                if (workedShifts.length === 1) {
                  if (matchedWorked) {
                    // Único turno do motoboy no dia; recebe todas as corridas do dia para que nenhuma entrega concluída no overtime fique separada ou em duplicidade
                    shiftRides = dayRidesList;
                  } else {
                    // Não é o turno escalado; fica vazio
                    shiftRides = [];
                  }
                } else {
                  shiftRides = dayRidesList.filter((r) =>
                    isTimeInShift(r.timeHHmm, shiftStart, shiftEnd),
                  );
                }

                const shiftProduction = shiftRides.reduce(
                  (s, r) => s + r.fareValue,
                  0,
                );
                const shiftDeliveries = shiftRides.reduce(
                  (s, r) => s + (r.numDeliveries || 1),
                  0,
                );
                const shiftRidesFee =
                  shiftDeliveries * (storeConfig.taxaCorridaPerEntrega || 1.6);

                let shiftDiariaFixa = 0;
                let shiftGarantidoMinimo = 0;
                let shiftPayout = 0;

                if (
                  matchedWorked ||
                  shiftProduction > 0 ||
                  diariaFromEntries > 0
                ) {
                  shiftDiariaFixa = resolveDiariaValue(
                    storeConfig.diaria,
                    d.iso,
                  );
                  if (ct.diaria) {
                    shiftDiariaFixa = resolveDiariaValue(ct.diaria, d.iso);
                  }
                  if (
                    matchedWorked &&
                    matchedWorked.dailyRate != null &&
                    Number.isFinite(matchedWorked.dailyRate)
                  ) {
                    shiftDiariaFixa = matchedWorked.dailyRate;
                  } else if (
                    diariaFromEntries > 0 &&
                    workedShifts.length <= 1
                  ) {
                    shiftDiariaFixa = diariaFromEntries;
                  }

                  if (matchedWorked) {
                    shiftGarantidoMinimo =
                      matchedWorked.minGuaranteedOverride != null &&
                      Number.isFinite(matchedWorked.minGuaranteedOverride)
                        ? matchedWorked.minGuaranteedOverride
                        : pickGarantidoForShift(shiftStart, shiftEnd) ||
                          pickGarantidoPorHoras(driverId, d.iso) ||
                          shiftDiariaFixa;
                  } else {
                    shiftGarantidoMinimo = 0;
                  }

                  shiftPayout = Math.max(
                    shiftProduction + shiftDiariaFixa,
                    shiftGarantidoMinimo,
                  );

                  dayDiariaFixa += shiftDiariaFixa;
                  dayGarantidoMinimo += shiftGarantidoMinimo;
                  dayPayout += shiftPayout;
                }

                shiftsBreakdown.push({
                  name: shiftName,
                  producaoReal: shiftProduction,
                  entregas: shiftDeliveries,
                  diaria: shiftDiariaFixa,
                  garantidoMinimo: shiftGarantidoMinimo,
                  ridesFee: shiftRidesFee,
                });

                if (!shiftsSummary[shiftName]) {
                  shiftsSummary[shiftName] = {
                    producaoReal: 0,
                    diaria: 0,
                    garantidoMinimo: 0,
                    ridesFee: 0,
                  };
                }
                shiftsSummary[shiftName].producaoReal += shiftProduction;
                shiftsSummary[shiftName].diaria += shiftDiariaFixa;
                shiftsSummary[shiftName].garantidoMinimo +=
                  shiftGarantidoMinimo;
                shiftsSummary[shiftName].ridesFee += shiftRidesFee;
              }
            } else {
              // reportType === 'garantida'
              if (workedShifts.length > 0) {
                for (const w of workedShifts) {
                  const shiftRides = dayRidesList.filter((r) =>
                    isTimeInShift(r.timeHHmm, w.start, w.end),
                  );
                  const shiftProduction = shiftRides.reduce(
                    (s, r) => s + r.fareValue,
                    0,
                  );

                  let shiftDiariaFixa = resolveDiariaValue(
                    storeConfig.diaria,
                    d.iso,
                  );
                  const matchedTurno = configuredTurnos.find((ct) => {
                    const startM = timeToMinutes(w.start);
                    const csm = timeToMinutes(ct.startTime);
                    return Math.abs(startM - csm) <= 120;
                  });
                  if (matchedTurno && matchedTurno.diaria) {
                    shiftDiariaFixa = resolveDiariaValue(
                      matchedTurno.diaria,
                      d.iso,
                    );
                  }

                  if (w.dailyRate != null && Number.isFinite(w.dailyRate)) {
                    shiftDiariaFixa = w.dailyRate;
                  } else if (
                    diariaFromEntries > 0 &&
                    workedShifts.length === 1
                  ) {
                    shiftDiariaFixa = diariaFromEntries;
                  }

                  const shiftGarantidoMinimo = getGarantidoDiarioConfig(
                    storeConfig,
                    d.iso,
                  );
                  const shiftPayout = Math.max(
                    shiftProduction + shiftDiariaFixa,
                    shiftGarantidoMinimo,
                  );

                  dayDiariaFixa += shiftDiariaFixa;
                  dayGarantidoMinimo += shiftGarantidoMinimo;
                  dayPayout += shiftPayout;
                }
              } else if (
                productionValue > 0 ||
                diariaFromEntries > 0 ||
                scheduleDailyByDriver[driverId]?.[d.iso] !== undefined
              ) {
                dayDiariaFixa =
                  diariaFromEntries > 0
                    ? diariaFromEntries
                    : (scheduleDailyByDriver[driverId]?.[d.iso] ??
                      resolveDiariaValue(storeConfig.diaria, d.iso));
                dayGarantidoMinimo = getGarantidoDiarioConfig(
                  storeConfig,
                  d.iso,
                );
                dayPayout = Math.max(
                  productionValue + dayDiariaFixa,
                  dayGarantidoMinimo,
                );
              }
            }

            netSelected = dayPayout + extras - advances;
          } else {
            // reportType === 'producao'
            const diariaFromSchedule =
              scheduleDailyByDriver[driverId]?.[d.iso] || 0;
            dayDiariaFixa =
              diariaFromEntries > 0 ? diariaFromEntries : diariaFromSchedule;
            const excess = Math.max(0, productionValue - dayDiariaFixa);
            netSelected = dayDiariaFixa + excess + extras - advances;
          }

          days[d.iso] = {
            producaoReal: productionValue,
            entregas: deliveries,
            diaria: dayDiariaFixa,
            extras,
            adiantamentos: advances,
            ridesFee,
            total: netSelected,
            producaoDia: producaoDia,
            garantidoMinimo: dayGarantidoMinimo,
            shifts: shiftsBreakdown,
          };

          totalDiaria += dayDiariaFixa;
          totalGarantido += dayGarantidoMinimo;
          totalProducaoReal += productionValue;
          totalEntregas += deliveries;
          totalRidesFee += ridesFee;
          totalAdiantamentos += advances;
          totalLiquido +=
            viewMode === "motoboy" ? netSelected : netSelected + ridesFee;
        }

        return {
          name,
          days,
          shiftsSummary,
          totalDiaria,
          totalGarantido,
          totalTaxa: totalProducaoReal,
          totalProducaoReal,
          totalEntregas,
          taxaCorridas: totalRidesFee,
          totalAdiantamentos,
          totalLiquido,
        };
      })
      .sort((a, b) => a.name.localeCompare(b.name));

    const sumTaxaCorridas = rows.reduce((s, r) => s + r.taxaCorridas, 0);
    const totalMotoboys = rows.reduce((s, r) => s + r.totalLiquido, 0);

    const pisoByPerc =
      storeConfig.pisoPercentual > 0
        ? totalMotoboys * (storeConfig.pisoPercentual / 100)
        : 0;
    const pisoEfetivo = Math.max(storeConfig.pisoFixo || 0, pisoByPerc);
    const txAdm = Math.max(0, pisoEfetivo - sumTaxaCorridas);

    const txSupervisao = storeConfig.taxaSupervisao || 0;
    const debitoPendente = storeConfig.debitoPendente || 0;
    const totalALiquidar =
      totalMotoboys + txAdm + txSupervisao + debitoPendente;

    const totalShiftsSummary: Record<
      string,
      {
        producaoReal: number;
        diaria: number;
        garantidoMinimo: number;
        ridesFee: number;
      }
    > = {};
    for (const r of rows) {
      if (r.shiftsSummary) {
        for (const [sName, sVals] of Object.entries(r.shiftsSummary)) {
          if (!totalShiftsSummary[sName])
            totalShiftsSummary[sName] = {
              producaoReal: 0,
              diaria: 0,
              garantidoMinimo: 0,
              ridesFee: 0,
            };
          totalShiftsSummary[sName].producaoReal += sVals.producaoReal;
          totalShiftsSummary[sName].diaria += sVals.diaria;
          totalShiftsSummary[sName].garantidoMinimo += sVals.garantidoMinimo;
          totalShiftsSummary[sName].ridesFee += sVals.ridesFee;
        }
      }
    }

    return {
      viewMode,
      drivers: rows,
      totalShiftsSummary,
      reportType,
      showDiaria,
      showTxCol,
      showEntregas,
      totals: {
        logistica: totalMotoboys,
        taxaAdm: txAdm,
        taxaCorridas: sumTaxaCorridas,
        supervisao: txSupervisao,
        debito: debitoPendente,
        totalALiquidar,
      },
    };
  }, [
    companyId,
    storeConfig,
    weekPeriod,
    machineRides,
    syncVersion,
    scheduleDailyByDriver,
    scheduleShiftsByDriver,
    viewMode,
  ]);

  if (!reportData)
    return (
      <div className="p-8 text-center text-zinc-500">
        Carregando dados do relatório...
      </div>
    );

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 bg-[#F9F9FA]">
      <div className="space-y-6 max-w-[1400px] mx-auto pb-20">
        {ridesWarning && (
          <div className="bg-amber-50 border border-amber-200 text-amber-900 px-4 py-3 rounded-xl text-xs font-semibold">
            {ridesWarning}
          </div>
        )}
        {/* Header Estilo Print - Escala Equilibrada */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-800 p-6 sm:p-8 rounded-2xl shadow-lg border border-blue-700/50 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-6 text-white relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl -mr-20 -mt-20 pointer-events-none" />
          <div className="relative z-10">
            <h1 className="text-3xl font-black tracking-tight">
              {companyName}
            </h1>
            <div className="flex items-center gap-2 mt-2">
              <Calendar className="h-4 w-4 opacity-80" />
              <span className="text-sm font-semibold opacity-90">
                Período: {weekPeriod.label}
              </span>
            </div>
          </div>
          <div className="text-left sm:text-right relative z-10">
            <p className="text-[10px] font-black uppercase tracking-[0.2em] opacity-80 mb-2">
              Status do Relatório
            </p>
            <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur-md border border-white/20 px-4 py-2 rounded-full shadow-sm">
              <div className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
              <p className="text-xs font-bold uppercase tracking-wider text-emerald-50">
                {reportData.reportType === "producao"
                  ? "Consolidado Dinâmico"
                  : reportData.reportType === "garantida_horas"
                    ? "Garantida por Horas"
                    : "Garantida Mínima"}
              </p>
            </div>
          </div>
        </div>

        {/* Cards Section - Escala Equilibrada */}
        {viewMode === "loja" && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            <StatCard
              label="Logística Total"
              value={reportData.totals.logistica}
              color="blue"
            />
            <StatCard
              label="Taxa ADM (Corridas)"
              value={reportData.totals.taxaAdm}
              color="orange"
              sub="Piso mínimo"
            />
            <StatCard
              label="Total Corridas"
              value={reportData.totals.taxaCorridas}
              color="purple"
              sub={`R$ ${(storeConfig?.taxaCorridaPerEntrega || 1.6).toFixed(2)}/entrega`}
            />
            <StatCard
              label="Taxa Supervisão"
              value={reportData.totals.supervisao}
              color="green"
            />
            <StatCard
              label="Débito Pendente"
              value={reportData.totals.debito}
              color="red"
            />
          </div>
        )}

        {/* Ações e Navegação Semanal */}
        <div className="flex flex-col sm:flex-row items-center justify-between bg-white px-4 py-3 rounded-2xl shadow-sm ring-1 ring-zinc-200/60 gap-4 mb-4">
          <div className="flex flex-wrap items-center gap-2">
            {isAdmin && (
              <div className="flex bg-zinc-100 p-1 rounded-lg border border-zinc-200 mr-2">
                <button
                  onClick={() => setViewMode("loja")}
                  className={`px-3 py-1.5 text-xs font-bold rounded-md transition-all ${
                    viewMode === "loja"
                      ? "bg-white text-zinc-900 shadow-sm ring-1 ring-zinc-200"
                      : "text-zinc-500 hover:text-zinc-700"
                  }`}
                >
                  Visão Loja
                </button>
                <button
                  onClick={() => setViewMode("motoboy")}
                  className={`px-3 py-1.5 text-xs font-bold rounded-md transition-all ${
                    viewMode === "motoboy"
                      ? "bg-white text-zinc-900 shadow-sm ring-1 ring-zinc-200"
                      : "text-zinc-500 hover:text-zinc-700"
                  }`}
                >
                  Visão Motoboy
                </button>
              </div>
            )}
            <button
              onClick={() => {
                if (!reportData) return;
                exportToCSV({
                  rows: reportData.drivers.map((d: any) => ({
                    nome: d.name,
                    dias: Object.fromEntries(
                      Object.entries(d.days).map(
                        ([iso, day]: [string, any]) => [
                          iso,
                          {
                            producaoReal: day.producaoReal,
                            entregas: day.entregas,
                            diaria: day.diaria,
                            taxa: day.total,
                            valorPago: day.total,
                          },
                        ],
                      ),
                    ),
                    totalDiaria: d.totalDiaria,
                    totalTaxa: d.totalTaxa,
                    taxaCorridas: d.taxaCorridas,
                    adiantamentos: d.totalAdiantamentos,
                    totalLiquido: d.totalLiquido,
                    producaoExibida: d.totalProducaoReal,
                    totalProducaoReal: d.totalProducaoReal,
                    totalEntregas: d.totalEntregas,
                    payoutTotal: d.totalLiquido,
                  })),
                  weekDates: weekPeriod.dates.map((d) => ({
                    iso: d.iso,
                    dayName: d.label,
                  })),
                  reportType: reportData.reportType as any,
                  includeTaxaCorridas: reportData.showTxCol,
                  companyName: companyName,
                  periodLabel: weekPeriod.label,
                  totalGeral: reportData.totals.logistica,
                  txAdm: reportData.totals.taxaAdm,
                  txSupervisao: reportData.totals.supervisao,
                  debitoPendente: reportData.totals.debito,
                  totalALiquidar: reportData.totals.totalALiquidar,
                });
              }}
              disabled={reportData.drivers.length === 0}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Download className="h-4 w-4" /> Baixar Planilha
            </button>

            {/* Botão PDF */}
            <button
              onClick={() => {
                if (!reportData) return;
                exportToPDF({
                  rows: reportData.drivers.map((d: any) => ({
                    nome: d.name,
                    dias: Object.fromEntries(
                      Object.entries(d.days).map(
                        ([iso, day]: [string, any]) => [
                          iso,
                          {
                            producaoReal: day.producaoReal,
                            entregas: day.entregas,
                            diaria: day.diaria,
                            taxa: day.total,
                            valorPago: day.total,
                          },
                        ],
                      ),
                    ),
                    totalDiaria: d.totalDiaria,
                    totalTaxa: d.totalTaxa,
                    taxaCorridas: d.taxaCorridas,
                    adiantamentos: d.totalAdiantamentos,
                    totalLiquido: d.totalLiquido,
                    producaoExibida: d.totalProducaoReal,
                    totalProducaoReal: d.totalProducaoReal,
                    totalEntregas: d.totalEntregas,
                    payoutTotal: d.totalLiquido,
                  })),
                  weekDates: weekPeriod.dates.map((d) => ({
                    iso: d.iso,
                    dayName: d.label,
                    fullLabel: d.fullLabel,
                  })),
                  reportType: reportData.reportType as any,
                  includeTaxaCorridas: reportData.showTxCol,
                  companyName: companyName,
                  periodLabel: weekPeriod.label,
                  totalGeral: reportData.totals.logistica,
                  txAdm: reportData.totals.taxaAdm,
                  txSupervisao: reportData.totals.supervisao,
                  debitoPendente: reportData.totals.debito,
                  totalALiquidar: reportData.totals.totalALiquidar,
                });
              }}
              disabled={reportData.drivers.length === 0}
              className="flex items-center gap-2 px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <FileText className="h-4 w-4" /> Baixar PDF
            </button>

            <button
              onClick={() => window.print()}
              className="flex items-center gap-2 px-4 py-2 bg-zinc-100 hover:bg-zinc-200 text-zinc-700 text-xs font-bold rounded-xl transition-colors"
            >
              Imprimir
            </button>
          </div>

          <div className="flex items-center gap-4 bg-zinc-50 px-2 py-1 rounded-xl">
            <button
              onClick={() => setCurrentWeekOffset((o) => o - 1)}
              className="p-2 hover:bg-white hover:shadow-sm rounded-lg transition-all text-zinc-500 hover:text-zinc-900 focus:ring-2 focus:ring-zinc-200 outline-none"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-zinc-400" />
              <span className="text-sm font-bold text-zinc-700 tracking-wide">
                {weekPeriod.label}
              </span>
            </div>
            <button
              onClick={() => setCurrentWeekOffset((o) => o + 1)}
              className="p-2 hover:bg-white hover:shadow-sm rounded-lg transition-all text-zinc-500 hover:text-zinc-900 focus:ring-2 focus:ring-zinc-200 outline-none"
            >
              <ChevronRight className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Table Section - Escala Equilibrada */}
        <div className="bg-white rounded-2xl shadow-sm ring-1 ring-zinc-200/60 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-max text-left whitespace-nowrap text-[11px] sm:text-xs">
              <thead className="bg-zinc-50/80 border-b border-zinc-200 text-zinc-500 font-bold uppercase tracking-wider">
                <tr>
                  <th className="px-3 py-2.5 sticky left-0 bg-zinc-50 z-10 border-r border-zinc-100">
                    Motoboy
                  </th>
                  {weekPeriod.dates.map((d) => (
                    <th key={d.iso} className="px-2 py-2.5 text-center">
                      <div>{d.label}</div>
                      <div className="text-[9px] opacity-50">{d.fullLabel}</div>
                    </th>
                  ))}
                  {reportData.reportType === "producao" ? (
                    <>
                      <th className="px-3 py-2.5 text-right">Diária</th>
                      <th className="px-3 py-2.5 text-right">Taxa</th>
                    </>
                  ) : (
                    <>
                      <th className="px-3 py-2.5 text-right">Produção</th>
                      {reportData.showDiaria && (
                        <th className="px-3 py-2.5 text-right">Diária</th>
                      )}
                      <th className="px-3 py-2.5 text-right">Garantido</th>
                    </>
                  )}
                  {reportData.showTxCol && (
                    <th className="px-3 py-2.5 text-right">Tx Corridas</th>
                  )}
                  <th className="px-3 py-2.5 text-right">Adto.</th>
                  <th className="px-4 py-2.5 text-right bg-zinc-900 text-white font-black border-l border-zinc-800 sticky right-0 z-20 shadow-[-4px_0_12px_rgba(0,0,0,0.1)]">
                    Total Líquido
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 font-bold">
                {reportData.drivers.map((mb, i) => (
                  <tr
                    key={i}
                    className="hover:bg-zinc-50/50 transition-colors group"
                  >
                    <td className="px-3 py-1.5 sticky left-0 bg-white group-hover:bg-zinc-50 z-10 border-r border-zinc-100 text-zinc-900">
                      {mb.name}
                    </td>
                    {weekPeriod.dates.map((d) => {
                      const day = mb.days[d.iso];
                      return (
                        <td
                          key={d.iso}
                          className="px-2 py-1.5 text-center align-middle"
                        >
                          {day &&
                          (day.producaoReal > 0 ||
                            day.entregas > 0 ||
                            day.diaria > 0 ||
                            day.extras > 0 ||
                            (day.shifts &&
                              day.shifts.some(
                                (s: any) =>
                                  s.producaoReal > 0 ||
                                  s.diaria > 0 ||
                                  s.garantidoMinimo > 0,
                              ))) ? (
                            reportData.reportType === "garantida_horas" &&
                            day.shifts &&
                            day.shifts.length > 0 ? (
                              <div className="flex flex-col items-center leading-tight py-1">
                                <table className="mx-auto text-[10px] sm:text-[11px] font-mono font-bold text-emerald-600 leading-tight">
                                  <tbody>
                                    {day.shifts.map((s: any, sIdx: number) => (
                                      <tr key={sIdx}>
                                        <td className="text-right pr-1 font-semibold text-emerald-700">
                                          {s.name}:
                                        </td>
                                        <td className="text-left font-normal text-[10px] opacity-75 pr-0.5 align-baseline">
                                          R$
                                        </td>
                                        <td className="text-right align-baseline">
                                          {formatCurrency(s.producaoReal)
                                            .replace("R$", "")
                                            .replace(/\s/g, "")
                                            .trim()}
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                                {reportData.showEntregas &&
                                  day.shifts.some(
                                    (s: any) => s.entregas > 0,
                                  ) && (
                                    <div className="text-[10px] font-mono font-medium text-zinc-400 mt-1 text-center tracking-tight">
                                      {day.shifts
                                        .filter((s: any) => s.entregas > 0)
                                        .map(
                                          (s: any) =>
                                            `${s.name}: ${s.entregas}`,
                                        )
                                        .join(" | ")}
                                    </div>
                                  )}
                              </div>
                            ) : (
                              <div className="flex flex-col items-center leading-tight py-1">
                                <span className="text-emerald-600 font-mono font-bold text-xs">
                                  {formatCurrency(day.producaoDia || 0)}
                                </span>
                                {reportData.showEntregas &&
                                  day.entregas > 0 && (
                                    <span className="text-[9px] text-zinc-400 uppercase tracking-tighter mt-0.5">
                                      {day.entregas} ents.
                                    </span>
                                  )}
                              </div>
                            )
                          ) : (
                            <span className="text-zinc-200">—</span>
                          )}
                        </td>
                      );
                    })}
                    {reportData.reportType === "producao" ? (
                      <>
                        <td className="px-3 py-1.5 text-right font-mono text-zinc-600 align-middle">
                          {formatCurrency(mb.totalDiaria)}
                        </td>
                        <td className="px-3 py-1.5 text-right font-mono text-emerald-600 align-middle">
                          {formatCurrency(mb.totalTaxa)}
                        </td>
                      </>
                    ) : (
                      <>
                        <td className="px-3 py-1.5 text-right font-mono align-middle font-semibold text-zinc-900 text-xs">
                          {reportData.reportType === "garantida_horas" &&
                          mb.shiftsSummary &&
                          Object.keys(mb.shiftsSummary).length > 0 ? (
                            <table className="ml-auto text-[10px] sm:text-[11px] font-mono font-semibold text-zinc-900 leading-tight">
                              <tbody>
                                {Object.entries(mb.shiftsSummary).map(
                                  ([sName, sVals]: [string, any]) => (
                                    <tr key={sName}>
                                      <td className="text-right pr-1 text-zinc-500 font-normal">
                                        {sName}:
                                      </td>
                                      <td className="text-left font-normal text-[10px] opacity-60 pr-0.5 align-baseline">
                                        R$
                                      </td>
                                      <td className="text-right align-baseline">
                                        {formatCurrency(sVals.producaoReal)
                                          .replace("R$", "")
                                          .replace(/\s/g, "")
                                          .trim()}
                                      </td>
                                    </tr>
                                  ),
                                )}
                              </tbody>
                            </table>
                          ) : (
                            <span>{formatCurrency(mb.totalProducaoReal)}</span>
                          )}
                        </td>
                        {reportData.showDiaria && (
                          <td className="px-3 py-1.5 text-right font-mono align-middle font-semibold text-orange-600 text-xs">
                            {reportData.reportType === "garantida_horas" &&
                            mb.shiftsSummary &&
                            Object.keys(mb.shiftsSummary).length > 0 ? (
                              <table className="ml-auto text-[10px] sm:text-[11px] font-mono font-semibold text-orange-600 leading-tight">
                                <tbody>
                                  {Object.entries(mb.shiftsSummary).map(
                                    ([sName, sVals]: [string, any]) => (
                                      <tr key={sName}>
                                        <td className="text-right pr-1 text-orange-400 font-normal">
                                          {sName}:
                                        </td>
                                        <td className="text-left font-normal text-[10px] opacity-60 pr-0.5 align-baseline">
                                          R$
                                        </td>
                                        <td className="text-right align-baseline">
                                          {formatCurrency(sVals.diaria)
                                            .replace("R$", "")
                                            .replace(/\s/g, "")
                                            .trim()}
                                        </td>
                                      </tr>
                                    ),
                                  )}
                                </tbody>
                              </table>
                            ) : (
                              <span>{formatCurrency(mb.totalDiaria)}</span>
                            )}
                          </td>
                        )}
                        <td className="px-3 py-1.5 text-right font-mono align-middle font-semibold text-indigo-600 text-xs">
                          {reportData.reportType === "garantida_horas" &&
                          mb.shiftsSummary &&
                          Object.keys(mb.shiftsSummary).length > 0 ? (
                            <table className="ml-auto text-[10px] font-mono font-semibold text-indigo-600 leading-tight">
                              <tbody>
                                {Object.entries(mb.shiftsSummary).map(
                                  ([sName, sVals]: [string, any]) => (
                                    <tr key={sName}>
                                      <td className="text-right pr-1 text-indigo-400 font-normal">
                                        {sName}:
                                      </td>
                                      <td className="text-left font-normal text-[10px] opacity-60 pr-0.5 align-baseline">
                                        R$
                                      </td>
                                      <td className="text-right align-baseline">
                                        {formatCurrency(sVals.garantidoMinimo)
                                          .replace("R$", "")
                                          .replace(/\s/g, "")
                                          .trim()}
                                      </td>
                                    </tr>
                                  ),
                                )}
                              </tbody>
                            </table>
                          ) : (
                            <span>{formatCurrency(mb.totalGarantido)}</span>
                          )}
                        </td>
                      </>
                    )}
                    {reportData.showTxCol && (
                      <td className="px-3 py-1.5 text-right font-mono align-middle italic text-zinc-500 text-xs">
                        {reportData.reportType === "garantida_horas" &&
                        mb.shiftsSummary &&
                        Object.keys(mb.shiftsSummary).length > 0 ? (
                          <table className="ml-auto text-xs font-mono italic text-zinc-500 leading-tight">
                            <tbody>
                              {Object.entries(mb.shiftsSummary).map(
                                ([sName, sVals]: [string, any]) => (
                                  <tr key={sName}>
                                    <td className="text-right pr-1 text-zinc-400 font-normal">
                                      {sName}:
                                    </td>
                                    <td className="text-left font-normal text-[10px] opacity-60 pr-0.5 align-baseline">
                                      R$
                                    </td>
                                    <td className="text-right align-baseline">
                                      {formatCurrency(sVals.ridesFee)
                                        .replace("R$", "")
                                        .replace(/\s/g, "")
                                        .trim()}
                                    </td>
                                  </tr>
                                ),
                              )}
                            </tbody>
                          </table>
                        ) : (
                          <span>{formatCurrency(mb.taxaCorridas)}</span>
                        )}
                      </td>
                    )}
                    <td className="px-3 py-1.5 text-right text-rose-500 font-mono align-middle">
                      {mb.totalAdiantamentos > 0
                        ? `-${formatCurrency(mb.totalAdiantamentos)}`
                        : "—"}
                    </td>
                    <td className="px-4 py-1.5 text-right font-mono text-zinc-900 bg-zinc-50 border-l border-zinc-100 font-black text-sm group-hover:bg-zinc-100 transition-colors align-middle sticky right-0 z-10 shadow-[-4px_0_12px_rgba(0,0,0,0.05)]">
                      {formatCurrency(mb.totalLiquido)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-zinc-900 border-t-2 border-zinc-800 font-black text-white">
                <tr>
                  <td className="px-3 py-2.5 sticky left-0 bg-zinc-900 z-10 text-[10px] uppercase tracking-widest border-r border-zinc-800 align-middle">
                    Total Acumulado
                  </td>
                  {weekPeriod.dates.map((d) => (
                    <td
                      key={d.iso}
                      className="px-2 py-2.5 text-center align-middle"
                    >
                      —
                    </td>
                  ))}
                  {reportData.reportType === "producao" ? (
                    <>
                      <td className="px-3 py-2.5 text-right font-mono align-middle">
                        {formatCurrency(
                          reportData.drivers.reduce(
                            (s, d) => s + d.totalDiaria,
                            0,
                          ),
                        )}
                      </td>
                      <td className="px-3 py-2.5 text-right font-mono align-middle">
                        {formatCurrency(
                          reportData.drivers.reduce(
                            (s, d) => s + d.totalTaxa,
                            0,
                          ),
                        )}
                      </td>
                    </>
                  ) : (
                    <>
                      <td className="px-3 py-2.5 text-right font-mono align-middle text-xs">
                        {reportData.reportType === "garantida_horas" &&
                        reportData.totalShiftsSummary &&
                        Object.keys(reportData.totalShiftsSummary).length >
                          0 ? (
                          <table className="ml-auto text-[10px] sm:text-[11px] font-mono text-white leading-tight font-bold">
                            <tbody>
                              {Object.entries(
                                reportData.totalShiftsSummary,
                              ).map(([sName, sVals]: [string, any]) => (
                                <tr key={sName}>
                                  <td className="text-right pr-1 text-zinc-400 font-normal">
                                    {sName}:
                                  </td>
                                  <td className="text-left font-normal text-[10px] opacity-60 pr-0.5 align-baseline text-zinc-400">
                                    R$
                                  </td>
                                  <td className="text-right align-baseline">
                                    {formatCurrency(sVals.producaoReal)
                                      .replace("R$", "")
                                      .replace(/\s/g, "")
                                      .trim()}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        ) : (
                          <span>
                            {formatCurrency(
                              reportData.drivers.reduce(
                                (s, d) => s + d.totalProducaoReal,
                                0,
                              ),
                            )}
                          </span>
                        )}
                      </td>
                      {reportData.showDiaria && (
                        <td className="px-3 py-2.5 text-right font-mono align-middle text-orange-400 text-xs">
                          {reportData.reportType === "garantida_horas" &&
                          reportData.totalShiftsSummary &&
                          Object.keys(reportData.totalShiftsSummary).length >
                            0 ? (
                            <table className="ml-auto text-[10px] sm:text-[11px] font-mono text-orange-400 leading-tight font-bold">
                              <tbody>
                                {Object.entries(
                                  reportData.totalShiftsSummary,
                                ).map(([sName, sVals]: [string, any]) => (
                                  <tr key={sName}>
                                    <td className="text-right pr-1 text-orange-300/70 font-normal">
                                      {sName}:
                                    </td>
                                    <td className="text-left font-normal text-[10px] opacity-60 pr-0.5 align-baseline text-orange-300/70">
                                      R$
                                    </td>
                                    <td className="text-right align-baseline">
                                      {formatCurrency(sVals.diaria)
                                        .replace("R$", "")
                                        .replace(/\s/g, "")
                                        .trim()}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          ) : (
                            <span>
                              {formatCurrency(
                                reportData.drivers.reduce(
                                  (s, d) => s + d.totalDiaria,
                                  0,
                                ),
                              )}
                            </span>
                          )}
                        </td>
                      )}
                      <td className="px-3 py-2.5 text-right font-mono align-middle text-indigo-400 text-xs">
                        {reportData.reportType === "garantida_horas" &&
                        reportData.totalShiftsSummary &&
                        Object.keys(reportData.totalShiftsSummary).length >
                          0 ? (
                          <table className="ml-auto text-[10px] sm:text-[11px] font-mono text-indigo-400 leading-tight font-bold">
                            <tbody>
                              {Object.entries(
                                reportData.totalShiftsSummary,
                              ).map(([sName, sVals]: [string, any]) => (
                                <tr key={sName}>
                                  <td className="text-right pr-1 text-indigo-300/70 font-normal">
                                    {sName}:
                                  </td>
                                  <td className="text-left font-normal text-[10px] opacity-60 pr-0.5 align-baseline text-indigo-300/70">
                                    R$
                                  </td>
                                  <td className="text-right align-baseline">
                                    {formatCurrency(sVals.garantidoMinimo)
                                      .replace("R$", "")
                                      .replace(/\s/g, "")
                                      .trim()}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        ) : (
                          <span>
                            {formatCurrency(
                              reportData.drivers.reduce(
                                (s, d) => s + d.totalGarantido,
                                0,
                              ),
                            )}
                          </span>
                        )}
                      </td>
                    </>
                  )}
                  {reportData.showTxCol && (
                    <td className="px-3 py-2.5 text-right font-mono align-middle text-zinc-300 text-xs">
                      {reportData.reportType === "garantida_horas" &&
                      reportData.totalShiftsSummary &&
                      Object.keys(reportData.totalShiftsSummary).length > 0 ? (
                        <table className="ml-auto text-[10px] sm:text-[11px] font-mono text-zinc-300 leading-tight font-bold">
                          <tbody>
                            {Object.entries(reportData.totalShiftsSummary).map(
                              ([sName, sVals]: [string, any]) => (
                                <tr key={sName}>
                                  <td className="text-right pr-1 text-zinc-400 font-normal">
                                    {sName}:
                                  </td>
                                  <td className="text-left font-normal text-[10px] opacity-60 pr-0.5 align-baseline text-zinc-400">
                                    R$
                                  </td>
                                  <td className="text-right align-baseline">
                                    {formatCurrency(sVals.ridesFee)
                                      .replace("R$", "")
                                      .replace(/\s/g, "")
                                      .trim()}
                                  </td>
                                </tr>
                              ),
                            )}
                          </tbody>
                        </table>
                      ) : (
                        <span>
                          {formatCurrency(reportData.totals.taxaCorridas)}
                        </span>
                      )}
                    </td>
                  )}
                  <td className="px-3 py-2.5 text-right font-mono text-zinc-400 align-middle">
                    -
                    {formatCurrency(
                      reportData.drivers.reduce(
                        (s, d) => s + d.totalAdiantamentos,
                        0,
                      ),
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono text-[15px] border-l border-zinc-800 bg-zinc-900 text-white align-middle sticky right-0 z-20 shadow-[-4px_0_12px_rgba(0,0,0,0.1)]">
                    {formatCurrency(reportData.totals.logistica)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>

        {/* Total a Liquidar */}
        {viewMode === "loja" && (
          <div className="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm ring-1 ring-zinc-200/60 gap-6 relative overflow-hidden mt-2">
            <div className="absolute inset-0 bg-gradient-to-br from-transparent to-zinc-50/80 pointer-events-none" />
            <div className="relative z-10 w-full md:w-auto">
              <div className="flex items-center gap-3 mb-2">
                <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 shrink-0">
                  <DollarSign className="h-5 w-5" strokeWidth={2.5} />
                </div>
                <h3 className="text-2xl font-black text-zinc-900 uppercase tracking-tight">
                  Total a Liquidar (Loja)
                </h3>
              </div>
              <p className="text-xs text-zinc-500 font-medium ml-14">
                Tabela + TX Adm + TX Supervisão + Débito Pendente
              </p>
              <div className="mt-6 ml-14 flex flex-col gap-2.5 text-xs font-bold text-zinc-500 uppercase tracking-widest">
                <div className="flex justify-between w-64 items-center">
                  <span className="opacity-70">Logística:</span>{" "}
                  <span className="text-zinc-900">
                    {formatCurrency(reportData.totals.logistica)}
                  </span>
                </div>
                {reportData.totals.taxaAdm > 0 && (
                  <div className="flex justify-between w-64 items-center">
                    <span className="opacity-70">+ Taxa ADM:</span>{" "}
                    <span className="text-zinc-900">
                      {formatCurrency(reportData.totals.taxaAdm)}
                    </span>
                  </div>
                )}
                {reportData.totals.supervisao > 0 && (
                  <div className="flex justify-between w-64 items-center">
                    <span className="opacity-70">+ Supervisão:</span>{" "}
                    <span className="text-emerald-600">
                      {formatCurrency(reportData.totals.supervisao)}
                    </span>
                  </div>
                )}
                {reportData.totals.debito > 0 && (
                  <div className="flex justify-between w-64 items-center">
                    <span className="opacity-70">+ Débito:</span>{" "}
                    <span className="text-rose-600">
                      {formatCurrency(reportData.totals.debito)}
                    </span>
                  </div>
                )}
              </div>
            </div>
            <div className="relative z-10 w-full md:w-auto text-left md:text-right">
              <p className="text-[11px] font-bold text-zinc-400 uppercase tracking-widest mb-1.5">
                Valor Final
              </p>
              <div className="text-3xl sm:text-4xl font-black text-blue-600 tracking-tight">
                {formatCurrency(reportData.totals.totalALiquidar)}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  color,
  sub,
}: {
  label: string;
  value: number;
  color: "blue" | "orange" | "purple" | "green" | "red";
  sub?: string;
}) {
  const colorMap = {
    blue: "text-blue-600",
    orange: "text-orange-600",
    purple: "text-purple-600",
    green: "text-emerald-600",
    red: "text-rose-600",
  };

  return (
    <div className="px-5 py-4 rounded-2xl bg-white shadow-sm ring-1 ring-zinc-200/60 transition-shadow hover:shadow-md flex flex-col justify-center">
      <h3 className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">
        {label}
      </h3>
      <p
        className={cn(
          "text-xl sm:text-2xl font-black tracking-tight mt-1",
          colorMap[color],
        )}
      >
        {formatCurrency(value)}
      </p>
      {sub && (
        <p className="text-[10px] text-zinc-400 font-bold uppercase mt-1 tracking-wide">
          {sub}
        </p>
      )}
    </div>
  );
}

function formatDateISO(d: Date) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function addDaysISO(iso: string, days: number) {
  const [y, m, d] = iso.split("-").map((n) => Number(n));
  const dt = new Date(y, (m || 1) - 1, d || 1);
  dt.setDate(dt.getDate() + days);
  return formatDateISO(dt);
}

function parseDateTime(raw: string): { dateISO: string; timeHHmm: string } {
  const v = String(raw || "").trim();
  if (!v) return { dateISO: "", timeHHmm: "00:00" };
  const [datePart, timePartRaw] = v.includes("T") ? v.split("T") : v.split(" ");
  const dateISO = (datePart || "").trim();
  const timePart = (timePartRaw || "").trim();
  const timeHHmm = timePart ? timePart.slice(0, 5) : "00:00";
  return { dateISO, timeHHmm };
}

function timeToMinutes(hhmm: string) {
  const [h, m] = String(hhmm || "00:00").split(":");
  const hh = Number(h || 0);
  const mm = Number(m || 0);
  return (Number.isFinite(hh) ? hh : 0) * 60 + (Number.isFinite(mm) ? mm : 0);
}

function isOvernightShift(start: string, end: string) {
  const s = timeToMinutes(start);
  const e = timeToMinutes(end);
  return e < s;
}

function isTimeInShift(time: string, start: string, end: string) {
  const t = timeToMinutes(time);
  const s = timeToMinutes(start);
  const e = timeToMinutes(end);
  if (e >= s) return t >= s && t <= e;
  return t >= s || t <= e;
}

function resolveBusinessDateISO(args: {
  driverId: string;
  rideDateISO: string;
  rideTimeHHmm: string;
  shiftsByDriver: Record<
    string,
    Record<string, Array<{ start: string; end: string }>>
  >;
  cutoffHHmm: string;
}) {
  const { driverId, rideDateISO, rideTimeHHmm, shiftsByDriver, cutoffHHmm } =
    args;
  const cutoffMinutes = timeToMinutes(cutoffHHmm);
  const shiftsToday = shiftsByDriver[driverId]?.[rideDateISO] || [];
  if (shiftsToday.some((s) => isTimeInShift(rideTimeHHmm, s.start, s.end)))
    return rideDateISO;

  const prev = addDaysISO(rideDateISO, -1);
  const shiftsPrev = shiftsByDriver[driverId]?.[prev] || [];
  if (
    shiftsPrev.some(
      (s) =>
        isOvernightShift(s.start, s.end) &&
        isTimeInShift(rideTimeHHmm, s.start, s.end),
    )
  )
    return prev;
  const prevQualifies = shiftsPrev.some(
    (s) =>
      isOvernightShift(s.start, s.end) || timeToMinutes(s.end) <= cutoffMinutes,
  );
  if (timeToMinutes(rideTimeHHmm) < cutoffMinutes && prevQualifies) return prev;
  if (
    shiftsPrev.some(
      (s) =>
        isOvernightShift(s.start, s.end) &&
        isTimeInShift(rideTimeHHmm, s.start, s.end),
    )
  )
    return prev;
  return rideDateISO;
}
