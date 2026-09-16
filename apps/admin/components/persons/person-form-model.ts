import { z } from "zod";
import type { AdminPersonEditorDictionary } from "@/lib/i18n/types";

export const FEAST_RANK_VALUES = ["solemnity", "feast", "memorial", "opt_memorial", "commemoration"] as const;
export const LITURGICAL_COLOR_VALUES = ["white", "red", "green", "violet", "rose", "black", "gold"] as const;
const LITURGICAL_COLOR_FORM_VALUES = ["", ...LITURGICAL_COLOR_VALUES] as const;

export function optionalText(value?: string | null) {
  const normalized = value?.trim();
  return normalized ? normalized : null;
}

function isRealRecurringDate(month: number, day: number) {
  const value = new Date(Date.UTC(2000, month - 1, day));
  return value.getUTCMonth() === month - 1 && value.getUTCDate() === day;
}

export function normalizeAliasForComparison(value: string) {
  return value
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .replace(/[łŁ]/g, "l")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
}

export function createPersonSchema(copy: AdminPersonEditorDictionary["validation"]) {
  const optionalMediaUrl = z.string().optional().refine(
    (value) => !value || value.startsWith("/") || /^https?:\/\//i.test(value),
    copy.mediaUrl,
  );
  const optionalHttpUrl = z.string().optional().refine(
    (value) => !value || /^https?:\/\//i.test(value),
    copy.httpUrl,
  );

  return z.object({
  canonical_name: z.string().min(2, copy.canonicalNameMin),
  canonical_name_en: z.string().optional(),
  latin_name: z.string().optional(),
  person_type: z.enum(["saint", "blessed", "venerable", "servant_of_god", "candidate"]),
  status: z.enum(["draft", "review", "published", "archived"]),
  gender: z.enum(["male", "female", "unknown"]),
  era: z.string().optional(),
  birth_year: z.number().int().min(-5000).max(2100).optional().nullable(),
  death_year: z.number().int().min(-5000).max(2100).optional().nullable(),
  beatification_date: z.string().optional(),
  beatification_year: z.number().int().min(1).max(2100).optional().nullable(),
  canonization_date: z.string().optional(),
  canonization_year: z.number().int().min(1).max(2100).optional().nullable(),
  birth_country_id: z.string().optional().nullable(),
  death_country_id: z.string().optional().nullable(),
  state_of_life_id: z.string().optional().nullable(),
  summary_pl: z.string().optional(),
  biography_pl: z.string().optional(),
  prayers: z.string().optional(),
  iconographic_attributes: z.string().optional(),
  is_featured: z.boolean(),
  avatar_url: optionalMediaUrl,
  avatar_thumbnail_url: optionalMediaUrl,
  avatar_title: z.string().optional(),
  avatar_license: z.enum([
    "public_domain",
    "cc_by",
    "cc_by_sa",
    "cc_by_nc",
    "cc_by_nc_sa",
    "all_rights_reserved",
    "fair_use",
    "unknown",
  ]),
  avatar_photographer: z.string().optional(),
  avatar_source_url: optionalMediaUrl,
  feast_calendar_code: z.string().optional(),
  feast_month: z.number().int().min(1).max(12).optional().nullable(),
  feast_day: z.number().int().min(1).max(31).optional().nullable(),
  feast_rank: z.enum(FEAST_RANK_VALUES),
  feast_liturgical_color: z.enum(LITURGICAL_COLOR_FORM_VALUES).optional(),
  feast_is_primary: z.boolean(),
  feast_source_title: z.string().optional(),
  feast_source_url: optionalHttpUrl,
  feast_notes: z.string().optional(),
  aliases: z.array(z.object({
    value: z.string().trim().min(2, copy.aliasRequired)
      .refine((value) => normalizeAliasForComparison(value).length > 0, copy.aliasCharacters),
    language_code: z.string().trim()
      .min(2, copy.languageCodeRequired)
      .max(10, copy.languageCodeMax)
      .regex(/^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$/, copy.languageCodeFormat),
    kind: z.enum(["birth_name", "religious_name", "alias", "abbreviation", "transliteration"]),
  })),
  patronages: z.array(z.object({
    patronage_type: z.string().min(2, copy.patronageTypeRequired),
    name_pl: z.string().min(2, copy.patronageNameRequired),
    name_en: z.string().optional(),
    description: z.string().optional(),
    is_official: z.boolean(),
  })),
  change_summary: z.string().optional(),
}).superRefine((data, ctx) => {
  const aliasKeys = data.aliases.map((alias) => normalizeAliasForComparison(alias.value));
  if (new Set(aliasKeys).size !== aliasKeys.length) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: copy.duplicateAliases,
      path: ["aliases"],
    });
  }

  const hasMonth = data.feast_month !== null && data.feast_month !== undefined;
  const hasDay = data.feast_day !== null && data.feast_day !== undefined;

  if (hasMonth !== hasDay) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: copy.feastDateIncomplete,
      path: hasMonth ? ["feast_day"] : ["feast_month"],
    });
  }

  if (hasMonth && hasDay && !isRealRecurringDate(data.feast_month!, data.feast_day!)) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: copy.feastDateInvalid,
      path: ["feast_day"],
    });
  }

  if ((hasMonth || hasDay) && !optionalText(data.feast_calendar_code)) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: copy.feastCalendarRequired,
      path: ["feast_calendar_code"],
    });
  }
  });
}

