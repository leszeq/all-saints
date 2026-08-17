"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowLeft, Loader2, Save } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getApiErrorMessage, personsApi, geographyApi, taxonomyApi } from "@/lib/api";
import { cn } from "@/lib/utils";

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
  birth_country_id: z.string().optional().nullable(),
  death_country_id: z.string().optional().nullable(),
  state_of_life_id: z.string().optional().nullable(),
  summary_pl: z.string().optional(),
  biography_pl: z.string().optional(),
  is_featured: z.boolean(),
  change_summary: z.string().optional(),
});

type PersonFormData = z.infer<typeof personSchema>;

function normalizePersonPayload(data: PersonFormData, isEdit: boolean) {
  const optionalText = (value?: string | null) => {
    const normalized = value?.trim();
    return normalized ? normalized : null;
  };
  const optionalId = (value?: string | null) => value || null;
  const { change_summary, ...personFields } = data;

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
    ...(isEdit ? { change_summary: optionalText(change_summary) } : {}),
  };
}

type PersonPayload = ReturnType<typeof normalizePersonPayload>;

const TABS = [
  { id: "basic", label: "Dane podstawowe" },
  { id: "dates", label: "Daty i miejsca" },
  { id: "biography", label: "Biografia" },
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
    formState: { errors, isDirty },
  } = useForm<PersonFormData>({
    resolver: zodResolver(personSchema),
    defaultValues: {
      person_type: "saint",
      status: "draft",
      gender: "unknown",
      is_featured: false,
      ...defaultValues,
    },
  });

  const createMutation = useMutation({
    mutationFn: (data: PersonPayload) => personsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["persons"] });
      router.push("/dashboard/persons");
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: PersonPayload) => personsApi.update(personId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["persons"] });
      router.push(`/dashboard/persons/${personId}`);
    },
  });

  const mutation = isEdit ? updateMutation : createMutation;

  const onSubmit = (data: PersonFormData) => {
    mutation.mutate(normalizePersonPayload(data, Boolean(isEdit)));
  };

  const inputCls =
    "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all";
  const labelCls = "block text-sm font-medium text-foreground mb-1";
  const errorCls = "mt-1 text-xs text-destructive";

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {/* Tabs */}
      <div className="flex gap-1 rounded-lg border border-border bg-muted/40 p-1 w-fit">
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
              <option value="candidate">Kandydat/ka</option>
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
              <option value="apostolic">Epoka apostolska (I w.)</option>
              <option value="early_church">Wczesny Kościół (II–V w.)</option>
              <option value="late_antiquity">Późna starożytność (V–VII w.)</option>
              <option value="medieval">Średniowiecze</option>
              <option value="early_modern">Nowożytność</option>
              <option value="modern">Epoka nowoczesna (XIX–XX w.)</option>
              <option value="contemporary">Współczesność (XXI w.)</option>
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
