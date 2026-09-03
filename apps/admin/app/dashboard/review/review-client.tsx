"use client";

import * as Dialog from "@radix-ui/react-dialog";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Edit3,
  Loader2,
  MessageSquareText,
  RefreshCw,
  Search,
  Send,
  X,
} from "lucide-react";
import { SaintAvatar } from "@/components/persons/saint-avatar";
import { editorialApi, getApiErrorMessage } from "@/lib/api";
import { useAuthStore } from "@/lib/store/auth";
import {
  EDITORIAL_PRIORITY_COLORS,
  EDITORIAL_PRIORITY_LABELS,
  formatEditorialAge,
  type EditorialPriority,
  type PublicationStatus,
} from "@/lib/editorial";
import {
  cn,
  formatDateTime,
  PERSON_STATUS_COLORS,
  PERSON_STATUS_LABELS,
  PERSON_TYPE_LABELS,
} from "@/lib/utils";

const PER_PAGE = 15;

type QueueStatusFilter = "" | "draft" | "review";
type QueuePriorityFilter = "" | EditorialPriority;

export interface EditorialQueueInitialFilters {
  status: QueueStatusFilter;
  priority: QueuePriorityFilter;
  attention: boolean;
}

export function EditorialQueueClient({
  initialFilters,
}: {
  initialFilters: EditorialQueueInitialFilters;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<QueueStatusFilter>(initialFilters.status);
  const [priorityFilter, setPriorityFilter] = useState<QueuePriorityFilter>(initialFilters.priority);
  const [attentionFilter, setAttentionFilter] = useState(initialFilters.attention);
  const [actionError, setActionError] = useState("");
  const [returnDecision, setReturnDecision] = useState<{
    id: string;
    version: number;
    name: string;
  } | null>(null);
  const [returnNote, setReturnNote] = useState("");
  const hasPermission = useAuthStore((state) => state.hasPermission);
  const canCreate = hasPermission("persons:create");
  const canEdit = hasPermission("persons:update");
  const canSubmit = hasPermission("persons:submit");
  const canReview = hasPermission("persons:review");

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedSearch(search.trim());
      setPage(1);
    }, 350);
    return () => window.clearTimeout(timer);
  }, [search]);

  const queueQuery = useQuery({
    queryKey: ["editorial", "queue", page, debouncedSearch, statusFilter, priorityFilter, attentionFilter],
    queryFn: () =>
      editorialApi.queue({
        page,
        per_page: PER_PAGE,
        ...(debouncedSearch ? { search: debouncedSearch } : {}),
        ...(statusFilter ? { status: statusFilter } : {}),
        ...(priorityFilter ? { priority: priorityFilter } : {}),
        ...(attentionFilter ? { attention: true } : {}),
      }),
  });

  const transitionMutation = useMutation({
    mutationFn: ({ id, targetStatus, version, note }: { id: string; targetStatus: PublicationStatus; version: number; note?: string }) =>
      editorialApi.transition(id, targetStatus, version, note),
    onMutate: () => setActionError(""),
    onSuccess: async () => {
      setReturnDecision(null);
      setReturnNote("");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["editorial"] }),
        queryClient.invalidateQueries({ queryKey: ["persons"] }),
      ]);
    },
    onError: (error) => setActionError(getApiErrorMessage(error)),
  });

  const queue = queueQuery.data?.data;
  const items = queue?.items ?? [];
  const counts = queue?.counts;

  const changeFilters = (
    status: QueueStatusFilter,
    priority: QueuePriorityFilter,
    attention = false,
  ) => {
    setStatusFilter(status);
    setPriorityFilter(priority);
    setAttentionFilter(attention);
    setPage(1);

    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (priority) params.set("priority", priority);
    if (attention) params.set("attention", "1");
    const queryString = params.toString();
    router.replace(queryString ? `/dashboard/review?${queryString}` : "/dashboard/review", {
      scroll: false,
    });
  };

  return (
    <div className="mx-auto max-w-[1500px] space-y-5">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="admin-label">Redakcja</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Kolejka redakcyjna</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Przygotuj szkice, przekaż je do recenzji i publikuj zweryfikowane rekordy.
          </p>
        </div>
        {canCreate && (
          <Link
            href="/dashboard/persons/new"
            className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground hover:bg-primary/90"
          >
            Dodaj nowy rekord <ArrowRight className="h-4 w-4" />
          </Link>
        )}
      </header>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6" aria-label="Stan kolejki">
        {[
          { label: "Wszystkie", value: counts?.total ?? 0, status: "" as const, priority: "" as const },
          { label: "Szkice", value: counts?.draft ?? 0, status: "draft" as const, priority: "" as const },
          { label: "W recenzji", value: counts?.review ?? 0, status: "review" as const, priority: "" as const },
          { label: "Wymagają uwagi", value: counts?.attention ?? 0, status: "" as const, priority: "" as const, attention: true },
          { label: "Pilne", value: counts?.urgent ?? 0, status: "" as const, priority: "urgent" as const },
          { label: "Wysoki priorytet", value: counts?.high ?? 0, status: "" as const, priority: "high" as const },
        ].map(({ label, value, status, priority, attention = false }) => {
          const selected =
            statusFilter === status &&
            priorityFilter === priority &&
            attentionFilter === attention;
          return (
            <button
              key={label}
              onClick={() => changeFilters(status, priority, attention)}
              className={cn(
                "admin-card p-4 text-left transition-colors hover:border-primary/40",
                selected && "border-primary bg-primary/[0.04] ring-1 ring-primary/20",
              )}
            >
              <span className="text-xs text-muted-foreground">{label}</span>
              <span className="mt-1 block text-2xl font-semibold">{value.toLocaleString("pl-PL")}</span>
            </button>
          );
        })}
      </section>

      <section className="admin-card overflow-hidden">
        <div className="flex flex-col gap-3 border-b border-border p-4 lg:flex-row lg:items-center">
          <div className="relative min-w-64 flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Szukaj po imieniu lub nazwie łacińskiej…"
              className="h-10 w-full rounded-lg border border-input bg-background pl-9 pr-3 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(event) => changeFilters(event.target.value as QueueStatusFilter, priorityFilter)}
            className="h-10 rounded-lg border border-input bg-background px-3 text-sm outline-none focus:border-primary"
          >
            <option value="">Wszystkie etapy</option>
            <option value="draft">Szkice</option>
            <option value="review">W recenzji</option>
          </select>
          <select
            value={priorityFilter}
            onChange={(event) => changeFilters(statusFilter, event.target.value as QueuePriorityFilter)}
            className="h-10 rounded-lg border border-input bg-background px-3 text-sm outline-none focus:border-primary"
          >
            <option value="">Każdy priorytet</option>
            <option value="urgent">Pilny</option>
            <option value="high">Wysoki</option>
            <option value="normal">Standardowy</option>
          </select>
          <button
            onClick={() => queueQuery.refetch()}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-border px-3 text-sm text-muted-foreground hover:bg-accent hover:text-foreground"
          >
            <RefreshCw className={cn("h-4 w-4", queueQuery.isFetching && "animate-spin")} /> Odśwież
          </button>
        </div>

        {actionError && (
          <div className="m-4 flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /> {actionError}
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="min-w-[1180px] w-full text-sm">
            <thead className="border-b border-border bg-muted/40">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Rekord</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Etap / priorytet</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Kompletność</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Problemy</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Ostatnia zmiana</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">Decyzja</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {queueQuery.isLoading ? (
                <tr><td colSpan={6} className="py-16 text-center text-muted-foreground"><Loader2 className="mx-auto mb-2 h-5 w-5 animate-spin" />Ładowanie kolejki…</td></tr>
              ) : queueQuery.isError ? (
                <tr><td colSpan={6} className="py-16 text-center text-rose-600">Nie udało się pobrać kolejki redakcyjnej.</td></tr>
              ) : items.length === 0 ? (
                <tr><td colSpan={6} className="py-16 text-center"><Check className="mx-auto mb-2 h-7 w-7 text-emerald-500" /><p className="font-medium">Brak rekordów dla wybranych filtrów</p><p className="mt-1 text-xs text-muted-foreground">Zmień kryteria albo dodaj nowy szkic.</p></td></tr>
              ) : items.map((item) => {
                const mutationForItem = transitionMutation.isPending && transitionMutation.variables?.id === item.id;
                return (
                  <tr key={item.id} className="align-top hover:bg-muted/20">
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-3">
                        <SaintAvatar name={item.canonical_name} avatar={item.avatar} className="h-10 w-10 text-xs" />
                        <div className="min-w-0">
                          <Link href={`/dashboard/persons/${item.id}`} className="block max-w-64 truncate font-medium hover:text-primary">{item.canonical_name}</Link>
                          <p className="mt-1 text-xs text-muted-foreground">{PERSON_TYPE_LABELS[item.person_type] ?? item.person_type}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex flex-col items-start gap-1.5">
                        <span className={cn("rounded-full px-2 py-1 text-[10px] font-semibold", PERSON_STATUS_COLORS[item.status])}>{PERSON_STATUS_LABELS[item.status]}</span>
                        <span className={cn("rounded-full px-2 py-1 text-[10px] font-semibold", EDITORIAL_PRIORITY_COLORS[item.priority])}>{EDITORIAL_PRIORITY_LABELS[item.priority]}</span>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <div className="w-44">
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted"><div className={cn("h-full rounded-full", item.completeness_score >= 85 ? "bg-emerald-500" : item.completeness_score >= 60 ? "bg-blue-500" : item.completeness_score >= 35 ? "bg-amber-500" : "bg-rose-500")} style={{ width: `${item.completeness_score}%` }} /></div>
                          <span className="text-xs font-semibold">{item.completeness_score}%</span>
                        </div>
                        <details className="group mt-2 text-[10px]">
                          <summary className="flex cursor-pointer list-none items-center gap-1 text-muted-foreground hover:text-foreground">
                            <CircleHelp className="h-3 w-3" /> Jak liczymy?
                          </summary>
                          <ul className="mt-2 space-y-1.5 rounded-lg border border-border bg-background p-2.5 shadow-sm">
                            {item.completeness_criteria.map((criterion) => (
                              <li key={criterion.key} className="flex items-start justify-between gap-2">
                                <span className={criterion.completed ? "text-foreground" : "text-muted-foreground"}>
                                  {criterion.completed ? "✓" : "—"} {criterion.label}
                                </span>
                                <span className="shrink-0 font-semibold">+{criterion.weight}</span>
                              </li>
                            ))}
                          </ul>
                        </details>
                      </div>
                    </td>
                    <td className="max-w-[310px] px-4 py-4">
                      <div className="flex flex-wrap gap-1.5">
                        {item.issues.length ? item.issues.slice(0, 3).map((issue) => <span key={issue.code} className={cn("rounded-md border px-2 py-1 text-[10px]", issue.severity === "critical" ? "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/20 dark:text-rose-300" : "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/50 dark:bg-amber-950/20 dark:text-amber-300")}>{issue.label}</span>) : <span className="text-xs text-emerald-600">Brak wykrytych problemów</span>}
                        {item.issues.length > 3 && <span className="px-1 py-1 text-[10px] text-muted-foreground">+{item.issues.length - 3}</span>}
                      </div>
                    </td>
                    <td className="px-4 py-4 text-xs">
                      <p className="font-medium">{item.last_modified_by?.full_name ?? "System"}</p>
                      <p className="mt-1 text-muted-foreground">{formatDateTime(item.updated_at)}</p>
                      <p className="mt-0.5 text-[10px] text-muted-foreground">{formatEditorialAge(item.age_days)}</p>
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex justify-end gap-1.5">
                        {canEdit && <Link href={`/dashboard/persons/${item.id}/edit`} className="inline-flex h-8 items-center gap-1 rounded-md border border-border px-2.5 text-xs hover:bg-accent"><Edit3 className="h-3.5 w-3.5" /> Edytuj</Link>}
                        {item.status === "draft" && canSubmit ? (
                          <button disabled={mutationForItem} onClick={() => transitionMutation.mutate({ id: item.id, targetStatus: "review", version: item.version })} className="inline-flex h-8 items-center gap-1 rounded-md bg-blue-600 px-2.5 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-50">{mutationForItem ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />} Do recenzji</button>
                        ) : item.status === "review" && canReview ? (
                          <>
                            <button disabled={mutationForItem} onClick={() => { setActionError(""); setReturnNote(""); setReturnDecision({ id: item.id, version: item.version, name: item.canonical_name }); }} className="inline-flex h-8 items-center gap-1 rounded-md border border-border px-2.5 text-xs hover:bg-accent disabled:opacity-50"><ArrowLeft className="h-3.5 w-3.5" /> Zwróć</button>
                            <button disabled={mutationForItem || !item.can_publish} title={!item.can_publish ? "Uzupełnij krytyczne braki przed akceptacją" : "Zatwierdź i opublikuj rekord"} onClick={() => transitionMutation.mutate({ id: item.id, targetStatus: "published", version: item.version })} className="inline-flex h-8 items-center gap-1 rounded-md bg-emerald-600 px-2.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-40">{mutationForItem ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />} Zatwierdź</button>
                          </>
                        ) : (
                          <span className="inline-flex h-8 items-center rounded-md bg-muted px-2.5 text-[10px] font-medium text-muted-foreground">Tylko podgląd</span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <footer className="flex flex-col gap-3 border-t border-border px-4 py-3 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <span>{queue ? `Wyświetlono ${items.length} z ${queue.total} rekordów` : "—"}</span>
          <div className="flex items-center gap-2">
            <button disabled={page <= 1} onClick={() => setPage((value) => value - 1)} className="inline-flex h-8 items-center gap-1 rounded-md border border-border px-2.5 hover:bg-accent disabled:opacity-40"><ChevronLeft className="h-3.5 w-3.5" /> Wstecz</button>
            <span className="px-2">Strona {page} z {queue?.pages ?? 1}</span>
            <button disabled={!queue || page >= queue.pages} onClick={() => setPage((value) => value + 1)} className="inline-flex h-8 items-center gap-1 rounded-md border border-border px-2.5 hover:bg-accent disabled:opacity-40">Dalej <ChevronRight className="h-3.5 w-3.5" /></button>
          </div>
        </footer>
      </section>

      <Dialog.Root open={returnDecision !== null} onOpenChange={(open) => { if (!open) { setReturnDecision(null); setReturnNote(""); } }}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-slate-950/55 backdrop-blur-[2px]" />
          <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-xl border border-border bg-card p-6 shadow-2xl focus:outline-none">
            <Dialog.Title className="pr-10 text-lg font-semibold">Zwróć rekord do przeredagowania</Dialog.Title>
            <Dialog.Description className="mt-1 text-sm leading-6 text-muted-foreground">
              Wskaż redaktorowi konkretne poprawki dla: <span className="font-medium text-foreground">{returnDecision?.name}</span>.
            </Dialog.Description>
            <Dialog.Close className="absolute right-4 top-4 flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground" aria-label="Zamknij"><X className="h-4 w-4" /></Dialog.Close>
            <label className="mt-5 block text-sm font-medium" htmlFor="review-note">Komentarz recenzenta</label>
            <div className="relative mt-2">
              <MessageSquareText className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <textarea id="review-note" value={returnNote} onChange={(event) => setReturnNote(event.target.value)} rows={5} maxLength={2000} placeholder="Np. uzupełnij źródło dla daty kanonizacji i doprecyzuj drugi akapit biogramu…" className="w-full rounded-lg border border-input bg-background py-2.5 pl-9 pr-3 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/15" />
            </div>
            <p className="mt-1 text-[11px] text-muted-foreground">Komentarz jest wymagany i zostanie zapisany w historii rekordu.</p>
            <div className="mt-5 flex justify-end gap-2 border-t border-border pt-4">
              <Dialog.Close className="h-10 rounded-lg border border-border px-4 text-sm font-medium hover:bg-muted">Anuluj</Dialog.Close>
              <button
                disabled={!returnDecision || !returnNote.trim() || transitionMutation.isPending}
                onClick={() => returnDecision && transitionMutation.mutate({ id: returnDecision.id, targetStatus: "draft", version: returnDecision.version, note: returnNote.trim() })}
                className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {transitionMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowLeft className="h-4 w-4" />} Zwróć redaktorowi
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
