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
import type { EditorialQueueItem } from "@/lib/editorial";
import type {
  AdminCompletionKey,
  AdminDashboardDictionary,
  AdminDomainDictionary,
  AdminEditorialIssueKey,
} from "@/lib/i18n/types";
import { cn, PERSON_STATUS_COLORS } from "@/lib/utils";

const metricTones = {
  review: "text-blue-700 bg-blue-50 dark:bg-blue-950/30 dark:text-blue-300",
  draft: "text-amber-700 bg-amber-50 dark:bg-amber-950/30 dark:text-amber-300",
  quality: "text-rose-700 bg-rose-50 dark:bg-rose-950/30 dark:text-rose-300",
  license: "text-orange-700 bg-orange-50 dark:bg-orange-950/30 dark:text-orange-300",
};

const completionColors: Record<AdminCompletionKey, string> = {
  complete: "bg-emerald-500",
  partial: "bg-blue-500",
  low: "bg-amber-500",
  critical: "bg-rose-500",
};

function formatMonth(value: string, locale: string) {
  const [year, month] = value.split("-").map(Number);
  return new Intl.DateTimeFormat(locale, { month: "short" })
    .format(new Date(year, month - 1, 1))
    .replace(".", "");
}

function formatEditorialAge(days: number, locale: string): string {
  return new Intl.RelativeTimeFormat(locale, { numeric: "auto" }).format(
    -Math.max(0, days),
    "day",
  );
}

