"use client";

import Link from "next/link";
import type { ElementType } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  BookOpenText,
  CheckCircle2,
  Clock3,
  FileWarning,
  ImageOff,
  Loader2,
  Plus,
  ShieldCheck,
  Users,
} from "lucide-react";
import { SaintAvatar } from "@/components/persons/saint-avatar";
import { editorialApi } from "@/lib/api";
import { formatEditorialAge, type EditorialQueueItem } from "@/lib/editorial";
import {
  cn,
  formatDateTime,
  PERSON_STATUS_COLORS,
  PERSON_STATUS_LABELS,
} from "@/lib/utils";

const metricTones = {
  review: "text-blue-700 bg-blue-50 dark:bg-blue-950/30 dark:text-blue-300",
  draft: "text-amber-700 bg-amber-50 dark:bg-amber-950/30 dark:text-amber-300",
  quality: "text-rose-700 bg-rose-50 dark:bg-rose-950/30 dark:text-rose-300",
  license: "text-orange-700 bg-orange-50 dark:bg-orange-950/30 dark:text-orange-300",
};

const completionColors: Record<string, string> = {
  complete: "bg-emerald-500",
  partial: "bg-blue-500",
  low: "bg-amber-500",
  critical: "bg-rose-500",
};

function formatMonth(value: string) {
  const [year, month] = value.split("-").map(Number);
  return new Intl.DateTimeFormat("pl-PL", { month: "short" })
    .format(new Date(year, month - 1, 1))
    .replace(".", "");
}

function QueuePreviewRow({ item }: { item: EditorialQueueItem }) {
  return (
    <li className="flex items-center gap-3 py-3">
      <span
        className={cn(
          "h-2 w-2 shrink-0 rounded-full",
          item.priority === "urgent"
            ? "bg-rose-500"
            : item.priority === "high"
              ? "bg-amber-500"
              : "bg-slate-400",
        )}
      />
      <div className="min-w-0 flex-1">
        <Link
          href={`/dashboard/persons/${item.id}`}
          className="block truncate text-xs font-medium hover:text-primary"
        >
          {item.canonical_name}
        </Link>
        <p className="mt-1 truncate text-[10px] text-muted-foreground">
          {item.issues[0]?.label ?? "Gotowy do dalszego etapu"} · kompletność {item.completeness_score}%
        </p>
      </div>
      <span className="text-[10px] text-muted-foreground">
        {formatEditorialAge(item.age_days)}
      </span>
    </li>
  );
}

