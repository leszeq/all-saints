"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Bot,
  CheckCircle2,
  DatabaseZap,
  FileText,
  Loader2,
  RefreshCw,
  Search,
  Sparkles,
  Tags,
} from "lucide-react";
import { aiApi, getApiErrorMessage } from "@/lib/api";
import {
  AI_SUGGESTION_KIND_LABELS,
  AI_SUGGESTION_STATUS_COLORS,
  AI_SUGGESTION_STATUS_LABELS,
  type AiSuggestionItem,
  type AiSuggestionKind,
  type AiSuggestionStatus,
} from "@/lib/ai";
import { cn, formatDateTime } from "@/lib/utils";

type KindFilter = "" | AiSuggestionKind;
type StatusFilter = "" | AiSuggestionStatus;

const kindOptions: Array<{ value: KindFilter; label: string }> = [
  { value: "", label: "Wszystkie" },
  { value: "embedding", label: "Embeddingi" },
  { value: "summary", label: "Streszczenia" },
  { value: "tags", label: "Tagi" },
];

function renderKindIcon(kind: AiSuggestionKind) {
  if (kind === "embedding") return <DatabaseZap className="h-4 w-4" />;
  if (kind === "summary") return <FileText className="h-4 w-4" />;
  return <Tags className="h-4 w-4" />;
}

function actionLabel(item: AiSuggestionItem) {
  if (item.status === "blocked") return "Zablokowane";
  if (item.action === "generate_embedding") return "Generuj embedding";
  if (item.action === "generate_summary") return "Generuj streszczenie";
  if (item.action === "generate_tags") return "Generuj tagi";
  return "Otwórz do decyzji";
}

function confidenceTone(score: number) {
  if (score >= 80) return "bg-emerald-500";
  if (score >= 60) return "bg-blue-500";
  if (score > 0) return "bg-amber-500";
  return "bg-rose-500";
}

