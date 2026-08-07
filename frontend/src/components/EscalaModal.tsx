import React, { useEffect, useMemo, useState } from "react";
import { X, CalendarDays, Clock, Bike, Edit2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import {
  cn,
  isBrazilianHoliday,
  getBrazilianHolidayName,
  formatCurrency,
} from "../lib/utils";

export interface WeekDate {
  iso: string;
  label: string;
  dayName: string;
}

export interface DriverOption {
  driverUUID: string;
  driverId?: string;
  driverName: string;
  driverPhone?: string | null;
}

export interface TurnoConfig {
  id: string;
  label?: string;
  nome?: string;
  inicio?: string;
  startTime?: string;
  fim?: string;
  endTime?: string;
  diaria?: any;
}

export interface FaixaHorasConfig {
  id: string;
  label: string;
  horasMinimas: number;
  horasMaximas: number;
  valor: number;
}

export interface CompanyEscalaConfig {
  report_type: "producao" | "garantida" | "garantida_horas";
  daily_rate_weekday: number;
  daily_rate_saturday: number;
  daily_rate_sunday: number;
  daily_rate_holiday: number;
  turnos_config: TurnoConfig[];
  faixas_horas_config: FaixaHorasConfig[];
}

export interface EscalaSavePayload {
  entryId?: string;
  driverUUID: string;
  selectedDates: string[];
  shiftLabel: string;
  shiftStart: string;
  shiftEnd: string;
  dailyRateOverride: number | null;
  minGuaranteedOverride: number | null;
  notes: string;
}

export interface EditingEntry {
  id: string;
  driverUUID: string;
  entryDate: string;
  shiftLabel: string;
  shiftStart: string;
  shiftEnd: string;
  dailyRate: number;
  minGuaranteedOverride?: number | null;
  notes?: string | null;
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

interface EscalaModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (payload: EscalaSavePayload) => void;
  weekDates: WeekDate[];
  drivers: DriverOption[];
  companyName: string;
  config: CompanyEscalaConfig | null;
  defaultSelectedDate: string;
  defaultDriverUUID?: string;
  editingEntry?: EditingEntry | null;
}

export function EscalaModal({
  isOpen,
  onClose,
  onSave,
  weekDates,
  drivers,
  companyName,
  config,
  defaultSelectedDate,
  defaultDriverUUID,
  editingEntry,
}: EscalaModalProps) {
  const [driverUUID, setDriverUUID] = useState("");
  const [selectedDates, setSelectedDates] = useState<string[]>([]);
  const [selectedTurnoId, setSelectedTurnoId] = useState<string>("");
  const [shiftLabel, setShiftLabel] = useState("Integral");
  const [shiftStart, setShiftStart] = useState("08:00");
  const [shiftEnd, setShiftEnd] = useState("18:00");
  const [dailyRateOverride, setDailyRateOverride] = useState<number | null>(
    null,
  );
  const [minGuaranteedOverride, setMinGuaranteedOverride] = useState<
    number | null
  >(null);
  const [notes, setNotes] = useState("");

  const hasTurnos = Boolean(
    config &&
    Array.isArray(config.turnos_config) &&
    config.turnos_config.length > 0,
  );
  const isGarantidaHoras = config?.report_type === "garantida_horas";

  const turnoOptions = useMemo(() => config?.turnos_config || [], [config]);

  // Previsão Tarifária em Tempo Real
  const priceBreakdown = useMemo(() => {
    if (!config || selectedDates.length === 0) return null;

    const list = selectedDates.map((dateISO) => {
      let rate = 60;
      let isHoliday = isBrazilianHoliday(dateISO);
      let holidayName = getBrazilianHolidayName(dateISO);

      const dow = new Date(dateISO + "T12:00:00").getDay();

      if (dailyRateOverride != null) {
        rate = dailyRateOverride;
      } else {
        let baseRate = config.daily_rate_weekday;
        if (isHoliday) {
          baseRate = config.daily_rate_holiday;
        } else if (dow === 0) {
          baseRate = config.daily_rate_sunday;
        } else if (dow === 6) {
          baseRate = config.daily_rate_saturday;
        }

        if (hasTurnos && selectedTurnoId) {
          const turno = config.turnos_config.find(
            (t) => t.id === selectedTurnoId,
          );
          if (turno && turno.diaria != null) {
            rate = resolveDiariaObj(turno.diaria, dateISO, baseRate);
          } else {
            rate = baseRate;
          }
        } else {
          rate = baseRate;
        }
      }

      let minGuaranteed = 0;
      if (minGuaranteedOverride != null) {
        minGuaranteed = minGuaranteedOverride;
      } else if (
        config.report_type === "garantida_horas" &&
        config.faixas_horas_config?.length > 0
      ) {
        const [sh, sm] = shiftStart.split(":").map(Number);
        const [eh, em] = shiftEnd.split(":").map(Number);
        let diff = eh + em / 60 - (sh + sm / 60);
        if (diff < 0) diff += 24;
        const sortedFaixas = [...config.faixas_horas_config].sort(
          (a, b) => Number(a.horasMaximas) - Number(b.horasMaximas),
        );
        const faixa =
          sortedFaixas.find(
            (f) =>
              diff >= Number(f.horasMinimas) && diff <= Number(f.horasMaximas),
          ) || sortedFaixas[sortedFaixas.length - 1];
        if (faixa) minGuaranteed = Number(faixa.valor) || 0;
      } else if (config.report_type === "garantida") {
        minGuaranteed = Number(config.daily_rate_weekday || 0);
      }

      const dateParts = dateISO.split("-");
      const formattedDate = `${dateParts[2]}/${dateParts[1]}`;

      return {
        dateISO,
        formattedDate,
        dayName: [
          "Domingo",
          "Segunda",
          "Terça",
          "Quarta",
          "Quinta",
          "Sexta",
          "Sábado",
        ][dow],
        rate,
        isHoliday,
        holidayName,
        minGuaranteed,
      };
    });

    const total = list.reduce((acc, curr) => acc + curr.rate, 0);

    return {
      list,
      total,
    };
  }, [
    config,
    selectedDates,
    selectedTurnoId,
    shiftStart,
    shiftEnd,
    dailyRateOverride,
    minGuaranteedOverride,
    hasTurnos,
    config?.turnos_config,
    config?.faixas_horas_config,
  ]);

  useEffect(() => {
    if (!isOpen) return;
    if (editingEntry) {
      setDriverUUID(editingEntry.driverUUID);
      setSelectedDates([editingEntry.entryDate]);
      setShiftLabel(editingEntry.shiftLabel || "Integral");
      setShiftStart(editingEntry.shiftStart || "08:00");
      setShiftEnd(editingEntry.shiftEnd || "18:00");
      setDailyRateOverride(
        Number.isFinite(editingEntry.dailyRate) ? editingEntry.dailyRate : null,
      );
      setMinGuaranteedOverride(
        editingEntry.minGuaranteedOverride != null
          ? editingEntry.minGuaranteedOverride
          : null,
      );
      setNotes(editingEntry.notes || "");
      if (hasTurnos) {
        const turno = turnoOptions.find(
          (t) => (t.nome || t.label) === editingEntry.shiftLabel,
        );
        setSelectedTurnoId(turno?.id || "");
      } else {
        setSelectedTurnoId("");
      }
      return;
    }

    setDriverUUID(defaultDriverUUID || "");
    setSelectedDates(defaultSelectedDate ? [defaultSelectedDate] : []);
    setNotes("");
    setDailyRateOverride(null);
    setMinGuaranteedOverride(null);

    if (hasTurnos) {
      const first = turnoOptions[0];
      setSelectedTurnoId(first?.id || "");
      setShiftLabel(first?.nome || first?.label || "Integral");
      setShiftStart(first?.startTime || first?.inicio || "08:00");
      setShiftEnd(first?.endTime || first?.fim || "18:00");
    } else {
      setSelectedTurnoId("");
      setShiftLabel("Integral");
      setShiftStart("08:00");
      setShiftEnd("18:00");
    }
  }, [isOpen, defaultSelectedDate, hasTurnos, turnoOptions, editingEntry]);

  useEffect(() => {
    if (!hasTurnos) return;
    const turno = turnoOptions.find((t) => t.id === selectedTurnoId);
    if (!turno) return;
    setShiftLabel(turno.nome || turno.label || "Integral");
    setShiftStart(turno.startTime || turno.inicio || "08:00");
    setShiftEnd(turno.endTime || turno.fim || "18:00");
  }, [hasTurnos, selectedTurnoId, turnoOptions]);

  if (!isOpen) return null;
  const selectableDrivers = drivers.filter((d) => Boolean(d.driverUUID));

  const toggleDate = (iso: string) => {
    setSelectedDates((prev) =>
      prev.includes(iso) ? prev.filter((d) => d !== iso) : [...prev, iso],
    );
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({
      entryId: editingEntry?.id,
      driverUUID,
      selectedDates,
      shiftLabel,
      shiftStart,
      shiftEnd,
      dailyRateOverride,
      minGuaranteedOverride,
      notes,
    });
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-zinc-900/40 backdrop-blur-sm z-[50]"
            onClick={onClose}
          />
          <motion.div
            initial={{ x: "100%", opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: "100%", opacity: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed top-0 right-0 h-full w-full max-w-md bg-white shadow-2xl z-[51] flex flex-col border-l border-zinc-200"
          >
            <div className="px-6 py-4 border-b border-zinc-200 flex items-center justify-between bg-zinc-50/50">
              <h2 className="text-lg font-bold text-zinc-900">
                {editingEntry ? "Editar Alocação" : "Nova Alocação"}
              </h2>
              <button
                onClick={onClose}
                className="p-2 text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 rounded-full transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              <form
                id="escala-form"
                onSubmit={handleSubmit}
                className="space-y-6"
              >
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider flex items-center gap-2 border-b border-zinc-100 pb-2">
                    <CalendarDays className="h-4 w-4 text-indigo-500" />
                    Informações da Alocação
                  </h3>

                  <div>
                    <label className="block text-xs font-semibold text-zinc-700 mb-1">
                      Motoboy
                    </label>
                    <div className="relative">
                      <Bike className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
                      <select
                        required
                        value={driverUUID}
                        onChange={(e) => setDriverUUID(e.target.value)}
                        disabled={Boolean(editingEntry)}
                        className={cn(
                          "w-full pl-9 pr-3 py-2 text-sm border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all",
                          editingEntry
                            ? "bg-zinc-50 text-zinc-500 cursor-not-allowed"
                            : "bg-white",
                        )}
                      >
                        <option value="" disabled>
                          Selecione um motoboy
                        </option>
                        {selectableDrivers.map((d) => (
                          <option key={d.driverUUID} value={d.driverUUID}>
                            {d.driverName}
                            {d.driverPhone ? ` (${d.driverPhone})` : ""}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-zinc-700 mb-1">
                      Local / Empresa
                    </label>
                    <div className="relative">
                      <input
                        value={companyName}
                        readOnly
                        className="w-full px-3 py-2 text-sm bg-zinc-50 border border-zinc-200 rounded-lg text-zinc-500 cursor-not-allowed"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="block text-xs font-semibold text-zinc-700">
                      Dias da Semana
                    </label>
                    <div className="grid grid-cols-4 gap-2">
                      {weekDates.map((d) => (
                        <button
                          key={d.iso}
                          type="button"
                          onClick={() => toggleDate(d.iso)}
                          disabled={Boolean(editingEntry)}
                          className={cn(
                            "px-2 py-2 rounded-lg border text-xs font-bold",
                            selectedDates.includes(d.iso)
                              ? "bg-zinc-900 text-white border-zinc-900"
                              : "bg-white text-zinc-700 border-zinc-200 hover:bg-zinc-50",
                            editingEntry ? "opacity-60 cursor-not-allowed" : "",
                          )}
                        >
                          <div className="text-[10px] opacity-80">
                            {d.dayName.toUpperCase()}
                          </div>
                          <div className="font-mono text-[11px]">{d.label}</div>
                        </button>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() =>
                          setSelectedDates(weekDates.map((d) => d.iso))
                        }
                        disabled={Boolean(editingEntry)}
                        className="px-3 py-1.5 text-[11px] font-bold border border-zinc-200 rounded-lg bg-white hover:bg-zinc-50"
                      >
                        Selecionar todos
                      </button>
                      <button
                        type="button"
                        onClick={() => setSelectedDates([])}
                        disabled={Boolean(editingEntry)}
                        className="px-3 py-1.5 text-[11px] font-bold border border-zinc-200 rounded-lg bg-white hover:bg-zinc-50"
                      >
                        Limpar
                      </button>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    {hasTurnos ? (
                      <div className="col-span-2">
                        <label className="block text-xs font-semibold text-zinc-700 mb-1">
                          Turno
                        </label>
                        <select
                          value={selectedTurnoId}
                          onChange={(e) => setSelectedTurnoId(e.target.value)}
                          className="w-full px-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                        >
                          {turnoOptions.map((t) => (
                            <option key={t.id} value={t.id}>
                              {t.nome || t.label} ({t.startTime || t.inicio}–
                              {t.endTime || t.fim})
                            </option>
                          ))}
                        </select>
                      </div>
                    ) : (
                      <>
                        <div>
                          <label className="block text-xs font-semibold text-zinc-700 mb-1">
                            Início
                          </label>
                          <input
                            type="time"
                            value={shiftStart}
                            onChange={(e) => setShiftStart(e.target.value)}
                            className="w-full px-3 py-2 text-sm font-mono bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-semibold text-zinc-700 mb-1">
                            Fim
                          </label>
                          <input
                            type="time"
                            value={shiftEnd}
                            onChange={(e) => setShiftEnd(e.target.value)}
                            className="w-full px-3 py-2 text-sm font-mono bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                          />
                        </div>
                      </>
                    )}
                  </div>
                </div>

                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider flex items-center gap-2 border-b border-zinc-100 pb-2">
                    <Edit2 className="h-4 w-4 text-emerald-500" />
                    Valores e Contrato
                  </h3>

                  <div>
                    <label className="block text-xs font-semibold text-zinc-700 mb-1">
                      {editingEntry
                        ? "Diária Fixa do Turno (R$)"
                        : "Diária Fixa (Personalizada) R$"}
                    </label>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={dailyRateOverride ?? ""}
                      onChange={(e) => {
                        const v = e.target.value;
                        setDailyRateOverride(
                          v === "" ? null : parseFloat(v) || 0,
                        );
                      }}
                      className="w-full px-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all font-mono"
                      placeholder={
                        editingEntry
                          ? ""
                          : "Deixe em branco para usar a diária padrão da loja"
                      }
                    />
                    {!editingEntry && (
                      <p className="text-[11px] text-zinc-500 mt-1">
                        Se vazio, usa o valor padrão do dia (seg-sex/sáb/dom)
                        configurado na empresa.
                      </p>
                    )}
                  </div>

                  {(config?.report_type === "garantida" ||
                    config?.report_type === "garantida_horas") && (
                    <div>
                      <label className="block text-xs font-semibold text-zinc-700 mb-1">
                        {editingEntry
                          ? "Garantido Mínimo do Turno (R$)"
                          : "Garantido Mínimo (Personalizado) R$"}
                      </label>
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={minGuaranteedOverride ?? ""}
                        onChange={(e) => {
                          const v = e.target.value;
                          setMinGuaranteedOverride(
                            v === "" ? null : parseFloat(v) || 0,
                          );
                        }}
                        className="w-full px-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 transition-all font-mono"
                        placeholder={
                          editingEntry
                            ? ""
                            : "Deixe em branco para usar o cálculo automático (faixas horárias)"
                        }
                      />
                      {!editingEntry && (
                        <p className="text-[11px] text-zinc-500 mt-1">
                          Se vazio, o garantido mínimo será calculado
                          automaticamente com base nas faixas horárias
                          configuradas.
                        </p>
                      )}
                    </div>
                  )}

                  <div>
                    <label className="block text-xs font-semibold text-zinc-700 mb-1">
                      Observações
                    </label>
                    <textarea
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      className="w-full px-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
                      rows={3}
                    />
                  </div>

                  {/* Previsão Tarifária Widget */}
                  {priceBreakdown && (
                    <div className="bg-zinc-50 border border-zinc-200/80 rounded-xl p-4 space-y-3 shadow-sm relative overflow-hidden backdrop-blur-md">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">
                          Resumo Financeiro da Escala
                        </span>
                        {selectedDates.length > 1 && (
                          <span className="text-[10px] font-extrabold text-indigo-600 bg-indigo-50 border border-indigo-100 px-2 py-0.5 rounded-full">
                            {selectedDates.length} dias selecionados
                          </span>
                        )}
                      </div>

                      <div className="divide-y divide-zinc-200/60 max-h-36 overflow-y-auto pr-1">
                        {priceBreakdown.list.map((item) => (
                          <div
                            key={item.dateISO}
                            className="py-2 first:pt-0 last:pb-0 flex items-center justify-between gap-3 text-xs"
                          >
                            <div className="flex flex-col">
                              <span className="font-bold text-zinc-800 flex items-center gap-1.5">
                                {item.dayName} ({item.formattedDate})
                                {item.isHoliday && (
                                  <span
                                    className="px-1.5 py-0.5 bg-amber-100 border border-amber-200/60 text-amber-800 rounded-md text-[9px] font-black tracking-wide"
                                    title={item.holidayName || "Feriado"}
                                  >
                                    🇧🇷 Feriado
                                  </span>
                                )}
                              </span>
                              {item.isHoliday && item.holidayName && (
                                <span className="text-[10px] font-medium text-amber-700 mt-0.5">
                                  {item.holidayName} · Diária de Feriado
                                  aplicada
                                </span>
                              )}
                            </div>
                            <div className="text-right font-mono">
                              <span className="font-bold text-zinc-950">
                                {formatCurrency(item.rate)}
                              </span>
                              {item.minGuaranteed > 0 && (
                                <span className="block text-[9px] text-zinc-500 font-medium font-sans">
                                  Gar. Mín: {formatCurrency(item.minGuaranteed)}
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>

                      <div className="pt-3 border-t border-zinc-200 flex items-center justify-between font-black text-sm">
                        <span className="text-zinc-700 uppercase text-xs tracking-wider">
                          Custo Total Previsto:
                        </span>
                        <span className="text-emerald-600 font-mono text-base">
                          {formatCurrency(priceBreakdown.total)}
                        </span>
                      </div>

                      {priceBreakdown.list.some((i) => i.isHoliday) && (
                        <div className="p-2.5 bg-amber-50/70 border border-amber-200/60 rounded-lg flex gap-2 text-[10px] text-amber-800 leading-relaxed items-start mt-2">
                          <span className="text-base select-none mt-0.5 leading-none">
                            ⚠️
                          </span>
                          <div>
                            <span className="font-extrabold text-amber-900 block mb-0.5">
                              Aviso de Feriado Nacional
                            </span>
                            A data selecionada coincide com um feriado nacional.
                            A diária de feriado especial (
                            <strong>
                              {formatCurrency(config?.daily_rate_holiday || 80)}
                            </strong>
                            ) foi aplicada automaticamente na estimativa.
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </form>
            </div>

            <div className="p-4 border-t border-zinc-200 bg-zinc-50 flex gap-3">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2 border border-zinc-200 bg-white text-zinc-700 rounded-lg hover:bg-zinc-50 text-sm font-bold transition-all"
              >
                Cancelar
              </button>
              <button
                type="submit"
                form="escala-form"
                className="flex-1 px-4 py-2 bg-zinc-900 text-white rounded-lg hover:bg-zinc-800 text-sm font-bold shadow-sm transition-all"
                disabled={!driverUUID || selectedDates.length === 0}
              >
                Salvar Alocação
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
