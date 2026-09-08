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
import { useAdminSystemCopy } from "@/components/admin-system-copy-context";
import { aiApi } from "@/lib/api";
import {
  AI_FEATURE_STATUS_COLORS,
  AI_SUGGESTION_STATUS_COLORS,
  type AiDashboard,
  type AiFeatureStatus,
  type AiSuggestionItem,
} from "@/lib/ai";
import { formatAdminDateTime } from "@/lib/i18n/format";
import { formatAdminApiError } from "@/lib/i18n/api-errors";
import type {
  AdminAiCenterDictionary,
  AdminAiFeatureKey,
  AdminAiFeatureStatusKey,
  AdminDomainDictionary,
} from "@/lib/i18n/types";
import { cn } from "@/lib/utils";

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
  locale,
}: {
  label: string;
  value: number | string;
  detail: string;
  icon: ElementType;
  tone: string;
  locale: string;
}) {
  const displayValue = typeof value === "number" ? new Intl.NumberFormat(locale).format(value) : value;

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

function featureDetail(
  feature: AiFeatureStatus,
  dashboard: AiDashboard,
  copy: AdminAiCenterDictionary,
  locale: string,
) {
  const formatNumber = (value: number) => new Intl.NumberFormat(locale).format(value);
  if (feature.key === "embeddings") {
    return `${formatNumber(dashboard.total_embeddings)} ${copy.modules.details.embeddingsMiddle} ${formatNumber(dashboard.total_persons)} ${copy.modules.details.embeddingsSuffix}`;
  }
  if (feature.key === "semantic_search") {
    return dashboard.total_embeddings > 0
      ? copy.modules.details.semanticReady
      : copy.modules.details.semanticNeedsData;
  }
  if (feature.key === "summaries") {
    return dashboard.summary_provider === "extractive-fallback"
      ? copy.modules.details.summariesFallback
      : `${copy.modules.details.summariesPrefix} ${formatNumber(dashboard.ai_summaries)}`;
  }
  if (feature.key === "tagging") {
    return dashboard.summary_provider === "extractive-fallback"
      ? copy.modules.details.taggingDisabled
      : `${copy.modules.details.taggingPrefix} ${formatNumber(dashboard.ai_tags)}`;
  }
  return feature.detail;
}

function SuggestionPreview({
  item,
  copy,
  domainCopy,
}: {
  item: AiSuggestionItem;
  copy: AdminAiCenterDictionary["recent"];
  domainCopy: AdminDomainDictionary;
}) {
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
            {domainCopy.aiSuggestionStatusLabels[item.status]}
          </span>
          <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">
            {domainCopy.aiSuggestionKindLabels[item.kind]}
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
        {copy.openAction} <ArrowRight className="h-3.5 w-3.5" />
      </Link>
    </li>
  );
}

interface AiCentreClientProps {
  copy: AdminAiCenterDictionary;
  domainCopy: AdminDomainDictionary;
  locale: string;
}

