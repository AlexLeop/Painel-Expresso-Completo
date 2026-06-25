import React, { useState } from "react";
import { X, MapPin, Plus, Trash2, ChevronRight, Check, Loader2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn, formatCurrency } from "../lib/utils";
import { AddressAutocomplete } from "./AddressAutocomplete";
import { authFetch } from "../lib/api";

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

const getStateAbbr = (stateName?: string, fallback = 'SP') => {
  if (!stateName) return fallback;
  const map: Record<string, string> = {
    'Acre': 'AC', 'Alagoas': 'AL', 'Amapá': 'AP', 'Amazonas': 'AM',
    'Bahia': 'BA', 'Ceará': 'CE', 'Distrito Federal': 'DF',
    'Espírito Santo': 'ES', 'Goiás': 'GO', 'Maranhão': 'MA',
    'Mato Grosso': 'MT', 'Mato Grosso do Sul': 'MS', 'Minas Gerais': 'MG',
    'Pará': 'PA', 'Paraíba': 'PB', 'Paraná': 'PR', 'Pernambuco': 'PE',
    'Piauí': 'PI', 'Rio de Janeiro': 'RJ', 'Rio Grande do Norte': 'RN',
    'Rio Grande do Sul': 'RS', 'Rondônia': 'RO', 'Roraima': 'RR',
    'Santa Catarina': 'SC', 'São Paulo': 'SP', 'Sergipe': 'SE', 'Tocantins': 'TO',
  };
  return map[stateName] || (stateName.length === 2 ? stateName.toUpperCase() : stateName.substring(0, 2).toUpperCase());
};

