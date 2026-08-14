"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowLeft, Loader2, Save } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { personsApi, geographyApi, taxonomyApi } from "@/lib/api";
import { cn } from "@/lib/utils";

const personSchema = z.object({
  canonical_name: z.string().min(2, "Minimum 2 znaki"),
  canonical_name_en: z.string().optional(),
  latin_name: z.string().optional(),
  person_type: z.enum(["saint", "blessed", "venerable", "servant_of_god", "candidate"]),
  status: z.enum(["draft", "review", "published", "archived"]),
  gender: z.enum(["male", "female", "unknown"]),
  era: z.string().optional(),
  birth_year: z.union([z.number(), z.string()]).optional().nullable(),
  death_year: z.union([z.number(), z.string()]).optional().nullable(),
  birth_country_id: z.string().optional().nullable(),
  death_country_id: z.string().optional().nullable(),
  state_of_life_id: z.string().optional().nullable(),
  summary_pl: z.string().optional(),
  biography_pl: z.string().optional(),
  is_featured: z.boolean(),
  change_summary: z.string().optional(),
});

type PersonFormData = z.infer<typeof personSchema>;

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

  const { data: countriesData } = useQuery({
    queryKey: ["countries"],
    queryFn: () => geographyApi.countries(),
    staleTime: Infinity,
  });
  const { data: statesData } = useQuery({
    queryKey: ["states-of-life"],
    queryFn: () => taxonomyApi.statesOfLife(),
    staleTime: Infinity,
  });

  const countries = countriesData?.data ?? [];
  const statesOfLife = statesData?.data ?? [];

  const {
    register,
    handleSubmit,
    formState: { errors, isDirty },
    watch,
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
    mutationFn: (data: PersonFormData) => personsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["persons"] });
      router.push("/dashboard/persons");
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: PersonFormData) => personsApi.update(personId!, data),
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
              <option value="ancient">Starożytność</option>
              <option value="early_christian">Wczesnochrześcijańska</option>
              <option value="medieval">Średniowiecze</option>
              <option value="early_modern">Nowożytność</option>
              <option value="modern">Nowoczesność</option>
              <option value="contemporary">Współczesność</option>
            </select>
          </div>

          <div>
            <label className={labelCls}>Stan życia</label>
            <select {...register("state_of_life_id")} className={inputCls}>
              <option value="">—</option>
              {statesOfLife.map((s: Record<string, string>) => (
                <option key={s.id} value={s.id}>{s.name_pl}</option>
              ))}
            </select>
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
              {...register("birth_year", { valueAsNumber: true })}
              className={inputCls}
              placeholder="np. 1181"
            />
          </div>

          <div>
            <label className={labelCls}>Rok śmierci</label>
            <input
              type="number"
              {...register("death_year", { valueAsNumber: true })}
              className={inputCls}
              placeholder="np. 1226"
            />
          </div>

          <div>
            <label className={labelCls}>Kraj urodzenia</label>
            <select {...register("birth_country_id")} className={inputCls}>
              <option value="">—</option>
              {countries.map((c: Record<string, string>) => (
                <option key={c.id} value={c.id}>{c.name_pl}</option>
              ))}
            </select>
          </div>

          <div>
            <label className={labelCls}>Kraj śmierci</label>
            <select {...register("death_country_id")} className={inputCls}>
              <option value="">—</option>
              {countries.map((c: Record<string, string>) => (
                <option key={c.id} value={c.id}>{c.name_pl}</option>
              ))}
            </select>
          </div>
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
        <p className="text-sm text-destructive text-center">
          Wystąpił błąd podczas zapisu. Spróbuj ponownie.
        </p>
      )}
    </form>
  );
}