export function AiCentreClient({ copy, domainCopy, locale }: AiCentreClientProps) {
  const queryClient = useQueryClient();
  const { apiErrors } = useAdminSystemCopy();
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
      ? formatAdminApiError(batchEmbeddingMutation.error ?? batchTagMutation.error, apiErrors)
      : "";
  const coverage = Math.min(100, Math.max(0, dashboard?.coverage_percent ?? 0));
  const embeddingBatchDisabled = dashboard?.embedding_provider === "disabled";
  const tagBatchDisabled = dashboard?.summary_provider === "extractive-fallback";

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
        <p className="mt-2 text-sm text-muted-foreground">
          {copy.loadError.description}
        </p>
        <button
          onClick={() => dashboardQuery.refetch()}
          className="mt-5 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
        >
          {copy.loadError.refreshAction}
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1500px] space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="admin-label">{copy.kicker}</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">{copy.title}</h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            {copy.description}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => dashboardQuery.refetch()}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-border px-4 text-sm font-semibold hover:bg-accent"
          >
            <RefreshCw className={cn("h-4 w-4", dashboardQuery.isFetching && "animate-spin")} />
            {copy.refreshAction}
          </button>
          <Link
            href="/dashboard/ai/suggestions"
            className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground shadow-sm hover:bg-primary/90"
          >
            {copy.suggestionsAction} ({new Intl.NumberFormat(locale).format(dashboard.pending_suggestions)}) <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label={copy.metricsAriaLabel}>
        <MetricCard
          label={copy.metrics.coverage.label}
          value={`${new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(coverage)}%`}
          detail={`${new Intl.NumberFormat(locale).format(dashboard.total_embeddings)} ${copy.modules.details.embeddingsMiddle} ${new Intl.NumberFormat(locale).format(dashboard.total_persons)} ${copy.metrics.coverage.profilesSuffix}`}
          icon={BrainCircuit}
          tone={metricTones.embeddings}
          locale={locale}
        />
        <MetricCard
          label={copy.metrics.missing.label}
          value={dashboard.missing_embeddings}
          detail={copy.metrics.missing.detail}
          icon={DatabaseZap}
          tone={metricTones.missing}
          locale={locale}
        />
        <MetricCard
          label={copy.metrics.suggestions.label}
          value={dashboard.pending_suggestions}
          detail={copy.metrics.suggestions.detail}
          icon={Sparkles}
          tone={metricTones.suggestions}
          locale={locale}
        />
        <MetricCard
          label={copy.metrics.blocked.label}
          value={dashboard.blocked_suggestions}
          detail={copy.metrics.blocked.detail}
          icon={AlertTriangle}
          tone={metricTones.blocked}
          locale={locale}
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
              <h2 className="text-sm font-semibold">{copy.modules.title}</h2>
              <p className="mt-1 text-xs text-muted-foreground">
                {copy.modules.configuration.prefix} {copy.modules.configuration.embeddings}{" "}
                {dashboard.embedding_provider} · {copy.modules.configuration.model}{" "}
                {dashboard.embedding_model} · {copy.modules.configuration.summaries}{" "}
                {dashboard.summary_provider}
              </p>
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-muted px-2.5 py-1 text-[11px] text-muted-foreground">
              {copy.modules.lastEmbeddingPrefix}{" "}
              {dashboard.last_generated_at
                ? formatAdminDateTime(dashboard.last_generated_at, locale)
                : copy.modules.noEmbedding}
            </span>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {dashboard.feature_statuses.map((feature) => {
              const Icon = featureIcons[feature.key] ?? Bot;
              const localizedFeature = copy.modules.features[feature.key as AdminAiFeatureKey];
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
                      {domainCopy.aiFeatureStatusLabels[feature.status as AdminAiFeatureStatusKey] ?? feature.status}
                    </span>
                  </div>
                  <h3 className="mt-3 text-sm font-semibold">{localizedFeature?.label ?? feature.label}</h3>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">
                    {localizedFeature?.description ?? feature.description}
                  </p>
                  <p className="mt-3 text-[11px] font-medium text-foreground/75">
                    {featureDetail(feature, dashboard, copy, locale)}
                  </p>
                </article>
              );
            })}
          </div>

          <div className="mt-5">
            <div className="mb-2 flex items-center justify-between text-xs">
              <span className="font-medium">{copy.modules.progress}</span>
              <span className="text-muted-foreground">
                {new Intl.NumberFormat(locale, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                }).format(coverage)}%
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <div className="h-full rounded-full bg-primary" style={{ width: `${coverage}%` }} />
            </div>
          </div>
        </article>

        <article className="admin-card p-5">
          <h2 className="text-sm font-semibold">{copy.operations.title}</h2>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            {copy.operations.description}
          </p>
          <div className="mt-5 space-y-3">
            <button
              disabled={batchEmbeddingMutation.isPending || embeddingBatchDisabled}
              onClick={() => batchEmbeddingMutation.mutate()}
              className="flex w-full items-center justify-between gap-3 rounded-xl border border-border p-4 text-left transition-colors hover:border-primary/40 disabled:cursor-wait disabled:opacity-60"
            >
              <span>
                <span className="block text-sm font-semibold">{copy.operations.embeddingsAction}</span>
                <span className="mt-1 block text-xs text-muted-foreground">
                  {embeddingBatchDisabled
                    ? copy.operations.embeddingsDisabled
                    : copy.operations.embeddingsEnabled}
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
                <span className="block text-sm font-semibold">{copy.operations.tagsAction}</span>
                <span className="mt-1 block text-xs text-muted-foreground">
                  {tagBatchDisabled
                    ? copy.operations.tagsDisabled
                    : copy.operations.tagsEnabled}
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
            {copy.operations.safetyNotice}
          </div>
        </article>
      </section>

      <section className="admin-card p-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold">{copy.recent.title}</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              {copy.recent.description}
            </p>
          </div>
          <Link href="/dashboard/ai/suggestions" className="text-xs font-semibold text-primary">
            {copy.recent.allAction}
          </Link>
        </div>
        {dashboard.recent_suggestions.length ? (
          <ul className="mt-4 divide-y divide-border">
            {dashboard.recent_suggestions.map((item) => (
              <SuggestionPreview
                key={item.id}
                item={item}
                copy={copy.recent}
                domainCopy={domainCopy}
              />
            ))}
          </ul>
        ) : (
          <div className="mt-6 rounded-lg bg-emerald-50 p-5 text-center text-xs text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300">
            {copy.recent.empty}
          </div>
        )}
      </section>
    </div>
  );
}