export function CreateRideModal({ isOpen, onClose, onSave, currentCompany, initialData }: CreateRideModalProps) {
  const [step, setStep] = useState(1);
  const [pickupAddress, setPickupAddress] = useState(initialData?.coleta?.endereco || "");
  const [pickupResult, setPickupResult] = useState<any>(null);
  const [deliveries, setDeliveries] = useState<DeliveryPoint[]>(() => {
    if (initialData?.entrega?.endereco) {
      return [{
        id: Date.now(),
        address: initialData.entrega.endereco.split(',')[0] || "",
        number: initialData.entrega.endereco.split(',')[1]?.trim() || "",
        complement: "",
        name: initialData.cliente || "",
        phone: initialData.telefoneCliente || "",
        notes: ""
      }];
    }
    return [{ id: Date.now(), address: "", number: "", complement: "", name: "", phone: "", notes: "" }];
  });
  
  const [categoriaCondutor, setCategoriaCondutor] = useState(initialData?.tipo || "Entrega padrão");
  const [formaPagamento, setFormaPagamento] = useState("Faturado");
  const [observacaoGeral, setObservacaoGeral] = useState("");

  const [isEstimating, setIsEstimating] = useState(false);
  const [estimativa, setEstimativa] = useState<{ valor: number; distancia: number; tempo: number } | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  React.useEffect(() => {
    if (isOpen) {
      setStep(1);
      setPickupAddress(initialData?.coleta?.endereco || "");
      if (initialData?.entrega?.endereco) {
        setDeliveries([{
          id: Date.now(),
          address: initialData.entrega.endereco.split(',')[0] || "",
          number: initialData.entrega.endereco.split(',')[1]?.trim() || "",
          complement: "",
          name: initialData.cliente || "",
          phone: initialData.telefoneCliente || "",
          notes: ""
        }]);
      } else {
        setDeliveries([{ id: Date.now(), address: "", number: "", complement: "", name: "", phone: "", notes: "" }]);
      }
      setCategoriaCondutor(initialData?.tipo || "Entrega padrão");
      setObservacaoGeral("");
      setEstimativa(null);
    }
  }, [isOpen, initialData]);

  if (!isOpen) return null;

  const handleAddDelivery = () => {
    setDeliveries([
      ...deliveries,
      { id: Date.now(), address: "", number: "", complement: "", name: "", phone: "", notes: "" }
    ]);
  };

  const handleRemoveDelivery = (id: number) => {
    if (deliveries.length > 1) {
      setDeliveries(deliveries.filter(d => d.id !== id));
    }
  };

  const updateDelivery = (id: number, field: keyof DeliveryPoint, value: string) => {
    setDeliveries(deliveries.map(d => d.id === id ? { ...d, [field]: value } : d));
  };

  const handleNextStep = async (e: React.FormEvent) => {
    e.preventDefault();
    setStep(2);
    setIsEstimating(true);
    try {
      let totalVal = 0;
      let totalKm = 0;
      let totalMin = 0;

      const defaultLat = currentCompany?.lat ?? currentCompany?.latitude ?? "-23.5505";
      const defaultLng = currentCompany?.lng ?? currentCompany?.longitude ?? "-46.6333";
      const defaultEnd = currentCompany?.endereco ?? currentCompany?.address ?? currentCompany?.nome ?? currentCompany?.name ?? "Av. Principal";
      const defaultBairro = currentCompany?.bairro ?? "Centro";
      const defaultCidade = currentCompany?.cidade ?? "São Paulo";
      const defaultUF = getStateAbbr(currentCompany?.uf ?? currentCompany?.estado ?? "SP");

      const pickupStateAbbr = getStateAbbr(pickupResult?.address?.state || defaultUF);
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
        const from = i === 0 ? pickup : {
          endereco: deliveries[i-1].address || "",
          bairro: deliveries[i-1].bairro || defaultBairro,
          cidade: deliveries[i-1].cidade || defaultCidade,
          estado: getStateAbbr(deliveries[i-1].estado || defaultUF),
          lat: deliveries[i-1].lat || defaultLat,
          lng: deliveries[i-1].lng || defaultLng,
        };
        legs.push({ from, to: d });
      }

      const results = await Promise.all(legs.map(async leg => {
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
          const res = await authFetch(`/api/machine/rides/estimate?${params.toString()}`);
          if (res.ok) {
            const data = await res.json();
            return data.response || data;
          }
        } catch { /* silent */ }
        return null;
      }));

      let hasSuccess = false;
      results.forEach(resp => {
        if (!resp) return;
        const v = resp.estimativa_valor ?? resp.valor_corrida ?? resp.valor;
        const km = resp.estimativa_km ?? resp.distancia_km ?? resp.distancia;
        const min = resp.estimativa_minutos ?? resp.tempo_estimado ?? resp.tempo;
        if (v != null) { totalVal += Number(v); hasSuccess = true; }
        if (km != null) totalKm += Number(km);
        if (min != null) totalMin += Number(min);
      });

      if (hasSuccess) {
        setEstimativa({ valor: totalVal, distancia: totalKm, tempo: totalMin });
      } else {
        setEstimativa({ valor: deliveries.length * 9.0, distancia: deliveries.length * 5.0, tempo: deliveries.length * 15 });
      }
    } catch (err) {
      setEstimativa({ valor: deliveries.length * 9.0, distancia: deliveries.length * 5.0, tempo: deliveries.length * 15 });
    } finally {
      setIsEstimating(false);
    }
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      const defaultLat = currentCompany?.lat ?? currentCompany?.latitude ?? "-23.5505";
      const defaultLng = currentCompany?.lng ?? currentCompany?.longitude ?? "-46.6333";
      const defaultEnd = currentCompany?.endereco ?? currentCompany?.address ?? currentCompany?.nome ?? currentCompany?.name ?? "Av. Principal";
      const defaultBairro = currentCompany?.bairro ?? "Centro";
      const defaultCidade = currentCompany?.cidade ?? "São Paulo";
      const defaultUF = getStateAbbr(currentCompany?.uf ?? currentCompany?.estado ?? "SP");

      const pickupStateAbbr = getStateAbbr(pickupResult?.address?.state || defaultUF);
      const pickup = {
        endereco: pickupResult?.address?.road || pickupAddress || defaultEnd,
        bairro: pickupResult?.address?.suburb || defaultBairro,
        cidade: pickupResult?.address?.city || defaultCidade,
        estado: pickupStateAbbr,
        lat: pickupResult?.lat || defaultLat,
        lng: pickupResult?.lon || defaultLng,
      };

      const machineEmpId = currentCompany?.machineEmpresaId || currentCompany?.machine_empresa_id || (!isNaN(Number(currentCompany?.id)) ? Number(currentCompany?.id) : 112905);

      const payload = {
        empresa_id: machineEmpId,
        forma_pagamento: formaPagamento === "Faturado" ? "F" : "D",
        partida: pickup,
        paradas: deliveries.map(d => ({
          endereco_parada: `${d.address || ""}${d.number ? ", " + d.number : ""}`,
          bairro_parada: d.bairro || defaultBairro,
          cidade_parada: d.cidade || defaultCidade,
          estado_parada: getStateAbbr(d.estado || defaultUF),
          lat_parada: d.lat || "",
          lng_parada: d.lng || "",
          complemento_parada: d.complement || "",
          nome_cliente_parada: d.name || "",
          telefone_cliente_parada: d.phone || "",
          observacao_parada: d.notes || observacaoGeral || ""
        })),
        retorno: false
      };

      const res = await authFetch('/api/machine/rides/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || data.details || "Erro ao criar corrida na Machine");
      }

      const id = data?.response?.id || data?.id || Math.floor(1000 + Math.random() * 9000);
      const val = estimativa?.valor || deliveries.length * 9.0;
      const km = estimativa?.distancia || deliveries.length * 5.0;

      const newRide = {
        id,
        codigoPedido: `M-${id}`,
        status: "Aguardando",
        status_solicitacao: "D",
        tipo: categoriaCondutor,
        cliente: deliveries[0]?.name || "Cliente",
        telefoneCliente: deliveries[0]?.phone || "",
        empresa: currentCompany?.name || currentCompany?.nome || "Empresa",
        motoboy: { nome: "Aguardando...", foto: "?", exp: "-", cnh: "-", id_num: "-", placa: "-", veiculo: "-" },
        coleta: { hora: new Date().toLocaleTimeString('pt-BR', {hour: '2-digit', minute:'2-digit'}), endereco: pickup.endereco },
        entrega: { hora: "--:--", endereco: `${deliveries[0].address}, ${deliveries[0].number}` },
        valor: val,
        horario: new Date().toLocaleTimeString('pt-BR', {hour: '2-digit', minute:'2-digit'}),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        lastLoc: pickup.endereco,
        lastStop: "Nenhuma",
        distancia: `${km.toFixed(1)} km`,
        speed: "0 km/h",
      };

      onSave(newRide);
      
      setTimeout(() => {
        setStep(1);
        setPickupAddress("");
        setPickupResult(null);
        setDeliveries([{ id: Date.now(), address: "", number: "", complement: "", name: "", phone: "", notes: "" }]);
        setCategoriaCondutor("Entrega padrão");
        setFormaPagamento("Faturado");
        setObservacaoGeral("");
        setEstimativa(null);
      }, 300);
    } catch (err: any) {
      alert("Falha ao criar corrida: " + err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-zinc-900/40 backdrop-blur-sm z-[1000] flex items-center justify-center p-4 xl:p-0"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.95, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.95, y: 20 }}
          onClick={(e) => e.stopPropagation()}
          className="bg-white w-full max-w-3xl rounded-2xl shadow-2xl overflow-hidden border border-zinc-200/80 flex flex-col max-h-[90vh]"
        >
          {/* Header */}
          <div className="px-6 py-5 border-b border-zinc-200 flex items-center justify-between bg-zinc-50/50 shrink-0">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-zinc-900 text-white">Despacho</span>
                <span className="text-xs font-semibold text-zinc-500">Nova Entrega Manual</span>
              </div>
              <h2 className="text-xl font-bold text-zinc-900 tracking-tight">Criar Nova Solicitação</h2>
            </div>
            <button onClick={onClose} className="p-2 text-zinc-400 hover:text-zinc-600 rounded-xl hover:bg-zinc-100 transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Stepper Progress */}
          <div className="grid grid-cols-2 border-b border-zinc-200 bg-zinc-50/30 text-xs font-bold uppercase tracking-wider shrink-0">
            <div className={cn("p-3 text-center border-r border-zinc-200 flex items-center justify-center gap-2 transition-colors", step === 1 ? "bg-white text-zinc-900 border-b-2 border-b-zinc-900" : "text-zinc-400")}>
              <span className={cn("w-5 h-5 rounded-full flex items-center justify-center text-[10px]", step === 1 ? "bg-zinc-900 text-white" : "bg-zinc-200 text-zinc-600")}>1</span>
              Endereços e Contatos
            </div>
            <div className={cn("p-3 text-center flex items-center justify-center gap-2 transition-colors", step === 2 ? "bg-white text-zinc-900 border-b-2 border-b-zinc-900" : "text-zinc-400")}>
              <span className={cn("w-5 h-5 rounded-full flex items-center justify-center text-[10px]", step === 2 ? "bg-zinc-900 text-white" : "bg-zinc-200 text-zinc-600")}>2</span>
              Cotação e Pagamento
            </div>
          </div>

          {/* Content Step 1 */}
          {step === 1 && (
            <div className="flex-1 overflow-y-auto px-6 pb-6 pt-4">
              <form id="step-1-form" onSubmit={handleNextStep} className="space-y-6">
                
                {/* Coleta */}
                <div className="space-y-4 bg-zinc-50 p-4 rounded-xl border border-zinc-200/60">
                  <h3 className="text-sm font-bold text-zinc-800 flex items-center gap-2 uppercase tracking-wide">
                    <div className="w-6 h-6 rounded-full bg-zinc-200 text-zinc-700 flex items-center justify-center font-bold text-xs">C</div>
                     Dados de Coleta
                  </h3>
                  <div>
                    <label className="block text-xs font-semibold text-zinc-700 mb-1">Endereço de Coleta (Opcional)</label>
                    <AddressAutocomplete
                      value={pickupAddress}
                      onChange={setPickupAddress}
                      onSelect={setPickupResult}
                      placeholder="R. Oito Vista Alegre, 24..."
                    />
                    <p className="text-[10px] text-zinc-500 mt-1.5">Se em branco, usará o endereço padrão da empresa ({currentCompany?.endereco || "Av. Principal"}).</p>
                  </div>
                </div>

                {/* Entregas */}
                <div className="space-y-4">
                  {deliveries.map((delivery, index) => (
                    <div key={delivery.id} className="relative bg-white border border-zinc-200 shadow-sm rounded-xl p-5 mb-4">
                      
                      <div className="flex items-center justify-between mb-4 pb-3 border-b border-zinc-100">
                        <h3 className="text-sm font-bold text-zinc-800 flex items-center gap-2 uppercase tracking-wide">
                           <div className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center font-bold text-xs">{index + 1}</div>
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
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">Endereço *</label>
                            <AddressAutocomplete
                              required
                              value={delivery.address}
                              onChange={val => updateDelivery(delivery.id, 'address', val)}
                                onSelect={res => {
                                  setDeliveries(deliveries.map(d => d.id === delivery.id ? {
                                    ...d,
                                    address: res.address?.road || res.display_name.split(',')[0],
                                    bairro: res.address?.suburb || 'Centro',
                                    cidade: res.address?.city || 'São Paulo',
                                    estado: getStateAbbr(res.address?.state, 'SP'),
                                    lat: res.lat,
                                    lng: res.lon
                                  } : d));
                                }}
                              placeholder="Rua, Avenida..."
                            />
                          </div>
                          <div className="col-span-4 sm:col-span-2">
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">Número *</label>
                            <input required type="text" value={delivery.number} onChange={e => updateDelivery(delivery.id, 'number', e.target.value)} className="w-full px-3 py-2 text-sm border border-zinc-200 rounded-lg focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900" placeholder="123" />
                          </div>
                          <div className="col-span-8 sm:col-span-2">
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">Complemento</label>
                            <input type="text" value={delivery.complement} onChange={e => updateDelivery(delivery.id, 'complement', e.target.value)} className="w-full px-3 py-2 text-sm border border-zinc-200 rounded-lg focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900" placeholder="Apto 4" />
                          </div>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">Nome do Cliente *</label>
                            <input required type="text" value={delivery.name} onChange={e => updateDelivery(delivery.id, 'name', e.target.value)} className="w-full px-3 py-2 text-sm border border-zinc-200 rounded-lg focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900" placeholder="João da Silva" />
                          </div>
                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">Telefone *</label>
                            <input required type="text" value={delivery.phone} onChange={e => updateDelivery(delivery.id, 'phone', e.target.value)} className="w-full px-3 py-2 text-sm border border-zinc-200 rounded-lg focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900" placeholder="(11) 90000-0000" />
                          </div>
                        </div>

                        <div>
                          <label className="block text-xs font-semibold text-zinc-700 mb-1">Observações para o entregador</label>
                          <textarea 
                            value={delivery.notes} 
                            onChange={e => updateDelivery(delivery.id, 'notes', e.target.value)} 
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
                  <span className="text-xs font-bold text-emerald-700 tracking-wider">COLETA</span>
                  <span className="text-sm font-medium text-emerald-900 border-l border-emerald-200 pl-2">Coleta: {pickupAddress || currentCompany?.endereco || "Endereço principal da empresa"}</span>
                </div>

                {/* Resumo da solicitação */}
                <div className="bg-zinc-50 border border-zinc-200/80 rounded-xl p-4">
                  <h3 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-4">Resumo da solicitação</h3>
                  
                  <div className="space-y-3 mb-6">
                    <div className="flex justify-between items-start text-sm">
                      <span className="text-zinc-500 font-medium">Coleta</span>
                      <span className="font-bold text-zinc-900 text-right max-w-[60%]">{pickupAddress || currentCompany?.endereco || "Endereço principal da empresa"}</span>
                    </div>
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-zinc-500 font-medium">Entregas</span>
                      <span className="font-bold text-zinc-900">{deliveries.length} ponto{deliveries.length > 1 ? 's' : ''}</span>
                    </div>
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-zinc-500 font-medium">Empresa</span>
                      <span className="font-bold text-zinc-900">{currentCompany?.nome || "Empresa teste"}</span>
                    </div>
                  </div>

                  <div className="border-t border-zinc-200/80 pt-4 space-y-3">
                    {deliveries.map((delivery, index) => (
                      <div key={delivery.id} className="flex items-center gap-3">
                         <div className="w-5 h-5 rounded-full bg-zinc-800 text-white flex items-center justify-center font-bold text-[10px] shrink-0">
                           {index + 1}
                         </div>
                         <div className="text-sm font-bold text-zinc-800">
                           {delivery.address || "Endereço não informado"}, {delivery.number} <span className="text-zinc-400 font-normal text-[11px] ml-1">({delivery.name || "Sem nome"})</span>
                         </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Estimativa */}
                <div className="bg-zinc-50 border border-zinc-200/80 rounded-xl p-4">
                   <h3 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-4">Estimativa da Entrega</h3>
                   <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      
                      <div className="bg-white border border-zinc-200/80 rounded-xl p-4 flex flex-col items-center justify-center text-center">
                        <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-1">Valor</span>
                        <span className="text-lg font-black text-zinc-900">
                          {isEstimating ? <Loader2 className="w-5 h-5 animate-spin text-zinc-400 mx-auto" /> : formatCurrency(estimativa?.valor || deliveries.length * 9.00)}
                        </span>
                      </div>

                      <div className="bg-white border border-zinc-200/80 rounded-xl p-4 flex flex-col items-center justify-center text-center">
                        <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-1">Distância</span>
                        <span className="text-lg font-black text-indigo-600">
                          {isEstimating ? <Loader2 className="w-5 h-5 animate-spin text-indigo-400 mx-auto" /> : `${(estimativa?.distancia || deliveries.length * 5.0).toFixed(1).replace('.', ',')} km`}
                        </span>
                      </div>

                      <div className="bg-white border border-zinc-200/80 rounded-xl p-4 flex flex-col items-center justify-center text-center">
                        <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-1">Tempo Estimado</span>
                        <span className="text-lg font-black text-emerald-600">
                          {isEstimating ? <Loader2 className="w-5 h-5 animate-spin text-emerald-400 mx-auto" /> : `${Math.round(estimativa?.tempo || deliveries.length * 15)} min`}
                        </span>
                      </div>

                   </div>
                </div>

                {/* Categoria and PG */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  <div>
                    <h3 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-2">Categoria do Condutor</h3>
                    <div className="inline-flex">
                      <button className="px-4 py-2 border border-zinc-300 rounded-lg text-sm font-bold text-zinc-800 bg-white shadow-sm flex items-center gap-2">
                         {categoriaCondutor}
                      </button>
                    </div>
                  </div>
                  <div>
                    <h3 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-2">Forma de Pagamento</h3>
                    <div className="inline-flex">
                      <button className="px-4 py-2 border border-zinc-300 rounded-lg text-sm font-bold text-zinc-900 bg-zinc-50 shadow-sm flex items-center gap-2">
                         {formaPagamento}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Observação Geral */}
                <div>
                   <h3 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-2">Observação Geral</h3>
                   <textarea 
                     value={observacaoGeral}
                     onChange={e => setObservacaoGeral(e.target.value)}
                     placeholder="Instrução para o motoboy (opcional)"
                     className="w-full px-4 py-3 bg-white border border-zinc-200 rounded-xl text-sm focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 min-h-[80px] resize-none"
                   />
                </div>

             </div>
          )}

          {/* Footer Actions */}
          <div className="p-4 border-t border-zinc-200 bg-zinc-50 flex justify-end gap-3 shrink-0">
            {step === 1 ? (
              <>
                <button type="button" onClick={onClose} className="px-5 py-2.5 border border-zinc-200 bg-white text-zinc-700 rounded-xl hover:bg-zinc-50 text-sm font-bold transition-all">Cancelar</button>
                <button type="submit" form="step-1-form" disabled={isEstimating} className="px-6 py-2.5 bg-zinc-900 hover:bg-zinc-800 disabled:opacity-50 text-white rounded-xl text-sm font-bold shadow-sm transition-all flex items-center gap-2">
                  {isEstimating ? <Loader2 className="w-4 h-4 animate-spin" /> : <>Avançar <ChevronRight className="w-4 h-4" /></>}
                </button>
              </>
            ) : (
              <div className="flex w-full sm:w-auto gap-3">
                <button type="button" onClick={() => setStep(1)} disabled={isSubmitting} className="px-5 py-2.5 border border-zinc-200 bg-white text-zinc-700 rounded-xl hover:bg-zinc-50 text-sm font-bold transition-all">Voltar</button>
                <button type="button" onClick={handleSubmit} disabled={isSubmitting || isEstimating} className="flex-1 sm:flex-none px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-xl text-sm font-bold shadow-[0_0_15px_rgba(5,150,105,0.3)] transition-all flex items-center justify-center gap-2">
                  {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Check className="w-4 h-4" /> Solicitar Entrega</>}
                </button>
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
