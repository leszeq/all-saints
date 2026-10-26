"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart3,
  CheckCircle2,
  ExternalLink,
  FileSearch,
  Loader2,
  MessageSquareText,
  MousePointerClick,
  Search,
  XCircle,
  type LucideIcon,
} from "lucide-react";
import { analyticsApi } from "@/lib/api";
import type { ProductEventAggregate, ProductEventName } from "@/lib/analytics";
import type { AdminAnalyticsDictionary } from "@/lib/i18n/types";
import { cn } from "@/lib/utils";

const RANGE_DAYS = 28;

function getDateRange() {
  const end = new Date();
  const start = new Date(end);
  start.setDate(start.getDate() - RANGE_DAYS + 1);
  const format = (value: Date) => value.toISOString().slice(0, 10);
  return { start_date: format(start), end_date: format(end) };
}

function sumEventCount(items: ProductEventAggregate[], eventName: ProductEventName): number {
  return items
    .filter((item) => item.event_name === eventName)
    .reduce((total, item) => total + item.event_count, 0);
}

function sumMetric(
  items: ProductEventAggregate[],
  eventName: ProductEventName,
  field: "zero_results_count" | "search_success_count",
): number {
  return items
    .filter((item) => item.event_name === eventName)
    .reduce((total, item) => total + item[field], 0);
}

