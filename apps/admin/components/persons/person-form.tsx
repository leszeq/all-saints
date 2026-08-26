"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowLeft, FileImage, ImagePlus, Info, Loader2, Save, Upload, X } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getApiErrorMessage, personsApi, geographyApi, sourcesApi, taxonomyApi } from "@/lib/api";
import { cn, ERA_LABELS } from "@/lib/utils";
import { SaintAvatar } from "@/components/persons/saint-avatar";

const optionalMediaUrl = z.string().optional().refine(
  (value) => !value || value.startsWith("/") || /^https?:\/\//i.test(value),
  "Podaj adres HTTP(S) lub ścieżkę zaczynającą się od /",
);

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
  change_summary: z.string().optional(),
});

type PersonFormData = z.infer<typeof personSchema>;

function normalizePersonPayload(data: PersonFormData, isEdit: boolean) {
  const optionalText = (value?: string | null) => {
    const normalized = value?.trim();
    return normalized ? normalized : null;
  };
  const optionalId = (value?: string | null) => value || null;
  const {
    change_summary,
    avatar_url,
    avatar_thumbnail_url,
    avatar_title,
    avatar_license,
    avatar_photographer,
    avatar_source_url,
    beatification_date,
    beatification_year,
    canonization_date,
    canonization_year,
    ...personFields
  } = data;
  const normalizedAvatarUrl = optionalText(avatar_url);
  const beatification = {
    beatification_date: optionalText(beatification_date),
    beatification_year: Number.isFinite(beatification_year) ? beatification_year : null,
  };
  const canonization = {
    canonization_date: optionalText(canonization_date),
    canonization_year: Number.isFinite(canonization_year) ? canonization_year : null,
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
    avatar: normalizedAvatarUrl
      ? {
          url: normalizedAvatarUrl,
          thumbnail_url: optionalText(avatar_thumbnail_url),
          title: optionalText(avatar_title),
          license: avatar_license,
          photographer: optionalText(avatar_photographer),
          source_url: optionalText(avatar_source_url),
        }
      : null,
    beatification: Object.values(beatification).some(Boolean) ? beatification : null,
    canonization: Object.values(canonization).some(Boolean) ? canonization : null,
    ...(isEdit ? { change_summary: optionalText(change_summary) } : {}),
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
  const optionalText = (value?: string | null) => value?.trim() || null;
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

const TABS = [
  { id: "basic", label: "Dane podstawowe" },
  { id: "dates", label: "Daty i miejsca" },
  { id: "biography", label: "Biografia" },
  { id: "devotion", label: "Kult i ikonografia" },
  { id: "avatar", label: "Avatar" },
];

interface PersonFormProps {
  personId?: string;
  defaultValues?: Partial<PersonFormData>;
  isEdit?: boolean;
}

export function PersonForm({ personId, defaultValues, isEdit }: PersonFormProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("basic");
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [avatarFileError, setAvatarFileError] = useState<string | null>(null);

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

  const countries = countriesQuery.data?.data ?? [];
  const statesOfLife = statesQuery.data?.data ?? [];

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isDirty },
  } = useForm<PersonFormData>({
    resolver: zodResolver(personSchema),
    defaultValues: {
      person_type: "saint",
      status: "draft",
      gender: "unknown",
      is_featured: false,
      avatar_license: "unknown",
      ...defaultValues,
    },
  });

  const createMutation = useMutation({
    mutationFn: async (data: PersonFormData) =>
      personsApi.create(await preparePersonPayload(data, false, avatarFile)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["persons"] });
      router.push("/dashboard/persons");
    },
  });

  const updateMutation = useMutation({
    mutationFn: async (data: PersonFormData) =>
      personsApi.update(personId!, await preparePersonPayload(data, true, avatarFile)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["persons"] });
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
  const avatarDisplayUrl = avatarPreview || avatarUrl || null;

  useEffect(() => {
    return () => {
      if (avatarPreview) URL.revokeObjectURL(avatarPreview);
    };
  }, [avatarPreview]);

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

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {/* Tabs */}
      <div className="flex w-fit max-w-full flex-wrap gap-1 rounded-lg border border-border bg-muted/40 p-1">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
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
