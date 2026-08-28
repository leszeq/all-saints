"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, BookOpenText, CalendarDays, Edit, HeartHandshake, History } from "lucide-react";
import { calendarApi, personsApi, sourcesApi } from "@/lib/api";
import { SaintAvatar } from "@/components/persons/saint-avatar";
import {
  cn,
  ERA_LABELS,
  FEAST_RANK_LABELS,
  formatDateTime,
  GENDER_LABELS,
  LITURGICAL_COLOR_LABELS,
  PERSON_STATUS_COLORS,
  PERSON_STATUS_LABELS,
  PERSON_TYPE_COLORS,
  PERSON_TYPE_LABELS,
} from "@/lib/utils";

interface PersonFeastEntry {
  id: string;
  month?: number | null;
  day?: number | null;
  rank?: string | null;
  liturgical_color?: string | null;
  is_primary?: boolean;
  calendar?: {
    code?: string | null;
    name?: string | null;
  } | null;
}

const PATRONAGE_TYPE_LABELS: Record<string, string> = {
  illness: "Choroba",
  healthcare: "Opieka zdrowotna",
  family: "Rodzina",
  profession: "Zawód",
  work: "Praca",
  travel: "Podróż",
  country: "Kraj",
  city: "Miasto",
  diocese: "Diecezja",
  group: "Grupa osób",
  cause: "Sprawa / intencja",
  other: "Inne",
};

function formatRecognitionDate(value?: string | null, year?: number | null) {
  if (value && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return new Intl.DateTimeFormat("pl-PL", {
      day: "numeric",
      month: "long",
      year: "numeric",
      timeZone: "UTC",
    }).format(new Date(`${value}T00:00:00Z`));
  }
  return value || (year ? String(year) : "—");
}

function formatFeastDate(month?: number | null, day?: number | null) {
  if (!month || !day) return "—";
  return new Intl.DateTimeFormat("pl-PL", {
    day: "numeric",
    month: "long",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(2000, month - 1, day)));
}

