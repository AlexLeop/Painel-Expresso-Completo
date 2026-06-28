export interface DailySummary {
  motoboyId: string;
  date: string;
  isWeekend: boolean;

  // Inputs operacionais
  totalRides: number;
  ridesValue: number; // Produção real (fare_value das corridas 'F')

  // Parâmetros do motoboy/empresa
  dailyRate: number; // Diária configurada
  rideFee: number; // Taxa por entrega (ex: R$ 1,00)

  // Lançamentos manuais
  extras: number;
  advances: number; // Adiantamentos
}

export interface DailyCalculationResult {
  productionMode: {
    baseRate: number; // Diária
    excess: number; // Excedente (Produção - Diária, min 0)
    ridesFeeTotal: number; // (totalRides * rideFee)
    extras: number;
    advances: number;
    finalValue: number;
  };
  guaranteeMode: {
    guarantee: number; // max(Produção Real + Extras, Diária)
    ridesFeeTotal: number;
    advances: number;
    finalValue: number;
  };
}

export function calculateDay(summary: DailySummary): DailyCalculationResult {
  const { totalRides, ridesValue, dailyRate, rideFee, extras, advances } =
    summary;

  const ridesFeeTotal = totalRides * rideFee;
  const production = ridesValue;

  // --- Modo Produção Padrão ---
  // Total = Diária + Produção + Taxa Corridas + Extras - Adiantamentos
  const productionFinalValue =
    dailyRate + production + ridesFeeTotal + extras - advances;

  // --- Modo Garantida Mínima ---
  // Total = max(Produção, Diária) + Taxa Corridas + Extras - Adiantamentos
  const guarantee = Math.max(production, dailyRate);
  const guaranteeFinalValue = guarantee + ridesFeeTotal + extras - advances;

  return {
    productionMode: {
      baseRate: dailyRate,
      excess: production, // No modo produção padrão, o 'excedente' é a produção inteira
      ridesFeeTotal,
      extras,
      advances,
      finalValue: productionFinalValue,
    },
    guaranteeMode: {
      guarantee,
      ridesFeeTotal,
      advances,
      finalValue: guaranteeFinalValue,
    },
  };
}

export interface WeeklyCompanySummary {
  companyId: string;
  totalRidesFee: number;
  minimumRidesFeeFloor: number; // Piso de taxas da empresa
}

export function calculateCompanyFloor(summary: WeeklyCompanySummary): number {
  const { totalRidesFee, minimumRidesFeeFloor } = summary;

  // Complemento de piso
  if (totalRidesFee < minimumRidesFeeFloor) {
    return minimumRidesFeeFloor - totalRidesFee;
  }

  return 0;
}