function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
  tone,
  locale,
}: {
  label: string;
  value: number | string;
  detail: string;
  icon: LucideIcon;
  tone: string;
  locale: string;
}) {
  return (
    <article className="admin-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-muted-foreground">{label}</p>
          <p className="mt-2 text-3xl font-semibold tracking-tight">
            {typeof value === "number" ? new Intl.NumberFormat(locale).format(value) : value}
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

export function AnalyticsDashboardClient({
  copy,
  locale,
}: {
  copy: AdminAnalyticsDictionary;
  locale: string;
}) {
  const dateRange = useMemo(() => getDateRange(), []);
  const aggregateQuery = useQuery({
    queryKey: ["analytics", "aggregates", dateRange],
    queryFn: async () => (await analyticsApi.rebuild(dateRange)).data,
    staleTime: 15 * 60 * 1000,
  });
  const items = useMemo(() => aggregateQuery.data?.items ?? [], [aggregateQuery.data?.items]);
  const numberFormatter = new Intl.NumberFormat(locale);
  const dateFormatter = new Intl.DateTimeFormat(locale, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  const metrics = useMemo(() => {
    const searches = sumEventCount(items, "search_submitted") + sumEventCount(items, "filter_applied");
    const results = sumEventCount(items, "search_results");
    const success = sumMetric(items, "search_results", "search_success_count");
    const zeroResults = sumMetric(items, "search_results", "zero_results_count");
    const successRate = results ? `${Math.round((success / results) * 100)}%` : "—";
    return {
      searches,
      results,
      success,
      successRate,
      zeroResults,
      profiles: sumEventCount(items, "profile_opened"),
      sources: sumEventCount(items, "source_opened"),
      feedback: sumEventCount(items, "feedback_submitted"),
    };
  }, [items]);

  const dailyRows = useMemo(() => {
    const byDay = new Map<string, ProductEventAggregate[]>();
    items.forEach((item) => {
      const current = byDay.get(item.day) ?? [];
      current.push(item);
      byDay.set(item.day, current);
    });
    return [...byDay.entries()]
      .sort(([left], [right]) => right.localeCompare(left))
      .map(([day, dayItems]) => ({
        day,
        searches: sumEventCount(dayItems, "search_submitted") + sumEventCount(dayItems, "filter_applied"),
        results: sumEventCount(dayItems, "search_results"),
        success: sumMetric(dayItems, "search_results", "search_success_count"),
        zeroResults: sumMetric(dayItems, "search_results", "zero_results_count"),
        profiles: sumEventCount(dayItems, "profile_opened"),
        sources: sumEventCount(dayItems, "source_opened"),
      }));
  }, [items]);

  if (aggregateQuery.isLoading) {
    return (
      <div className="flex min-h-[420px] items-center justify-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> {copy.loading}
      </div>
    );
  }

  if (aggregateQuery.isError || !aggregateQuery.data) {
    return (
      <div className="admin-card mx-auto max-w-xl p-8 text-center">
        <XCircle className="mx-auto h-8 w-8 text-rose-500" />
        <h1 className="mt-3 text-lg font-semibold">{copy.loadError.title}</h1>
        <p className="mt-2 text-sm text-muted-foreground">{copy.loadError.description}</p>
        <button
          type="button"
          onClick={() => aggregateQuery.refetch()}
          className="mt-5 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
        >
          {copy.loadError.refreshAction}
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1500px] space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="admin-label">{copy.header.kicker}</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">{copy.header.title}</h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">{copy.header.description}</p>
        </div>
        <button
          type="button"
          onClick={() => aggregateQuery.refetch()}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-semibold hover:bg-muted"
        >
          <BarChart3 className="h-4 w-4" /> {copy.header.refreshAction}
        </button>
      </header>

      <div className="flex items-center justify-between rounded-xl border border-border bg-muted/20 px-4 py-3 text-xs text-muted-foreground">
        <span>{copy.rangeLabel}: <strong className="text-foreground">{copy.rangeValue}</strong></span>
        <span>{copy.generatedAt}: {dateFormatter.format(new Date(aggregateQuery.data.generated_at))}</span>
      </div>

      <section aria-label={copy.header.title} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label={copy.metrics.searches.label} value={metrics.searches} detail={copy.metrics.searches.detail} icon={Search} tone="bg-blue-100 text-blue-700" locale={locale} />
        <MetricCard label={copy.metrics.results.label} value={metrics.results} detail={copy.metrics.results.detail} icon={FileSearch} tone="bg-violet-100 text-violet-700" locale={locale} />
        <MetricCard label={copy.metrics.success.label} value={`${numberFormatter.format(metrics.success)} · ${metrics.successRate}`} detail={copy.metrics.success.detail} icon={CheckCircle2} tone="bg-emerald-100 text-emerald-700" locale={locale} />
        <MetricCard label={copy.metrics.zeroResults.label} value={metrics.zeroResults} detail={copy.metrics.zeroResults.detail} icon={XCircle} tone="bg-rose-100 text-rose-700" locale={locale} />
        <MetricCard label={copy.metrics.profiles.label} value={metrics.profiles} detail={copy.metrics.profiles.detail} icon={MousePointerClick} tone="bg-amber-100 text-amber-700" locale={locale} />
        <MetricCard label={copy.metrics.sources.label} value={metrics.sources} detail={copy.metrics.sources.detail} icon={ExternalLink} tone="bg-cyan-100 text-cyan-700" locale={locale} />
        <MetricCard label={copy.metrics.feedback.label} value={metrics.feedback} detail={copy.metrics.feedback.detail} icon={MessageSquareText} tone="bg-slate-100 text-slate-700" locale={locale} />
      </section>

      <section className="admin-card overflow-hidden">
        <div className="border-b border-border p-5">
          <h2 className="text-base font-semibold">{copy.funnelTitle}</h2>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">{copy.funnelDescription}</p>
        </div>
        {dailyRows.length === 0 ? (
          <p className="p-8 text-center text-sm text-muted-foreground">{copy.noData}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-xs">
              <thead className="bg-muted/30 text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                <tr>
                  <th className="px-5 py-3 font-semibold">{copy.table.day}</th>
                  <th className="px-3 py-3 font-semibold">{copy.table.searches}</th>
                  <th className="px-3 py-3 font-semibold">{copy.table.results}</th>
                  <th className="px-3 py-3 font-semibold">{copy.table.success}</th>
                  <th className="px-3 py-3 font-semibold">{copy.table.zeroResults}</th>
                  <th className="px-3 py-3 font-semibold">{copy.table.profiles}</th>
                  <th className="px-5 py-3 font-semibold">{copy.table.sources}</th>
                </tr>
              </thead>
              <tbody>
                {dailyRows.map((row) => (
                  <tr key={row.day} className="border-t border-border">
                    <td className="px-5 py-3 font-medium">{dateFormatter.format(new Date(`${row.day}T00:00:00Z`))}</td>
                    <td className="px-3 py-3">{numberFormatter.format(row.searches)}</td>
                    <td className="px-3 py-3">{numberFormatter.format(row.results)}</td>
                    <td className="px-3 py-3 text-emerald-700">{numberFormatter.format(row.success)}</td>
                    <td className="px-3 py-3 text-rose-700">{numberFormatter.format(row.zeroResults)}</td>
                    <td className="px-3 py-3">{numberFormatter.format(row.profiles)}</td>
                    <td className="px-5 py-3">{numberFormatter.format(row.sources)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <p className="text-xs leading-5 text-muted-foreground">{copy.privacyNotice}</p>
    </div>
  );
}
