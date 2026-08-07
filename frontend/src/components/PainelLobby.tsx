import React, { useState, useMemo } from "react";
import {
  Package,
  Clock,
  MapPin,
  Truck,
  ChevronRight,
  CheckSquare,
  Square,
  Layers,
  User,
  Navigation,
} from "lucide-react";
import { cn, formatCurrency } from "../lib/utils";
import { motion, AnimatePresence } from "framer-motion";
import { authFetch } from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

export interface LobbyRide {
  id: string | number;
  codigoPedido: string;
  cliente: string;
  empresa: string;
  coleta: { endereco: string; hora: string };
  entrega: { endereco: string; hora: string };
  paradas: any[];
  valor: number;
  distancia: string;
  status: string;
  rawStatus: string;
  tipo: string;
  motoboy: { nome: string; placa: string; id_num: string };
  timestamp: number;
  origin: { lat: number; lng: number } | null;
  destination: { lat: number; lng: number } | null;
}

interface PainelLobbyProps {
  rides: LobbyRide[];
  storeLocation: [number, number] | null;
  companyData: any | null;
  onRidesGrouped?: () => void;
}

export function PainelLobby({
  rides,
  storeLocation,
  companyData,
  onRidesGrouped,
}: PainelLobbyProps) {
  const { session } = useAuth();
  const [selectedIds, setSelectedIds] = useState<Set<string | number>>(
    new Set(),
  );
  const [isGrouping, setIsGrouping] = useState(false);

  const toggleSelection = (id: string | number) => {
    const next = new Set(selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedIds(next);
  };

  const selectAll = () => {
    if (selectedIds.size === rides.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(rides.map((o) => o.id)));
    }
  };

  const handleGroupAndDispatch = async () => {
    if (selectedIds.size === 0) return;
    setIsGrouping(true);

    try {
      const selectedOrders = rides.filter((o) => selectedIds.has(o.id));
      const machineEmpId = session?.user?.machine_empresa_id || companyData?.id;

      if (!machineEmpId) {
        throw new Error("ID da empresa não encontrado.");
      }

      const storeLat = storeLocation?.[0] || companyData?.lat || "";
      const storeLng = storeLocation?.[1] || companyData?.lng || "";
      const storeEndereco = companyData?.endereco || "";
      const storeName = companyData?.nome_fantasia || companyData?.nome || "Loja";
      const storeBairro = companyData?.bairro || "";
      const storeCidade = companyData?.cidade || "";
      const storeEstado = companyData?.estado || "RJ";

      const payload = {
        empresa_id: machineEmpId,
        forma_pagamento: "F",
        endereco_partida: storeEndereco || "",
        bairro_partida: storeBairro || "",
        cidade_partida: storeCidade || "",
        estado_partida: storeEstado || "",
        lat_partida: String(storeLat),
        lng_partida: String(storeLng),
        nome_cliente_partida: storeName,
        telefone_cliente_partida: "",
        observacao_partida: "Coleta agrupada",
        pontos: selectedOrders.flatMap((order) => {
          if (order.paradas && order.paradas.length > 0) {
            return order.paradas.map((p) => ({
              endereco_parada: p.endereco || order.entrega?.endereco || "",
              bairro_parada: p.bairro || "",
              cidade_parada: p.cidade || storeCidade,
              estado_parada: p.uf || storeEstado,
              lat_parada: String(p.lat || order.destination?.lat || ""),
              lng_parada: String(p.lng || order.destination?.lng || ""),
              nome_cliente_parada: p.nome_cliente || order.cliente || "",
              telefone_cliente_parada: p.telefone_cliente || "",
              observacao_parada:
                p.observacao || `Pedido #${order.codigoPedido}`,
            }));
          } else {
            return [
              {
                endereco_parada: order.entrega?.endereco || "",
                bairro_parada: "",
                cidade_parada: storeCidade,
                estado_parada: storeEstado,
                lat_parada: String(order.destination?.lat || ""),
                lng_parada: String(order.destination?.lng || ""),
                nome_cliente_parada: order.cliente || "",
                telefone_cliente_parada: "",
                observacao_parada: `Pedido #${order.codigoPedido}`,
              },
            ];
          }
        }),
      };

      const res = await authFetch("/api/v1/db/orders/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      
      const errorData = await res.json().catch(() => ({}));

      if (!res.ok || errorData.error || errorData.sucesso === false || errorData.success === false) {
        throw new Error(
          errorData.msg || errorData.error || "Erro ao agrupar corrida na Machine API",
        );
      }

      // Cancel original rides so they don't show up in the Lobby anymore
      await Promise.allSettled(
        selectedOrders.map((order) =>
          authFetch("/api/v1/db/orders/cancel", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id_mch: order.id, motivo_id: 7 }),
          }),
        ),
      );

      setSelectedIds(new Set());
      onRidesGrouped?.();
    } catch (error: any) {
      alert(error.message);
    } finally {
      setIsGrouping(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-zinc-50/50">
      <div className="p-4 border-b border-zinc-200/80 bg-white sticky top-0 z-10 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-zinc-900 tracking-tight flex items-center gap-2">
            <Layers className="w-5 h-5 text-[#E55C00]" />
            Lobby de Expedição
            <span className="text-zinc-400 font-medium ml-1 text-sm bg-zinc-100 px-2 py-0.5 rounded-full">
              {rides.length}
            </span>
          </h2>
          <p className="text-xs text-zinc-500 mt-1">
            Pedidos aguardando roteirização e despacho.
          </p>
        </div>

        {rides.length > 0 && (
          <button
            onClick={selectAll}
            className="text-xs font-semibold text-zinc-500 hover:text-zinc-900 transition-colors"
          >
            {selectedIds.size === rides.length
              ? "Desmarcar todos"
              : "Selecionar todos"}
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        <AnimatePresence>
          {rides.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center h-40 text-zinc-400"
            >
              <Package className="w-10 h-10 mb-3 opacity-20" />
              <p className="text-sm font-medium">
                Nenhum pedido pendente no lobby.
              </p>
            </motion.div>
          ) : (
            rides.map((order) => {
              const isSelected = selectedIds.has(order.id);
              const minutesAgo = order.timestamp
                ? Math.max(
                    0,
                    Math.round((Date.now() - order.timestamp) / 60000),
                  )
                : 0;
              const timeLabel =
                minutesAgo < 1
                  ? "Agora"
                  : minutesAgo < 60
                    ? `${minutesAgo} min`
                    : `${Math.floor(minutesAgo / 60)}h${minutesAgo % 60}m`;
              const stopCount = Array.isArray(order.paradas)
                ? order.paradas.length
                : 0;
              return (
                <motion.div
                  key={order.id}
                  layout
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  onClick={() => toggleSelection(order.id)}
                  className={cn(
                    "bg-white border rounded-xl p-3.5 cursor-pointer transition-all shadow-sm relative overflow-hidden group",
                    isSelected
                      ? "border-[#E55C00] ring-1 ring-[#E55C00] bg-orange-50/10"
                      : "border-zinc-200 hover:border-zinc-300",
                  )}
                >
                  {/* Time Badge */}
                  <div
                    className={cn(
                      "absolute top-0 right-0 px-2.5 py-1 rounded-bl-xl text-[10px] font-bold tracking-wider flex items-center gap-1",
                      minutesAgo > 15
                        ? "bg-rose-100 text-rose-700"
                        : minutesAgo > 5
                          ? "bg-amber-100 text-amber-700"
                          : "bg-emerald-100 text-emerald-700",
                    )}
                  >
                    <Clock className="w-3 h-3" />
                    {timeLabel}
                  </div>

                  <div className="flex items-start gap-3">
                    <div className="mt-1">
                      {isSelected ? (
                        <CheckSquare className="w-5 h-5 text-[#E55C00]" />
                      ) : (
                        <Square className="w-5 h-5 text-zinc-300 group-hover:text-zinc-400" />
                      )}
                    </div>

                    <div className="flex-1 min-w-0 pr-16">
                      {/* Header */}
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-[10px] font-mono font-bold text-zinc-400 bg-zinc-100 px-1.5 py-0.5 rounded">
                          #{order.codigoPedido}
                        </span>
                        <span className="text-[9px] font-bold uppercase tracking-wider text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200/60">
                          {order.status}
                        </span>
                      </div>

                      {/* Info row */}
                      <div className="flex items-center gap-2 text-[10px] text-zinc-500 mb-2">
                        <div className="flex items-center gap-1">
                          <Truck
                            strokeWidth={1.5}
                            className="w-3 h-3 shrink-0"
                          />
                          <span className="truncate">
                            {order.motoboy?.nome || "Sem motorista"}
                          </span>
                        </div>
                        <span className="text-zinc-300">•</span>
                        <div className="flex items-center gap-1">
                          <User
                            strokeWidth={1.5}
                            className="w-3 h-3 shrink-0"
                          />
                          <span className="truncate">{order.cliente}</span>
                        </div>
                      </div>

                      {/* Coleta address */}
                      <div className="flex items-center gap-1.5 text-xs text-zinc-600 mb-1.5">
                        <MapPin className="w-3 h-3 shrink-0 text-emerald-500" />
                        <span className="truncate font-medium">
                          {order.coleta?.endereco || "Endereço não disponível"}
                        </span>
                      </div>

                      {/* Entrega address */}
                      <div className="flex items-center gap-1.5 text-xs text-zinc-500 mb-2">
                        <Navigation className="w-3 h-3 shrink-0 text-zinc-400" />
                        <span className="truncate">
                          {order.entrega?.endereco || "Destino"}
                        </span>
                        {stopCount > 1 && (
                          <span className="text-[9px] font-bold text-zinc-400 bg-zinc-100 px-1 py-0.5 rounded">
                            +{stopCount - 1}
                          </span>
                        )}
                      </div>

                      {/* Footer: distance + value */}
                      <div className="flex items-center gap-3 text-[11px] font-semibold text-zinc-500">
                        <span className="flex items-center gap-1">
                          <MapPin className="w-3 h-3" />
                          {order.distancia}
                        </span>
                        <span>•</span>
                        <span className="text-zinc-800 font-bold">
                          {formatCurrency(order.valor)}
                        </span>
                      </div>
                    </div>
                  </div>
                </motion.div>
              );
            })
          )}
        </AnimatePresence>
      </div>

      {/* Footer Action */}
      <AnimatePresence>
        {selectedIds.size > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="p-4 bg-white border-t border-zinc-200 shadow-[0_-10px_30px_rgba(0,0,0,0.05)] z-20"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold text-zinc-500 uppercase tracking-wider">
                {selectedIds.size} pedido{selectedIds.size > 1 ? "s" : ""}{" "}
                selecionado{selectedIds.size > 1 ? "s" : ""}
              </span>
              <span className="text-sm font-black text-zinc-900">
                Rotas otimizadas
              </span>
            </div>

            <button
              onClick={handleGroupAndDispatch}
              disabled={isGrouping}
              className="w-full py-3.5 bg-zinc-900 hover:bg-zinc-800 text-white rounded-xl text-sm font-bold shadow-md transition-all flex items-center justify-center gap-2 disabled:opacity-70"
            >
              {isGrouping ? (
                <>
                  <svg
                    className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  Enviando para Fila...
                </>
              ) : (
                <>
                  Agrupar e Chamar Moto
                  <ChevronRight className="w-4 h-4" />
                </>
              )}
            </button>
            <p className="text-[10px] text-center text-zinc-400 mt-2">
              Será criada 1 corrida com {selectedIds.size} parada
              {selectedIds.size > 1 ? "s" : ""} para o 1º da Fila.
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
