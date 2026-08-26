"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpenText, FileArchive, Loader2, Plus, Star, Trash2 } from "lucide-react";
import { getApiErrorMessage, sourcesApi } from "@/lib/api";

type SourceKind = "bibliography" | "historical";

interface BibliographySource {
  id: string;
  title: string;
  authors?: string | null;
  year?: number | null;
  source_type: string;
}

interface HistoricalSource {
  id: string;
  title: string;
  repository?: string | null;
  date_range?: string | null;
  source_type: string;
}

interface PersonSourceLink {
  id: string;
  bibliography_id?: string | null;
  historical_source_id?: string | null;
  bibliography?: BibliographySource | null;
  historical_source?: HistoricalSource | null;
  page_reference?: string | null;
  is_primary: boolean;
  notes?: string | null;
}

const inputClassName =
  "h-10 w-full rounded-lg border border-input bg-background px-3 text-sm outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20";

function sourceTitle(link: PersonSourceLink) {
  return link.bibliography?.title ?? link.historical_source?.title ?? "Nieznane źródło";
}

function sourceMeta(link: PersonSourceLink) {
  if (link.bibliography) {
    return [link.bibliography.authors, link.bibliography.year].filter(Boolean).join(" · ");
  }
  return [link.historical_source?.repository, link.historical_source?.date_range]
    .filter(Boolean)
    .join(" · ");
}

