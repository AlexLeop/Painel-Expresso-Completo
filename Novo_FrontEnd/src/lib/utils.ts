import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: number) {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL'
  }).format(value);
}

export function toLocalDateISO(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

export function getEasterDate(year: number): Date {
  const a = year % 19;
  const b = Math.floor(year / 100);
  const c = year % 100;
  const d = Math.floor(b / 4);
  const e = b % 4;
  const f = Math.floor((b + 8) / 25);
  const g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4);
  const k = c % 4;
  const L = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 22 * L) / 451);
  const month = Math.floor((h + L - 7 * m + 114) / 31); // 3 = Março, 4 = Abril
  const day = ((h + L - 7 * m + 114) % 31) + 1;
  return new Date(year, month - 1, day, 12, 0, 0);
}

export function getBrazilianHolidaysMap(year: number): Map<string, string> {
  const holidays = new Map<string, string>();
  holidays.set(`${year}-01-01`, "Confraternização Universal (Ano Novo)");
  holidays.set(`${year}-04-21`, "Tiradentes");
  holidays.set(`${year}-05-01`, "Dia do Trabalho");
  holidays.set(`${year}-09-07`, "Independência do Brasil");
  holidays.set(`${year}-10-12`, "Nossa Senhora Aparecida");
  holidays.set(`${year}-11-02`, "Finados");
  holidays.set(`${year}-11-15`, "Proclamação da República");
  holidays.set(`${year}-11-20`, "Dia da Consciência Negra");
  holidays.set(`${year}-12-25`, "Natal");

  const easter = getEasterDate(year);
  
  const goodFriday = new Date(easter);
  goodFriday.setDate(easter.getDate() - 2);
  holidays.set(toLocalDateISO(goodFriday), "Sexta-feira Santa");

  const carnival = new Date(easter);
  carnival.setDate(easter.getDate() - 47);
  holidays.set(toLocalDateISO(carnival), "Terça de Carnaval");

  const corpusChristi = new Date(easter);
  corpusChristi.setDate(easter.getDate() + 60);
  holidays.set(toLocalDateISO(corpusChristi), "Corpus Christi");

  return holidays;
}

export function isBrazilianHoliday(dateInput: string | Date): boolean {
  let dateStr = "";
  let year = new Date().getFullYear();

  if (dateInput instanceof Date) {
    dateStr = toLocalDateISO(dateInput);
    year = dateInput.getFullYear();
  } else {
    dateStr = dateInput.substring(0, 10);
    year = parseInt(dateStr.split("-")[0], 10);
  }

  if (isNaN(year)) return false;
  const holidays = getBrazilianHolidaysMap(year);
  return holidays.has(dateStr);
}

export function getBrazilianHolidayName(dateInput: string | Date): string | null {
  let dateStr = "";
  let year = new Date().getFullYear();

  if (dateInput instanceof Date) {
    dateStr = toLocalDateISO(dateInput);
    year = dateInput.getFullYear();
  } else {
    dateStr = dateInput.substring(0, 10);
    year = parseInt(dateStr.split("-")[0], 10);
  }

  if (isNaN(year)) return null;
  const holidays = getBrazilianHolidaysMap(year);
  return holidays.get(dateStr) || null;
}

