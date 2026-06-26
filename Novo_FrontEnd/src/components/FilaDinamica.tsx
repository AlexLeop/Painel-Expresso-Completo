import React from "react";
import {
  Truck,
  Clock,
  MapPin,
  CheckCircle2,
  Wifi,
  Circle,
  Navigation,
} from "lucide-react";
import { cn } from "../lib/utils";

interface DriverPosition {
  machine_condutor_id: string;
  latitude: number;
  longitude: number;
  speed?: number;
  heading?: number;
  machine_ride_id?: string | null;
  received_at: string;
}

interface DriverInfo {
  name: string;
  phone: string;
  status: string;
}

interface FilaDinamicaProps {
  driverPositions: DriverPosition[];
  driverDirectory: Record<string, DriverInfo>;
  /** IDs de motoristas com corrida ativa (status A ou E) */
  busyDriverIds: Set<string>;
  storeLocation: [number, number] | null;
  /** Callback when a driver card is clicked */
  onDriverClick?: (driverId: string, isOnRide: boolean) => void;
}

function haversineKm(
  aLat: number,
  aLng: number,
  bLat: number,
  bLng: number,
): number {
  const R = 6371;
  const dLat = ((bLat - aLat) * Math.PI) / 180;
  const dLng = ((bLng - aLng) * Math.PI) / 180;
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((aLat * Math.PI) / 180) *
      Math.cos((bLat * Math.PI) / 180) *
      Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h));
}

function timeAgoLabel(isoStr: string): string {
  if (!isoStr) return "";
  try {
    const ts = new Date(isoStr).getTime();
    if (isNaN(ts)) return "";
    const diff = Math.max(0, Math.round((Date.now() - ts) / 60000));
    if (diff < 1) return "agora";
    if (diff < 60) return `${diff}min`;
    return `${Math.floor(diff / 60)}h${diff % 60}m`;
  } catch {
    return "";
  }
}

export function FilaDinamica({
  driverPositions,
  driverDirectory,
  busyDriverIds,
  storeLocation,
  onDriverClick,
}: FilaDinamicaProps) {
  const allDrivers = driverPositions.map((pos) => {
    const id = String(pos.machine_condutor_id || "");
    const info = driverDirectory[id];
    // "Em Rota" = tem corrida com status A ou E atribuída
    const isOnRide = busyDriverIds.has(id);

    let distKm: number | null = null;
    if (
      storeLocation &&
      Number.isFinite(pos.latitude) &&
      Number.isFinite(pos.longitude)
    ) {
      distKm = haversineKm(
        storeLocation[0],
        storeLocation[1],
        pos.latitude,
        pos.longitude,
      );
    }

    return {
      id,
      name: info?.name || `Motoboy #${id}`,
      phone: info?.phone || "",
      isOnRide,
      distKm,
      receivedAt: pos.received_at || "",
    };
  });

  // Em Rota: tem corrida ativa atribuída (status A ou E)
  const onRide = allDrivers
    .filter((d) => d.isOnRide)
    .sort((a, b) => (a.distKm ?? 999) - (b.distKm ?? 999));

  // Ativos: online, sem corrida (apenas mostrar que estão ativos)
  const active = allDrivers
    .filter((d) => !d.isOnRide)
    .sort((a, b) => (a.distKm ?? 999) - (b.distKm ?? 999));

  return (
    <div className="flex-1 overflow-y-auto bg-zinc-50/30 p-4 space-y-6">
      {/* Em Rota — drivers with active ride */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-zinc-900 flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]"></div>
            Em Rota
          </h3>
          <span className="text-xs font-semibold text-zinc-500 bg-white px-2 py-0.5 rounded-full border border-zinc-200 shadow-sm">
            {onRide.length}
          </span>
        </div>

        <div className="space-y-2">
          {onRide.length === 0 ? (
            <div className="text-sm text-zinc-500 italic p-4 text-center bg-white border border-dashed border-zinc-200 rounded-xl">
              Nenhum motoboy em rota no momento
            </div>
          ) : (
            onRide.map((driver) => (
              <div
                key={driver.id}
                onClick={() => onDriverClick?.(driver.id, true)}
                className="bg-white border border-amber-100 rounded-xl p-3 flex items-center gap-3 shadow-sm relative overflow-hidden cursor-pointer hover:border-amber-300 transition-all"
              >
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-amber-500"></div>
                <div className="w-8 h-8 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center shrink-0">
                  <Navigation className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-bold text-zinc-900 truncate">
                    {driver.name}
                  </div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <div className="text-xs text-amber-600 font-medium flex items-center gap-1">
                      <Truck className="w-3 h-3" />
                      Em corrida
                    </div>
                    {driver.distKm !== null &&
                      Number.isFinite(driver.distKm) && (
                        <div className="text-[10px] text-zinc-400 flex items-center gap-0.5">
                          <MapPin className="w-3 h-3" />
                          {driver.distKm.toFixed(1)} km
                        </div>
                      )}
                    {driver.receivedAt && (
                      <div className="text-[10px] text-zinc-400 flex items-center gap-0.5">
                        <Clock className="w-3 h-3" />
                        {timeAgoLabel(driver.receivedAt)}
                      </div>
                    )}
                  </div>
                </div>
                <div className="text-xs font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-100 shrink-0">
                  Em rota
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Ativos — online drivers without a ride */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-zinc-900 flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
            Ativos
          </h3>
          <span className="text-xs font-semibold text-zinc-500 bg-white px-2 py-0.5 rounded-full border border-zinc-200 shadow-sm">
            {active.length}
          </span>
        </div>

        <div className="space-y-2">
          {active.length === 0 ? (
            <div className="text-sm text-zinc-500 italic p-4 text-center bg-white border border-dashed border-zinc-200 rounded-xl flex flex-col items-center gap-2">
              <Wifi className="w-5 h-5 text-zinc-300" />
              Nenhum motoboy ativo no momento
            </div>
          ) : (
            active.map((driver, idx) => (
              <div
                key={driver.id}
                onClick={() => onDriverClick?.(driver.id, false)}
                className="bg-white border border-zinc-200 rounded-xl p-3 flex items-center gap-3 shadow-sm relative overflow-hidden group cursor-pointer hover:border-emerald-300 transition-all"
              >
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-emerald-400"></div>
                <div className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-xs shrink-0">
                  {idx + 1}º
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-bold text-zinc-900 truncate">
                    {driver.name}
                  </div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <div className="text-xs text-emerald-600 font-medium flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" />
                      Ativo
                    </div>
                    {driver.distKm !== null &&
                      Number.isFinite(driver.distKm) && (
                        <div className="text-[10px] text-zinc-400 flex items-center gap-0.5">
                          <MapPin className="w-3 h-3" />
                          {driver.distKm.toFixed(1)} km
                        </div>
                      )}
                    {driver.receivedAt && (
                      <div className="text-[10px] text-zinc-400 flex items-center gap-0.5">
                        <Clock className="w-3 h-3" />
                        {timeAgoLabel(driver.receivedAt)}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
