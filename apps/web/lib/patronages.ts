import type { PersonTypeKey } from "@/lib/i18n/types";

export interface PatronageConcept {
  slug: string;
  patronage_type: string;
  name_pl: string;
  name_en: string | null;
  description: string | null;
  person_count: number;
}

export interface PatronageConceptPerson {
  id: string;
  slug: string;
  canonical_name: string;
  canonical_name_en: string | null;
  person_type: PersonTypeKey;
  summary_pl: string | null;
}

export interface PatronageConceptPersonsResponse {
  concept: PatronageConcept;
  items: PatronageConceptPerson[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

/** Keep links aligned with the backend's type-qualified slug projection. */
export function patronageConceptSlug(type: string, name: string): string {
  return `${type}-${name}`
    .replace(/[łŁ]/g, "l")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}
