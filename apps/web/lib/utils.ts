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
