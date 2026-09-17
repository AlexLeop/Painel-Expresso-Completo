import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import {
  X,
  MapPin,
  Plus,
  Trash2,
  ChevronRight,
  Check,
  Loader2,
  AlertCircle,
  ExternalLink,
  Store,
  Wallet,
  Banknote,
  CreditCard,
  QrCode,
  Receipt,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn, formatCurrency } from "../lib/utils";
import { AddressAutocomplete } from "./AddressAutocomplete";
import { authFetch } from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

interface CreateRideModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (ride: any) => void;
  currentCompany?: any;
  initialData?: any;
}

interface DeliveryPoint {
  id: number;
  address: string;
  number: string;
  complement: string;
  name: string;
  phone: string;
  notes: string;
  bairro?: string;
  cidade?: string;
  estado?: string;
  lat?: string;
  lng?: string;
}

const getStateAbbr = (stateName?: string, fallback = "SP") => {
  if (!stateName) return fallback;
  const map: Record<string, string> = {
    Acre: "AC",
    Alagoas: "AL",
    Amapá: "AP",
    Amazonas: "AM",
    Bahia: "BA",
    Ceará: "CE",
    "Distrito Federal": "DF",
    "Espírito Santo": "ES",
    Goiás: "GO",
    Maranhão: "MA",
    "Mato Grosso": "MT",
    "Mato Grosso do Sul": "MS",
    "Minas Gerais": "MG",
    Pará: "PA",
    Paraíba: "PB",
    Paraná: "PR",
    Pernambuco: "PE",
    Piauí: "PI",
    "Rio de Janeiro": "RJ",
    "Rio Grande do Norte": "RN",
    "Rio Grande do Sul": "RS",
    Rondônia: "RO",
    Roraima: "RR",
    "Santa Catarina": "SC",
    "São Paulo": "SP",
    Sergipe: "SE",
    Tocantins: "TO",
  };
  return (
    map[stateName] ||
    (stateName.length === 2
      ? stateName.toUpperCase()
      : stateName.substring(0, 2).toUpperCase())
  );
};

