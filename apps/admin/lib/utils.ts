import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { format, parseISO } from "date-fns";
import { pl } from "date-fns/locale";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date | null | undefined): string {
  if (!date) return "—";
  try {
    const d = typeof date === "string" ? parseISO(date) : date;
    return format(d, "d MMMM yyyy", { locale: pl });
  } catch {
    return String(date);
  }
}

export function formatDateTime(date: string | Date | null | undefined): string {
  if (!date) return "—";
  try {
    const d = typeof date === "string" ? parseISO(date) : date;
    return format(d, "d MMM yyyy, HH:mm", { locale: pl });
  } catch {
    return String(date);
  }
}

export const PERSON_TYPE_LABELS: Record<string, string> = {
  saint: "Święty/a",
  blessed: "Błogosławiony/a",
  venerable: "Czcigodny/a",
  servant_of_god: "Sługa Boży/a",
  candidate: "Kandydat/ka (status redakcyjny)",
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

export const PERSON_STATUS_LABELS: Record<string, string> = {
  draft: "Szkic",
  review: "W recenzji",
  published: "Opublikowany",
  archived: "Zarchiwizowany",
};

export const PERSON_STATUS_COLORS: Record<string, string> = {
  draft: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  review: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  published: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  archived: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400",
};

export const GENDER_LABELS: Record<string, string> = {
  male: "Mężczyzna",
  female: "Kobieta",
  unknown: "Nieznana",
};

export const PERSON_TYPE_COLORS: Record<string, string> = {
  saint: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400",
  blessed: "bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-400",
  venerable: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  servant_of_god: "bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-400",
  candidate: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400",
};

export const SOURCE_TYPE_LABELS: Record<string, string> = {
  book: "Książka",
  article: "Artykuł",
  encyclopedia: "Encyklopedia",
  website: "Strona WWW",
  manuscript: "Rękopis",
  archive: "Archiwum",
  document: "Dokument",
  hagiography: "Hagiografia",
  vita: "Żywot",
  other: "Inne",
};

export const IMAGE_LICENSE_LABELS: Record<string, string> = {
  public_domain: "Domena publiczna",
  cc_by: "CC BY",
  cc_by_sa: "CC BY-SA",
  cc_by_nc: "CC BY-NC",
  cc_by_nc_sa: "CC BY-NC-SA",
  all_rights_reserved: "Wszelkie prawa zastrzeżone",
  fair_use: "Dozwolony użytek",
  unknown: "Nieznana",
};

export const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  decree: "Dekret",
  bull: "Bulla",
  encyclical: "Encyklika",
  biography: "Biografia",
  letter: "List",
  vita: "Żywot",
  process: "Akta procesu",
  other: "Inny",
};

export const CHURCH_TYPE_LABELS: Record<string, string> = {
  parish: "Parafia",
  cathedral: "Katedra",
  basilica: "Bazylika",
  chapel: "Kaplica",
  monastery: "Klasztor",
  sanctuary: "Sanktuarium",
  shrine: "Miejsce kultu",
  pilgrimage_site: "Miejsce pielgrzymkowe",
  other: "Inne",
};

export const ORDER_CHARISM_LABELS: Record<string, string> = {
  contemplative: "Kontemplacyjny",
  apostolic: "Apostolski",
  mendicant: "Żebraczy",
  monastic: "Monastyczny",
  missionary: "Misyjny",
  educational: "Edukacyjny",
  charitable: "Charytatywny",
  military: "Rycerski",
  other: "Inny",
};

export const COMMUNITY_TYPE_LABELS: Record<string, string> = {
  religious_order: "Zakon",
  congregation: "Zgromadzenie",
  monastic_family: "Rodzina monastyczna",
  society_apostolic_life: "Stowarzyszenie życia apostolskiego",
  secular_institute: "Instytut świecki",
  federation: "Federacja",
  other: "Inne",
};
