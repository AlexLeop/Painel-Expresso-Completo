import React, { useState } from "react";
import {
  Calculator,
  CheckCircle2,
  AlertCircle,
  Banknote,
  CreditCard,
  Receipt,
  ArrowRightLeft,
} from "lucide-react";
import { formatCurrency, cn } from "../lib/utils";

import { useApiQuery } from "../lib/useApiQuery";

export default function AcertoInLoco() {
  const { data: driversData, isLoading } = useApiQuery<any>(
    "/api/operator/drivers",
  );
  const rawDrivers = driversData?.items || driversData;
  const driversList = Array.isArray(rawDrivers) ? rawDrivers : [];

  const [selectedDriver, setSelectedDriver] = useState<string | null>(null);
  const [acertados, setAcertados] = useState<Set<string>>(new Set());

  // Auto-select first driver if none selected
  React.useEffect(() => {
    if (driversList.length > 0 && !selectedDriver) {
      setSelectedDriver(driversList[0].id);
    }
  }, [driversList, selectedDriver]);

  const driver = driversList.find((d: any) => d.id === selectedDriver);

  const marcarAcerto = () => {
    if (driver) {
      const next = new Set(acertados);
      next.add(driver.id);
      setAcertados(next);
    }
  };

  if (!driver) return null;

  const totalTaxas = driver.totalTaxas || 0;
  const dinheiroRecebido = driver.dinheiroRecebido || 0;
  const saldoFinal = totalTaxas - dinheiroRecebido;
  const isLojaPaga = saldoFinal >= 0;
  const isAcertado = acertados.has(driver.id);

  return (
    <div className="flex flex-col md:flex-row gap-6">
      {/* Lista de Motoboys */}
      <div className="w-full md:w-1/3 bg-white rounded-xl shadow-sm ring-1 ring-zinc-950/5 overflow-hidden flex flex-col">
        <div className="p-4 border-b border-zinc-100 bg-zinc-50/50">
          <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider">
            Motoboys em Turno
          </h3>
        </div>
        <div className="divide-y divide-zinc-100 flex-1 overflow-y-auto max-h-[500px]">
          {isLoading ? (
            <div className="p-4 text-center text-sm text-zinc-500">
              Carregando motoboys...
            </div>
          ) : driversList.length === 0 ? (
            <div className="p-4 text-center text-sm text-zinc-500">
              Nenhum motoboy ativo.
            </div>
          ) : (
            driversList.map((d: any) => {
              const isSelected = selectedDriver === d.id;
              const hasAcertado = acertados.has(d.id);
              const entregas = d.entregas || 0;
              return (
                <button
                  key={d.id}
                  onClick={() => setSelectedDriver(d.id)}
                  className={cn(
                    "w-full text-left p-4 transition-all hover:bg-zinc-50 flex items-center justify-between",
                    isSelected
                      ? "bg-zinc-50 border-l-4 border-zinc-900"
                      : "border-l-4 border-transparent",
                  )}
                >
                  <div>
                    <div className="text-sm font-bold text-zinc-900">
                      {d.name}
                    </div>
                    <div className="text-xs text-zinc-500 mt-0.5">
                      {entregas} entregas hoje
                    </div>
                  </div>
                  {hasAcertado && (
                    <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  )}
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* Detalhes do Acerto */}
      <div className="flex-1 bg-white rounded-xl shadow-sm ring-1 ring-zinc-950/5 p-6 relative overflow-hidden">
        {isAcertado && (
          <div className="absolute top-4 right-4 bg-emerald-100 text-emerald-700 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-widest flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4" />
            Turno Fechado
          </div>
        )}

        <h2 className="text-xl font-bold text-zinc-900">{driver.name}</h2>
        <p className="text-sm text-zinc-500 mt-1">
          Fechamento de turno e acerto de caixa.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-8">
          <div className="p-5 rounded-xl border border-zinc-200 bg-zinc-50/50 flex flex-col justify-center">
            <div className="flex items-center gap-2 mb-2 text-zinc-500">
              <Receipt className="w-5 h-5" />
              <span className="text-xs font-bold uppercase tracking-wider">
                Taxas Devidas ao Motoboy
              </span>
            </div>
            <div className="text-3xl font-black text-zinc-900">
              {formatCurrency(totalTaxas)}
            </div>
            <div className="text-xs text-zinc-500 mt-2">
              Ganhos de entregas no dia
            </div>
          </div>

          <div className="p-5 rounded-xl border border-rose-100 bg-rose-50/30 flex flex-col justify-center">
            <div className="flex items-center gap-2 mb-2 text-rose-600">
              <Banknote className="w-5 h-5" />
              <span className="text-xs font-bold uppercase tracking-wider">
                Dinheiro em Mãos
              </span>
            </div>
            <div className="text-3xl font-black text-rose-600">
              {formatCurrency(dinheiroRecebido)}
            </div>
            <div className="text-xs text-rose-500 mt-2">
              Valor recebido em espécie dos clientes
            </div>
          </div>
        </div>

        <div className="mt-8 pt-8 border-t border-zinc-100">
          <div className="flex flex-col items-center justify-center p-8 rounded-2xl border-2 border-dashed border-zinc-200 bg-zinc-50/30">
            <h3 className="text-sm font-bold text-zinc-500 uppercase tracking-widest mb-4">
              Resultado do Acerto
            </h3>

            <div
              className={cn(
                "text-5xl font-black tracking-tight",
                isLojaPaga ? "text-emerald-600" : "text-amber-600",
              )}
            >
              {formatCurrency(Math.abs(saldoFinal))}
            </div>

            <div className="flex items-center gap-2 mt-4">
              <ArrowRightLeft
                className={cn(
                  "w-5 h-5",
                  isLojaPaga ? "text-emerald-500" : "text-amber-500",
                )}
              />
              <span className="text-sm font-bold text-zinc-700">
                {isLojaPaga
                  ? "Loja paga o motoboy via Pix/Dinheiro"
                  : "Motoboy devolve o troco para o caixa da Loja"}
              </span>
            </div>
          </div>
        </div>

        {!isAcertado && (
          <div className="mt-8 flex justify-end">
            <button
              onClick={marcarAcerto}
              className="bg-zinc-900 hover:bg-zinc-800 text-white px-8 py-3 rounded-xl font-bold uppercase tracking-wider text-sm transition-all shadow-md hover:shadow-lg flex items-center gap-2"
            >
              <CheckCircle2 className="w-5 h-5" />
              Confirmar Acerto de Caixa
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