export function CreateRideModal({
  isOpen,
  onClose,
  onSave,
  currentCompany,
  initialData,
}: CreateRideModalProps) {
  const { session } = useAuth();
  const isLojista = session?.user?.role === "lojista";
  const [partnerStores, setPartnerStores] = useState<any[]>([]);
  const [selectedStoreId, setSelectedStoreId] = useState<string>("");
  const [selectedStore, setSelectedStore] = useState<any>(null);
  const [trocoPara, setTrocoPara] = useState<string>("");
  const [balanceError, setBalanceError] = useState<string | null>(null);

  const [step, setStep] = useState(1);
  const [pickupAddress, setPickupAddress] = useState(
    initialData?.coleta?.endereco || "",
  );
  const [pickupResult, setPickupResult] = useState<any>(null);
  const [deliveries, setDeliveries] = useState<DeliveryPoint[]>(() => {
    if (initialData?.entrega?.endereco) {
      return [
        {
          id: Date.now(),
          address: initialData.entrega.endereco.split(",")[0] || "",
          number: initialData.entrega.endereco.split(",")[1]?.trim() || "",
          complement: "",
          name: initialData.cliente || "",
          phone: initialData.telefoneCliente || "",
          notes: "",
        },
      ];
    }
    return [
      {
        id: Date.now(),
        address: "",
        number: "",
        complement: "",
        name: "",
        phone: "",
        notes: "",
      },
    ];
  });

  const [categoriaCondutor, setCategoriaCondutor] = useState(
    initialData?.tipo || "Entrega padrão",
  );
  const [formaPagamento, setFormaPagamento] = useState("JA_PAGO");
  const [observacaoGeral, setObservacaoGeral] = useState("");

  const [isEstimating, setIsEstimating] = useState(false);
  const [estimativa, setEstimativa] = useState<{
    valor: number;
    distancia: number;
    tempo: number;
  } | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Carregar lojas parceiras para despacho centralizado
  useEffect(() => {
    if (!isOpen) return;
    authFetch("/api/v1/db/companies")
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => {
        const list = Array.isArray(data) ? data : data?.response || [];
        setPartnerStores(list);
        if (list.length > 0) {
          const matched =
            list.find((s: any) => String(s.id) === String(currentCompany?.id)) ||
            list[0];
          setSelectedStoreId(String(matched.id));
          setSelectedStore(matched);
          if (!initialData?.coleta?.endereco && (matched.endereco || matched.nome)) {
            setPickupAddress(matched.endereco || matched.nome);
          }
        }
      })
      .catch(() => {});
  }, [isOpen, currentCompany]);

  const handleStoreChange = (id: string) => {
    setSelectedStoreId(id);
    const store = partnerStores.find((s) => String(s.id) === String(id));
    if (store) {
      setSelectedStore(store);
      setPickupAddress(store.endereco || store.nome || "");
      setBalanceError(null);
    }
  };

  useEffect(() => {
    if (isOpen) {
      setStep(1);
      setPickupAddress(
        initialData?.coleta?.endereco ||
          selectedStore?.endereco ||
          selectedStore?.nome ||
          "",
      );
      setBalanceError(null);
      setTrocoPara("");
      if (initialData?.entrega?.endereco) {
        setDeliveries([
          {
            id: Date.now(),
            address: initialData.entrega.endereco.split(",")[0] || "",
            number: initialData.entrega.endereco.split(",")[1]?.trim() || "",
            complement: "",
            name: initialData.cliente || "",
            phone: initialData.telefoneCliente || "",
            notes: "",
          },
        ]);
      } else {
        setDeliveries([
          {
            id: Date.now(),
            address: "",
            number: "",
            complement: "",
            name: "",
            phone: "",
            notes: "",
          },
        ]);
      }
      setCategoriaCondutor(initialData?.tipo || "Entrega padrão");
      setFormaPagamento("JA_PAGO");
      setObservacaoGeral("");
      setEstimativa(null);
    }
  }, [isOpen, initialData]);

  if (!isOpen) return null;

  const handleAddDelivery = () => {
    setDeliveries([
      ...deliveries,
      {
        id: Date.now(),
        address: "",
        number: "",
        complement: "",
        name: "",
        phone: "",
        notes: "",
      },
    ]);
  };

  const handleRemoveDelivery = (id: number) => {
    if (deliveries.length > 1) {
      setDeliveries(deliveries.filter((d) => d.id !== id));
    }
  };

  const updateDelivery = (
    id: number,
    field: keyof DeliveryPoint,
    value: string,
  ) => {
    setDeliveries(
      deliveries.map((d) => (d.id === id ? { ...d, [field]: value } : d)),
    );
  };

  const handleNextStep = async (e: React.FormEvent) => {
    e.preventDefault();
    setStep(2);
    setIsEstimating(true);
    try {
      let totalVal = 0;
      let totalKm = 0;
      let totalMin = 0;

      const defaultLat =
        currentCompany?.lat ?? currentCompany?.latitude ?? "-23.5505";
      const defaultLng =
        currentCompany?.lng ?? currentCompany?.longitude ?? "-46.6333";
      const defaultEnd =
        currentCompany?.endereco ??
        currentCompany?.address ??
        currentCompany?.nome ??
        currentCompany?.name ??
        "Av. Principal";
      const defaultBairro = currentCompany?.bairro ?? "Centro";
      const defaultCidade = currentCompany?.cidade ?? "São Paulo";
      const defaultUF = getStateAbbr(
        currentCompany?.uf ?? currentCompany?.estado ?? "SP",
      );

      const pickupStateAbbr = getStateAbbr(
        pickupResult?.address?.state || defaultUF,
      );
      const pickup = {
        endereco: pickupResult?.address?.road || pickupAddress || defaultEnd,
        bairro: pickupResult?.address?.suburb || defaultBairro,
        cidade: pickupResult?.address?.city || defaultCidade,
        estado: pickupStateAbbr,
        lat: pickupResult?.lat || defaultLat,
        lng: pickupResult?.lon || defaultLng,
      };

      const legs = [];
      for (let i = 0; i < deliveries.length; i++) {
        const d = deliveries[i];
        const from =
          i === 0
            ? pickup
            : {
                endereco: deliveries[i - 1].address || "",
                bairro: deliveries[i - 1].bairro || defaultBairro,
                cidade: deliveries[i - 1].cidade || defaultCidade,
                estado: getStateAbbr(deliveries[i - 1].estado || defaultUF),
                lat: deliveries[i - 1].lat || defaultLat,
                lng: deliveries[i - 1].lng || defaultLng,
              };
        legs.push({ from, to: d });
      }

      const results = await Promise.all(
        legs.map(async (leg) => {
          const params = new URLSearchParams({
            endereco_partida: leg.from.endereco,
            bairro_partida: leg.from.bairro,
            cidade_partida: leg.from.cidade,
            estado_partida: leg.from.estado,
            lat_partida: String(leg.from.lat),
            lng_partida: String(leg.from.lng),
            endereco_desejado: `${leg.to.address || ""}${leg.to.number ? ", " + leg.to.number : ""}`,
            bairro_desejado: leg.to.bairro || defaultBairro,
            cidade_desejado: leg.to.cidade || defaultCidade,
            estado_desejado: getStateAbbr(leg.to.estado || defaultUF),
            lat_desejado: String(leg.to.lat || defaultLat),
            lng_desejado: String(leg.to.lng || defaultLng),
          });

          try {
            const res = await authFetch(
              `/api/v1/db/orders/estimate?${params.toString()}`,
            );
            if (res.ok) {
              const data = await res.json();
              return data.response || data;
            }
          } catch {
            /* silent */
          }
          return null;
        }),
      );

      let hasSuccess = false;
      results.forEach((resp) => {
        if (!resp) return;
        const v = resp.estimativa_valor ?? resp.valor_corrida ?? resp.valor;
        const km = resp.estimativa_km ?? resp.distancia_km ?? resp.distancia;
        const min =
          resp.estimativa_minutos ?? resp.tempo_estimado ?? resp.tempo;
        if (v != null) {
          totalVal += Number(v);
          hasSuccess = true;
        }
        if (km != null) totalKm += Number(km);
        if (min != null) totalMin += Number(min);
      });

      if (hasSuccess) {
        setEstimativa({ valor: totalVal, distancia: totalKm, tempo: totalMin });
      } else {
        setEstimativa({
          valor: deliveries.length * 9.0,
          distancia: deliveries.length * 5.0,
          tempo: deliveries.length * 15,
        });
      }
    } catch (err) {
      setEstimativa({
        valor: deliveries.length * 9.0,
        distancia: deliveries.length * 5.0,
        tempo: deliveries.length * 15,
      });
    } finally {
      setIsEstimating(false);
    }
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setBalanceError(null);
    try {
      const defaultLat =
        selectedStore?.lat ?? currentCompany?.lat ?? currentCompany?.latitude ?? "-23.5505";
      const defaultLng =
        selectedStore?.lng ?? currentCompany?.lng ?? currentCompany?.longitude ?? "-46.6333";
      const defaultEnd =
        selectedStore?.endereco ??
        selectedStore?.nome ??
        currentCompany?.endereco ??
        currentCompany?.address ??
        currentCompany?.nome ??
        currentCompany?.name ??
        "Av. Principal";
      const defaultBairro = currentCompany?.bairro ?? "Centro";
      const defaultCidade = currentCompany?.cidade ?? "São Paulo";
      const defaultUF = getStateAbbr(
        currentCompany?.uf ?? currentCompany?.estado ?? "SP",
      );

      const pickupStateAbbr = getStateAbbr(
        pickupResult?.address?.state || defaultUF,
      );
      const pickup = {
        endereco: pickupResult?.address?.road || pickupAddress || defaultEnd,
        bairro: pickupResult?.address?.suburb || defaultBairro,
        cidade: pickupResult?.address?.city || defaultCidade,
        estado: pickupStateAbbr,
        lat: pickupResult?.lat || defaultLat,
        lng: pickupResult?.lon || defaultLng,
      };

      const estimatedVal = estimativa?.valor || deliveries.length * 9.0;
      const estimatedKm = estimativa?.distancia || deliveries.length * 5.0;
      const estimatedCents = Math.round(estimatedVal * 100);

      // Despacho nativo via backend operator router (com validação pré-pago e PostGIS seguro)
      const dispatchPayload = {
        store_id: selectedStore?.id || currentCompany?.id || "default",
        coleta_endereco: pickup.endereco || "",
        coleta_lat: Number(pickup.lat) || undefined,
        coleta_lng: Number(pickup.lng) || undefined,
        destinos: deliveries.map((d) => ({
          endereco: d.address || "",
          numero: d.number || "",
          complemento: d.complement || "",
          cliente: d.name || "",
          telefone: d.phone || "",
          notas: d.notes || "",
          lat: Number(d.lat) || undefined,
          lng: Number(d.lng) || undefined,
        })),
        forma_pagamento: formaPagamento,
        troco_para:
          formaPagamento === "DINHEIRO" && trocoPara ? Number(trocoPara) : null,
        valor_estimado_cents: estimatedCents,
        distancia_metros: Math.round(estimatedKm * 1000),
        observacao: observacaoGeral || "",
      };

      const res = await authFetch("/api/v1/operator/dispatch-store-ride", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(dispatchPayload),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok || data.success === false) {
        if (data.insufficient_balance) {
          setBalanceError(data.error);
          return;
        }
        throw new Error(data.error || data.msg || "Erro ao despachar entrega pela loja");
      }

      const id =
        data?.order_id ||
        data?.id ||
        Math.floor(1000 + Math.random() * 9000);

      const storeName =
        selectedStore?.nome ||
        selectedStore?.name ||
        currentCompany?.name ||
        currentCompany?.nome ||
        "Loja Parceira";

      const newRide = {
        id,
        codigoPedido: `M-${id}`,
        status: "Aguardando",
        status_solicitacao: "D",
        tipo: categoriaCondutor,
        cliente: deliveries[0]?.name || "Cliente",
        telefoneCliente: deliveries[0]?.phone || "",
        empresa: storeName,
        motoboy: {
          nome: "Aguardando...",
          foto: "?",
          exp: "-",
          cnh: "-",
          id_num: "-",
          placa: "-",
          veiculo: "-",
        },
        coleta: {
          hora: new Date().toLocaleTimeString("pt-BR", {
            hour: "2-digit",
            minute: "2-digit",
          }),
          endereco: pickup.endereco,
        },
        entrega: {
          hora: "--:--",
          endereco: `${deliveries[0].address}, ${deliveries[0].number}`,
        },
        valor: estimatedVal,
        horario: new Date().toLocaleTimeString("pt-BR", {
          hour: "2-digit",
          minute: "2-digit",
        }),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        lastLoc: pickup.endereco,
        lastStop: "Nenhuma",
        distancia: `${estimatedKm.toFixed(1)} km`,
        speed: "0 km/h",
      };

      onSave(newRide);

      setTimeout(() => {
        setStep(1);
        setPickupAddress("");
        setPickupResult(null);
        setDeliveries([
          {
            id: Date.now(),
            address: "",
            number: "",
            complement: "",
            name: "",
            phone: "",
            notes: "",
          },
        ]);
        setCategoriaCondutor("Entrega padrão");
        setFormaPagamento("JA_PAGO");
        setObservacaoGeral("");
        setTrocoPara("");
        setBalanceError(null);
        setEstimativa(null);
      }, 300);
    } catch (err: any) {
      alert("Falha ao criar corrida: " + err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "unset";
    }
    return () => {
      document.body.style.overflow = "unset";
    };
  }, [isOpen]);

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[9999] overflow-hidden pointer-events-none">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-zinc-950/50 backdrop-blur-xs pointer-events-auto transition-all"
            onClick={onClose}
          />

          {/* Lateral Slide-Over Drawer */}
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
            className="fixed top-0 right-0 h-full w-full max-w-3xl lg:max-w-4xl bg-white shadow-2xl border-l border-zinc-200 z-10 flex flex-col pointer-events-auto overflow-hidden"
          >
            {/* Header */}
            <div className="px-6 md:px-8 py-5 border-b border-zinc-200 flex items-center justify-between bg-zinc-50/70 shrink-0">
              <div className="flex items-center gap-3.5">
                <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-zinc-800 to-zinc-950 flex items-center justify-center text-white shadow-md shrink-0">
                  <MapPin className="w-6 h-6 text-emerald-400" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-zinc-900 text-white">
                      Despacho Operacional
                    </span>
                    <span className="text-xs font-semibold text-zinc-500">
                      Nova Entrega Manual
                    </span>
                  </div>
                  <h2 className="text-xl font-black text-zinc-900 tracking-tight mt-0.5">
                    Criar Nova Solicitação
                  </h2>
                  <p className="text-xs text-zinc-500 font-medium">
                    Preencha os endereços de coleta, destinatários e forma de pagamento
                  </p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 rounded-xl transition-all cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Stepper Progress */}
          <div className="grid grid-cols-2 border-b border-zinc-200 bg-zinc-50/30 text-xs font-bold uppercase tracking-wider shrink-0">
            <div
              className={cn(
                "p-3 text-center border-r border-zinc-200 flex items-center justify-center gap-2 transition-colors",
                step === 1
                  ? "bg-white text-zinc-900 border-b-2 border-b-zinc-900"
                  : "text-zinc-400",
              )}
            >
              <span
                className={cn(
                  "w-5 h-5 rounded-full flex items-center justify-center text-[10px]",
                  step === 1
                    ? "bg-zinc-900 text-white"
                    : "bg-zinc-200 text-zinc-600",
                )}
              >
                1
              </span>
              Endereços e Contatos
            </div>
            <div
              className={cn(
                "p-3 text-center flex items-center justify-center gap-2 transition-colors",
                step === 2
                  ? "bg-white text-zinc-900 border-b-2 border-b-zinc-900"
                  : "text-zinc-400",
              )}
            >
              <span
                className={cn(
                  "w-5 h-5 rounded-full flex items-center justify-center text-[10px]",
                  step === 2
                    ? "bg-zinc-900 text-white"
                    : "bg-zinc-200 text-zinc-600",
                )}
              >
                2
              </span>
              Cotação e Pagamento
            </div>
          </div>

          {/* Content Step 1 */}
          {step === 1 && (
            <div className="flex-1 overflow-y-auto px-6 pb-6 pt-4">
              <form
                id="step-1-form"
                onSubmit={handleNextStep}
                className="space-y-6"
              >
                {/* Seleção de Loja Parceira Solicitante (Módulo 03 - Despacho Centralizado) */}
                {!isLojista && partnerStores.length > 0 && (
                  <div className="bg-indigo-50/70 border border-indigo-200/80 rounded-xl p-4 space-y-2.5">
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-bold text-indigo-950 flex items-center gap-1.5 uppercase tracking-wider">
                        <Store className="w-4 h-4 text-indigo-600" />
                        Loja Parceira Solicitante *
                      </label>
                      {selectedStore && (
                        <span
                          className={cn(
                            "text-[11px] font-bold px-2.5 py-0.5 rounded-full border",
                            String(selectedStore.billing_mode || "").toUpperCase().includes("PRE")
                              ? "bg-amber-100/90 text-amber-900 border-amber-300"
                              : "bg-emerald-100/90 text-emerald-900 border-emerald-300",
                          )}
                        >
                          {String(selectedStore.billing_mode || "").toUpperCase().includes("PRE")
                            ? "Pré-Pago"
                            : "Pós-Pago"}{" "}
                          • Saldo: {formatCurrency((selectedStore.balance_cents || 0) / 100)}
                        </span>
                      )}
                    </div>
                    <select
                      value={selectedStoreId}
                      onChange={(e) => handleStoreChange(e.target.value)}
                      className="w-full px-3.5 py-2 text-sm bg-white border border-indigo-200 rounded-lg font-semibold text-zinc-900 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 shadow-sm"
                    >
                      {partnerStores.map((s) => {
                        const isPre = String(s.billing_mode || "").toUpperCase().includes("PRE");
                        return (
                          <option key={s.id} value={s.id}>
                            {s.nome || s.name} {isPre ? `(Pré-Pago: ${formatCurrency((s.balance_cents || 0) / 100)})` : "(Pós-Pago / Faturado)"}
                          </option>
                        );
                      })}
                    </select>
                  </div>
                )}

                {/* Coleta */}
                <div className="space-y-4 bg-zinc-50 p-4 rounded-xl border border-zinc-200/60">
                  <h3 className="text-sm font-bold text-zinc-800 flex items-center gap-2 uppercase tracking-wide">
                    <div className="w-6 h-6 rounded-full bg-zinc-200 text-zinc-700 flex items-center justify-center font-bold text-xs">
                      C
                    </div>
                    Dados de Coleta
                  </h3>
                  <div>
                    <label className="block text-xs font-semibold text-zinc-700 mb-1">
                      Endereço de Coleta (Opcional)
                    </label>
                    <AddressAutocomplete
                      value={pickupAddress}
                      onChange={setPickupAddress}
                      onSelect={setPickupResult}
                      placeholder="R. Oito Vista Alegre, 24..."
                    />
                    <p className="text-[10px] text-zinc-500 mt-1.5">
                      Se em branco, usará o endereço padrão da empresa (
                      {currentCompany?.endereco || "Av. Principal"}).
                    </p>
                  </div>
                </div>

                {/* Entregas */}
                <div className="space-y-4">
                  {deliveries.map((delivery, index) => (
                    <div
                      key={delivery.id}
                      className="relative bg-white border border-zinc-200 shadow-sm rounded-xl p-5 mb-4"
                    >
                      <div className="flex items-center justify-between mb-4 pb-3 border-b border-zinc-100">
                        <h3 className="text-sm font-bold text-zinc-800 flex items-center gap-2 uppercase tracking-wide">
                          <div className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center font-bold text-xs">
                            {index + 1}
                          </div>
                          Entrega {index + 1}
                        </h3>
                        {deliveries.length > 1 && (
                          <button
                            type="button"
                            onClick={() => handleRemoveDelivery(delivery.id)}
                            className="p-1.5 text-zinc-400 hover:text-red-500 hover:bg-red-50 rounded-md transition-colors"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>

                      <div className="space-y-3">
                        <div className="grid grid-cols-12 gap-3">
                          <div className="col-span-12 sm:col-span-8">
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              Endereço *
                            </label>
                            <AddressAutocomplete
                              required
                              value={delivery.address}
                              onChange={(val) =>
                                updateDelivery(delivery.id, "address", val)
                              }
                              onSelect={(res) => {
                                setDeliveries(
                                  deliveries.map((d) =>
                                    d.id === delivery.id
                                      ? {
                                          ...d,
                                          address:
                                            res.address?.road ||
                                            res.display_name.split(",")[0],
                                          bairro:
                                            res.address?.suburb || "Centro",
                                          cidade:
                                            res.address?.city || "São Paulo",
                                          estado: getStateAbbr(
                                            res.address?.state,
                                            "SP",
                                          ),
                                          lat: res.lat,
                                          lng: res.lon,
                                        }
                                      : d,
                                  ),
                                );
                              }}
                              placeholder="Rua, Avenida..."
                            />
                          </div>
                          <div className="col-span-4 sm:col-span-2">
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              Número *
                            </label>
                            <input
                              required
                              type="text"
                              value={delivery.number}
                              onChange={(e) =>
                                updateDelivery(
                                  delivery.id,
                                  "number",
                                  e.target.value,
                                )
                              }
                              className="w-full px-3 py-2 text-sm border border-zinc-200 rounded-lg focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900"
                              placeholder="123"
                            />
                          </div>
                          <div className="col-span-8 sm:col-span-2">
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              Complemento
                            </label>
                            <input
                              type="text"
                              value={delivery.complement}
                              onChange={(e) =>
                                updateDelivery(
                                  delivery.id,
                                  "complement",
                                  e.target.value,
                                )
                              }
                              className="w-full px-3 py-2 text-sm border border-zinc-200 rounded-lg focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900"
                              placeholder="Apto 4"
                            />
                          </div>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              Nome do Cliente *
                            </label>
                            <input
                              required
                              type="text"
                              value={delivery.name}
                              onChange={(e) =>
                                updateDelivery(
                                  delivery.id,
                                  "name",
                                  e.target.value,
                                )
                              }
                              className="w-full px-3 py-2 text-sm border border-zinc-200 rounded-lg focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900"
                              placeholder="João da Silva"
                            />
                          </div>
                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              Telefone *
                            </label>
                            <input
                              required
                              type="text"
                              value={delivery.phone}
                              onChange={(e) =>
                                updateDelivery(
                                  delivery.id,
                                  "phone",
                                  e.target.value,
                                )
                              }
                              className="w-full px-3 py-2 text-sm border border-zinc-200 rounded-lg focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900"
                              placeholder="(11) 90000-0000"
                            />
                          </div>
                        </div>

                        <div>
                          <label className="block text-xs font-semibold text-zinc-700 mb-1">
                            Observações para o entregador
                          </label>
                          <textarea
                            value={delivery.notes}
                            onChange={(e) =>
                              updateDelivery(
                                delivery.id,
                                "notes",
                                e.target.value,
                              )
                            }
                            className="w-full px-3 py-2 text-sm border border-zinc-200 rounded-lg focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 min-h-[60px] resize-none"
                            placeholder="Ex: Deixar na portaria, Cuidado frágil..."
                          />
                        </div>
                      </div>
                    </div>
                  ))}

                  <button
                    type="button"
                    onClick={handleAddDelivery}
                    className="w-full py-3 flex items-center justify-center gap-2 border-2 border-dashed border-zinc-200 text-zinc-600 font-semibold text-sm rounded-xl hover:border-zinc-900 hover:text-zinc-900 transition-colors bg-zinc-50/50 hover:bg-zinc-100/50"
                  >
                    <Plus className="w-4 h-4" />
                    Adicionar ponto de entrega
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Content Step 2 */}
          {step === 2 && (
            <div className="flex-1 overflow-y-auto px-6 pb-6 pt-4 space-y-4">
              {/* Alert Coleta */}
              <div className="bg-emerald-50 border border-emerald-200/60 rounded-xl p-3 flex items-center gap-2">
                <span className="text-xs font-bold text-emerald-700 tracking-wider">
                  COLETA
                </span>
                <span className="text-sm font-medium text-emerald-900 border-l border-emerald-200 pl-2">
                  Coleta:{" "}
                  {pickupAddress ||
                    currentCompany?.endereco ||
                    "Endereço principal da empresa"}
                </span>
              </div>

              {/* Resumo da solicitação */}
              <div className="bg-zinc-50 border border-zinc-200/80 rounded-xl p-4">
                <h3 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-4">
                  Resumo da solicitação
                </h3>

                <div className="space-y-3 mb-6">
                  <div className="flex justify-between items-start text-sm">
                    <span className="text-zinc-500 font-medium">Coleta</span>
                    <span className="font-bold text-zinc-900 text-right max-w-[60%]">
                      {pickupAddress ||
                        currentCompany?.endereco ||
                        "Endereço principal da empresa"}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-zinc-500 font-medium">Entregas</span>
                    <span className="font-bold text-zinc-900">
                      {deliveries.length} ponto
                      {deliveries.length > 1 ? "s" : ""}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-zinc-500 font-medium">Empresa Solicitante</span>
                    <div className="text-right">
                      <span className="font-bold text-zinc-900 block">
                        {selectedStore?.nome || currentCompany?.nome || "Empresa"}
                      </span>
                      <span
                        className={cn(
                          "text-[10px] font-bold px-2 py-0.5 rounded-full inline-block mt-0.5",
                          String(selectedStore?.billing_mode || "")
                            .toUpperCase()
                            .includes("PRE")
                            ? "bg-amber-100 text-amber-900"
                            : "bg-emerald-100 text-emerald-900",
                        )}
                      >
                        {String(selectedStore?.billing_mode || "")
                          .toUpperCase()
                          .includes("PRE")
                          ? "Pré-Pago"
                          : "Pós-Pago"}{" "}
                        • Saldo: {formatCurrency((selectedStore?.balance_cents || 0) / 100)}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="border-t border-zinc-200/80 pt-4 space-y-3">
                  {deliveries.map((delivery, index) => (
                    <div key={delivery.id} className="flex items-center gap-3">
                      <div className="w-5 h-5 rounded-full bg-zinc-800 text-white flex items-center justify-center font-bold text-[10px] shrink-0">
                        {index + 1}
                      </div>
                      <div className="text-sm font-bold text-zinc-800">
                        {delivery.address || "Endereço não informado"},{" "}
                        {delivery.number}{" "}
                        <span className="text-zinc-400 font-normal text-[11px] ml-1">
                          ({delivery.name || "Sem nome"})
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Estimativa */}
              <div className="bg-zinc-50 border border-zinc-200/80 rounded-xl p-4">
                <h3 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-4">
                  Estimativa da Entrega
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="bg-white border border-zinc-200/80 rounded-xl p-4 flex flex-col items-center justify-center text-center">
                    <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-1">
                      Valor
                    </span>
                    <span className="text-lg font-black text-zinc-900">
                      {isEstimating ? (
                        <Loader2 className="w-5 h-5 animate-spin text-zinc-400 mx-auto" />
                      ) : (
                        formatCurrency(
                          estimativa?.valor || deliveries.length * 9.0,
                        )
                      )}
                    </span>
                  </div>

                  <div className="bg-white border border-zinc-200/80 rounded-xl p-4 flex flex-col items-center justify-center text-center">
                    <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-1">
                      Distância
                    </span>
                    <span className="text-lg font-black text-indigo-600">
                      {isEstimating ? (
                        <Loader2 className="w-5 h-5 animate-spin text-indigo-400 mx-auto" />
                      ) : (
                        `${(estimativa?.distancia || deliveries.length * 5.0).toFixed(1).replace(".", ",")} km`
                      )}
                    </span>
                  </div>

                  <div className="bg-white border border-zinc-200/80 rounded-xl p-4 flex flex-col items-center justify-center text-center">
                    <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-1">
                      Tempo Estimado
                    </span>
                    <span className="text-lg font-black text-emerald-600">
                      {isEstimating ? (
                        <Loader2 className="w-5 h-5 animate-spin text-emerald-400 mx-auto" />
                      ) : (
                        `${Math.round(estimativa?.tempo || deliveries.length * 15)} min`
                      )}
                    </span>
                  </div>
                </div>
              </div>

              {/* Categoria do Condutor */}
              <div>
                <h3 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-2">
                  Categoria do Condutor
                </h3>
                <div className="inline-flex">
                  <button
                    type="button"
                    className="px-4 py-2 border border-zinc-300 rounded-lg text-sm font-bold text-zinc-800 bg-white shadow-sm flex items-center gap-2"
                  >
                    {categoriaCondutor}
                  </button>
                </div>
              </div>

              {/* Forma de Pagamento (Padrão MotorK) */}
              <div>
                <h3 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-2.5">
                  Forma de Pagamento
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                  {[
                    { id: "JA_PAGO", label: "Já Pago", desc: "No App / Loja", icon: Receipt },
                    { id: "DINHEIRO", label: "Dinheiro", desc: "Na Entrega", icon: Banknote },
                    { id: "PIX", label: "PIX", desc: "Na Entrega", icon: QrCode },
                    { id: "CARTAO", label: "Cartão", desc: "Maquininha", icon: CreditCard },
                  ].map((m) => {
                    const Icon = m.icon;
                    const isSelected = formaPagamento === m.id;
                    return (
                      <button
                        key={m.id}
                        type="button"
                        onClick={() => {
                          setFormaPagamento(m.id);
                          setBalanceError(null);
                        }}
                        className={cn(
                          "p-3 rounded-xl border text-left flex flex-col justify-between transition-all",
                          isSelected
                            ? "bg-zinc-900 text-white border-zinc-900 shadow-sm"
                            : "bg-white text-zinc-800 border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50/50",
                        )}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <Icon className={cn("w-4 h-4", isSelected ? "text-white" : "text-zinc-500")} />
                          {isSelected && <Check className="w-3.5 h-3.5 text-emerald-400" />}
                        </div>
                        <div>
                          <div className="text-xs font-bold">{m.label}</div>
                          <div className={cn("text-[10px]", isSelected ? "text-zinc-300" : "text-zinc-400")}>
                            {m.desc}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Troco para Dinheiro */}
              {formaPagamento === "DINHEIRO" && (
                <div className="bg-zinc-50 border border-zinc-200 rounded-xl p-3.5 space-y-1.5">
                  <label className="text-xs font-bold text-zinc-700 block">
                    Troco para quanto? (Opcional)
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs font-bold text-zinc-400">
                      R$
                    </span>
                    <input
                      type="number"
                      step="0.01"
                      placeholder="Ex: 50,00"
                      value={trocoPara}
                      onChange={(e) => setTrocoPara(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900"
                    />
                  </div>
                  <p className="text-[10px] text-zinc-500">
                    Deixe em branco se o cliente tiver o valor exato em espécie.
                  </p>
                </div>
              )}

              {/* Observação Geral */}
              <div>
                <h3 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-2">
                  Observação Geral
                </h3>
                <textarea
                  value={observacaoGeral}
                  onChange={(e) => setObservacaoGeral(e.target.value)}
                  placeholder="Instrução para o motoboy (opcional)"
                  className="w-full px-4 py-3 bg-white border border-zinc-200 rounded-xl text-sm focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 min-h-[70px] resize-none"
                />
              </div>

              {/* Validação de Saldo Pré-Pago (Módulo 03 / MotorK Benchmark) */}
              {(() => {
                const isPre = String(selectedStore?.billing_mode || "")
                  .toUpperCase()
                  .includes("PRE");
                const estimatedCents = Math.round(
                  (estimativa?.valor || deliveries.length * 9.0) * 100,
                );
                const balCents = selectedStore?.balance_cents ?? 0;
                const isBlocked = isPre && balCents < estimatedCents;

                if (isBlocked || balanceError) {
                  return (
                    <div className="bg-amber-50 border border-amber-300 rounded-xl p-4 flex items-start gap-3 text-amber-950">
                      <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                      <div className="space-y-1.5 flex-1">
                        <h4 className="font-bold text-sm text-amber-900">
                          Saldo Pré-Pago Insuficiente
                        </h4>
                        <p className="text-xs text-amber-800 leading-relaxed">
                          {balanceError || (
                            <>
                              A loja parceira{" "}
                              <strong>
                                {selectedStore?.nome || "selecionada"}
                              </strong>{" "}
                              possui saldo disponível de{" "}
                              <span className="font-bold">
                                {formatCurrency(balCents / 100)}
                              </span>
                              , porém o valor estimado desta entrega é de{" "}
                              <span className="font-bold">
                                {formatCurrency(estimatedCents / 100)}
                              </span>
                              . Para liberar o despacho, realize uma recarga via PIX.
                            </>
                          )}
                        </p>
                        <div className="pt-1.5">
                          <a
                            href="/creditos"
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-bold transition-all shadow-sm"
                          >
                            <Wallet className="w-3.5 h-3.5" /> Recarregar Créditos{" "}
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        </div>
                      </div>
                    </div>
                  );
                }
                return null;
              })()}
            </div>
          )}

          {/* Standard Footer */}
          <div className="px-6 md:px-8 py-4 border-t border-zinc-200 bg-zinc-50/90 backdrop-blur-xs flex items-center justify-between gap-4 shrink-0">
            {step === 1 ? (
              <>
                <button
                  type="button"
                  onClick={onClose}
                  className="px-5 py-2.5 border border-zinc-200 bg-white text-zinc-700 rounded-xl hover:bg-zinc-100 text-xs font-bold transition-all cursor-pointer shadow-xs"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  form="step-1-form"
                  disabled={isEstimating}
                  className="px-6 py-2.5 bg-zinc-900 hover:bg-zinc-800 disabled:opacity-50 text-white rounded-xl text-xs font-bold shadow-sm transition-all flex items-center gap-2 cursor-pointer"
                >
                  {isEstimating ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <span>Avançar</span>
                      <ChevronRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  disabled={isSubmitting}
                  className="px-5 py-2.5 border border-zinc-200 bg-white text-zinc-700 rounded-xl hover:bg-zinc-100 text-xs font-bold transition-all cursor-pointer shadow-xs"
                >
                  Voltar
                </button>
                {(() => {
                  const isPre = String(selectedStore?.billing_mode || "")
                    .toUpperCase()
                    .includes("PRE");
                  const estimatedCents = Math.round(
                    (estimativa?.valor || deliveries.length * 9.0) * 100,
                  );
                  const isBlocked =
                    isPre && (selectedStore?.balance_cents ?? 0) < estimatedCents;

                  return (
                    <button
                      type="button"
                      onClick={handleSubmit}
                      disabled={isSubmitting || isEstimating || isBlocked}
                      className={cn(
                        "px-6 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 cursor-pointer",
                        isBlocked
                          ? "bg-zinc-200 text-zinc-400 cursor-not-allowed border border-zinc-300"
                          : "bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm shadow-emerald-600/20",
                      )}
                    >
                      {isSubmitting ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : isBlocked ? (
                        <>
                          <AlertCircle className="w-4 h-4" /> Saldo Insuficiente
                        </>
                      ) : (
                        <>
                          <Check className="w-4 h-4" /> Solicitar Entrega
                        </>
                      )}
                    </button>
                  );
                })()}
              </>
            )}
          </div>
        </motion.div>
      </div>
    )}
  </AnimatePresence>,
  document.body,
);
}
