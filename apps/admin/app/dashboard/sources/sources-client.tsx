"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Archive,
  BadgeCheck,
  BookOpenText,
  ExternalLink,
  FileText,
  Image as ImageIcon,
  Link2,
  RefreshCw,
  Search,
  ShieldAlert,
} from "lucide-react";
import { sourcesApi } from "@/lib/api";
import { formatAdminDateTime } from "@/lib/i18n/format";
import type {
  AdminAvatarLicenseKey,
  AdminDocumentTypeKey,
  AdminDomainDictionary,
  AdminSourcesHubDictionary,
  AdminSourceTypeKey,
} from "@/lib/i18n/types";

type ApiRecord = Record<string, unknown>;
export type SourcesInitialLicenseFilter = "" | "unknown";

function valueText(value: unknown, fallback = "—") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function scoreLabel(score: unknown, noScoreLabel: string) {
  if (typeof score !== "number") return noScoreLabel;
  return `${score}/5`;
}

function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
  locale,
}: {
  label: string;
  value: number;
  detail: string;
  icon: typeof BookOpenText;
  locale: string;
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
        <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Icon className="h-4 w-4" />
        </span>
      </div>
      <p className="mt-3 text-[11px] text-muted-foreground">{detail}</p>
    </article>
  );
}

function EmptyRow({ colSpan, label }: { colSpan: number; label: string }) {
  return (
    <tr>
      <td colSpan={colSpan} className="px-4 py-8 text-center text-sm text-muted-foreground">
        {label}
      </td>
    </tr>
  );
}