function formatDashboardDateTime(value: string, locale: string): string {
  try {
    return new Intl.DateTimeFormat(locale, {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function getIssueLabel(
  issue: EditorialQueueItem["issues"][number],
  domainCopy: AdminDomainDictionary,
): string {
  return Object.prototype.hasOwnProperty.call(domainCopy.editorialIssueLabels, issue.code)
    ? domainCopy.editorialIssueLabels[issue.code as AdminEditorialIssueKey]
    : issue.label;
}

function getCompletionLabel(
  key: string,
  fallback: string,
  domainCopy: AdminDomainDictionary,
): string {
  return Object.prototype.hasOwnProperty.call(domainCopy.completionLabels, key)
    ? domainCopy.completionLabels[key as AdminCompletionKey]
    : fallback;
}

function QueuePreviewRow({
  item,
  copy,
  domainCopy,
  locale,
}: {
  item: EditorialQueueItem;
  copy: AdminDashboardDictionary;
  domainCopy: AdminDomainDictionary;
  locale: string;
}) {
  const firstIssue = item.issues[0];

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
          {firstIssue ? getIssueLabel(firstIssue, domainCopy) : copy.queue.readyForNextStage} ·{" "}
          {copy.queue.completenessPrefix} {item.completeness_score}%
        </p>
      </div>
      <span className="text-[10px] text-muted-foreground">
        {formatEditorialAge(item.age_days, locale)}
      </span>
    </li>
  );
}

export function EditorialDashboardClient({
  copy,
  domainCopy,
  locale,
}: {
  copy: AdminDashboardDictionary;
  domainCopy: AdminDomainDictionary;
  locale: string;
}) {
  const dashboardQuery = useQuery({
    queryKey: ["editorial", "dashboard"],
    queryFn: () => editorialApi.dashboard(),
  });
  const dashboard = dashboardQuery.data?.data;
  const numberFormatter = new Intl.NumberFormat(locale);
  const today = new Intl.DateTimeFormat(locale, {
    weekday: "long",
    day: "numeric",
    month: "long",
  }).format(new Date());

  if (dashboardQuery.isLoading) {
    return (
      <div className="flex min-h-[420px] items-center justify-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> {copy.loading}
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className="admin-card mx-auto max-w-xl p-8 text-center">
        <AlertTriangle className="mx-auto h-8 w-8 text-amber-500" />
        <h1 className="mt-3 text-lg font-semibold">{copy.loadError.title}</h1>
        <p className="mt-2 text-sm text-muted-foreground">{copy.loadError.description}</p>
        <button
          onClick={() => dashboardQuery.refetch()}
          className="mt-5 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
        >
          {copy.loadError.refreshAction}
        </button>
      </div>
    );
  }

  const metrics: Array<{
    label: string;
    value: number;
    detail: string;
    href: string;
    icon: ElementType;
    tone: string;
  }> = [
    {
      label: copy.metrics.review.label,
      value: dashboard.queue_counts.review,
      detail: copy.metrics.review.detail,
      href: "/dashboard/review?status=review",
      icon: Clock3,
      tone: metricTones.review,
    },
    {
      label: copy.metrics.draft.label,
      value: dashboard.queue_counts.draft,
      detail: copy.metrics.draft.detail,
      href: "/dashboard/review?status=draft",
      icon: FileWarning,
      tone: metricTones.draft,
    },
    {
      label: copy.metrics.quality.label,
      value: dashboard.queue_counts.attention,
      detail: copy.metrics.quality.detail,
      href: "/dashboard/review?attention=1",
      icon: AlertTriangle,
      tone: metricTones.quality,
    },
    {
      label: copy.metrics.license.label,
      value: dashboard.unknown_license_images,
      detail: copy.metrics.license.detail,
      href: "/dashboard/sources?license=unknown#media",
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
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">{copy.header.title}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {copy.header.recordsDescriptionPrefix} {numberFormatter.format(dashboard.total_persons)}{" "}
            {copy.header.recordsDescriptionSuffix}
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/dashboard/review"
            className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-border px-4 text-sm font-semibold hover:bg-accent"
          >
            <Clock3 className="h-4 w-4" />
            <span>
              {copy.header.queueAction} ({numberFormatter.format(dashboard.queue_counts.total)})
            </span>
          </Link>
          <Link
            href="/dashboard/persons/new"
            className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground shadow-sm hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" /> {copy.header.addPersonAction}
          </Link>
        </div>
      </header>

      <section
        className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
        aria-label={copy.operationalQueuesAriaLabel}
      >
        {metrics.map(({ label, value, detail, href, icon: Icon, tone }) => (
          <Link
            key={label}
            href={href}
            className="admin-card group p-4 transition-colors hover:border-primary/40 hover:bg-primary/[0.03]"
            aria-label={`${label}: ${numberFormatter.format(value)}. ${copy.metricOpenAriaLabelSuffix}`}
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium text-muted-foreground">{label}</p>
                <p className="mt-2 text-3xl font-semibold tracking-tight">
                  {numberFormatter.format(value)}
                </p>
              </div>
              <span className={cn("flex h-9 w-9 items-center justify-center rounded-lg", tone)}>
                <Icon className="h-4 w-4" />
              </span>
            </div>
            <p className="mt-3 inline-flex items-center gap-1 text-[11px] text-muted-foreground">
              {detail}
              <ArrowRight className="h-3 w-3 opacity-0 transition-opacity group-hover:opacity-100" />
            </p>
          </Link>
        ))}
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.45fr_.85fr]">
        <article className="admin-card p-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold">{copy.activity.title}</h2>
              <p className="mt-1 text-xs text-muted-foreground">{copy.activity.description}</p>
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300">
              <CheckCircle2 className="h-3 w-3" /> {copy.activity.currentData}
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
                  {numberFormatter.format(count)}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-2 grid grid-cols-12 text-center text-[9px] text-muted-foreground">
            {dashboard.monthly_activity.map(({ month }) => (
              <span key={month}>{formatMonth(month, locale)}</span>
            ))}
          </div>
        </article>

        <article className="admin-card p-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold">{copy.queue.title}</h2>
              <p className="mt-1 text-xs text-muted-foreground">
                {numberFormatter.format(dashboard.queue_counts.total)} {copy.queue.recordsSuffix}
              </p>
            </div>
            <Link href="/dashboard/review" className="text-xs font-semibold text-primary">
              {copy.queue.openAction}
            </Link>
          </div>
          {dashboard.queue_preview.length ? (
            <ul className="mt-4 divide-y divide-border">
              {dashboard.queue_preview.map((item) => (
                <QueuePreviewRow
                  key={item.id}
                  item={item}
                  copy={copy}
                  domainCopy={domainCopy}
                  locale={locale}
                />
              ))}
            </ul>
          ) : (
            <div className="mt-8 rounded-lg bg-emerald-50 p-5 text-center text-xs text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300">
              {copy.queue.empty}
            </div>
          )}
        </article>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.2fr_.8fr_.8fr]">
        <article className="admin-card p-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold">{copy.recent.title}</h2>
              <p className="mt-1 text-xs text-muted-foreground">{copy.recent.description}</p>
            </div>
            <Link href="/dashboard/persons" className="inline-flex items-center gap-1 text-xs font-semibold text-primary">
              {copy.recent.personsAction} <ArrowRight className="h-3 w-3" />
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
                    {person.last_modified_by?.full_name ?? copy.recent.systemActor} ·{" "}
                    {formatDashboardDateTime(person.updated_at, locale)}
                  </p>
                </div>
                <span className={cn("rounded-full px-2 py-1 text-[9px] font-semibold", PERSON_STATUS_COLORS[person.status])}>
                  {domainCopy.personStatusLabels[person.status] ?? person.status}
                </span>
              </div>
            ))}
          </div>
        </article>

        <article className="admin-card p-5">
          <h2 className="text-sm font-semibold">{copy.completion.title}</h2>
          <p className="mt-1 text-xs text-muted-foreground">{copy.completion.description}</p>
          <div className="mt-6 space-y-4">
            {dashboard.completion.map(({ key, label, count, percentage }) => (
              <div key={key}>
                <div className="flex justify-between text-[11px]">
                  <span>
                    {getCompletionLabel(key, label, domainCopy)}{" "}
                    <span className="text-muted-foreground">({numberFormatter.format(count)})</span>
                  </span>
                  <span className="font-semibold">{percentage}%</span>
                </div>
                <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-muted">
                  <div
                    className={cn(
                      "h-full rounded-full",
                      completionColors[key as AdminCompletionKey] ?? "bg-slate-500",
                    )}
                    style={{ width: `${percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </article>

        <article className="admin-card p-5">
          <h2 className="text-sm font-semibold">{copy.resources.title}</h2>
          <p className="mt-1 text-xs text-muted-foreground">{copy.resources.description}</p>
          <dl className="mt-5 space-y-3 text-xs">
            {[
              [copy.resources.labels.users, dashboard.resources.users, Users],
              [copy.resources.labels.countries, dashboard.resources.countries, ShieldCheck],
              [copy.resources.labels.orders, dashboard.resources.orders, ShieldCheck],
              [copy.resources.labels.bibliography, dashboard.resources.bibliography, BookOpenText],
            ].map(([label, value, Icon]) => {
              const ResourceIcon = Icon as ElementType;
              return (
                <div key={String(label)} className="flex items-center justify-between border-b border-border pb-3">
                  <dt className="flex items-center gap-2 text-muted-foreground"><ResourceIcon className="h-3.5 w-3.5" />{String(label)}</dt>
                  <dd className="font-semibold">{numberFormatter.format(Number(value))}</dd>
                </div>
              );
            })}
          </dl>
          <div className="mt-5 flex items-center gap-2 rounded-lg bg-emerald-50 px-3 py-2 text-[10px] font-medium text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300">
            <span className="status-dot bg-emerald-500" /> {copy.resources.synchronized}
          </div>
        </article>
      </section>

      {dashboard.unknown_license_images > 0 && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/20 dark:text-amber-200">
          <AlertTriangle className="h-4 w-4" />
          <span>
            <strong>{copy.licenseAlert.prefix}</strong>{" "}
            {numberFormatter.format(dashboard.unknown_license_images)} {copy.licenseAlert.suffix}
          </span>
        </div>
      )}
    </div>
  );
}
