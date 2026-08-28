"use client";

import Link from "next/link";
import type { ElementType } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  Bot,
  BrainCircuit,
  CheckCircle2,
  DatabaseZap,
  FileText,
  Loader2,
  RefreshCw,
  Sparkles,
  Tags,
  WandSparkles,
} from "lucide-react";
import { aiApi, getApiErrorMessage } from "@/lib/api";
import {
  AI_FEATURE_STATUS_COLORS,
  AI_FEATURE_STATUS_LABELS,
  AI_SUGGESTION_KIND_LABELS,
  AI_SUGGESTION_STATUS_COLORS,
  AI_SUGGESTION_STATUS_LABELS,
  type AiSuggestionItem,
} from "@/lib/ai";
import { cn, formatDateTime } from "@/lib/utils";

const featureIcons: Record<string, ElementType> = {
  embeddings: DatabaseZap,
  semantic_search: BrainCircuit,
  summaries: FileText,
  tagging: Tags,
};

const metricTones = {
  embeddings: "text-blue-700 bg-blue-50 dark:bg-blue-950/30 dark:text-blue-300",
  missing: "text-amber-700 bg-amber-50 dark:bg-amber-950/30 dark:text-amber-300",
  suggestions: "text-purple-700 bg-purple-50 dark:bg-purple-950/30 dark:text-purple-300",
  blocked: "text-rose-700 bg-rose-50 dark:bg-rose-950/30 dark:text-rose-300",
};

function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
  tone,
}: {
  label: string;
  value: number | string;
  detail: string;
  icon: ElementType;
  tone: string;
}) {
  const displayValue = typeof value === "number" ? value.toLocaleString("pl-PL") : value;

  return (
    <article className="admin-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-muted-foreground">{label}</p>
          <p className="mt-2 text-3xl font-semibold tracking-tight">{displayValue}</p>
        </div>
        <span className={cn("flex h-9 w-9 items-center justify-center rounded-lg", tone)}>
          <Icon className="h-4 w-4" />
        </span>
      </div>
      <p className="mt-3 text-[11px] text-muted-foreground">{detail}</p>
    </article>
  );
}

function SuggestionPreview({ item }: { item: AiSuggestionItem }) {
  return (
    <li className="flex flex-col gap-3 py-4 sm:flex-row sm:items-start">
      <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
        {item.kind === "embedding" ? (
          <DatabaseZap className="h-4 w-4" />
        ) : item.kind === "summary" ? (
          <FileText className="h-4 w-4" />
        ) : (
          <Tags className="h-4 w-4" />
        )}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <Link
            href={`/dashboard/persons/${item.person_id}`}
            className="font-medium hover:text-primary"
          >
            {item.person_name}
          </Link>
          <span
            className={cn(
              "rounded-full px-2 py-0.5 text-[10px] font-semibold",
              AI_SUGGESTION_STATUS_COLORS[item.status],
            )}
          >
            {AI_SUGGESTION_STATUS_LABELS[item.status]}
          </span>
          <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">
            {AI_SUGGESTION_KIND_LABELS[item.kind]}
          </span>
        </div>
        <p className="mt-1 text-xs font-medium">{item.title}</p>
        <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">
          {item.description}
        </p>
      </div>
      <Link
        href="/dashboard/ai/suggestions"
        className="inline-flex h-8 shrink-0 items-center justify-center gap-1 rounded-md border border-border px-2.5 text-xs hover:bg-accent"
      >
        Otwórz <ArrowRight className="h-3.5 w-3.5" />
      </Link>
    </li>
  );
}

