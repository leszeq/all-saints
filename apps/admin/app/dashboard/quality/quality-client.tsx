"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ElementType, KeyboardEvent, MouseEvent } from "react";
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
import { formatAdminDateTime } from "@/lib/i18n/format";
import type {
  AdminDomainDictionary,
  AdminDuplicateReasonKey,
  AdminEditorialIssueKey,
  AdminPersonTypeKey,
  AdminQualityDictionary,
  AdminSeverityKey,
  AdminSourceVerificationIssueKey,
  AdminSourceVerificationTypeKey,
} from "@/lib/i18n/types";
import { cn, PERSON_STATUS_COLORS } from "@/lib/utils";

export type QualityTab = "issues" | "duplicates" | "sources";

const tabs: Array<{ key: QualityTab; href: string; icon: ElementType }> = [
  { key: "issues", href: "/dashboard/quality/issues", icon: Database },
  { key: "duplicates", href: "/dashboard/quality/duplicates", icon: Network },
  { key: "sources", href: "/dashboard/quality/sources", icon: ShieldCheck },
];

const severityTone: Record<string, string> = {
  critical: "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/20 dark:text-rose-300",
  warning: "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/50 dark:bg-amber-950/20 dark:text-amber-300",
};

const sourceSectionHrefs: Record<string, string> = {
  bibliography: "/dashboard/sources#bibliography",
  historical_source: "/dashboard/sources#historical-sources",
  image: "/dashboard/sources#media",
  person_source: "/dashboard/sources#bibliography",
};

function sourceVerificationTarget(
  item: EditorialSourceVerificationItem,
  copy: AdminQualityDictionary,
) {
  if (item.related_person_id) {
    const hash = item.item_type === "image" ? "avatar" : "sources";
    const target = item.item_type === "image"
      ? copy.sources.targets.editAvatar
      : copy.sources.targets.editSources;
    return {
      href: `/dashboard/persons/${item.related_person_id}/edit#${hash}`,
      ...target,
    };
  }

  if (item.item_type === "image" && item.issue_code === "unknown_image_license") {
    return {
      href: "/dashboard/sources?license=unknown#media",
      ...copy.sources.targets.checkMedia,
    };
  }

  return {
    href: sourceSectionHrefs[item.item_type] ?? "/dashboard/sources",
    ...copy.sources.targets.openSection,
  };
}

function getPersonTypeLabel(key: string, domainCopy: AdminDomainDictionary): string {
  return Object.prototype.hasOwnProperty.call(domainCopy.personTypeLabels, key)
    ? domainCopy.personTypeLabels[key as AdminPersonTypeKey]
    : key;
}

function getEditorialIssueLabel(
  code: string,
  fallback: string,
  domainCopy: AdminDomainDictionary,
): string {
  return Object.prototype.hasOwnProperty.call(domainCopy.editorialIssueLabels, code)
    ? domainCopy.editorialIssueLabels[code as AdminEditorialIssueKey]
    : fallback;
}

function getSeverityLabel(key: string, domainCopy: AdminDomainDictionary): string {
  return Object.prototype.hasOwnProperty.call(domainCopy.severityLabels, key)
    ? domainCopy.severityLabels[key as AdminSeverityKey]
    : key;
}

function getSourceTypeLabel(key: string, domainCopy: AdminDomainDictionary): string {
  return Object.prototype.hasOwnProperty.call(domainCopy.sourceVerificationTypeLabels, key)
    ? domainCopy.sourceVerificationTypeLabels[key as AdminSourceVerificationTypeKey]
    : key;
}

function getSourceIssueLabel(
  item: EditorialSourceVerificationItem,
  domainCopy: AdminDomainDictionary,
): string {
  return Object.prototype.hasOwnProperty.call(
    domainCopy.sourceVerificationIssueLabels,
    item.issue_code,
  )
    ? domainCopy.sourceVerificationIssueLabels[
        item.issue_code as AdminSourceVerificationIssueKey
      ]
    : item.issue;
}

function getDuplicateReason(
  group: EditorialDuplicateGroup,
  domainCopy: AdminDomainDictionary,
): string {
  return Object.prototype.hasOwnProperty.call(
    domainCopy.duplicateReasonLabels,
    group.reason_code,
  )
    ? domainCopy.duplicateReasonLabels[group.reason_code as AdminDuplicateReasonKey]
    : group.reason;
}

