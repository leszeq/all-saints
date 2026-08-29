"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useFieldArray, useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowLeft, BookOpenText, CalendarDays, FileImage, HeartHandshake, ImagePlus, Info, Loader2, Plus, Save, Trash2, Upload, X } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { calendarApi, getApiErrorMessage, personsApi, geographyApi, sourcesApi, taxonomyApi } from "@/lib/api";
import { cn, ERA_LABELS, FEAST_RANK_LABELS, LITURGICAL_COLOR_LABELS } from "@/lib/utils";
import { SaintAvatar } from "@/components/persons/saint-avatar";
import { PersonSourcesEditor } from "@/components/persons/person-sources-editor";

const FEAST_RANK_VALUES = ["solemnity", "feast", "memorial", "opt_memorial", "commemoration"] as const;
const LITURGICAL_COLOR_VALUES = ["white", "red", "green", "violet", "rose", "black", "gold"] as const;
const LITURGICAL_COLOR_FORM_VALUES = ["", ...LITURGICAL_COLOR_VALUES] as const;

const PATRONAGE_TYPE_OPTIONS = [
  { value: "illness", label: "Choroba / dolegliwość" },
  { value: "healthcare", label: "Chorzy, lekarze i opiekunowie" },
  { value: "family", label: "Rodzina, małżeństwo, dzieci" },
  { value: "profession", label: "Zawód / profesja" },
  { value: "work", label: "Praca i codzienne obowiązki" },
  { value: "travel", label: "Podróżni i pielgrzymi" },
  { value: "country", label: "Kraj" },
  { value: "city", label: "Miasto" },
  { value: "diocese", label: "Diecezja / wspólnota lokalna" },
  { value: "group", label: "Grupa osób" },
  { value: "cause", label: "Sprawa / intencja" },
  { value: "other", label: "Inne" },
] as const;

const MONTH_OPTIONS = [
  [1, "Styczeń"],
  [2, "Luty"],
  [3, "Marzec"],
  [4, "Kwiecień"],
  [5, "Maj"],
  [6, "Czerwiec"],
  [7, "Lipiec"],
  [8, "Sierpień"],
  [9, "Wrzesień"],
  [10, "Październik"],
  [11, "Listopad"],
  [12, "Grudzień"],
] as const;

const optionalMediaUrl = z.string().optional().refine(
  (value) => !value || value.startsWith("/") || /^https?:\/\//i.test(value),
  "Podaj adres HTTP(S) lub ścieżkę zaczynającą się od /",
);

const optionalHttpUrl = z.string().optional().refine(
  (value) => !value || /^https?:\/\//i.test(value),
  "Podaj pełny adres HTTP(S)",
);

function optionalText(value?: string | null) {
  const normalized = value?.trim();
  return normalized ? normalized : null;
}

function isRealRecurringDate(month: number, day: number) {
  const value = new Date(Date.UTC(2000, month - 1, day));
  return value.getUTCMonth() === month - 1 && value.getUTCDate() === day;
}

const personSchema = z.object({
  canonical_name: z.string().min(2, "Minimum 2 znaki"),
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
  patronages: z.array(z.object({
    patronage_type: z.string().min(2, "Wybierz typ patronatu"),
    name_pl: z.string().min(2, "Podaj, komu lub czemu patronuje dana osoba"),
    name_en: z.string().optional(),
    description: z.string().optional(),
    is_official: z.boolean(),
  })),
  change_summary: z.string().optional(),
}).superRefine((data, ctx) => {
  const hasMonth = data.feast_month !== null && data.feast_month !== undefined;
  const hasDay = data.feast_day !== null && data.feast_day !== undefined;

  if (hasMonth !== hasDay) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: "Uzupełnij miesiąc i dzień wspomnienia albo pozostaw oba pola puste.",
      path: hasMonth ? ["feast_day"] : ["feast_month"],
    });
  }

  if (hasMonth && hasDay && !isRealRecurringDate(data.feast_month!, data.feast_day!)) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: "Podana data wspomnienia nie istnieje w kalendarzu.",
      path: ["feast_day"],
    });
  }

  if ((hasMonth || hasDay) && !optionalText(data.feast_calendar_code)) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: "Wybierz kalendarz liturgiczny.",
      path: ["feast_calendar_code"],
    });
  }
});

type PersonFormData = z.infer<typeof personSchema>;