export type PersonFormData = z.infer<ReturnType<typeof createPersonSchema>>;

export interface FeastEntryResponse {
  id: string;
  month?: number | null;
  day?: number | null;
  rank?: string | null;
  liturgical_color?: string | null;
  is_primary?: boolean;
  notes?: string | null;
  source_title?: string | null;
  source_url?: string | null;
  calendar?: {
    code?: string | null;
    name?: string | null;
  } | null;
}

const PERSON_FORM_ONLY_FIELDS = [
  "change_summary",
  "avatar_url",
  "avatar_thumbnail_url",
  "avatar_title",
  "avatar_license",
  "avatar_photographer",
  "avatar_source_url",
  "beatification_date",
  "beatification_year",
  "canonization_date",
  "canonization_year",
  "feast_calendar_code",
  "feast_month",
  "feast_day",
  "feast_rank",
  "feast_liturgical_color",
  "feast_is_primary",
  "feast_source_title",
  "feast_source_url",
  "feast_notes",
] as const satisfies readonly (keyof PersonFormData)[];

function normalizePatronages(patronages: PersonFormData["patronages"]) {
  return patronages
    .map((patronage) => ({
      patronage_type: patronage.patronage_type.trim(),
      name_pl: patronage.name_pl.trim(),
      name_en: optionalText(patronage.name_en),
      description: optionalText(patronage.description),
      is_official: patronage.is_official,
    }))
    .filter((patronage) => patronage.patronage_type && patronage.name_pl);
}

function normalizeAliases(aliases: PersonFormData["aliases"]) {
  return aliases.map((alias) => ({
    value: alias.value.trim(),
    language_code: alias.language_code.trim().toLowerCase(),
    kind: alias.kind,
  }));
}

export function normalizePersonPayload(data: PersonFormData, isEdit: boolean) {
  const optionalId = (value?: string | null) => value || null;
  const personFields: Partial<PersonFormData> = { ...data };
  for (const field of PERSON_FORM_ONLY_FIELDS) {
    delete personFields[field];
  }

  const normalizedAvatarUrl = optionalText(data.avatar_url);
  const beatification = {
    beatification_date: optionalText(data.beatification_date),
    beatification_year: Number.isFinite(data.beatification_year) ? data.beatification_year : null,
  };
  const canonization = {
    canonization_date: optionalText(data.canonization_date),
    canonization_year: Number.isFinite(data.canonization_year) ? data.canonization_year : null,
  };

  return {
    ...personFields,
    canonical_name: data.canonical_name.trim(),
    canonical_name_en: optionalText(data.canonical_name_en),
    latin_name: optionalText(data.latin_name),
    era: data.era || null,
    birth_year: Number.isFinite(data.birth_year) ? data.birth_year : null,
    death_year: Number.isFinite(data.death_year) ? data.death_year : null,
    birth_country_id: optionalId(data.birth_country_id),
    death_country_id: optionalId(data.death_country_id),
    state_of_life_id: optionalId(data.state_of_life_id),
    summary_pl: optionalText(data.summary_pl),
    biography_pl: optionalText(data.biography_pl),
    prayers: optionalText(data.prayers),
    iconographic_attributes: optionalText(data.iconographic_attributes),
    aliases: normalizeAliases(data.aliases),
    patronages: normalizePatronages(data.patronages),
    avatar: normalizedAvatarUrl
      ? {
          url: normalizedAvatarUrl,
          thumbnail_url: optionalText(data.avatar_thumbnail_url),
          title: optionalText(data.avatar_title),
          license: data.avatar_license,
          photographer: optionalText(data.avatar_photographer),
          source_url: optionalText(data.avatar_source_url),
        }
      : null,
    beatification: Object.values(beatification).some(Boolean) ? beatification : null,
    canonization: Object.values(canonization).some(Boolean) ? canonization : null,
    ...(isEdit ? { change_summary: optionalText(data.change_summary) } : {}),
  };
}

export function buildFeastPayload(personId: string, data: PersonFormData, includeTarget: boolean) {
  if (data.feast_month === null || data.feast_month === undefined || data.feast_day === null || data.feast_day === undefined) {
    return null;
  }

  return {
    ...(includeTarget ? { person_id: personId } : {}),
    calendar_code: optionalText(data.feast_calendar_code) ?? "roman_pl",
    month: data.feast_month,
    day: data.feast_day,
    rank: data.feast_rank,
    liturgical_color: data.feast_liturgical_color || null,
    is_primary: data.feast_is_primary,
    source_title: optionalText(data.feast_source_title),
    source_url: optionalText(data.feast_source_url),
    notes: optionalText(data.feast_notes),
  };
}