function stopRowNavigation(event: MouseEvent<HTMLElement>) {
  event.stopPropagation();
}

function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
  locale,
  tone = "text-primary bg-primary/10",
}: {
  label: string;
  value: number;
  detail: string;
  icon: ElementType;
  locale: string;
  tone?: string;
}) {
  return (
    <article className="admin-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-muted-foreground">{label}</p>
          <p className="mt-2 text-3xl font-semibold tracking-tight">
            {new Intl.NumberFormat(locale).format(value)}
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

function lifeYears(
  person: { birth_year?: number | null; death_year?: number | null },
  copy: AdminQualityDictionary,
) {
  if (person.birth_year == null && person.death_year == null) {
    return copy.duplicates.unknownLifeDates;
  }
  return `${person.birth_year ?? "?"}–${person.death_year ?? "?"}`;
}

function IssuesPanel({
  report,
  copy,
  domainCopy,
  locale,
}: {
  report: EditorialQualityReport;
  copy: AdminQualityDictionary;
  domainCopy: AdminDomainDictionary;
  locale: string;
}) {
  const { issue_breakdown: breakdown, problem_records: records, summary } = report;
  const numberFormatter = new Intl.NumberFormat(locale);

  return (
    <div className="space-y-5">
      <section
        className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3"
        aria-label={copy.issues.typesAriaLabel}
      >
        {breakdown.map((issue) => (
          <article key={issue.code} className="admin-card p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-medium text-muted-foreground">
                  {getEditorialIssueLabel(issue.code, issue.label, domainCopy)}
                </p>
                <p className="mt-2 text-2xl font-semibold">
                  {numberFormatter.format(issue.count)}
                </p>
              </div>
              <span className={cn("rounded-full border px-2 py-1 text-[10px] font-semibold", severityTone[issue.severity] ?? "border-border bg-muted text-muted-foreground")}>
                {getSeverityLabel(issue.severity, domainCopy)}
              </span>
            </div>
          </article>
        ))}
      </section>

      {records.length === 0 ? (
        <EmptyState
          icon={CheckCircle2}
          title={copy.issues.emptyTitle}
          description={copy.issues.emptyDescription}
        />
      ) : (
        <section className="admin-card overflow-hidden">
          <div className="flex flex-col gap-2 border-b border-border px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-sm font-semibold">{copy.issues.recordsTitle}</h2>
              <p className="mt-1 text-xs text-muted-foreground">
                {copy.issues.shownPrefix} {numberFormatter.format(records.length)}{" "}
                {copy.issues.shownSeparator} {numberFormatter.format(summary.records_with_issues)}{" "}
                {copy.issues.shownSuffix}
              </p>
            </div>
            <Link href="/dashboard/review?attention=1" className="text-xs font-semibold text-primary">
              {copy.issues.openAttentionQueue}
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-[1180px] w-full text-sm">
              <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">{copy.issues.table.record}</th>
                  <th className="px-4 py-3">{copy.issues.table.status}</th>
                  <th className="px-4 py-3">{copy.issues.table.completeness}</th>
                  <th className="px-4 py-3">{copy.issues.table.documentation}</th>
                  <th className="px-4 py-3">{copy.issues.table.issues}</th>
                  <th className="px-4 py-3 text-right">{copy.issues.table.actions}</th>
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
                          <p className="mt-1 text-xs text-muted-foreground">
                            {getPersonTypeLabel(record.person_type, domainCopy)}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <span className={cn("rounded-full px-2 py-1 text-[10px] font-semibold", PERSON_STATUS_COLORS[record.status])}>
                        {domainCopy.personStatusLabels[record.status] ?? record.status}
                      </span>
                      <p className="mt-2 text-[10px] text-muted-foreground">
                        {formatAdminDateTime(record.updated_at, locale)}
                      </p>
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
                      <p>
                        {numberFormatter.format(record.source_count)}{" "}
                        {copy.issues.attachedSourcesSuffix}
                      </p>
                      <p>
                        {numberFormatter.format(record.image_count)} {copy.issues.imagesSuffix}
                      </p>
                      {record.unknown_license_count > 0 && (
                        <p className="text-rose-600">
                          {numberFormatter.format(record.unknown_license_count)}{" "}
                          {copy.issues.licensesToReviewSuffix}
                        </p>
                      )}
                    </td>
                    <td className="max-w-[360px] px-4 py-4">
                      <div className="flex flex-wrap gap-1.5">
                        {record.issues.map((issue) => (
                          <span key={issue.code} className={cn("rounded-md border px-2 py-1 text-[10px]", severityTone[issue.severity] ?? "border-border bg-muted text-muted-foreground")}>
                            {getEditorialIssueLabel(issue.code, issue.label, domainCopy)}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-4 text-right">
                      <Link href={`/dashboard/persons/${record.id}/edit`} className="inline-flex h-8 items-center gap-1 rounded-md border border-border px-2.5 text-xs hover:bg-accent">
                        {copy.issues.editAction} <ArrowRight className="h-3.5 w-3.5" />
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

function DuplicatesPanel({
  groups,
  copy,
  domainCopy,
  locale,
}: {
  groups: EditorialDuplicateGroup[];
  copy: AdminQualityDictionary;
  domainCopy: AdminDomainDictionary;
  locale: string;
}) {
  const numberFormatter = new Intl.NumberFormat(locale);

  if (groups.length === 0) {
    return (
      <EmptyState
        icon={CheckCircle2}
        title={copy.duplicates.emptyTitle}
        description={copy.duplicates.emptyDescription}
      />
    );
  }

  return (
    <section className="space-y-4">
      {groups.map((group) => (
        <article key={group.key} className="admin-card overflow-hidden">
          <div className="flex flex-col gap-3 border-b border-border px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-sm font-semibold">
                {copy.duplicates.suspicionPrefix} {group.key}
              </h2>
              <p className="mt-1 text-xs text-muted-foreground">
                {getDuplicateReason(group, domainCopy)}
              </p>
            </div>
            <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
              {copy.duplicates.confidencePrefix} {group.confidence}%
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
                    {getPersonTypeLabel(person.person_type, domainCopy)} ·{" "}
                    {lifeYears(person, copy)} · {numberFormatter.format(person.source_count)}{" "}
                    {copy.duplicates.sourcesSuffix}
                  </p>
                </div>
                <span className={cn("w-fit rounded-full px-2 py-1 text-[10px] font-semibold", PERSON_STATUS_COLORS[person.status])}>
                  {domainCopy.personStatusLabels[person.status] ?? person.status}
                </span>
                <Link href={`/dashboard/persons/${person.id}/edit`} className="inline-flex h-8 items-center gap-1 rounded-md border border-border px-2.5 text-xs hover:bg-accent">
                  {copy.duplicates.openAction} <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            ))}
          </div>
        </article>
      ))}
    </section>
  );
}

function SourcesPanel({
  report,
  copy,
  domainCopy,
  locale,
}: {
  report: EditorialQualityReport;
  copy: AdminQualityDictionary;
  domainCopy: AdminDomainDictionary;
  locale: string;
}) {
  const router = useRouter();
  const { source_stats: stats, source_verification_items: items } = report;
  const numberFormatter = new Intl.NumberFormat(locale);
  const navigateToTarget = (href: string) => router.push(href);
  const handleRowKeyDown = (
    event: KeyboardEvent<HTMLTableRowElement>,
    href: string,
  ) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      navigateToTarget(href);
    }
  };

  return (
    <div className="space-y-5">
      <section className="admin-card border-l-4 border-l-primary/60 p-5">
        <h2 className="text-sm font-semibold">{copy.sources.explanationTitle}</h2>
        <p className="mt-2 max-w-4xl text-sm leading-6 text-muted-foreground">
          {copy.sources.explanationDescription}
        </p>
      </section>

      <section
        className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3"
        aria-label={copy.sources.statisticsAriaLabel}
      >
        <MetricCard label={copy.sources.metrics.bibliography.label} value={stats.bibliography_sources} detail={copy.sources.metrics.bibliography.detail} icon={BookOpenText} locale={locale} />
        <MetricCard label={copy.sources.metrics.historical.label} value={stats.historical_sources} detail={copy.sources.metrics.historical.detail} icon={FileWarning} locale={locale} />
        <MetricCard label={copy.sources.metrics.assignments.label} value={stats.person_source_links} detail={copy.sources.metrics.assignments.detail} icon={ShieldCheck} locale={locale} />
        <MetricCard label={copy.sources.metrics.documented.label} value={stats.documented_persons} detail={copy.sources.metrics.documented.detail} icon={CheckCircle2} locale={locale} tone="bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300" />
        <MetricCard label={copy.sources.metrics.undocumented.label} value={stats.undocumented_persons} detail={copy.sources.metrics.undocumented.detail} icon={AlertTriangle} locale={locale} tone="bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-300" />
        <MetricCard label={copy.sources.metrics.unknownLicenses.label} value={stats.unknown_license_images} detail={`${copy.sources.metrics.unknownLicenses.detailPrefix} ${numberFormatter.format(stats.images)} ${copy.sources.metrics.unknownLicenses.detailSuffix}`} icon={ImageOff} locale={locale} tone="bg-rose-50 text-rose-700 dark:bg-rose-950/30 dark:text-rose-300" />
      </section>

      {items.length === 0 ? (
        <EmptyState
          icon={CheckCircle2}
          title={copy.sources.emptyTitle}
          description={copy.sources.emptyDescription}
        />
      ) : (
        <section className="admin-card overflow-hidden">
          <div className="flex flex-col gap-2 border-b border-border px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-sm font-semibold">{copy.sources.itemsTitle}</h2>
              <p className="mt-1 text-xs text-muted-foreground">
                {copy.sources.shownPrefix} {numberFormatter.format(items.length)}{" "}
                {copy.sources.shownSuffix}
              </p>
            </div>
            <Link href="/dashboard/sources?license=unknown#media" className="text-xs font-semibold text-primary">
              {copy.sources.mediaWithoutLicense}
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-[1040px] w-full text-sm">
              <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">{copy.sources.table.item}</th>
                  <th className="px-4 py-3">{copy.sources.table.issue}</th>
                  <th className="px-4 py-3">{copy.sources.table.relatedPerson}</th>
                  <th className="px-4 py-3">{copy.sources.table.sourceUrl}</th>
                  <th className="px-4 py-3 text-right">{copy.sources.table.destination}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {items.map((item: EditorialSourceVerificationItem) => {
                  const target = sourceVerificationTarget(item, copy);
                  const itemTitle =
                    item.item_type === "person_source" && item.related_person_name
                      ? `${copy.sources.personSourceTitlePrefix}: ${item.related_person_name}`
                      : item.title;

                  return (
                    <tr
                      key={`${item.item_type}:${item.id}:${item.issue_code}`}
                      role="link"
                      tabIndex={0}
                      title={target.hint}
                      onClick={() => navigateToTarget(target.href)}
                      onKeyDown={(event) => handleRowKeyDown(event, target.href)}
                      className="cursor-pointer align-top transition-colors hover:bg-muted/30 focus-visible:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
                    >
                      <td className="px-4 py-4">
                        <Link
                          href={target.href}
                          onClick={stopRowNavigation}
                          className="font-medium hover:text-primary"
                        >
                          {itemTitle}
                        </Link>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {getSourceTypeLabel(item.item_type, domainCopy)}
                        </p>
                        <p className="mt-1 text-[10px] text-muted-foreground">{target.hint}</p>
                      </td>
                      <td className="px-4 py-4">
                        <span className={cn("rounded-md border px-2 py-1 text-[10px]", severityTone[item.severity] ?? "border-border bg-muted text-muted-foreground")}>
                          {getSourceIssueLabel(item, domainCopy)}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        {item.related_person_id ? (
                          <Link
                            href={`/dashboard/persons/${item.related_person_id}`}
                            onClick={stopRowNavigation}
                            className="text-xs font-medium text-primary hover:underline"
                          >
                            {item.related_person_name}
                          </Link>
                        ) : (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="px-4 py-4">
                        {item.source_url ? (
                          <a
                            href={item.source_url}
                            target="_blank"
                            rel="noreferrer"
                            onClick={stopRowNavigation}
                            className="inline-flex max-w-72 items-center gap-1 text-xs text-primary hover:underline"
                          >
                            <ExternalLink className="h-3 w-3 shrink-0" />
                            <span className="truncate">{item.source_url}</span>
                          </a>
                        ) : (
                          <span className="text-xs text-muted-foreground">{copy.sources.noUrl}</span>
                        )}
                      </td>
                      <td className="px-4 py-4 text-right">
                        <Link
                          href={target.href}
                          onClick={stopRowNavigation}
                          className="inline-flex h-8 items-center gap-1 rounded-md border border-border px-2.5 text-xs font-semibold hover:bg-accent"
                        >
                          {target.label} <ArrowRight className="h-3.5 w-3.5" />
                        </Link>
                        <p className="mt-2 text-[10px] text-muted-foreground">
                          {formatAdminDateTime(item.updated_at, locale)}
                        </p>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

export function QualityClient({
  activeTab,
  copy,
  domainCopy,
  locale,
}: {
  activeTab: QualityTab;
  copy: AdminQualityDictionary;
  domainCopy: AdminDomainDictionary;
  locale: string;
}) {
  const qualityQuery = useQuery({
    queryKey: ["editorial", "quality"],
    queryFn: () => editorialApi.quality(),
  });
  const report = qualityQuery.data?.data;
  const numberFormatter = new Intl.NumberFormat(locale);

  if (qualityQuery.isLoading) {
    return (
      <div className="flex min-h-[420px] items-center justify-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> {copy.states.loading}
      </div>
    );
  }

  if (!report) {
    return (
      <div className="admin-card mx-auto max-w-xl p-8 text-center">
        <ShieldAlert className="mx-auto h-8 w-8 text-amber-500" />
        <h1 className="mt-3 text-lg font-semibold">{copy.states.loadErrorTitle}</h1>
        <p className="mt-2 text-sm text-muted-foreground">{copy.states.loadErrorDescription}</p>
        <button
          type="button"
          onClick={() => qualityQuery.refetch()}
          className="mt-5 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
        >
          {copy.states.refreshAction}
        </button>
      </div>
    );
  }

  const summary = report.summary;

  return (
    <div className="mx-auto max-w-[1500px] space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="admin-label">{copy.header.kicker}</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">{copy.header.title}</h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">{copy.header.description}</p>
        </div>
        <button
          type="button"
          onClick={() => qualityQuery.refetch()}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-border px-4 text-sm font-semibold hover:bg-accent"
        >
          <RefreshCw className={cn("h-4 w-4", qualityQuery.isFetching && "animate-spin")} />
          {copy.header.refreshAction}
        </button>
      </header>

      <section
        className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5"
        aria-label={copy.summaryAriaLabel}
      >
        <MetricCard label={copy.summary.recordsWithIssues.label} value={summary.records_with_issues} detail={copy.summary.recordsWithIssues.detail} icon={AlertTriangle} locale={locale} tone="bg-rose-50 text-rose-700 dark:bg-rose-950/30 dark:text-rose-300" />
        <MetricCard label={copy.summary.totalIssues.label} value={summary.total_issues} detail={copy.summary.totalIssues.detail} icon={Database} locale={locale} />
        <MetricCard label={copy.summary.duplicateGroups.label} value={summary.duplicate_groups} detail={`${numberFormatter.format(summary.duplicate_records)} ${copy.summary.duplicateGroups.recordsSuffix}`} icon={Copy} locale={locale} />
        <MetricCard label={copy.summary.sourcesToReview.label} value={summary.source_items_to_review} detail={copy.summary.sourcesToReview.detail} icon={ShieldCheck} locale={locale} />
        <MetricCard label={copy.summary.undocumentedProfiles.label} value={summary.undocumented_persons} detail={`${numberFormatter.format(summary.documented_persons)} ${copy.summary.undocumentedProfiles.documentedSuffix}`} icon={BookOpenText} locale={locale} />
      </section>

      <nav className="admin-card flex flex-col gap-2 p-2 sm:flex-row" aria-label={copy.tabsAriaLabel}>
        {tabs.map(({ key, href, icon: Icon }) => {
          const active = activeTab === key;
          return (
            <Link
              key={key}
              href={href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "inline-flex h-10 flex-1 items-center justify-center gap-2 rounded-lg px-3 text-sm font-semibold transition-colors",
                active ? "bg-primary text-primary-foreground shadow-sm" : "text-muted-foreground hover:bg-accent hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4" /> {copy.tabs[key]}
            </Link>
          );
        })}
      </nav>

      {activeTab === "issues" && (
        <IssuesPanel report={report} copy={copy} domainCopy={domainCopy} locale={locale} />
      )}
      {activeTab === "duplicates" && (
        <DuplicatesPanel
          groups={report.duplicate_groups}
          copy={copy}
          domainCopy={domainCopy}
          locale={locale}
        />
      )}
      {activeTab === "sources" && (
        <SourcesPanel report={report} copy={copy} domainCopy={domainCopy} locale={locale} />
      )}
    </div>
  );
}