interface FeastEntryResponse {
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

function normalizePersonPayload(data: PersonFormData, isEdit: boolean) {
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

async function preparePersonPayload(
  data: PersonFormData,
  isEdit: boolean,
  avatarFile: File | null,
) {
  const payload = normalizePersonPayload(data, isEdit);
  if (!avatarFile) return payload;

  const upload = await sourcesApi.uploadAvatar(avatarFile);
  return {
    ...payload,
    avatar: {
      url: upload.data.url,
      thumbnail_url: upload.data.thumbnail_url,
      title: optionalText(data.avatar_title),
      license: data.avatar_license,
      photographer: optionalText(data.avatar_photographer),
      source_url: optionalText(data.avatar_source_url),
      storage_key: upload.data.storage_key,
      width_px: upload.data.width_px,
      height_px: upload.data.height_px,
      file_size_bytes: upload.data.file_size_bytes,
      mime_type: upload.data.mime_type,
    },
  };
}

function buildFeastPayload(personId: string, data: PersonFormData, includeTarget: boolean) {
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

async function syncPersonFeast(
  personId: string,
  data: PersonFormData,
  existingEntryId: string | null,
) {
  const createPayload = buildFeastPayload(personId, data, true);
  if (createPayload) {
    if (existingEntryId) {
      const updatePayload = buildFeastPayload(personId, data, false);
      return calendarApi.updateEntry(existingEntryId, updatePayload);
    }
    return calendarApi.createEntry(createPayload);
  }

  if (existingEntryId) {
    return calendarApi.deleteEntry(existingEntryId);
  }

  return null;
}

const TABS = [
  { id: "basic", label: "Dane podstawowe" },
  { id: "dates", label: "Daty i miejsca" },
  { id: "biography", label: "Biografia" },
  { id: "patronages", label: "Patronaty" },
  { id: "devotion", label: "Kult i ikonografia" },
  { id: "sources", label: "Źródła" },
  { id: "avatar", label: "Avatar" },
];

interface PersonFormProps {
  personId?: string;
  defaultValues?: Partial<PersonFormData>;
  isEdit?: boolean;
  expectedVersion?: number;
}

export function PersonForm({ personId, defaultValues, isEdit, expectedVersion }: PersonFormProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("basic");
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [avatarFileError, setAvatarFileError] = useState<string | null>(null);
  const hydratedFeastPersonIdRef = useRef<string | null>(null);

  const countriesQuery = useQuery({
    queryKey: ["countries"],
    queryFn: () => geographyApi.countries(),
    staleTime: Infinity,
  });
  const statesQuery = useQuery({
    queryKey: ["states-of-life"],
    queryFn: () => taxonomyApi.statesOfLife(),
    staleTime: Infinity,
  });
  const calendarsQuery = useQuery({
    queryKey: ["liturgical-calendars"],
    queryFn: () => calendarApi.calendars(),
    staleTime: Infinity,
  });
  const feastEntriesQuery = useQuery({
    queryKey: ["calendar", "person-feasts", personId],
    queryFn: () => calendarApi.personEntries(personId!),
    enabled: Boolean(isEdit && personId),
  });

  const countries = countriesQuery.data?.data ?? [];
  const statesOfLife = statesQuery.data?.data ?? [];
  const calendars = calendarsQuery.data?.data ?? [];
  const feastEntries = useMemo(
    () => (feastEntriesQuery.data?.data ?? []) as FeastEntryResponse[],
    [feastEntriesQuery.data?.data],
  );
  const activeFeastEntry = useMemo(
    () =>
      feastEntries.find((entry) => entry.calendar?.code === "roman_pl") ??
      feastEntries.find((entry) => entry.is_primary) ??
      feastEntries[0] ??
      null,
    [feastEntries],
  );

  const {
    register,
    handleSubmit,
    control,
    setValue,
    formState: { errors, isDirty },
  } = useForm<PersonFormData>({
    resolver: zodResolver(personSchema),
    defaultValues: {
      person_type: "saint",
      status: "draft",
      gender: "unknown",
      is_featured: false,
      avatar_license: "unknown",
      feast_calendar_code: "roman_pl",
      feast_month: null,
      feast_day: null,
      feast_rank: "memorial",
      feast_liturgical_color: "",
      feast_is_primary: false,
      feast_source_title: "",
      feast_source_url: "",
      feast_notes: "",
      patronages: [],
      ...defaultValues,
    },
  });

  const {
    fields: patronageFields,
    append: appendPatronage,
    remove: removePatronage,
  } = useFieldArray({
    control,
    name: "patronages",
  });

  const createMutation = useMutation({
    mutationFn: async (data: PersonFormData) => {
      const response = await personsApi.create(await preparePersonPayload(data, false, avatarFile));
      await syncPersonFeast(response.data.id, data, null);
      return response;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["persons"] }),
        queryClient.invalidateQueries({ queryKey: ["editorial"] }),
        queryClient.invalidateQueries({ queryKey: ["calendar"] }),
      ]);
      router.push("/dashboard/persons");
    },
  });

  const updateMutation = useMutation({
    mutationFn: async (data: PersonFormData) => {
      const response = await personsApi.update(personId!, {
        ...(await preparePersonPayload(data, true, avatarFile)),
        expected_version: expectedVersion,
      });
      await syncPersonFeast(personId!, data, activeFeastEntry?.id ?? null);
      return response;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["persons"] }),
        queryClient.invalidateQueries({ queryKey: ["person", personId] }),
        queryClient.invalidateQueries({ queryKey: ["person-versions", personId] }),
        queryClient.invalidateQueries({ queryKey: ["editorial"] }),
        queryClient.invalidateQueries({ queryKey: ["calendar"] }),
        queryClient.invalidateQueries({ queryKey: ["calendar", "person-feasts", personId] }),
      ]);
      router.push(`/dashboard/persons/${personId}`);
    },
  });

  const mutation = isEdit ? updateMutation : createMutation;

  const onSubmit = (data: PersonFormData) => {
    mutation.mutate(data);
  };

  const inputCls =
    "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all";
  const labelCls = "block text-sm font-medium text-foreground mb-1";
  const errorCls = "mt-1 text-xs text-destructive";
  const avatarUrl = useWatch({ control, name: "avatar_url" });
  const canonicalName = useWatch({ control, name: "canonical_name" }) || "Nowa postać";
  const feastMonth = useWatch({ control, name: "feast_month" });
  const feastDay = useWatch({ control, name: "feast_day" });
  const avatarDisplayUrl = avatarPreview || avatarUrl || null;

  useEffect(() => {
    const syncTabFromHash = () => {
      const hash = window.location.hash.replace("#", "");
      if (TABS.some((tab) => tab.id === hash)) {
        setActiveTab(hash);
      }
    };

    syncTabFromHash();
    window.addEventListener("hashchange", syncTabFromHash);

    return () => window.removeEventListener("hashchange", syncTabFromHash);
  }, []);

  useEffect(() => {
    return () => {
      if (avatarPreview) URL.revokeObjectURL(avatarPreview);
    };
  }, [avatarPreview]);

  useEffect(() => {
    if (
      !isEdit ||
      !personId ||
      hydratedFeastPersonIdRef.current === personId ||
      feastEntriesQuery.isLoading
    ) {
      return;
    }

    if (activeFeastEntry) {
      setValue("feast_calendar_code", activeFeastEntry.calendar?.code ?? "roman_pl", { shouldDirty: false });
      setValue("feast_month", activeFeastEntry.month ?? null, { shouldDirty: false });
      setValue("feast_day", activeFeastEntry.day ?? null, { shouldDirty: false });
      setValue("feast_rank", (activeFeastEntry.rank as PersonFormData["feast_rank"]) ?? "memorial", { shouldDirty: false });
      setValue("feast_liturgical_color", (activeFeastEntry.liturgical_color as PersonFormData["feast_liturgical_color"]) ?? "", { shouldDirty: false });
      setValue("feast_is_primary", Boolean(activeFeastEntry.is_primary), { shouldDirty: false });
      setValue("feast_source_title", activeFeastEntry.source_title ?? "", { shouldDirty: false });
      setValue("feast_source_url", activeFeastEntry.source_url ?? "", { shouldDirty: false });
      setValue("feast_notes", activeFeastEntry.notes ?? "", { shouldDirty: false });
    }

    hydratedFeastPersonIdRef.current = personId;
  }, [
    activeFeastEntry,
    feastEntriesQuery.isLoading,
    isEdit,
    personId,
    setValue,
  ]);

  const selectAvatarFile = (file?: File) => {
    setAvatarFileError(null);
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setAvatarFileError("Wybierz obraz JPG, PNG lub WebP.");
      return;
    }
    if (file.size > 8 * 1024 * 1024) {
      setAvatarFileError("Obraz może mieć maksymalnie 8 MB.");
      return;
    }
    setAvatarFile(file);
    setAvatarPreview(URL.createObjectURL(file));
  };

  const clearAvatarFile = () => {
    setAvatarFile(null);
    setAvatarPreview(null);
    setAvatarFileError(null);
  };

  const clearFeastDate = () => {
    setValue("feast_month", null, { shouldDirty: true, shouldValidate: true });
    setValue("feast_day", null, { shouldDirty: true, shouldValidate: true });
    setValue("feast_is_primary", false, { shouldDirty: true });
    setValue("feast_source_title", "", { shouldDirty: true });
    setValue("feast_source_url", "", { shouldDirty: true, shouldValidate: true });
    setValue("feast_notes", "", { shouldDirty: true });
  };

  const selectTab = (tabId: string) => {
    setActiveTab(tabId);
    const nextUrl = `${window.location.pathname}${window.location.search}#${tabId}`;
    window.history.replaceState(null, "", nextUrl);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {/* Tabs */}
      <div className="flex w-fit max-w-full flex-wrap gap-1 rounded-lg border border-border bg-muted/40 p-1">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => selectTab(tab.id)}
            className={cn(
              "rounded-md px-4 py-1.5 text-sm font-medium transition-all",
              activeTab === tab.id
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ─── Tab: Basic ─────────────────────────────────────────────────── */}
      {activeTab === "basic" && (
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <label className={labelCls}>Imię kanoniczne (PL) *</label>
            <input {...register("canonical_name")} className={inputCls} placeholder="np. Św. Franciszek z Asyżu" />
            {errors.canonical_name && <p className={errorCls}>{errors.canonical_name.message}</p>}
          </div>

          <div>
            <label className={labelCls}>Imię kanoniczne (EN)</label>
            <input {...register("canonical_name_en")} className={inputCls} placeholder="St. Francis of Assisi" />
          </div>

          <div>
            <label className={labelCls}>Imię łacińskie</label>
            <input {...register("latin_name")} className={inputCls} placeholder="Franciscus Assisiensis" />
          </div>

          <div>
            <label className={labelCls}>Typ osoby *</label>
            <select {...register("person_type")} className={inputCls}>
              <option value="saint">Święty/a</option>
              <option value="blessed">Błogosławiony/a</option>
              <option value="venerable">Czcigodny/a</option>
              <option value="servant_of_god">Sługa Boży/a</option>
              <option value="candidate">Kandydat/ka (status redakcyjny)</option>
            </select>
          </div>

          <div>
            <label className={labelCls}>Status publikacji *</label>
            <select {...register("status")} className={inputCls}>
              <option value="draft">Szkic</option>
              <option value="review">W recenzji</option>
              <option value="published">Opublikowany</option>
              <option value="archived">Zarchiwizowany</option>
            </select>
          </div>

          <div>
            <label className={labelCls}>Płeć *</label>
            <select {...register("gender")} className={inputCls}>
              <option value="unknown">Nieznana</option>
              <option value="male">Mężczyzna</option>
              <option value="female">Kobieta</option>
            </select>
          </div>

          <div>
            <label className={labelCls}>Era</label>
            <select {...register("era")} className={inputCls}>
              <option value="">—</option>
              {Object.entries(ERA_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className={labelCls}>Stan życia</label>
            <select
              {...register("state_of_life_id")}
              className={inputCls}
              disabled={statesQuery.isLoading || statesQuery.isError || statesOfLife.length === 0}
            >
              <option value="">—</option>
              {statesQuery.isLoading && <option>Ładowanie danych…</option>}
              {statesQuery.isError && <option>Nie udało się pobrać danych</option>}
              {!statesQuery.isLoading && !statesQuery.isError && statesOfLife.length === 0 && (
                <option>Brak danych słownikowych</option>
              )}
              {statesOfLife.map((s: Record<string, string>) => (
                <option key={s.id} value={s.id}>{s.name_pl}</option>
              ))}
            </select>
            {statesQuery.isError && (
              <button type="button" onClick={() => statesQuery.refetch()} className="mt-1 text-xs text-primary hover:underline">
                Spróbuj pobrać ponownie
              </button>
            )}
          </div>

          <div className="flex items-center gap-2 sm:col-span-2">
            <input
              type="checkbox"
              id="is_featured"
              {...register("is_featured")}
              className="h-4 w-4 rounded border-input accent-primary"
            />
            <label htmlFor="is_featured" className="text-sm text-foreground">
              Wyróżnij na stronie głównej (featured)
            </label>
          </div>

          <section className="space-y-4 border-t border-border pt-5 sm:col-span-2">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
                  <CalendarDays className="h-4 w-4 text-primary" />
                  Wspomnienie liturgiczne
                </h3>
                <p className="mt-1 max-w-2xl text-xs leading-5 text-muted-foreground">
                  To pole tworzy powiązanie z kalendarzem liturgicznym. Publiczny portal pokaże wpis dopiero wtedy, gdy sama osoba ma status „Opublikowany”.
                </p>
              </div>
              {(activeFeastEntry || feastMonth || feastDay) && (
                <button
                  type="button"
                  onClick={clearFeastDate}
                  className="self-start rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                >
                  Wyczyść wspomnienie
                </button>
              )}
            </div>

            {feastEntriesQuery.isLoading && isEdit && (
              <p className="rounded-lg border border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
                Ładowanie aktualnych powiązań kalendarza…
              </p>
            )}

            {feastEntries.length > 1 && (
              <p className="rounded-lg border border-primary/15 bg-primary/5 px-3 py-2 text-xs leading-5 text-muted-foreground">
                Ta osoba ma {feastEntries.length} aktywne wpisy w kalendarzach. Formularz edytuje domyślnie wpis z Kalendarza Polskiego albo główny wpis dnia.
              </p>
            )}

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="lg:col-span-2">
                <label className={labelCls}>Kalendarz</label>
                <select {...register("feast_calendar_code")} className={inputCls}>
                  {calendars.length === 0 && (
                    <>
                      <option value="roman_pl">Kalendarz Polski</option>
                      <option value="roman_universal">Ogólny Kalendarz Rzymski</option>
                      <option value="roman_martyrology">Martyrologium Rzymskie</option>
                    </>
                  )}
                  {calendars.map((calendar: Record<string, string>) => (
                    <option key={calendar.code} value={calendar.code}>
                      {calendar.name}
                    </option>
                  ))}
                </select>
                {errors.feast_calendar_code && <p className={errorCls}>{errors.feast_calendar_code.message}</p>}
                {calendarsQuery.isError && (
                  <button type="button" onClick={() => calendarsQuery.refetch()} className="mt-1 text-xs text-primary hover:underline">
                    Spróbuj pobrać listę kalendarzy ponownie
                  </button>
                )}
              </div>

              <div>
                <label className={labelCls}>Miesiąc</label>
                <select
                  {...register("feast_month", {
                    setValueAs: (value) => value === "" ? null : Number(value),
                  })}
                  className={inputCls}
                >
                  <option value="">—</option>
                  {MONTH_OPTIONS.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
                {errors.feast_month && <p className={errorCls}>{errors.feast_month.message}</p>}
              </div>

              <div>
                <label className={labelCls}>Dzień</label>
                <input
                  type="number"
                  min={1}
                  max={31}
                  {...register("feast_day", {
                    setValueAs: (value) => value === "" ? null : Number(value),
                  })}
                  className={inputCls}
                  placeholder="np. 22"
                />
                {errors.feast_day && <p className={errorCls}>{errors.feast_day.message}</p>}
              </div>

              <div className="lg:col-span-2">
                <label className={labelCls}>Ranga liturgiczna</label>
                <select {...register("feast_rank")} className={inputCls}>
                  {FEAST_RANK_VALUES.map((rank) => (
                    <option key={rank} value={rank}>
                      {FEAST_RANK_LABELS[rank]}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className={labelCls}>Kolor liturgiczny</label>
                <select {...register("feast_liturgical_color")} className={inputCls}>
                  <option value="">—</option>
                  {LITURGICAL_COLOR_VALUES.map((color) => (
                    <option key={color} value={color}>
                      {LITURGICAL_COLOR_LABELS[color]}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-2 pt-7">
                <input
                  type="checkbox"
                  id="feast_is_primary"
                  {...register("feast_is_primary")}
                  className="h-4 w-4 rounded border-input accent-primary"
                />
                <label htmlFor="feast_is_primary" className="text-sm text-foreground">
                  Główne wspomnienie dnia
                </label>
              </div>

              <div className="lg:col-span-2">
                <label className={labelCls}>Tytuł źródła kalendarzowego</label>
                <input
                  {...register("feast_source_title")}
                  className={inputCls}
                  placeholder="np. Kalendarz liturgiczny diecezji / Martyrologium Romanum"
                />
              </div>

              <div className="lg:col-span-2">
                <label className={labelCls}>Link do źródła kalendarzowego</label>
                <input
                  {...register("feast_source_url")}
                  className={inputCls}
                  placeholder="https://…"
                />
                {errors.feast_source_url && <p className={errorCls}>{errors.feast_source_url.message}</p>}
              </div>

              <div className="sm:col-span-2 lg:col-span-4">
                <label className={labelCls}>Notatka redakcyjna</label>
                <textarea
                  {...register("feast_notes")}
                  rows={3}
                  className={cn(inputCls, "resize-y")}
                  placeholder="Np. wspomnienie w kalendarzu polskim, obchód lokalny, różnice względem Martyrologium…"
                />
              </div>
            </div>
          </section>
        </div>
      )}

      {/* ─── Tab: Dates & Places ────────────────────────────────────────── */}
      {activeTab === "dates" && (
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className={labelCls}>Rok urodzenia</label>
            <input
              type="number"
              {...register("birth_year", {
                setValueAs: (value) => value === "" ? null : Number(value),
              })}
              className={inputCls}
              placeholder="np. 1181"
            />
          </div>

          <div>
            <label className={labelCls}>Rok śmierci</label>
            <input
              type="number"
              {...register("death_year", {
                setValueAs: (value) => value === "" ? null : Number(value),
              })}
              className={inputCls}
              placeholder="np. 1226"
            />
          </div>

          <div>
            <label className={labelCls}>Kraj urodzenia</label>
            <select
              {...register("birth_country_id")}
              className={inputCls}
              disabled={countriesQuery.isLoading || countriesQuery.isError || countries.length === 0}
            >
              <option value="">—</option>
              {countriesQuery.isLoading && <option>Ładowanie krajów…</option>}
              {countriesQuery.isError && <option>Nie udało się pobrać krajów</option>}
              {!countriesQuery.isLoading && !countriesQuery.isError && countries.length === 0 && (
                <option>Brak krajów w bazie</option>
              )}
              {countries.map((c: Record<string, string>) => (
                <option key={c.id} value={c.id}>{c.name_pl}</option>
              ))}
            </select>
          </div>

          <div>
            <label className={labelCls}>Kraj śmierci</label>
            <select
              {...register("death_country_id")}
              className={inputCls}
              disabled={countriesQuery.isLoading || countriesQuery.isError || countries.length === 0}
            >
              <option value="">—</option>
              {countriesQuery.isLoading && <option>Ładowanie krajów…</option>}
              {countriesQuery.isError && <option>Nie udało się pobrać krajów</option>}
              {!countriesQuery.isLoading && !countriesQuery.isError && countries.length === 0 && (
                <option>Brak krajów w bazie</option>
              )}
              {countries.map((c: Record<string, string>) => (
                <option key={c.id} value={c.id}>{c.name_pl}</option>
              ))}
            </select>
          </div>
          {countriesQuery.isError && (
            <div className="sm:col-span-2">
              <button type="button" onClick={() => countriesQuery.refetch()} className="text-xs text-primary hover:underline">
                Spróbuj ponownie pobrać listę krajów
              </button>
            </div>
          )}

          <div className="border-t border-border pt-5 sm:col-span-2">
            <h3 className="text-sm font-semibold text-foreground">Droga do chwały ołtarzy</h3>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              Wpisz dokładną datę, gdy jest udokumentowana. Jeśli źródło podaje tylko rok, pozostaw datę pustą i uzupełnij pole roku.
            </p>
          </div>

          <section className="space-y-4 rounded-xl border border-border bg-muted/20 p-4">
            <h4 className="text-sm font-semibold text-foreground">Beatyfikacja</h4>
            <div>
              <label className={labelCls}>Dokładna data</label>
              <input type="date" {...register("beatification_date")} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Rok (gdy brak dokładnej daty)</label>
              <input
                type="number"
                {...register("beatification_year", {
                  setValueAs: (value) => value === "" ? null : Number(value),
                })}
                className={inputCls}
                placeholder="np. 1993"
              />
            </div>
          </section>

          <section className="space-y-4 rounded-xl border border-border bg-muted/20 p-4">
            <h4 className="text-sm font-semibold text-foreground">Kanonizacja</h4>
            <div>
              <label className={labelCls}>Dokładna data</label>
              <input type="date" {...register("canonization_date")} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Rok (gdy brak dokładnej daty)</label>
              <input
                type="number"
                {...register("canonization_year", {
                  setValueAs: (value) => value === "" ? null : Number(value),
                })}
                className={inputCls}
                placeholder="np. 2000"
              />
            </div>
          </section>
        </div>
      )}

      {/* ─── Tab: Biography ─────────────────────────────────────────────── */}
      {activeTab === "biography" && (
        <div className="space-y-4">
          <div>
            <label className={labelCls}>Streszczenie (PL)</label>
            <textarea
              {...register("summary_pl")}
              rows={3}
              className={cn(inputCls, "resize-none")}
              placeholder="Krótkie streszczenie..."
            />
          </div>
          <div>
            <label className={labelCls}>Biografia (PL)</label>
            <textarea
              {...register("biography_pl")}
              rows={10}
              className={cn(inputCls, "resize-y")}
              placeholder="Pełna biogram..."
            />
          </div>
          {isEdit && (
            <div>
              <label className={labelCls}>Opis zmian (dla historii wersji)</label>
              <input
                {...register("change_summary")}
                className={inputCls}
                placeholder="np. Uzupełniono biogram..."
              />
            </div>
          )}
        </div>
      )}

      {/* ─── Tab: Patronages ───────────────────────────────────────────── */}
      {activeTab === "patronages" && (
        <div className="space-y-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <HeartHandshake className="h-4 w-4 text-primary" />
                Patronaty
              </h3>
              <p className="mt-1 max-w-3xl text-xs leading-5 text-muted-foreground">
                Dodaj informacje, komu lub czemu dana osoba patronuje. Typ patronatu
                pomaga później filtrować katalog publiczny, np. chorzy, rodzina,
                praca albo podróżni.
              </p>
            </div>
            <button
              type="button"
              onClick={() =>
                appendPatronage({
                  patronage_type: "other",
                  name_pl: "",
                  name_en: "",
                  description: "",
                  is_official: false,
                })
              }
              className="inline-flex h-9 items-center justify-center gap-2 rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground hover:bg-primary/90"
            >
              <Plus className="h-3.5 w-3.5" />
              Dodaj patronat
            </button>
          </div>

          {patronageFields.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border bg-muted/20 p-8 text-center">
              <HeartHandshake className="mx-auto h-7 w-7 text-primary" />
              <h3 className="mt-3 text-sm font-semibold text-foreground">Brak patronatów</h3>
              <p className="mx-auto mt-1 max-w-lg text-xs leading-5 text-muted-foreground">
                Dodaj pierwszy patronat, np. „chorych”, „spraw beznadziejnych”,
                „podróżnych” albo konkretny kraj, miasto czy zawód.
              </p>
              <button
                type="button"
                onClick={() =>
                  appendPatronage({
                    patronage_type: "other",
                    name_pl: "",
                    name_en: "",
                    description: "",
                    is_official: false,
                  })
                }
                className="mt-4 inline-flex h-9 items-center justify-center gap-2 rounded-lg border border-border px-3 text-xs font-semibold hover:bg-accent"
              >
                <Plus className="h-3.5 w-3.5" />
                Dodaj patronat
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {patronageFields.map((field, index) => (
                <section key={field.id} className="rounded-xl border border-border bg-muted/15 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h4 className="text-sm font-semibold text-foreground">
                        Patronat #{index + 1}
                      </h4>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Wpisz konkretną grupę, sprawę, miejsce lub zawód.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => removePatronage(index)}
                      className="inline-flex h-8 items-center justify-center gap-1 rounded-md border border-border px-2.5 text-xs text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      Usuń
                    </button>
                  </div>

                  <div className="mt-4 grid gap-4 sm:grid-cols-2">
                    <div>
                      <label className={labelCls}>Typ patronatu *</label>
                      <select
                        {...register(`patronages.${index}.patronage_type` as const)}
                        className={inputCls}
                      >
                        {PATRONAGE_TYPE_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                      {errors.patronages?.[index]?.patronage_type && (
                        <p className={errorCls}>{errors.patronages?.[index]?.patronage_type?.message}</p>
                      )}
                    </div>

                    <div>
                      <label className={labelCls}>Patron / patronka od *</label>
                      <input
                        {...register(`patronages.${index}.name_pl` as const)}
                        className={inputCls}
                        placeholder="np. spraw beznadziejnych, chorych, podróżnych"
                      />
                      {errors.patronages?.[index]?.name_pl && (
                        <p className={errorCls}>{errors.patronages?.[index]?.name_pl?.message}</p>
                      )}
                    </div>

                    <div>
                      <label className={labelCls}>Nazwa EN</label>
                      <input
                        {...register(`patronages.${index}.name_en` as const)}
                        className={inputCls}
                        placeholder="np. hopeless causes"
                      />
                    </div>

                    <div className="flex items-center gap-2 pt-7">
                      <input
                        type="checkbox"
                        id={`patronage-official-${field.id}`}
                        {...register(`patronages.${index}.is_official` as const)}
                        className="h-4 w-4 rounded border-input accent-primary"
                      />
                      <label htmlFor={`patronage-official-${field.id}`} className="text-sm text-foreground">
                        Patronat oficjalnie potwierdzony
                      </label>
                    </div>

                    <div className="sm:col-span-2">
                      <label className={labelCls}>Opis / notatka redakcyjna</label>
                      <textarea
                        {...register(`patronages.${index}.description` as const)}
                        rows={3}
                        className={cn(inputCls, "resize-y")}
                        placeholder="Np. zakres patronatu, lokalna tradycja, źródło informacji lub uwagi do weryfikacji…"
                      />
                    </div>
                  </div>
                </section>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ─── Tab: Devotion & Iconography ──────────────────────────────── */}
      {activeTab === "devotion" && (
        <div className="grid gap-6 lg:grid-cols-2">
          <div>
            <label className={labelCls}>Modlitwa</label>
            <textarea
              {...register("prayers")}
              rows={10}
              className={cn(inputCls, "resize-y leading-6")}
              placeholder="Treść zatwierdzonej modlitwy związanej z postacią…"
            />
            <p className="mt-1.5 text-xs leading-5 text-muted-foreground">
              Podziały wierszy zostaną zachowane na profilu publicznym. Publikuj wyłącznie tekst o zweryfikowanym źródle i prawach do wykorzystania.
            </p>
          </div>

          <div>
            <label className={labelCls}>Atrybuty ikonograficzne</label>
            <textarea
              {...register("iconographic_attributes")}
              rows={10}
              className={cn(inputCls, "resize-y leading-6")}
              placeholder="Róże; cierń na czole; habit augustiański; krucyfiks"
            />
            <p className="mt-1.5 text-xs leading-5 text-muted-foreground">
              Oddziel atrybuty średnikiem lub nowym wierszem. Portal pokaże każdy element jako osobną etykietę.
            </p>
          </div>
        </div>
      )}

      {/* ─── Tab: Sources ────────────────────────────────────────────────── */}
      {activeTab === "sources" && (
        isEdit && personId ? (
          <PersonSourcesEditor personId={personId} />
        ) : (
          <div className="rounded-xl border border-dashed border-border bg-muted/20 p-8 text-center">
            <BookOpenText className="mx-auto h-7 w-7 text-primary" />
            <h3 className="mt-3 text-sm font-semibold text-foreground">Najpierw utwórz rekord osoby</h3>
            <p className="mx-auto mt-1 max-w-lg text-xs leading-5 text-muted-foreground">
              Źródła można przypisać po pierwszym zapisie, gdy postać otrzyma własny identyfikator.
              Po utworzeniu rekordu otwórz jego edycję i wróć do tej zakładki.
            </p>
          </div>
        )
      )}

      {/* ─── Tab: Avatar ───────────────────────────────────────────────── */}
      {activeTab === "avatar" && (
        <div className="grid gap-6 lg:grid-cols-[13rem_1fr]">
          <div className="rounded-xl border border-border bg-muted/25 p-5 text-center">
            <SaintAvatar
              name={canonicalName}
              avatar={avatarDisplayUrl ? { url: avatarDisplayUrl } : null}
              className="mx-auto h-32 w-32 text-3xl"
            />
            <p className="mt-4 text-sm font-semibold text-foreground">Podgląd avatara</p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              Bez obrazu pokażemy elegancki monogram, więc każdy profil pozostaje kompletny wizualnie.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <span className={labelCls}>Plik z dysku</span>
              <label
                htmlFor="avatar-file"
                className="flex cursor-pointer items-center justify-center gap-3 rounded-xl border border-dashed border-primary/35 bg-primary/5 px-5 py-6 text-sm text-foreground transition-colors hover:border-primary/60 hover:bg-primary/10"
              >
                <span className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
                  <Upload className="h-5 w-5" />
                </span>
                <span>
                  <strong className="block font-semibold">Wybierz obraz z dysku</strong>
                  <span className="mt-0.5 block text-xs text-muted-foreground">JPG, PNG lub WebP · maksymalnie 8 MB</span>
                </span>
                <input
                  key={avatarFile?.name ?? "empty-avatar-file"}
                  id="avatar-file"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  className="sr-only"
                  onChange={(event) => selectAvatarFile(event.target.files?.[0])}
                />
              </label>
              {avatarFileError && <p className={errorCls}>{avatarFileError}</p>}
              {avatarFile && (
                <div className="mt-2 flex items-center justify-between gap-3 rounded-lg border border-border bg-background px-3 py-2">
                  <div className="flex min-w-0 items-center gap-2">
                    <FileImage className="h-4 w-4 shrink-0 text-primary" />
                    <span className="truncate text-xs font-medium text-foreground">{avatarFile.name}</span>
                    <span className="shrink-0 text-xs text-muted-foreground">
                      {(avatarFile.size / 1024 / 1024).toFixed(2)} MB
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={clearAvatarFile}
                    className="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                    aria-label="Usuń wybrany plik"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              )}
            </div>

            <div className="sm:col-span-2 flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              <span className="h-px flex-1 bg-border" />
              lub użyj adresu
              <span className="h-px flex-1 bg-border" />
            </div>

            <div className="sm:col-span-2">
              <label className={labelCls}>Adres obrazu</label>
              <div className="relative">
                <ImagePlus className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  {...register("avatar_url")}
                  className={cn(inputCls, "pl-9")}
                  placeholder="https://…/portret.jpg lub /images/portret.jpg"
                />
              </div>
              {errors.avatar_url && <p className={errorCls}>{errors.avatar_url.message}</p>}
              {avatarFile && (
                <p className="mt-1 text-xs text-muted-foreground">Wybrany plik z dysku ma pierwszeństwo przed adresem URL.</p>
              )}
            </div>

            <div>
              <label className={labelCls}>Miniatura (opcjonalnie)</label>
              <input {...register("avatar_thumbnail_url")} className={inputCls} placeholder="https://…/miniatura.jpg" />
              {errors.avatar_thumbnail_url && <p className={errorCls}>{errors.avatar_thumbnail_url.message}</p>}
            </div>

            <div>
              <label className={labelCls}>Tytuł / tekst alternatywny</label>
              <input {...register("avatar_title")} className={inputCls} placeholder={`Portret: ${canonicalName}`} />
            </div>

            <div>
              <label className={labelCls}>Licencja</label>
              <select {...register("avatar_license")} className={inputCls}>
                <option value="unknown">Do weryfikacji</option>
                <option value="public_domain">Domena publiczna</option>
                <option value="cc_by">CC BY</option>
                <option value="cc_by_sa">CC BY-SA</option>
                <option value="cc_by_nc">CC BY-NC</option>
                <option value="cc_by_nc_sa">CC BY-NC-SA</option>
                <option value="all_rights_reserved">Wszelkie prawa zastrzeżone</option>
                <option value="fair_use">Dozwolony użytek</option>
              </select>
            </div>

            <div>
              <label className={labelCls}>Autor / fotograf</label>
              <input {...register("avatar_photographer")} className={inputCls} placeholder="Autor dzieła lub fotografii" />
            </div>

            <div className="sm:col-span-2">
              <label className={labelCls}>Źródło obrazu</label>
              <input {...register("avatar_source_url")} className={inputCls} placeholder="https://commons.wikimedia.org/…" />
              {errors.avatar_source_url && <p className={errorCls}>{errors.avatar_source_url.message}</p>}
            </div>

            <div className="sm:col-span-2 flex gap-2 rounded-lg border border-primary/15 bg-primary/5 p-3 text-xs leading-5 text-muted-foreground">
              <Info className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
              Avatar jest zapisywany jako główne zdjęcie w katalogu mediów. Pliki są automatycznie weryfikowane, konwertowane do WebP i otrzymują miniaturę. Usunięcie adresu wyłączy aktualny avatar bez kasowania rekordu osoby.
            </div>
          </div>
        </div>
      )}

      {/* Action bar */}
      <div className="flex items-center justify-between border-t border-border pt-4">
        <button
          type="button"
          onClick={() => router.back()}
          className="flex items-center gap-1.5 rounded-lg border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Anuluj
        </button>

        <button
          type="submit"
          disabled={mutation.isPending || (!isDirty && isEdit)}
          className="flex items-center gap-2 rounded-lg bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {mutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Save className="h-4 w-4" />
          )}
          {isEdit ? "Zapisz zmiany" : "Utwórz osobę"}
        </button>
      </div>

      {mutation.isError && (
        <p role="alert" className="rounded-lg border border-destructive/25 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {getApiErrorMessage(mutation.error)}
        </p>
      )}
    </form>
  );
}