function SuggestionCard({
  item,
  busy,
  onAction,
}: {
  item: AiSuggestionItem;
  busy: boolean;
  onAction: (item: AiSuggestionItem) => void;
}) {
  const canRunAction = item.status !== "blocked" && item.action !== "review_person";

  return (
    <article className="admin-card p-5 transition-colors hover:border-primary/40">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start">
        <div className="flex min-w-0 flex-1 gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
            {renderKindIcon(item.kind)}
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <Link
                href={`/dashboard/persons/${item.person_id}`}
                className="truncate text-sm font-semibold hover:text-primary"
              >
                {item.person_name}
              </Link>
              <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">
                {AI_SUGGESTION_KIND_LABELS[item.kind]}
              </span>
              <span
                className={cn(
                  "rounded-full px-2 py-0.5 text-[10px] font-semibold",
                  AI_SUGGESTION_STATUS_COLORS[item.status],
                )}
              >
                {AI_SUGGESTION_STATUS_LABELS[item.status]}
              </span>
            </div>
            <h2 className="mt-2 text-base font-semibold">{item.title}</h2>
            <p className="mt-1 max-w-3xl text-xs leading-5 text-muted-foreground">
              {item.description}
            </p>
          </div>
        </div>

        <div className="flex shrink-0 flex-wrap gap-2 xl:justify-end">
          {canRunAction ? (
            <button
              disabled={busy}
              onClick={() => onAction(item)}
              className="inline-flex h-9 items-center justify-center gap-2 rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground hover:bg-primary/90 disabled:cursor-wait disabled:opacity-60"
            >
              {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
              {actionLabel(item)}
            </button>
          ) : (
            <Link
              href={item.action_href}
              className={cn(
                "inline-flex h-9 items-center justify-center gap-2 rounded-lg px-3 text-xs font-semibold",
                item.status === "blocked"
                  ? "pointer-events-none border border-border text-muted-foreground opacity-60"
                  : "border border-border hover:bg-accent",
              )}
            >
              {actionLabel(item)} <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          )}
          <Link
            href={item.action_href}
            className="inline-flex h-9 items-center justify-center gap-2 rounded-lg border border-border px-3 text-xs font-semibold hover:bg-accent"
          >
            Edytuj osobę <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>

      <div className="mt-5 grid gap-3 lg:grid-cols-[1fr_1fr_.45fr]">
        <div className="rounded-xl border border-border bg-muted/30 p-4">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Obecna wartość
          </p>
          <p className="mt-2 text-xs leading-5 text-foreground/80">
            {item.current_value ?? "Brak wartości redakcyjnej lub nie dotyczy."}
          </p>
        </div>
        <div className="rounded-xl border border-primary/20 bg-primary/[0.03] p-4">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-primary">
            Sugestia / zadanie AI
          </p>
          <p className="mt-2 text-xs leading-5 text-foreground/80">
            {item.suggested_value ?? "Brak zapisanej sugestii."}
          </p>
        </div>
        <div className="rounded-xl border border-border bg-background p-4">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Pewność
          </p>
          <div className="mt-3 flex items-center gap-2">
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
              <div
                className={cn("h-full rounded-full", confidenceTone(item.confidence))}
                style={{ width: `${item.confidence}%` }}
              />
            </div>
            <span className="text-xs font-semibold">{item.confidence}%</span>
          </div>
          <p className="mt-3 text-[11px] leading-4 text-muted-foreground">{item.reason}</p>
          <p className="mt-2 text-[10px] text-muted-foreground">
            Aktualizacja: {formatDateTime(item.updated_at)}
          </p>
        </div>
      </div>
    </article>
  );
}

export function AiSuggestionsClient() {
  const queryClient = useQueryClient();
  const [kindFilter, setKindFilter] = useState<KindFilter>("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("");
  const [search, setSearch] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const suggestionsQuery = useQuery({
    queryKey: ["ai", "suggestions", kindFilter, statusFilter],
    queryFn: () =>
      aiApi.suggestions({
        limit: 100,
        ...(kindFilter ? { kind: kindFilter } : {}),
        ...(statusFilter ? { status: statusFilter } : {}),
      }),
  });

  const countsQuery = useQuery({
    queryKey: ["ai", "suggestions", "counts", kindFilter],
    queryFn: () =>
      aiApi.suggestions({
        limit: 1,
        ...(kindFilter ? { kind: kindFilter } : {}),
      }),
    staleTime: 30_000,
  });

  const actionMutation = useMutation({
    mutationFn: (item: AiSuggestionItem) => {
      if (item.action === "generate_embedding") return aiApi.generateEmbedding(item.person_id);
      if (item.action === "generate_summary") return aiApi.generateSummary(item.person_id);
      if (item.action === "generate_tags") return aiApi.generateTags(item.person_id);
      throw new Error("Ta sugestia wymaga ręcznej decyzji redaktora.");
    },
    onMutate: () => {
      setSuccessMessage("");
    },
    onSuccess: async (_response, item) => {
      setSuccessMessage(`Zadanie AI dla rekordu „${item.person_name}” zostało wykonane.`);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["ai"] }),
        queryClient.invalidateQueries({ queryKey: ["persons"] }),
      ]);
    },
  });

  const suggestions = suggestionsQuery.data?.data;
  const counts = countsQuery.data?.data;
  const actionError = actionMutation.error ? getApiErrorMessage(actionMutation.error) : "";
  const visibleItems = useMemo(() => {
    const term = search.trim().toLowerCase();
    const items = suggestions?.items ?? [];
    if (!term) return items;
    return items.filter((item) =>
      [
        item.person_name,
        item.title,
        item.description,
        item.reason,
        item.current_value ?? "",
        item.suggested_value ?? "",
      ]
        .join(" ")
        .toLowerCase()
        .includes(term),
    );
  }, [search, suggestions?.items]);

  const statusCards: Array<{ label: string; value: number; filter: StatusFilter }> = [
    {
      label: "Wszystkie",
      value:
        (counts?.pending_review ?? 0) +
        (counts?.ready_to_generate ?? 0) +
        (counts?.blocked ?? 0),
      filter: "",
    },
    { label: "Do decyzji", value: counts?.pending_review ?? 0, filter: "pending_review" },
    {
      label: "Do wygenerowania",
      value: counts?.ready_to_generate ?? 0,
      filter: "ready_to_generate",
    },
    { label: "Zablokowane", value: counts?.blocked ?? 0, filter: "blocked" },
  ];

  return (
    <div className="mx-auto max-w-[1500px] space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <Link
            href="/dashboard/ai"
            className="mb-3 inline-flex items-center gap-1 text-xs font-semibold text-muted-foreground hover:text-primary"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Centrum AI
          </Link>
          <p className="admin-label">AI</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Sugestie</h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            Przeglądaj robocze propozycje AI i uruchamiaj generowanie dla pojedynczych
            rekordów bez nadpisywania treści zatwierdzonej przez redakcję.
          </p>
        </div>
        <button
          onClick={() => {
            suggestionsQuery.refetch();
            countsQuery.refetch();
          }}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-border px-4 text-sm font-semibold hover:bg-accent"
        >
          <RefreshCw
            className={cn(
              "h-4 w-4",
              (suggestionsQuery.isFetching || countsQuery.isFetching) && "animate-spin",
            )}
          />
          Odśwież
        </button>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Status sugestii">
        {statusCards.map((card) => (
          <button
            key={card.label}
            onClick={() => setStatusFilter(card.filter)}
            className={cn(
              "admin-card p-4 text-left transition-colors hover:border-primary/40",
              statusFilter === card.filter && "border-primary bg-primary/[0.04] ring-1 ring-primary/20",
            )}
          >
            <span className="text-xs text-muted-foreground">{card.label}</span>
            <span className="mt-1 block text-2xl font-semibold">
              {card.value.toLocaleString("pl-PL")}
            </span>
          </button>
        ))}
      </section>

      <section className="admin-card p-4">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center">
          <div className="relative min-w-64 flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Szukaj po osobie, sugestii, uzasadnieniu…"
              className="h-10 w-full rounded-lg border border-input bg-background pl-9 pr-3 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </div>
          <div className="flex flex-wrap gap-2">
            {kindOptions.map((option) => (
              <button
                key={option.value || "all"}
                onClick={() => {
                  setKindFilter(option.value);
                  setStatusFilter("");
                }}
                className={cn(
                  "h-9 rounded-lg border border-border px-3 text-xs font-semibold transition-colors hover:bg-accent",
                  kindFilter === option.value && "border-primary bg-primary text-primary-foreground hover:bg-primary",
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </section>

      {successMessage && (
        <div className="flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-200">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> {successMessage}
        </div>
      )}
      {actionError && (
        <div className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /> {actionError}
        </div>
      )}

      {suggestionsQuery.isLoading ? (
        <div className="flex min-h-[320px] items-center justify-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Ładowanie sugestii…
        </div>
      ) : suggestionsQuery.isError ? (
        <div className="admin-card p-8 text-center">
          <AlertTriangle className="mx-auto h-8 w-8 text-amber-500" />
          <h2 className="mt-3 text-lg font-semibold">Nie udało się pobrać sugestii</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Sprawdź połączenie z API i spróbuj ponownie.
          </p>
        </div>
      ) : visibleItems.length === 0 ? (
        <div className="admin-card p-10 text-center">
          <Bot className="mx-auto h-8 w-8 text-emerald-500" />
          <h2 className="mt-3 text-sm font-semibold">Brak sugestii dla wybranych filtrów</h2>
          <p className="mx-auto mt-2 max-w-xl text-xs leading-5 text-muted-foreground">
            Zmień typ, status albo wyszukiwaną frazę. Jeśli kolejka jest zupełnie pusta,
            oznacza to, że aktywne rekordy nie mają obecnie zadań AI.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {visibleItems.map((item) => (
            <SuggestionCard
              key={item.id}
              item={item}
              busy={actionMutation.isPending && actionMutation.variables?.id === item.id}
              onAction={(suggestion) => actionMutation.mutate(suggestion)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
