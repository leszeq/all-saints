import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { format, parseISO } from "date-fns";
import { pl } from "date-fns/locale";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDatePL(dateStr?: string | null): string {
  if (!dateStr) return "—";
  try {
    const d = parseISO(dateStr);
    return format(d, "d MMMM yyyy", { locale: pl });
  } catch {
    return dateStr;
  }
}

export const PERSON_TYPE_LABELS: Record<string, string> = {
  saint: "Święty/a",
  blessed: "Błogosławiony/a",
  venerable: "Czcigodny/a",
  servant_of_god: "Sługa Boży/a",
  candidate: "Kandydat/ka na ołtarze",
};
