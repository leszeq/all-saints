"use client";

import Link from "next/link";
import type { ElementType } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  BookOpenText,
  CheckCircle2,
  Copy,
  Database,
  ExternalLink,
  FileWarning,
  ImageOff,
  Loader2,
  Network,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { SaintAvatar } from "@/components/persons/saint-avatar";
import { editorialApi } from "@/lib/api";
import type {
  EditorialDuplicateGroup,
  EditorialQualityRecord,
  EditorialQualityReport,
  EditorialSourceVerificationItem,
} from "@/lib/editorial";
import {
  cn,
  formatDateTime,
  PERSON_STATUS_COLORS,
  PERSON_STATUS_LABELS,
  PERSON_TYPE_LABELS,
} from "@/lib/utils";

export type QualityTab = "issues" | "duplicates" | "sources";

const tabs: Array<{ key: QualityTab; label: string; href: string; icon: ElementType }> = [
  { key: "issues", label: "Problemy jakości", href: "/dashboard/quality/issues", icon: Database },
  { key: "duplicates", label: "Duplikaty", href: "/dashboard/quality/duplicates", icon: Network },
  { key: "sources", label: "Weryfikacja źródeł", href: "/dashboard/quality/sources", icon: ShieldCheck },
];

const severityTone: Record<string, string> = {
  critical: "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/20 dark:text-rose-300",
  warning: "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/50 dark:bg-amber-950/20 dark:text-amber-300",
};

const sourceTypeLabels: Record<string, string> = {
  bibliography: "Bibliografia",
  historical_source: "Źródło historyczne",
  image: "Obraz",
  person_source: "Przypis do postaci",
};

function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
  tone = "text-primary bg-primary/10",
}: {
  label: string;
  value: number;
  detail: string;
  icon: ElementType;
  tone?: string;
}) {
  return (
    <article className="admin-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-muted-foreground">{label}</p>
          <p className="mt-2 text-3xl font-semibold tracking-tight">
            {value.toLocaleString("pl-PL")}
          </p>
        </div>
        <span className={cn("flex h-9 w-9 items-center justify-center rounded-lg", tone)}>
          <Icon className="h-4 w-4" />
        </span>
      </div>
      <p className="mt-3 text-[11px] text-muted-foreground">{detail}</p>
    </article>
  );
}

function EmptyState({
  icon: Icon,
  title,
  description,
}: {
  icon: ElementType;
  title: string;
  description: string;
}) {
  return (
    <div className="admin-card p-10 text-center">
      <Icon className="mx-auto h-8 w-8 text-emerald-500" />
      <h2 className="mt-3 text-sm font-semibold">{title}</h2>
      <p className="mx-auto mt-2 max-w-lg text-xs leading-5 text-muted-foreground">{description}</p>
    </div>
  );
}

function scoreBar(score: number) {
  return score >= 85 ? "bg-emerald-500" : score >= 60 ? "bg-blue-500" : score >= 35 ? "bg-amber-500" : "bg-rose-500";
}

function lifeYears(person: { birth_year?: number | null; death_year?: number | null }) {
  if (!person.birth_year && !person.death_year) return "Daty nieuzupełnione";
  return `${person.birth_year ?? "?"}–${person.death_year ?? "?"}`;
}

