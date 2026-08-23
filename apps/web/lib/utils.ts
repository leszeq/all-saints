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
  candidate: "Kandydat/ka (status redakcyjny)",
};

export const PERSON_TYPE_DESCRIPTIONS: Record<string, string> = {
  saint: "Osoby kanonizowane",
  blessed: "Osoby beatyfikowane",
  venerable: "Osoby, których heroiczność cnót została uznana",
  servant_of_god: "Osoby z formalnie rozpoczętym procesem beatyfikacyjnym",
  candidate: "Wewnętrzna lista kandydatów przed formalnym rozpoczęciem procesu",
};

export const ERA_LABELS: Record<string, string> = {
  apostolic: "Epoka apostolska (I w.)",
  early_church: "Wczesny Kościół (II–V w.)",
  late_antiquity: "Późna starożytność (V–VII w.)",
  medieval: "Średniowiecze",
  early_modern: "Nowożytność (XVI–XVIII w.)",
  modern: "Epoka nowoczesna (XIX–XX w.)",
  contemporary: "Współczesność (XXI w.)",
  unknown: "Nieznana",
};

export const TIME_PERIODS = {
  early_witnesses: {
    range: "I–V wiek",
    title: "Pierwsi świadkowie",
  },
  medieval: {
    range: "VI–XV wiek",
    title: "Klasztory i średniowiecze",
  },
  renewal: {
    range: "XVI–XVIII wiek",
    title: "Odnowa i misje",
  },
  modern: {
    range: "XIX–XXI wiek",
    title: "Święci bliscy naszym czasom",
  },
} as const;

export const LEGACY_ERA_PERIODS: Record<string, keyof typeof TIME_PERIODS> = {
  "Starożytność": "early_witnesses",
  "Średniowiecze": "medieval",
  "Nowożytność": "renewal",
  "Współczesność": "modern",
};

export const PATRONAGE_GROUPS = {
  health: {
    title: "W chorobie",
    detail: "Patroni chorych, lekarzy i opiekunów",
  },
  family: {
    title: "W rodzinie",
    detail: "Orędownicy małżeństw, dzieci i rodziców",
  },
  work: {
    title: "W pracy",
    detail: "Patroni zawodów i codziennych obowiązków",
  },
  travel: {
    title: "W drodze",
    detail: "Patroni podróżnych, kierowców i pielgrzymów",
  },
} as const;

export const LEGACY_SEARCH_PATRONAGES: Record<string, keyof typeof PATRONAGE_GROUPS> = {
  chorzy: "health",
  rodzina: "family",
  praca: "work",
  "podróżni": "travel",
};