export function SourcesClient({
  initialLicenseFilter,
  copy,
  domainCopy,
  locale,
}: {
  initialLicenseFilter: SourcesInitialLicenseFilter;
  copy: AdminSourcesHubDictionary;
  domainCopy: AdminDomainDictionary;
  locale: string;
}) {
  const [search, setSearch] = useState("");
  const licenseFilter = initialLicenseFilter;

  const bibliographyQuery = useQuery({
    queryKey: ["sources", "bibliography", search],
    queryFn: () => sourcesApi.bibliography({ search: search || undefined, per_page: 500 }),
  });
  const historicalQuery = useQuery({
    queryKey: ["sources", "historical", search],
    queryFn: () => sourcesApi.historicalSources({ search: search || undefined, per_page: 500 }),
  });
  const imagesQuery = useQuery({
    queryKey: ["sources", "images", licenseFilter],
    queryFn: () =>
      sourcesApi.images({
        ...(licenseFilter ? { license: licenseFilter } : {}),
        per_page: licenseFilter ? 500 : 100,
      }),
  });
  const unknownImagesQuery = useQuery({
    queryKey: ["sources", "images", "license", "unknown"],
    queryFn: () => sourcesApi.images({ license: "unknown", per_page: 500 }),
    enabled: licenseFilter !== "unknown",
  });
  const documentsQuery = useQuery({
    queryKey: ["sources", "documents"],
    queryFn: () => sourcesApi.documents({ per_page: 500 }),
  });

  const bibliography = (bibliographyQuery.data?.data ?? []) as ApiRecord[];
  const historicalSources = (historicalQuery.data?.data ?? []) as ApiRecord[];
  const images = (imagesQuery.data?.data ?? []) as ApiRecord[];
  const unknownLicenseImages = (
    licenseFilter === "unknown" ? images : (unknownImagesQuery.data?.data ?? [])
  ) as ApiRecord[];
  const documents = (documentsQuery.data?.data ?? []) as ApiRecord[];
  const mediaRows = licenseFilter === "unknown" ? images : images.slice(0, 20);
  const isLoading =
    bibliographyQuery.isLoading ||
    historicalQuery.isLoading ||
    imagesQuery.isLoading ||
    documentsQuery.isLoading;
  const bibliographyTotal = Number(
    bibliographyQuery.data?.headers["x-total-count"] ?? bibliography.length,
  );
  const historicalTotal = Number(
    historicalQuery.data?.headers["x-total-count"] ?? historicalSources.length,
  );
  const imagesTotal = Number(imagesQuery.data?.headers["x-total-count"] ?? images.length);
  const documentsTotal = Number(
    documentsQuery.data?.headers["x-total-count"] ?? documents.length,
  );
  const unknownLicenseCount = Number(
    (licenseFilter === "unknown" ? imagesQuery : unknownImagesQuery).data?.headers[
      "x-total-count"
    ] ?? unknownLicenseImages.length,
  );
  const websiteCount = bibliography.filter((source) => source.source_type === "website").length;
  const digitizedCount = historicalSources.filter((source) => source.is_digitized).length;
  const numberFormatter = new Intl.NumberFormat(locale);

  const refreshAll = () => {
    void Promise.all([
      bibliographyQuery.refetch(),
      historicalQuery.refetch(),
      imagesQuery.refetch(),
      unknownImagesQuery.refetch(),
      documentsQuery.refetch(),
    ]);
  };

  return (
    <div className="mx-auto max-w-[1500px] space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="admin-label">{copy.kicker}</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">{copy.title}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {copy.description}
          </p>
        </div>
        <button
          type="button"
          onClick={refreshAll}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-border px-4 text-sm font-semibold hover:bg-accent"
        >
          <RefreshCw className="h-4 w-4" /> {copy.refreshAction}
        </button>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label={copy.summaryAriaLabel}>
        <MetricCard
          label={copy.metrics.bibliography}
          value={bibliographyTotal}
          detail={`${numberFormatter.format(websiteCount)} ${copy.metrics.websiteSuffix}`}
          icon={BookOpenText}
          locale={locale}
        />
        <MetricCard
          label={copy.metrics.historical}
          value={historicalTotal}
          detail={`${numberFormatter.format(digitizedCount)} ${copy.metrics.digitizedSuffix}`}
          icon={Archive}
          locale={locale}
        />
        <MetricCard
          label={copy.metrics.media}
          value={imagesTotal}
          detail={`${numberFormatter.format(unknownLicenseCount)} ${copy.metrics.unknownLicenseSuffix}`}
          icon={ImageIcon}
          locale={locale}
        />
        <MetricCard
          label={copy.metrics.documents}
          value={documentsTotal}
          detail={`${numberFormatter.format(documents.filter((doc) => doc.is_public).length)} ${copy.metrics.publicDocumentsSuffix}`}
          icon={FileText}
          locale={locale}
        />
      </section>

      <section className="admin-card p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-sm font-semibold">{copy.search.title}</h2>
            <p className="mt-1 text-xs text-muted-foreground">{copy.search.description}</p>
          </div>
          <div className="relative w-full sm:max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              aria-label={copy.search.ariaLabel}
              placeholder={copy.search.placeholder}
              className="w-full rounded-lg border border-input bg-background py-2 pl-9 pr-3 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
        </div>
      </section>

      {unknownLicenseCount > 0 && (
        <div className="flex flex-col gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/20 dark:text-amber-200 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-4 w-4" />
            <span>{copy.licenseAlert.prefix} {numberFormatter.format(unknownLicenseCount)}. {copy.licenseAlert.suffix}</span>
          </div>
          {licenseFilter === "unknown" ? (
            <Link href="/dashboard/sources#media" className="font-semibold text-amber-950 underline-offset-4 hover:underline dark:text-amber-100">
              {copy.licenseAlert.showAll}
            </Link>
          ) : (
            <Link href="/dashboard/sources?license=unknown#media" className="font-semibold text-amber-950 underline-offset-4 hover:underline dark:text-amber-100">
              {copy.licenseAlert.showReview}
            </Link>
          )}
        </div>
      )}

      <section className="grid gap-5 xl:grid-cols-2">
        <article id="bibliography" className="admin-card scroll-mt-6 overflow-hidden">
          <div className="border-b border-border px-5 py-4">
            <h2 className="text-sm font-semibold">{copy.bibliography.title}</h2>
            <p className="mt-1 text-xs text-muted-foreground">{copy.bibliography.description}</p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-[760px] w-full text-sm">
              <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">{copy.bibliography.columns.title}</th>
                  <th className="px-4 py-3">{copy.bibliography.columns.type}</th>
                  <th className="px-4 py-3">{copy.bibliography.columns.year}</th>
                  <th className="px-4 py-3">{copy.bibliography.columns.score}</th>
                  <th className="px-4 py-3">{copy.bibliography.columns.updated}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {bibliographyQuery.isLoading ? (
                  <EmptyRow colSpan={5} label={copy.bibliography.loading} />
                ) : bibliography.length === 0 ? (
                  <EmptyRow colSpan={5} label={copy.bibliography.empty} />
                ) : (
                  bibliography.map((source) => (
                    <tr key={String(source.id)} className="hover:bg-muted/30">
                      <td className="px-4 py-3">
                        <p className="font-medium text-foreground">{valueText(source.title)}</p>
                        <p className="mt-1 truncate text-xs text-muted-foreground">
                          {valueText(source.authors, copy.bibliography.authorMissing)}
                        </p>
                        {Boolean(source.url) && (
                          <a
                            href={String(source.url)}
                            target="_blank"
                            rel="noreferrer"
                            className="mt-1 inline-flex max-w-72 items-center gap-1 text-xs text-primary hover:underline"
                          >
                            <ExternalLink className="h-3 w-3 shrink-0" />
                            <span className="truncate">{String(source.url)}</span>
                          </a>
                        )}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {domainCopy.sourceTypeLabels[String(source.source_type) as AdminSourceTypeKey] ?? valueText(source.source_type)}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">{valueText(source.year)}</td>
                      <td className="px-4 py-3">
                        <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                          {scoreLabel(source.reliability_score, copy.bibliography.noScore)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {formatAdminDateTime(source.updated_at as string, locale)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </article>

        <article id="historical-sources" className="admin-card scroll-mt-6 overflow-hidden">
          <div className="border-b border-border px-5 py-4">
            <h2 className="text-sm font-semibold">{copy.historical.title}</h2>
            <p className="mt-1 text-xs text-muted-foreground">{copy.historical.description}</p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-[760px] w-full text-sm">
              <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">{copy.historical.columns.source}</th>
                  <th className="px-4 py-3">{copy.historical.columns.repository}</th>
                  <th className="px-4 py-3">{copy.historical.columns.dating}</th>
                  <th className="px-4 py-3">{copy.historical.columns.digitization}</th>
                  <th className="px-4 py-3">{copy.historical.columns.updated}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {historicalQuery.isLoading ? (
                  <EmptyRow colSpan={5} label={copy.historical.loading} />
                ) : historicalSources.length === 0 ? (
                  <EmptyRow colSpan={5} label={copy.historical.empty} />
                ) : (
                  historicalSources.map((source) => (
                    <tr key={String(source.id)} className="hover:bg-muted/30">
                      <td className="px-4 py-3">
                        <p className="font-medium text-foreground">{valueText(source.title)}</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {domainCopy.sourceTypeLabels[String(source.source_type) as AdminSourceTypeKey] ?? valueText(source.source_type)}
                        </p>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {valueText(source.repository)}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {valueText(source.date_range)}
                      </td>
                      <td className="px-4 py-3">
                        {source.is_digitized ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300">
                            <BadgeCheck className="h-3 w-3" /> {copy.historical.yes}
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground">{copy.historical.no}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {formatAdminDateTime(source.updated_at as string, locale)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section className="grid gap-5 xl:grid-cols-2">
        <article id="media" className="admin-card scroll-mt-6 overflow-hidden">
          <div className="flex flex-col gap-3 border-b border-border px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-sm font-semibold">
                {licenseFilter === "unknown" ? copy.media.filteredTitle : copy.media.title}
              </h2>
              <p className="mt-1 text-xs text-muted-foreground">
                {licenseFilter === "unknown"
                  ? copy.media.filteredDescription
                  : copy.media.description}
              </p>
            </div>
            {licenseFilter === "unknown" && (
              <Link href="/dashboard/sources#media" className="text-xs font-semibold text-primary">
                {copy.media.clearFilter}
              </Link>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-[720px] w-full text-sm">
              <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">{copy.media.columns.image}</th>
                  <th className="px-4 py-3">{copy.media.columns.license}</th>
                  <th className="px-4 py-3">{copy.media.columns.source}</th>
                  <th className="px-4 py-3">{copy.media.columns.size}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {imagesQuery.isLoading ? (
                  <EmptyRow colSpan={4} label={copy.media.loading} />
                ) : mediaRows.length === 0 ? (
                  <EmptyRow
                    colSpan={4}
                    label={licenseFilter === "unknown" ? copy.media.filteredEmpty : copy.media.empty}
                  />
                ) : (
                  mediaRows.map((image) => (
                    <tr key={String(image.id)} className="hover:bg-muted/30">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <span className="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-muted">
                            {Boolean(image.thumbnail_url || image.url) ? (
                              // eslint-disable-next-line @next/next/no-img-element
                              <img
                                src={String(image.thumbnail_url || image.url)}
                                alt=""
                                className="h-full w-full object-cover"
                              />
                            ) : (
                              <ImageIcon className="h-4 w-4 text-muted-foreground" />
                            )}
                          </span>
                          <div className="min-w-0">
                            <p className="truncate font-medium text-foreground">{valueText(image.title, copy.media.untitled)}</p>
                            <p className="text-xs text-muted-foreground">{valueText(image.image_type, copy.media.imageTypeFallback)}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                          {domainCopy.avatarLicenseLabels[String(image.license) as AdminAvatarLicenseKey] ?? valueText(image.license)}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {Boolean(image.source_url) ? (
                          <a
                            href={String(image.source_url)}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex max-w-60 items-center gap-1 text-xs text-primary hover:underline"
                          >
                            <Link2 className="h-3 w-3 shrink-0" />
                            <span className="truncate">{String(image.source_url)}</span>
                          </a>
                        ) : (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {image.width_px && image.height_px ? `${image.width_px} × ${image.height_px}` : "—"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </article>

        <article className="admin-card overflow-hidden">
          <div className="border-b border-border px-5 py-4">
            <h2 className="text-sm font-semibold">{copy.documents.title}</h2>
            <p className="mt-1 text-xs text-muted-foreground">{copy.documents.description}</p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-[680px] w-full text-sm">
              <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">{copy.documents.columns.title}</th>
                  <th className="px-4 py-3">{copy.documents.columns.type}</th>
                  <th className="px-4 py-3">{copy.documents.columns.language}</th>
                  <th className="px-4 py-3">{copy.documents.columns.visibility}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {documentsQuery.isLoading ? (
                  <EmptyRow colSpan={4} label={copy.documents.loading} />
                ) : documents.length === 0 ? (
                  <EmptyRow colSpan={4} label={copy.documents.empty} />
                ) : (
                  documents.map((document) => (
                    <tr key={String(document.id)} className="hover:bg-muted/30">
                      <td className="px-4 py-3">
                        <p className="font-medium text-foreground">{valueText(document.title)}</p>
                        {Boolean(document.file_url) && (
                          <a
                            href={String(document.file_url)}
                            target="_blank"
                            rel="noreferrer"
                            className="mt-1 inline-flex max-w-72 items-center gap-1 text-xs text-primary hover:underline"
                          >
                            <ExternalLink className="h-3 w-3 shrink-0" />
                            <span className="truncate">{String(document.file_url)}</span>
                          </a>
                        )}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {domainCopy.documentTypeLabels[String(document.document_type) as AdminDocumentTypeKey] ?? valueText(document.document_type)}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {valueText(document.language_code)}
                      </td>
                      <td className="px-4 py-3">
                        {document.is_public ? (
                          <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300">
                            {copy.documents.public}
                          </span>
                        ) : (
                          <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                            {copy.documents.draft}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </article>
      </section>

      {isLoading && (
        <p className="text-xs text-muted-foreground">{copy.partialRefresh}</p>
      )}
    </div>
  );
}