export function PersonSourcesEditor({ personId }: { personId: string }) {
  const queryClient = useQueryClient();
  const [sourceKind, setSourceKind] = useState<SourceKind>("bibliography");
  const [sourceId, setSourceId] = useState("");
  const [pageReference, setPageReference] = useState("");
  const [notes, setNotes] = useState("");
  const [isPrimary, setIsPrimary] = useState(false);

  const linksQuery = useQuery({
    queryKey: ["person-sources", personId],
    queryFn: () => sourcesApi.personSources(personId),
  });
  const bibliographyQuery = useQuery({
    queryKey: ["sources", "bibliography"],
    queryFn: () => sourcesApi.bibliography(),
    staleTime: 60_000,
  });
  const historicalQuery = useQuery({
    queryKey: ["sources", "historical"],
    queryFn: () => sourcesApi.historicalSources(),
    staleTime: 60_000,
  });

  const links = (linksQuery.data?.data ?? []) as PersonSourceLink[];
  const bibliography = (bibliographyQuery.data?.data ?? []) as BibliographySource[];
  const historicalSources = (historicalQuery.data?.data ?? []) as HistoricalSource[];
  const selectableSources = sourceKind === "bibliography" ? bibliography : historicalSources;

  const addMutation = useMutation({
    mutationFn: () =>
      sourcesApi.assignPersonSource(personId, {
        bibliography_id: sourceKind === "bibliography" ? sourceId : null,
        historical_source_id: sourceKind === "historical" ? sourceId : null,
        page_reference: pageReference.trim() || null,
        notes: notes.trim() || null,
        is_primary: isPrimary,
      }),
    onSuccess: async () => {
      setSourceId("");
      setPageReference("");
      setNotes("");
      setIsPrimary(false);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["person-sources", personId] }),
        queryClient.invalidateQueries({ queryKey: ["editorial"] }),
      ]);
    },
  });

  const removeMutation = useMutation({
    mutationFn: (linkId: string) => sourcesApi.removePersonSource(personId, linkId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["person-sources", personId] }),
        queryClient.invalidateQueries({ queryKey: ["editorial"] }),
      ]);
    },
  });

  const error = addMutation.error ?? removeMutation.error ?? linksQuery.error;

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-primary/15 bg-primary/5 p-4 text-sm leading-6 text-muted-foreground">
        Przypisane tutaj pozycje są źródłami merytorycznymi postaci. Co najmniej jedno aktywne
        powiązanie zwiększa kompletność rekordu o <strong className="text-foreground">15 punktów</strong>.
        Źródło obrazu w zakładce „Avatar” służy wyłącznie do atrybucji grafiki i nie zastępuje
        źródła biogramu.
      </div>

      <section className="grid gap-4 rounded-xl border border-border bg-muted/20 p-4 md:grid-cols-2">
        <div>
          <label className="mb-1 block text-sm font-medium text-foreground">Rodzaj źródła</label>
          <select
            value={sourceKind}
            onChange={(event) => {
              setSourceKind(event.target.value as SourceKind);
              setSourceId("");
            }}
            className={inputClassName}
          >
            <option value="bibliography">Bibliografia / opracowanie</option>
            <option value="historical">Źródło historyczne</option>
          </select>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-foreground">Pozycja *</label>
          <select
            value={sourceId}
            onChange={(event) => setSourceId(event.target.value)}
            className={inputClassName}
            disabled={bibliographyQuery.isLoading || historicalQuery.isLoading}
          >
            <option value="">Wybierz źródło…</option>
            {selectableSources.map((source) => (
              <option key={source.id} value={source.id}>
                {source.title}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-foreground">Strony / sygnatura</label>
          <input
            value={pageReference}
            onChange={(event) => setPageReference(event.target.value)}
            className={inputClassName}
            placeholder="np. s. 124–130 albo rkps 42, k. 7r"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-foreground">Notatka redakcyjna</label>
          <input
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            className={inputClassName}
            placeholder="Zakres informacji potwierdzonych przez źródło"
          />
        </div>

        <div className="flex items-center gap-2 md:col-span-2">
          <input
            id="source-primary"
            type="checkbox"
            checked={isPrimary}
            onChange={(event) => setIsPrimary(event.target.checked)}
            className="h-4 w-4 rounded border-input accent-primary"
          />
          <label htmlFor="source-primary" className="text-sm text-foreground">
            Oznacz jako główne źródło profilu
          </label>
        </div>

        <div className="md:col-span-2">
          <button
            type="button"
            disabled={!sourceId || addMutation.isPending}
            onClick={() => addMutation.mutate()}
            className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {addMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Plus className="h-4 w-4" />
            )}
            Przypisz źródło
          </button>
        </div>
      </section>

      {error && (
        <p role="alert" className="rounded-lg border border-destructive/25 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {getApiErrorMessage(error)}
        </p>
      )}

      <section>
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-foreground">Źródła przypisane do postaci</h3>
            <p className="mt-1 text-xs text-muted-foreground">{links.length} aktywnych powiązań</p>
          </div>
        </div>

        {linksQuery.isLoading ? (
          <div className="flex items-center gap-2 rounded-lg border border-border p-4 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Ładowanie źródeł…
          </div>
        ) : links.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
            Brak przypisanych źródeł merytorycznych.
          </div>
        ) : (
          <ul className="divide-y divide-border overflow-hidden rounded-xl border border-border bg-card">
            {links.map((link) => {
              const HistoricalIcon = link.historical_source ? FileArchive : BookOpenText;
              const meta = sourceMeta(link);
              return (
                <li key={link.id} className="flex items-start gap-3 p-4">
                  <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <HistoricalIcon className="h-4 w-4" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium text-foreground">{sourceTitle(link)}</p>
                      {link.is_primary && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
                          <Star className="h-3 w-3" /> Główne
                        </span>
                      )}
                    </div>
                    {meta && <p className="mt-1 text-xs text-muted-foreground">{meta}</p>}
                    {link.page_reference && (
                      <p className="mt-1 text-xs text-foreground">Odwołanie: {link.page_reference}</p>
                    )}
                    {link.notes && <p className="mt-1 text-xs text-muted-foreground">{link.notes}</p>}
                  </div>
                  <button
                    type="button"
                    disabled={removeMutation.isPending}
                    onClick={() => removeMutation.mutate(link.id)}
                    className="rounded-md p-2 text-muted-foreground hover:bg-destructive/10 hover:text-destructive disabled:opacity-50"
                    aria-label={`Usuń źródło ${sourceTitle(link)}`}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