function IssuesPanel({ report }: { report: EditorialQualityReport }) {
  const { issue_breakdown: breakdown, problem_records: records, summary } = report;

  return (
    <div className="space-y-5">
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3" aria-label="Rodzaje problemów">
        {breakdown.map((issue) => (
          <article key={issue.code} className="admin-card p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-medium text-muted-foreground">{issue.label}</p>
                <p className="mt-2 text-2xl font-semibold">{issue.count.toLocaleString("pl-PL")}</p>
              </div>
              <span className={cn("rounded-full border px-2 py-1 text-[10px] font-semibold", severityTone[issue.severity] ?? "border-border bg-muted text-muted-foreground")}>
                {issue.severity === "critical" ? "Krytyczne" : "Ostrzeżenie"}
              </span>
            </div>
          </article>
        ))}
      </section>

      {records.length === 0 ? (
        <EmptyState
          icon={CheckCircle2}
          title="Nie wykryto problemów jakości"
          description="Wszystkie aktywne rekordy mają wymagane pola, źródła i media zgodnie z aktualnym modelem jakości."
        />
      ) : (
        <section className="admin-card overflow-hidden">
          <div className="flex flex-col gap-2 border-b border-border px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-sm font-semibold">Rekordy wymagające uzupełnienia</h2>
              <p className="mt-1 text-xs text-muted-foreground">
                Pokazujemy {records.length.toLocaleString("pl-PL")} z {summary.records_with_issues.toLocaleString("pl-PL")} rekordów z problemami.
              </p>
            </div>
            <Link href="/dashboard/review?attention=1" className="text-xs font-semibold text-primary">
              Otwórz kolejkę uwagi
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-[1180px] w-full text-sm">
              <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">Rekord</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Kompletność</th>
                  <th className="px-4 py-3">Dokumentacja</th>
                  <th className="px-4 py-3">Problemy</th>
                  <th className="px-4 py-3 text-right">Akcje</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {records.map((record: EditorialQualityRecord) => (
                  <tr key={record.id} className="align-top hover:bg-muted/20">
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-3">
                        <SaintAvatar name={record.canonical_name} avatar={record.avatar} className="h-10 w-10 text-xs" />
                        <div className="min-w-0">
                          <Link href={`/dashboard/persons/${record.id}`} className="block max-w-64 truncate font-medium hover:text-primary">
                            {record.canonical_name}
                          </Link>
                          <p className="mt-1 text-xs text-muted-foreground">{PERSON_TYPE_LABELS[record.person_type] ?? record.person_type}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <span className={cn("rounded-full px-2 py-1 text-[10px] font-semibold", PERSON_STATUS_COLORS[record.status])}>
                        {PERSON_STATUS_LABELS[record.status] ?? record.status}
                      </span>
                      <p className="mt-2 text-[10px] text-muted-foreground">{formatDateTime(record.updated_at)}</p>
                    </td>
                    <td className="px-4 py-4">
                      <div className="w-44">
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                            <div className={cn("h-full rounded-full", scoreBar(record.completeness_score))} style={{ width: `${record.completeness_score}%` }} />
                          </div>
                          <span className="text-xs font-semibold">{record.completeness_score}%</span>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4 text-xs text-muted-foreground">
                      <p>{record.source_count} źródeł przypiętych</p>
                      <p>{record.image_count} obrazów</p>
                      {record.unknown_license_count > 0 && <p className="text-rose-600">{record.unknown_license_count} licencji do sprawdzenia</p>}
                    </td>
                    <td className="max-w-[360px] px-4 py-4">
                      <div className="flex flex-wrap gap-1.5">
                        {record.issues.map((issue) => (
                          <span key={issue.code} className={cn("rounded-md border px-2 py-1 text-[10px]", severityTone[issue.severity] ?? "border-border bg-muted text-muted-foreground")}>
                            {issue.label}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-4 text-right">
                      <Link href={`/dashboard/persons/${record.id}/edit`} className="inline-flex h-8 items-center gap-1 rounded-md border border-border px-2.5 text-xs hover:bg-accent">
                        Edytuj <ArrowRight className="h-3.5 w-3.5" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

function DuplicatesPanel({ groups }: { groups: EditorialDuplicateGroup[] }) {
  if (groups.length === 0) {
    return (
      <EmptyState
        icon={CheckCircle2}
        title="Nie wykryto potencjalnych duplikatów"
        description="Aktualny algorytm nie znalazł aktywnych rekordów o tej samej znormalizowanej nazwie."
      />
    );
  }

  return (
    <section className="space-y-4">
      {groups.map((group) => (
        <article key={group.key} className="admin-card overflow-hidden">
          <div className="flex flex-col gap-3 border-b border-border px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-sm font-semibold">Podejrzenie duplikatu: {group.key}</h2>
              <p className="mt-1 text-xs text-muted-foreground">{group.reason}</p>
            </div>
            <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
              Pewność {group.confidence}%
            </span>
          </div>
          <div className="divide-y divide-border">
            {group.persons.map((person) => (
              <div key={person.id} className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center">
                <SaintAvatar name={person.canonical_name} avatar={person.avatar} className="h-10 w-10 text-xs" />
                <div className="min-w-0 flex-1">
                  <Link href={`/dashboard/persons/${person.id}`} className="font-medium hover:text-primary">
                    {person.canonical_name}
                  </Link>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {PERSON_TYPE_LABELS[person.person_type] ?? person.person_type} · {lifeYears(person)} · {person.source_count} źródeł
                  </p>
                </div>
                <span className={cn("w-fit rounded-full px-2 py-1 text-[10px] font-semibold", PERSON_STATUS_COLORS[person.status])}>
                  {PERSON_STATUS_LABELS[person.status] ?? person.status}
                </span>
                <Link href={`/dashboard/persons/${person.id}/edit`} className="inline-flex h-8 items-center gap-1 rounded-md border border-border px-2.5 text-xs hover:bg-accent">
                  Otwórz <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            ))}
          </div>
        </article>
      ))}
    </section>
  );
}

function SourcesPanel({ report }: { report: EditorialQualityReport }) {
  const { source_stats: stats, source_verification_items: items } = report;

  return (
    <div className="space-y-5">
      <section className="admin-card border-l-4 border-l-primary/60 p-5">
        <h2 className="text-sm font-semibold">Co znaczy „udokumentowane źródła”?</h2>
        <p className="mt-2 max-w-4xl text-sm leading-6 text-muted-foreground">
          W bazie rozróżniamy same rekordy źródłowe, czyli bibliografię i źródła historyczne, oraz przypisania tych źródeł do konkretnych postaci. Dla jakości encyklopedii najważniejszy jest wskaźnik „przypisania do profili”, bo pokazuje, ile informacji faktycznie ma dokumentację redakcyjną.
        </p>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3" aria-label="Statystyki źródeł">
        <MetricCard label="Bibliografia" value={stats.bibliography_sources} detail="Książki, artykuły, strony i opracowania" icon={BookOpenText} />
        <MetricCard label="Źródła historyczne" value={stats.historical_sources} detail="Rękopisy, archiwa i świadectwa pierwotne" icon={FileWarning} />
        <MetricCard label="Przypisania do profili" value={stats.person_source_links} detail="Źródła realnie przypięte do postaci" icon={ShieldCheck} />
        <MetricCard label="Udokumentowane profile" value={stats.documented_persons} detail="Postacie z co najmniej jednym źródłem" icon={CheckCircle2} tone="bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300" />
        <MetricCard label="Profile bez źródeł" value={stats.undocumented_persons} detail="Wymagają uzupełnienia bibliografii" icon={AlertTriangle} tone="bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-300" />
        <MetricCard label="Nieznane licencje" value={stats.unknown_license_images} detail={`Z ${stats.images.toLocaleString("pl-PL")} obrazów w bazie`} icon={ImageOff} tone="bg-rose-50 text-rose-700 dark:bg-rose-950/30 dark:text-rose-300" />
      </section>

      {items.length === 0 ? (
        <EmptyState
          icon={CheckCircle2}
          title="Źródła nie wymagają dodatkowej weryfikacji"
          description="Nie znaleziono brakujących ocen wiarygodności, dat dostępu, linków digitalizacji ani obrazów bez informacji o licencji."
        />
      ) : (
        <section className="admin-card overflow-hidden">
          <div className="flex flex-col gap-2 border-b border-border px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-sm font-semibold">Elementy wymagające weryfikacji</h2>
              <p className="mt-1 text-xs text-muted-foreground">
                Pokazujemy {items.length.toLocaleString("pl-PL")} najważniejszych zgłoszeń źródłowych.
              </p>
            </div>
            <Link href="/dashboard/sources?license=unknown#media" className="text-xs font-semibold text-primary">
              Media bez licencji
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-[1040px] w-full text-sm">
              <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">Element</th>
                  <th className="px-4 py-3">Problem</th>
                  <th className="px-4 py-3">Powiązana postać</th>
                  <th className="px-4 py-3">Źródło URL</th>
                  <th className="px-4 py-3">Aktualizacja</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {items.map((item: EditorialSourceVerificationItem) => (
                  <tr key={`${item.item_type}:${item.id}:${item.issue}`} className="align-top hover:bg-muted/20">
                    <td className="px-4 py-4">
                      <p className="font-medium">{item.title}</p>
                      <p className="mt-1 text-xs text-muted-foreground">{sourceTypeLabels[item.item_type] ?? item.item_type}</p>
                    </td>
                    <td className="px-4 py-4">
                      <span className={cn("rounded-md border px-2 py-1 text-[10px]", severityTone[item.severity] ?? "border-border bg-muted text-muted-foreground")}>
                        {item.issue}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      {item.related_person_id ? (
                        <Link href={`/dashboard/persons/${item.related_person_id}`} className="text-xs font-medium text-primary hover:underline">
                          {item.related_person_name}
                        </Link>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </td>
                    <td className="px-4 py-4">
                      {item.source_url ? (
                        <a href={item.source_url} target="_blank" rel="noreferrer" className="inline-flex max-w-72 items-center gap-1 text-xs text-primary hover:underline">
                          <ExternalLink className="h-3 w-3 shrink-0" />
                          <span className="truncate">{item.source_url}</span>
                        </a>
                      ) : (
                        <span className="text-xs text-muted-foreground">Brak</span>
                      )}
                    </td>
                    <td className="px-4 py-4 text-xs text-muted-foreground">{formatDateTime(item.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

export function QualityClient({ activeTab }: { activeTab: QualityTab }) {
  const qualityQuery = useQuery({
    queryKey: ["editorial", "quality"],
    queryFn: () => editorialApi.quality(),
  });
  const report = qualityQuery.data?.data;

  if (qualityQuery.isLoading) {
    return (
      <div className="flex min-h-[420px] items-center justify-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> Ładowanie centrum jakości…
      </div>
    );
  }

  if (!report) {
    return (
      <div className="admin-card mx-auto max-w-xl p-8 text-center">
        <ShieldAlert className="mx-auto h-8 w-8 text-amber-500" />
        <h1 className="mt-3 text-lg font-semibold">Nie udało się pobrać raportu jakości</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Sprawdź połączenie z API i spróbuj ponownie.
        </p>
        <button
          type="button"
          onClick={() => qualityQuery.refetch()}
          className="mt-5 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
        >
          Odśwież dane
        </button>
      </div>
    );
  }

  const summary = report.summary;

  return (
    <div className="mx-auto max-w-[1500px] space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="admin-label">Jakość danych</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Centrum jakości danych</h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            Operacyjny widok braków, potencjalnych duplikatów i źródeł wymagających weryfikacji redakcyjnej.
          </p>
        </div>
        <button
          type="button"
          onClick={() => qualityQuery.refetch()}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-border px-4 text-sm font-semibold hover:bg-accent"
        >
          <RefreshCw className={cn("h-4 w-4", qualityQuery.isFetching && "animate-spin")} />
          Odśwież raport
        </button>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5" aria-label="Podsumowanie jakości danych">
        <MetricCard label="Rekordy z problemami" value={summary.records_with_issues} detail="Aktywne profile wymagające uzupełnienia" icon={AlertTriangle} tone="bg-rose-50 text-rose-700 dark:bg-rose-950/30 dark:text-rose-300" />
        <MetricCard label="Problemy łącznie" value={summary.total_issues} detail="Suma wykrytych braków jakości" icon={Database} />
        <MetricCard label="Grupy duplikatów" value={summary.duplicate_groups} detail={`${summary.duplicate_records.toLocaleString("pl-PL")} rekordów do porównania`} icon={Copy} />
        <MetricCard label="Źródła do weryfikacji" value={summary.source_items_to_review} detail="Bibliografia, przypisy i media" icon={ShieldCheck} />
        <MetricCard label="Profile bez źródeł" value={summary.undocumented_persons} detail={`${summary.documented_persons.toLocaleString("pl-PL")} profili ma źródło`} icon={BookOpenText} />
      </section>

      <nav className="admin-card flex flex-col gap-2 p-2 sm:flex-row" aria-label="Zakładki jakości danych">
        {tabs.map(({ key, label, href, icon: Icon }) => {
          const active = activeTab === key;
          return (
            <Link
              key={key}
              href={href}
              className={cn(
                "inline-flex h-10 flex-1 items-center justify-center gap-2 rounded-lg px-3 text-sm font-semibold transition-colors",
                active ? "bg-primary text-primary-foreground shadow-sm" : "text-muted-foreground hover:bg-accent hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4" /> {label}
            </Link>
          );
        })}
      </nav>

      {activeTab === "issues" && <IssuesPanel report={report} />}
      {activeTab === "duplicates" && <DuplicatesPanel groups={report.duplicate_groups} />}
      {activeTab === "sources" && <SourcesPanel report={report} />}
    </div>
  );
}
