"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, BookOpenText, CalendarDays, Download, Edit, HeartHandshake, History, Loader2 } from "lucide-react";
import { calendarApi, personsApi, sourcesApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store/auth";
import { SaintAvatar } from "@/components/persons/saint-avatar";
import { formatAdminDateTime } from "@/lib/i18n/format";
import type {
  AdminDomainDictionary,
  AdminEraKey,
  AdminFeastRankKey,
  AdminGenderKey,
  AdminLiturgicalColorKey,
  AdminPatronageTypeKey,
  AdminPersonDetailDictionary,
  AdminPersonTypeKey,
  AdminPublicationStatusKey,
} from "@/lib/i18n/types";
import {
  cn,
  PERSON_STATUS_COLORS,
  PERSON_TYPE_COLORS,
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

interface PersonDetailClientProps {
  copy: AdminPersonDetailDictionary;
  domainCopy: AdminDomainDictionary;
  locale: string;
}

function formatRecognitionDate(
  value: string | null | undefined,
  year: number | null | undefined,
  locale: string,
) {
  if (value && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return new Intl.DateTimeFormat(locale, {
      day: "numeric",
      month: "long",
      year: "numeric",
      timeZone: "UTC",
    }).format(new Date(`${value}T00:00:00Z`));
  }
  return value || (year ? String(year) : "—");
}

function formatFeastDate(
  month: number | null | undefined,
  day: number | null | undefined,
  locale: string,
) {
  if (!month || !day) return "—";
  return new Intl.DateTimeFormat(locale, {
    day: "numeric",
    month: "long",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(2000, month - 1, day)));
}

export function PersonDetailClient({
  copy,
  domainCopy,
  locale,
}: PersonDetailClientProps) {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const canEdit = useAuthStore((state) => state.hasPermission("persons:update"));
  const canExport = useAuthStore((state) => state.hasPermission("export:read"));
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

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

  const exportProfile = async () => {
    setIsExporting(true);
    setExportError(null);
    try {
      const response = await personsApi.exportProfile(id);
      const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${response.data.source_slug ?? person?.slug ?? copy.exportFileFallback}.json`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch {
      setExportError(copy.exportError);
    } finally {
      setIsExporting(false);
    }
  };

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
        <p className="text-muted-foreground">{copy.notFound}</p>
        <button
          onClick={() => router.push("/dashboard/persons")}
          className="mt-4 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
        >
          {copy.backToListAction}
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
            type="button"
            aria-label={copy.backAriaLabel}
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
                {domainCopy.personTypeLabels[person.person_type as AdminPersonTypeKey] ?? person.person_type}
              </span>
              <span
                className={cn(
                  "rounded-full px-2.5 py-0.5 text-xs font-medium",
                  PERSON_STATUS_COLORS[person.status]
                )}
              >
                {domainCopy.personStatusLabels[person.status as AdminPublicationStatusKey] ?? person.status}
              </span>
            </div>
            {person.latin_name && (
              <p className="text-sm text-muted-foreground italic">
                {person.latin_name}
              </p>
            )}
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {canExport && <button type="button" disabled={isExporting} onClick={() => { void exportProfile(); }} className="flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-semibold hover:bg-accent disabled:opacity-50">{isExporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />} {copy.exportAction}</button>}
          {canEdit && <button
            onClick={() => router.push(`/dashboard/persons/${id}/edit`)}
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 transition-colors"
          >
            <Edit className="h-4 w-4" />
            {copy.editAction}
          </button>}
        </div>
      </div>
      {exportError && <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">{exportError}</p>}

      {/* Main Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Detail Specs */}
        <div className="col-span-2 space-y-6">
          {/* Summary & Bio */}
          <div className="rounded-xl border border-border bg-card p-6 space-y-4">
            <h2 className="text-base font-semibold text-foreground">
              {copy.biography.title}
            </h2>
            {person.summary_pl ? (
              <div className="rounded-lg bg-muted/40 p-4 text-sm text-foreground/90 italic">
                {person.summary_pl}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">{copy.biography.noSummary}</p>
            )}

            {person.biography_pl ? (
              <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-line text-sm text-foreground/80">
                {person.biography_pl}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">{copy.biography.noBiography}</p>
            )}
          </div>

          {/* Devotion & Iconography */}
          <div className="grid gap-6 md:grid-cols-2">
            <section className="rounded-xl border border-border bg-card p-6">
              <h2 className="text-base font-semibold text-foreground">{copy.prayer.title}</h2>
              {person.prayers ? (
                <p className="mt-4 whitespace-pre-line text-sm leading-6 text-foreground/80">
                  {person.prayers}
                </p>
              ) : (
                <p className="mt-4 text-sm text-muted-foreground">{copy.prayer.empty}</p>
              )}
            </section>

            <section className="rounded-xl border border-border bg-card p-6">
              <h2 className="text-base font-semibold text-foreground">{copy.iconography.title}</h2>
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
                <p className="mt-4 text-sm text-muted-foreground">{copy.iconography.empty}</p>
              )}
            </section>
          </div>

          <section className="rounded-xl border border-border bg-card p-6">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="flex items-center gap-2 text-base font-semibold text-foreground">
                  <HeartHandshake className="h-4 w-4 text-primary" /> {copy.patronages.title}
                </h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  {copy.patronages.description}
                </p>
              </div>
              {canEdit && <button
                onClick={() => router.push(`/dashboard/persons/${id}/edit#patronages`)}
                className="rounded-md border border-border px-3 py-1.5 text-xs font-medium hover:bg-accent"
              >
                {copy.patronages.manageAction}
              </button>}
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
                        {domainCopy.patronageTypeLabels[String(patronage.patronage_type) as AdminPatronageTypeKey] ?? String(patronage.patronage_type)}
                      </span>
                      {Boolean(patronage.is_official) && (
                        <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-medium text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300">
                          {copy.patronages.official}
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
                {copy.patronages.empty}
              </p>
            )}
          </section>

          <section className="rounded-xl border border-border bg-card p-6">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="flex items-center gap-2 text-base font-semibold text-foreground">
                  <BookOpenText className="h-4 w-4 text-primary" /> {copy.sources.title}
                </h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  {copy.sources.description}
                </p>
              </div>
              {canEdit && <button
                onClick={() => router.push(`/dashboard/persons/${id}/edit`)}
                className="rounded-md border border-border px-3 py-1.5 text-xs font-medium hover:bg-accent"
              >
                {copy.sources.manageAction}
              </button>}
            </div>
            {personSources.length ? (
              <ul className="mt-4 divide-y divide-border">
                {personSources.map((link: Record<string, unknown>) => {
                  const source = (link.bibliography ?? link.historical_source) as Record<string, unknown> | null;
                  return (
                    <li key={String(link.id)} className="py-3 first:pt-0 last:pb-0">
                      <p className="text-sm font-medium text-foreground">{String(source?.title ?? copy.sources.unknown)}</p>
                      {Boolean(link.page_reference) && (
                        <p className="mt-1 text-xs text-muted-foreground">{copy.sources.referencePrefix} {String(link.page_reference)}</p>
                      )}
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="mt-4 text-sm text-muted-foreground">{copy.sources.empty}</p>
            )}
          </section>

          {/* Dates & Details */}
          <div className="rounded-xl border border-border bg-card p-6 space-y-4">
            <h2 className="text-base font-semibold text-foreground">
              {copy.hagiographicMetadata.title}
            </h2>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="col-span-2 rounded-lg border border-primary/15 bg-primary/5 p-4">
                <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <CalendarDays className="h-3.5 w-3.5 text-primary" />
                  {copy.hagiographicMetadata.feast}
                </span>
                {primaryFeast ? (
                  <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1">
                    <span className="font-medium text-foreground">
                      {formatFeastDate(primaryFeast.month, primaryFeast.day, locale)}
                    </span>
                    <span className="text-muted-foreground">·</span>
                    <span className="text-foreground/80">
                      {domainCopy.feastRankLabels[String(primaryFeast.rank) as AdminFeastRankKey] ?? String(primaryFeast.rank)}
                    </span>
                    {primaryFeast.liturgical_color && (
                      <>
                        <span className="text-muted-foreground">·</span>
                        <span className="text-foreground/80">
                          {domainCopy.liturgicalColorLabels[primaryFeast.liturgical_color as AdminLiturgicalColorKey] ?? primaryFeast.liturgical_color}
                        </span>
                      </>
                    )}
                    <span className="text-muted-foreground">
                      {primaryFeast.calendar?.name ?? ""}
                    </span>
                  </div>
                ) : (
                  <p className="mt-2 text-sm text-muted-foreground">
                    {copy.hagiographicMetadata.noFeast}
                  </p>
                )}
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">{copy.hagiographicMetadata.gender}</span>
                <span className="font-medium text-foreground">
                  {domainCopy.genderLabels[person.gender as AdminGenderKey] ?? person.gender ?? "—"}
                </span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">{copy.hagiographicMetadata.era}</span>
                <span className="font-medium text-foreground">
                  {domainCopy.eraLabels[person.era as AdminEraKey] ?? person.era ?? "—"}
                </span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">{copy.hagiographicMetadata.stateOfLife}</span>
                <span className="font-medium text-foreground">
                  {person.state_of_life?.name_pl ?? "—"}
                </span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">{copy.hagiographicMetadata.birthYear}</span>
                <span className="font-medium text-foreground">{person.birth_year ?? "—"}</span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">{copy.hagiographicMetadata.deathYear}</span>
                <span className="font-medium text-foreground">{person.death_year ?? "—"}</span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">{copy.hagiographicMetadata.beatification}</span>
                <span className="font-medium text-foreground">
                  {formatRecognitionDate(
                    person.beatification?.beatification_date,
                    person.beatification?.beatification_year,
                    locale,
                  )}
                </span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">{copy.hagiographicMetadata.canonization}</span>
                <span className="font-medium text-foreground">
                  {formatRecognitionDate(
                    person.canonization?.canonization_date,
                    person.canonization?.canonization_year,
                    locale,
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
              {copy.history.titlePrefix} (v{person.version})
            </h2>

            {versions.length === 0 ? (
              <p className="text-xs text-muted-foreground">{copy.history.empty}</p>
            ) : (
              <ol className="relative border-l border-border ml-2 space-y-4">
                {versions.map((v: Record<string, unknown>) => (
                  <li key={v.id as string} className="ml-4 text-xs">
                    <div className="absolute -left-1.5 mt-1 h-3 w-3 rounded-full border border-background bg-primary" />
                    <time className="font-mono text-[10px] text-muted-foreground">
                      v{v.version_number as number} · {formatAdminDateTime(v.changed_at as string, locale)}
                    </time>
                    <p className="font-medium text-foreground mt-0.5">
                      {(v.change_summary as string) || copy.history.defaultChange}
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
