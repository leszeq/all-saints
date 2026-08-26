import type { SaintAvatarData } from "@/components/saint-avatar";

export interface CalendarPatronage {
  id: string;
  patronage_type: string;
  name_pl: string;
  name_en?: string | null;
  description?: string | null;
  is_official: boolean;
}

export interface CalendarPerson {
  id: string;
  slug: string;
  canonical_name: string;
  person_type: string;
  gender: string;
  birth_year?: number | null;
  death_year?: number | null;
  summary_pl?: string | null;
  is_featured: boolean;
  avatar?: SaintAvatarData | null;
  patronages: CalendarPatronage[];
}

export interface LiturgicalCalendarInfo {
  id: string;
  code: string;
  name: string;
  rite: string;
  scope: string;
  description?: string | null;
  is_active: boolean;
}

export interface CalendarEntry {
  id: string;
  month?: number | null;
  day?: number | null;
  date_note?: string | null;
  is_moveable: boolean;
  rank: string;
  liturgical_color?: string | null;
  is_primary: boolean;
  notes?: string | null;
  source_title?: string | null;
  source_url?: string | null;
  person: CalendarPerson;
  calendar: LiturgicalCalendarInfo;
  created_at: string;
  updated_at: string;
}

export interface CalendarDay {
  date: string;
  calendar_code: string;
  calendar_name: string;
  includes_universal: boolean;
  includes_martyrology: boolean;
  primary: CalendarEntry | null;
  entries: CalendarEntry[];
  total: number;
}

export interface CalendarMonth {
  year: number;
  month: number;
  calendar_code: string;
  calendar_name: string;
  includes_universal: boolean;
  includes_martyrology: boolean;
  days: CalendarDay[];
}

export const FEAST_RANK_LABELS: Record<string, string> = {
  solemnity: "Uroczystość",
  feast: "Święto",
  memorial: "Wspomnienie obowiązkowe",
  opt_memorial: "Wspomnienie dowolne",
  commemoration: "Wspomnienie",
};

export const FEAST_RANK_SHORT_LABELS: Record<string, string> = {
  solemnity: "Uroczystość",
  feast: "Święto",
  memorial: "Wspomnienie",
  opt_memorial: "Dowolne",
  commemoration: "Wspomnienie",
};

export function formatCalendarPersonCount(count: number): string {
  if (count === 1) return "1 postać";
  const lastTwoDigits = count % 100;
  const lastDigit = count % 10;
  if (lastDigit >= 2 && lastDigit <= 4 && !(lastTwoDigits >= 12 && lastTwoDigits <= 14)) {
    return `${count} postacie`;
  }
  return `${count} postaci`;
}

export function formatCalendarDate(value: string, options?: Intl.DateTimeFormatOptions) {
  const [year, month, day] = value.split("-").map(Number);
  return new Intl.DateTimeFormat("pl-PL", {
    timeZone: "UTC",
    day: "numeric",
    month: "long",
    year: "numeric",
    ...options,
  }).format(new Date(Date.UTC(year, month - 1, day)));
}

export function currentWarsawMonth(): string {
  const parts = new Intl.DateTimeFormat("en", {
    timeZone: "Europe/Warsaw",
    year: "numeric",
    month: "2-digit",
  }).formatToParts(new Date());
  const year = parts.find((part) => part.type === "year")?.value;
  const month = parts.find((part) => part.type === "month")?.value;
  return `${year}-${month}`;
}

export function currentWarsawDate(): string {
  const parts = new Intl.DateTimeFormat("en", {
    timeZone: "Europe/Warsaw",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const part = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((item) => item.type === type)?.value;
  return `${part("year")}-${part("month")}-${part("day")}`;
}

export function parseMonthKey(value?: string): { year: number; month: number } | null {
  const match = /^(\d{4})-(\d{2})$/.exec(value ?? "");
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  if (year < 1900 || year > 2200 || month < 1 || month > 12) return null;
  return { year, month };
}

export function shiftMonth(year: number, month: number, offset: number): string {
  const shifted = new Date(Date.UTC(year, month - 1 + offset, 1));
  return `${shifted.getUTCFullYear()}-${String(shifted.getUTCMonth() + 1).padStart(2, "0")}`;
}

export function shiftDate(value: string, offset: number): string {
  const [year, month, day] = value.split("-").map(Number);
  const shifted = new Date(Date.UTC(year, month - 1, day + offset));
  return [
    shifted.getUTCFullYear(),
    String(shifted.getUTCMonth() + 1).padStart(2, "0"),
    String(shifted.getUTCDate()).padStart(2, "0"),
  ].join("-");
}

export function isValidCalendarDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split("-").map(Number);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return (
    parsed.getUTCFullYear() === year &&
    parsed.getUTCMonth() === month - 1 &&
    parsed.getUTCDate() === day
  );
}