export function AiCentreClient() {
  const queryClient = useQueryClient();
  const dashboardQuery = useQuery({
    queryKey: ["ai", "dashboard"],
    queryFn: () => aiApi.dashboard(),
  });

  const batchEmbeddingMutation = useMutation({
    mutationFn: () => aiApi.batchEmbeddings({ overwrite_existing: false, batch_size: 50 }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["ai"] });
    },
  });

  const batchTagMutation = useMutation({
    mutationFn: () => aiApi.batchTags({ only_untagged: true }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["ai"] });
    },
  });

  const dashboard = dashboardQuery.data?.data;
  const actionError =
    batchEmbeddingMutation.error || batchTagMutation.error
      ? getApiErrorMessage(batchEmbeddingMutation.error ?? batchTagMutation.error)
      : "";
  const coverage = Math.min(100, Math.max(0, dashboard?.coverage_percent ?? 0));
  const embeddingBatchDisabled = dashboard?.embedding_provider === "disabled";
  const tagBatchDisabled = dashboard?.summary_provider === "extractive-fallback";

  if (dashboardQuery.isLoading) {
    return (
      <div className="flex min-h-[420px] items-center justify-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> Ładowanie centrum AI…
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className="admin-card mx-auto max-w-xl p-8 text-center">
        <AlertTriangle className="mx-auto h-8 w-8 text-amber-500" />
        <h1 className="mt-3 text-lg font-semibold">Nie udało się pobrać centrum AI</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Sprawdź połączenie z API i spróbuj ponownie.
        </p>
        <button
          onClick={() => dashboardQuery.refetch()}
          className="mt-5 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
        >
          Odśwież dane
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1500px] space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="admin-label">AI</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Centrum AI</h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            Monitoruj pokrycie embeddingami, stan dostawców oraz kolejkę sugestii,
            które wymagają świadomej decyzji redaktora.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => dashboardQuery.refetch()}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-border px-4 text-sm font-semibold hover:bg-accent"
          >
            <RefreshCw className={cn("h-4 w-4", dashboardQuery.isFetching && "animate-spin")} />
            Odśwież
          </button>
          <Link
            href="/dashboard/ai/suggestions"
            className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground shadow-sm hover:bg-primary/90"
          >
            Sugestie ({dashboard.pending_suggestions}) <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Metryki AI">
        <MetricCard
          label="Pokrycie embeddingami"
          value={`${coverage.toFixed(0)}%`}
          detail={`${dashboard.total_embeddings.toLocaleString("pl-PL")} z ${dashboard.total_persons.toLocaleString("pl-PL")} aktywnych profili`}
          icon={BrainCircuit}
          tone={metricTones.embeddings}
        />
        <MetricCard
          label="Brakujące embeddingi"
          value={dashboard.missing_embeddings}
          detail="Nie trafią do wyszukiwania semantycznego ani podobnych postaci"
          icon={DatabaseZap}
          tone={metricTones.missing}
        />
        <MetricCard
          label="Sugestie aktywne"
          value={dashboard.pending_suggestions}
          detail="Do decyzji redaktora lub gotowe do wygenerowania"
          icon={Sparkles}
          tone={metricTones.suggestions}
        />
        <MetricCard
          label="Zablokowane"
          value={dashboard.blocked_suggestions}
          detail="Wymagają skonfigurowania OpenAI/Ollama albo embeddingów"
          icon={AlertTriangle}
          tone={metricTones.blocked}
        />
      </section>

      {actionError && (
        <div className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /> {actionError}
        </div>
      )}

      <section className="grid gap-5 xl:grid-cols-[1fr_.85fr]">
        <article className="admin-card p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 className="text-sm font-semibold">Status modułów</h2>
              <p className="mt-1 text-xs text-muted-foreground">
                Konfiguracja: embeddingi {dashboard.embedding_provider} · model{" "}
                {dashboard.embedding_model} · streszczenia {dashboard.summary_provider}
              </p>
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-muted px-2.5 py-1 text-[11px] text-muted-foreground">
              Ostatni embedding: {dashboard.last_generated_at ? formatDateTime(dashboard.last_generated_at) : "brak"}
            </span>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {dashboard.feature_statuses.map((feature) => {
              const Icon = featureIcons[feature.key] ?? Bot;
              return (
                <article key={feature.key} className="rounded-xl border border-border bg-background p-4">
                  <div className="flex items-start justify-between gap-3">
                    <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <Icon className="h-4 w-4" />
                    </span>
                    <span
                      className={cn(
                        "rounded-full px-2 py-1 text-[10px] font-semibold",
                        AI_FEATURE_STATUS_COLORS[feature.status] ?? "bg-muted text-muted-foreground",
                      )}
                    >
                      {AI_FEATURE_STATUS_LABELS[feature.status] ?? feature.status}
                    </span>
                  </div>
                  <h3 className="mt-3 text-sm font-semibold">{feature.label}</h3>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">
                    {feature.description}
                  </p>
                  <p className="mt-3 text-[11px] font-medium text-foreground/75">
                    {feature.detail}
                  </p>
                </article>
              );
            })}
          </div>

          <div className="mt-5">
            <div className="mb-2 flex items-center justify-between text-xs">
              <span className="font-medium">Postęp embeddingów</span>
              <span className="text-muted-foreground">{coverage.toFixed(2)}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <div className="h-full rounded-full bg-primary" style={{ width: `${coverage}%` }} />
            </div>
          </div>
        </article>

        <article className="admin-card p-5">
          <h2 className="text-sm font-semibold">Akcje operacyjne</h2>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            Batchowe zadania trafiają do Celery. Pojedyncze akcje dla konkretnych
            profili są dostępne w kolejce sugestii.
          </p>
          <div className="mt-5 space-y-3">
            <button
              disabled={batchEmbeddingMutation.isPending || embeddingBatchDisabled}
              onClick={() => batchEmbeddingMutation.mutate()}
              className="flex w-full items-center justify-between gap-3 rounded-xl border border-border p-4 text-left transition-colors hover:border-primary/40 disabled:cursor-wait disabled:opacity-60"
            >
              <span>
                <span className="block text-sm font-semibold">Wygeneruj brakujące embeddingi</span>
                <span className="mt-1 block text-xs text-muted-foreground">
                  {embeddingBatchDisabled
                    ? "Wymaga skonfigurowanego dostawcy embeddingów."
                    : "Przetwarza aktywne profile bez wektora semantycznego."}
                </span>
              </span>
              {batchEmbeddingMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <WandSparkles className="h-4 w-4 text-primary" />
              )}
            </button>
            <button
              disabled={batchTagMutation.isPending || tagBatchDisabled}
              onClick={() => batchTagMutation.mutate()}
              className="flex w-full items-center justify-between gap-3 rounded-xl border border-border p-4 text-left transition-colors hover:border-primary/40 disabled:cursor-wait disabled:opacity-60"
            >
              <span>
                <span className="block text-sm font-semibold">Auto-tagi dla nieotagowanych</span>
                <span className="mt-1 block text-xs text-muted-foreground">
                  {tagBatchDisabled
                    ? "Wymaga dostawcy OpenAI albo Ollama."
                    : "Uruchamia tagowanie tylko tam, gdzie pole ai_tags jest puste."}
                </span>
              </span>
              {batchTagMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Tags className="h-4 w-4 text-primary" />
              )}
            </button>
          </div>
          <div className="mt-5 rounded-lg bg-muted/50 p-4 text-xs leading-5 text-muted-foreground">
            <CheckCircle2 className="mb-2 h-4 w-4 text-emerald-500" />
            AI zapisuje sugestie w polach roboczych. Publikowana treść nadal
            wymaga decyzji redakcyjnej — to bezpieczniejszy model dla danych
            hagiograficznych.
          </div>
        </article>
      </section>

      <section className="admin-card p-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold">Najnowsze sugestie i zadania</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              Pierwsze elementy z kolejki AI, posortowane według pilności.
            </p>
          </div>
          <Link href="/dashboard/ai/suggestions" className="text-xs font-semibold text-primary">
            Zobacz wszystkie
          </Link>
        </div>
        {dashboard.recent_suggestions.length ? (
          <ul className="mt-4 divide-y divide-border">
            {dashboard.recent_suggestions.map((item) => (
              <SuggestionPreview key={item.id} item={item} />
            ))}
          </ul>
        ) : (
          <div className="mt-6 rounded-lg bg-emerald-50 p-5 text-center text-xs text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300">
            Brak aktywnych sugestii AI dla aktualnych danych.
          </div>
        )}
      </section>
    </div>
  );
}