export default function PersonDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const { data: personData, isLoading } = useQuery({
    queryKey: ["person", id],
    queryFn: () => personsApi.get(id),
  });

  const { data: versionsData } = useQuery({
    queryKey: ["person-versions", id],
    queryFn: () => personsApi.versions(id),
  });

  const { data: sourcesData } = useQuery({
    queryKey: ["person-sources", id],
    queryFn: () => sourcesApi.personSources(id),
  });

  const { data: feastData } = useQuery({
    queryKey: ["calendar", "person-feasts", id],
    queryFn: () => calendarApi.personEntries(id),
  });

  const person = personData?.data;
  const versions = versionsData?.data ?? [];
  const personSources = sourcesData?.data ?? [];
  const feastEntries = (feastData?.data ?? []) as PersonFeastEntry[];
  const primaryFeast =
    feastEntries.find((entry) => entry.calendar?.code === "roman_pl") ??
    feastEntries.find((entry) => entry.is_primary) ??
    feastEntries[0] ??
    null;

  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 w-64 rounded bg-muted" />
        <div className="h-4 w-96 rounded bg-muted" />
        <div className="h-96 w-full rounded-xl bg-muted" />
      </div>
    );
  }

  if (!person) {
    return (
      <div className="py-12 text-center">
        <p className="text-muted-foreground">Osoba nie została znaleziona.</p>
        <button
          onClick={() => router.push("/dashboard/persons")}
          className="mt-4 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
        >
          Wróć do listy
        </button>
      </div>
    );
  }

  const patronages = Array.isArray(person.patronages)
    ? (person.patronages as Array<Record<string, unknown>>)
    : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/dashboard/persons")}
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-border text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <SaintAvatar
            name={person.canonical_name}
            avatar={person.avatar}
            className="h-16 w-16 text-lg"
          />
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-foreground">
                {person.canonical_name}
              </h1>
              <span
                className={cn(
                  "rounded-full px-2.5 py-0.5 text-xs font-medium",
                  PERSON_TYPE_COLORS[person.person_type]
                )}
              >
                {PERSON_TYPE_LABELS[person.person_type] ?? person.person_type}
              </span>
              <span
                className={cn(
                  "rounded-full px-2.5 py-0.5 text-xs font-medium",
                  PERSON_STATUS_COLORS[person.status]
                )}
              >
                {PERSON_STATUS_LABELS[person.status] ?? person.status}
              </span>
            </div>
            {person.latin_name && (
              <p className="text-sm text-muted-foreground italic">
                {person.latin_name}
              </p>
            )}
          </div>
        </div>

        <button
          onClick={() => router.push(`/dashboard/persons/${id}/edit`)}
          className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 transition-colors"
        >
          <Edit className="h-4 w-4" />
          Edytuj
        </button>
      </div>

      {/* Main Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Detail Specs */}
        <div className="col-span-2 space-y-6">
          {/* Summary & Bio */}
          <div className="rounded-xl border border-border bg-card p-6 space-y-4">
            <h2 className="text-base font-semibold text-foreground">
              Biografia & Streszczenie
            </h2>
            {person.summary_pl ? (
              <div className="rounded-lg bg-muted/40 p-4 text-sm text-foreground/90 italic">
                {person.summary_pl}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Brak streszczenia.</p>
            )}

            {person.biography_pl ? (
              <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-line text-sm text-foreground/80">
                {person.biography_pl}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Brak biogramu.</p>
            )}
          </div>

          {/* Devotion & Iconography */}
          <div className="grid gap-6 md:grid-cols-2">
            <section className="rounded-xl border border-border bg-card p-6">
              <h2 className="text-base font-semibold text-foreground">Modlitwa</h2>
              {person.prayers ? (
                <p className="mt-4 whitespace-pre-line text-sm leading-6 text-foreground/80">
                  {person.prayers}
                </p>
              ) : (
                <p className="mt-4 text-sm text-muted-foreground">Brak przypisanej modlitwy.</p>
              )}
            </section>

            <section className="rounded-xl border border-border bg-card p-6">
              <h2 className="text-base font-semibold text-foreground">Atrybuty ikonograficzne</h2>
              {person.iconographic_attributes ? (
                <div className="mt-4 flex flex-wrap gap-2">
                  {String(person.iconographic_attributes)
                    .split(/[;\n]/)
                    .map((attribute: string) => attribute.trim())
                    .filter(Boolean)
                    .map((attribute: string) => (
                      <span
                        key={attribute}
                        className="rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-medium text-foreground"
                      >
                        {attribute}
                      </span>
                    ))}
                </div>
              ) : (
                <p className="mt-4 text-sm text-muted-foreground">Brak opisanych atrybutów.</p>
              )}
            </section>
          </div>

          <section className="rounded-xl border border-border bg-card p-6">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="flex items-center gap-2 text-base font-semibold text-foreground">
                  <HeartHandshake className="h-4 w-4 text-primary" /> Patronaty
                </h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  Informacje wykorzystywane w katalogu publicznym i eksploracji według patronatu.
                </p>
              </div>
              <button
                onClick={() => router.push(`/dashboard/persons/${id}/edit#patronages`)}
                className="rounded-md border border-border px-3 py-1.5 text-xs font-medium hover:bg-accent"
              >
                Zarządzaj
              </button>
            </div>
            {patronages.length ? (
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {patronages.map((patronage) => (
                  <article
                    key={String(patronage.id)}
                    className="rounded-lg border border-border bg-muted/25 p-4"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold text-foreground">
                        {String(patronage.name_pl)}
                      </span>
                      <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
                        {PATRONAGE_TYPE_LABELS[String(patronage.patronage_type)] ?? String(patronage.patronage_type)}
                      </span>
                      {Boolean(patronage.is_official) && (
                        <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-medium text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300">
                          oficjalny
                        </span>
                      )}
                    </div>
                    {Boolean(patronage.description) && (
                      <p className="mt-2 text-xs leading-5 text-muted-foreground">
                        {String(patronage.description)}
                      </p>
                    )}
                  </article>
                ))}
              </div>
            ) : (
              <p className="mt-4 text-sm text-muted-foreground">
                Brak przypisanych patronatów.
              </p>
            )}
          </section>

          <section className="rounded-xl border border-border bg-card p-6">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="flex items-center gap-2 text-base font-semibold text-foreground">
                  <BookOpenText className="h-4 w-4 text-primary" /> Źródła merytoryczne
                </h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  Powiązania uwzględniane przy ocenie kompletności rekordu.
                </p>
              </div>
              <button
                onClick={() => router.push(`/dashboard/persons/${id}/edit`)}
                className="rounded-md border border-border px-3 py-1.5 text-xs font-medium hover:bg-accent"
              >
                Zarządzaj
              </button>
            </div>
            {personSources.length ? (
              <ul className="mt-4 divide-y divide-border">
                {personSources.map((link: Record<string, unknown>) => {
                  const source = (link.bibliography ?? link.historical_source) as Record<string, unknown> | null;
                  return (
                    <li key={String(link.id)} className="py-3 first:pt-0 last:pb-0">
                      <p className="text-sm font-medium text-foreground">{String(source?.title ?? "Nieznane źródło")}</p>
                      {Boolean(link.page_reference) && (
                        <p className="mt-1 text-xs text-muted-foreground">Odwołanie: {String(link.page_reference)}</p>
                      )}
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="mt-4 text-sm text-muted-foreground">Brak przypisanych źródeł merytorycznych.</p>
            )}
          </section>

          {/* Dates & Details */}
          <div className="rounded-xl border border-border bg-card p-6 space-y-4">
            <h2 className="text-base font-semibold text-foreground">
              Metadane Hagiograficzne
            </h2>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="col-span-2 rounded-lg border border-primary/15 bg-primary/5 p-4">
                <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <CalendarDays className="h-3.5 w-3.5 text-primary" />
                  Wspomnienie liturgiczne
                </span>
                {primaryFeast ? (
                  <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1">
                    <span className="font-medium text-foreground">
                      {formatFeastDate(primaryFeast.month, primaryFeast.day)}
                    </span>
                    <span className="text-muted-foreground">·</span>
                    <span className="text-foreground/80">
                      {FEAST_RANK_LABELS[String(primaryFeast.rank)] ?? String(primaryFeast.rank)}
                    </span>
                    {primaryFeast.liturgical_color && (
                      <>
                        <span className="text-muted-foreground">·</span>
                        <span className="text-foreground/80">
                          {LITURGICAL_COLOR_LABELS[primaryFeast.liturgical_color] ?? primaryFeast.liturgical_color}
                        </span>
                      </>
                    )}
                    <span className="text-muted-foreground">
                      {primaryFeast.calendar?.name ?? ""}
                    </span>
                  </div>
                ) : (
                  <p className="mt-2 text-sm text-muted-foreground">
                    Brak ręcznie przypisanego dnia wspomnienia w kalendarzu.
                  </p>
                )}
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">Płeć</span>
                <span className="font-medium text-foreground">
                  {GENDER_LABELS[person.gender] ?? person.gender ?? "—"}
                </span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">Era</span>
                <span className="font-medium text-foreground">
                  {ERA_LABELS[person.era] ?? person.era ?? "—"}
                </span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">Stan życia</span>
                <span className="font-medium text-foreground">
                  {person.state_of_life?.name_pl ?? "—"}
                </span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">Rok urodzenia</span>
                <span className="font-medium text-foreground">{person.birth_year ?? "—"}</span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">Rok śmierci</span>
                <span className="font-medium text-foreground">{person.death_year ?? "—"}</span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">Beatyfikacja</span>
                <span className="font-medium text-foreground">
                  {formatRecognitionDate(
                    person.beatification?.beatification_date,
                    person.beatification?.beatification_year,
                  )}
                </span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">Kanonizacja</span>
                <span className="font-medium text-foreground">
                  {formatRecognitionDate(
                    person.canonization?.canonization_date,
                    person.canonization?.canonization_year,
                  )}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* History Snapshots Sidebar */}
        <div className="space-y-6">
          <div className="rounded-xl border border-border bg-card p-6">
            <h2 className="flex items-center gap-2 text-base font-semibold text-foreground mb-4">
              <History className="h-4 w-4 text-primary" />
              Historia zmian (v{person.version})
            </h2>

            {versions.length === 0 ? (
              <p className="text-xs text-muted-foreground">Brak zarejestrowanych wersji.</p>
            ) : (
              <ol className="relative border-l border-border ml-2 space-y-4">
                {versions.map((v: Record<string, unknown>) => (
                  <li key={v.id as string} className="ml-4 text-xs">
                    <div className="absolute -left-1.5 mt-1 h-3 w-3 rounded-full border border-background bg-primary" />
                    <time className="font-mono text-[10px] text-muted-foreground">
                      v{v.version_number as number} · {formatDateTime(v.changed_at as string)}
                    </time>
                    <p className="font-medium text-foreground mt-0.5">
                      {(v.change_summary as string) || "Modyfikacja danych"}
                    </p>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