export default function DashboardPage() {
  const dashboardQuery = useQuery({
    queryKey: ["editorial", "dashboard"],
    queryFn: () => editorialApi.dashboard(),
  });
  const dashboard = dashboardQuery.data?.data;
  const today = new Intl.DateTimeFormat("pl-PL", {
    weekday: "long",
    day: "numeric",
    month: "long",
  }).format(new Date());

  if (dashboardQuery.isLoading) {
    return (
      <div className="flex min-h-[420px] items-center justify-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> Ładowanie danych redakcyjnych…
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className="admin-card mx-auto max-w-xl p-8 text-center">
        <AlertTriangle className="mx-auto h-8 w-8 text-amber-500" />
        <h1 className="mt-3 text-lg font-semibold">Nie udało się pobrać pulpitu</h1>
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

  const metrics: Array<{
    label: string;
    value: number;
    detail: string;
    icon: ElementType;
    tone: string;
  }> = [
    {
      label: "Do recenzji",
      value: dashboard.queue_counts.review,
      detail: "rekordy oczekujące na decyzję",
      icon: Clock3,
      tone: metricTones.review,
    },
    {
      label: "Szkice",
      value: dashboard.queue_counts.draft,
      detail: "rekordy w przygotowaniu",
      icon: FileWarning,
      tone: metricTones.draft,
    },
    {
      label: "Wymagają uwagi",
      value: dashboard.attention_count,
      detail: "profile z istotnymi brakami danych",
      icon: AlertTriangle,
      tone: metricTones.quality,
    },
    {
      label: "Licencje do sprawdzenia",
      value: dashboard.unknown_license_images,
      detail: "obrazy z nieznanym statusem licencji",
      icon: ImageOff,
      tone: metricTones.license,
    },
  ];
  const chartMax = Math.max(1, ...dashboard.monthly_activity.map(({ count }) => count));

  return (
    <div className="mx-auto max-w-[1500px] space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="admin-label capitalize">{today}</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Pulpit redakcyjny</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Bieżąca kondycja {dashboard.total_persons.toLocaleString("pl-PL")} rekordów w bazie wiedzy.
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/dashboard/review"
            className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-border px-4 text-sm font-semibold hover:bg-accent"
          >
            <Clock3 className="h-4 w-4" /> Kolejka ({dashboard.queue_counts.total})
          </Link>
          <Link
            href="/dashboard/persons/new"
            className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground shadow-sm hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" /> Dodaj postać
          </Link>
        </div>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Kolejki operacyjne">
        {metrics.map(({ label, value, detail, icon: Icon, tone }) => (
          <div key={label} className="admin-card p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium text-muted-foreground">{label}</p>
                <p className="mt-2 text-3xl font-semibold tracking-tight">{value.toLocaleString("pl-PL")}</p>
              </div>
              <span className={cn("flex h-9 w-9 items-center justify-center rounded-lg", tone)}>
                <Icon className="h-4 w-4" />
              </span>
            </div>
            <p className="mt-3 text-[11px] text-muted-foreground">{detail}</p>
          </div>
        ))}
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.45fr_.85fr]">
        <article className="admin-card p-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold">Aktywność opublikowanych profili</h2>
              <p className="mt-1 text-xs text-muted-foreground">Rekordy zmienione w ostatnich 12 miesiącach</p>
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300">
              <CheckCircle2 className="h-3 w-3" /> dane bieżące
            </span>
          </div>
          <div className="mt-8 flex h-44 items-end gap-2 border-b border-l border-border px-3 pt-4">
            {dashboard.monthly_activity.map(({ month, count }) => (
              <div key={month} className="group relative flex h-full flex-1 items-end">
                <div
                  className="min-h-0.5 w-full rounded-t-sm bg-primary/75 transition-colors group-hover:bg-primary"
                  style={{ height: `${Math.max(2, (count / chartMax) * 100)}%` }}
                />
                <span className="pointer-events-none absolute -top-5 left-1/2 hidden -translate-x-1/2 rounded bg-foreground px-1.5 py-0.5 text-[9px] text-background group-hover:block">
                  {count}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-2 grid grid-cols-12 text-center text-[9px] text-muted-foreground">
            {dashboard.monthly_activity.map(({ month }) => <span key={month}>{formatMonth(month)}</span>)}
          </div>
        </article>

        <article className="admin-card p-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold">Najpilniejsze w kolejce</h2>
              <p className="mt-1 text-xs text-muted-foreground">
                {dashboard.queue_counts.total} rekordów wymaga pracy redakcyjnej
              </p>
            </div>
            <Link href="/dashboard/review" className="text-xs font-semibold text-primary">Otwórz kolejkę</Link>
          </div>
          {dashboard.queue_preview.length ? (
            <ul className="mt-4 divide-y divide-border">
              {dashboard.queue_preview.map((item) => <QueuePreviewRow key={item.id} item={item} />)}
            </ul>
          ) : (
            <div className="mt-8 rounded-lg bg-emerald-50 p-5 text-center text-xs text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300">
              Kolejka jest pusta — wszystkie rekordy zostały obsłużone.
            </div>
          )}
        </article>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.2fr_.8fr_.8fr]">
        <article className="admin-card p-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold">Ostatnio zmienione rekordy</h2>
              <p className="mt-1 text-xs text-muted-foreground">Najnowsza aktywność w bazie</p>
            </div>
            <Link href="/dashboard/persons" className="inline-flex items-center gap-1 text-xs font-semibold text-primary">
              Lista osób <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
          <div className="mt-4 divide-y divide-border">
            {dashboard.recent_records.map((person) => (
              <div key={person.id} className="flex items-center gap-3 py-3">
                <SaintAvatar name={person.canonical_name} avatar={person.avatar} className="h-8 w-8 text-[10px]" />
                <div className="min-w-0 flex-1">
                  <Link href={`/dashboard/persons/${person.id}`} className="block truncate text-xs font-medium hover:text-primary">
                    {person.canonical_name}
                  </Link>
                  <p className="mt-1 truncate text-[10px] text-muted-foreground">
                    {person.last_modified_by?.full_name ?? "System"} · {formatDateTime(person.updated_at)}
                  </p>
                </div>
                <span className={cn("rounded-full px-2 py-1 text-[9px] font-semibold", PERSON_STATUS_COLORS[person.status])}>
                  {PERSON_STATUS_LABELS[person.status] ?? person.status}
                </span>
              </div>
            ))}
          </div>
        </article>

        <article className="admin-card p-5">
          <h2 className="text-sm font-semibold">Kompletność danych</h2>
          <p className="mt-1 text-xs text-muted-foreground">Wszystkie aktywne profile</p>
          <div className="mt-6 space-y-4">
            {dashboard.completion.map(({ key, label, count, percentage }) => (
              <div key={key}>
                <div className="flex justify-between text-[11px]">
                  <span>{label} <span className="text-muted-foreground">({count})</span></span>
                  <span className="font-semibold">{percentage}%</span>
                </div>
                <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-muted">
                  <div className={cn("h-full rounded-full", completionColors[key])} style={{ width: `${percentage}%` }} />
                </div>
              </div>
            ))}
          </div>
        </article>

        <article className="admin-card p-5">
          <h2 className="text-sm font-semibold">Zasoby redakcyjne</h2>
          <p className="mt-1 text-xs text-muted-foreground">Aktywne dane dostępne przez API</p>
          <dl className="mt-5 space-y-3 text-xs">
            {[
              ["Użytkownicy", dashboard.resources.users, Users],
              ["Państwa", dashboard.resources.countries, ShieldCheck],
              ["Zakony", dashboard.resources.orders, ShieldCheck],
              ["Bibliografia", dashboard.resources.bibliography, BookOpenText],
            ].map(([label, value, Icon]) => {
              const ResourceIcon = Icon as ElementType;
              return (
                <div key={String(label)} className="flex items-center justify-between border-b border-border pb-3">
                  <dt className="flex items-center gap-2 text-muted-foreground"><ResourceIcon className="h-3.5 w-3.5" />{String(label)}</dt>
                  <dd className="font-semibold">{Number(value).toLocaleString("pl-PL")}</dd>
                </div>
              );
            })}
          </dl>
          <div className="mt-5 flex items-center gap-2 rounded-lg bg-emerald-50 px-3 py-2 text-[10px] font-medium text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300">
            <span className="status-dot bg-emerald-500" /> Dane zsynchronizowane z API
          </div>
        </article>
      </section>

      {dashboard.unknown_license_images > 0 && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/20 dark:text-amber-200">
          <AlertTriangle className="h-4 w-4" />
          <span>
            <strong>Do uzupełnienia:</strong> {dashboard.unknown_license_images} obrazów ma nieznaną licencję. Publikacja powiązanych profili jest blokowana.
          </span>
        </div>
      )}
    </div>
  );
}
