export type PatronageConceptStatus = "draft" | "review" | "approved" | "rejected";
export type ConceptAliasKind = "official" | "common" | "historical" | "local";

export interface ConceptAlias {
  id: string;
  concept_id: string;
  value: string;
  normalized_value: string;
  language_code: string;
  alias_kind: ConceptAliasKind;
  source_reference: string | null;
  created_at: string;
  updated_at: string;
}

export interface PatronageConcept {
  id: string;
  slug: string;
  patronage_type: string;
  name_pl: string;
  name_en: string | null;
  description: string | null;
  status: PatronageConceptStatus;
  reviewed_by_id: string | null;
  reviewed_at: string | null;
  review_note: string | null;
  aliases: ConceptAlias[];
  assignment_count: number;
  person_count: number;
}

export interface PatronageConceptPayload {
  patronage_type: string;
  name_pl: string;
  name_en?: string | null;
  description?: string | null;
}

export interface ConceptAliasPayload {
  value: string;
  language_code: string;
  alias_kind: ConceptAliasKind;
  source_reference?: string | null;
}

export interface PatronageConceptReviewPayload {
  target_status: PatronageConceptStatus;
  note?: string | null;
}
