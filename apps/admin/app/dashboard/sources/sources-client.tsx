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
import {
  DOCUMENT_TYPE_LABELS,
  formatDateTime,
  IMAGE_LICENSE_LABELS,
  SOURCE_TYPE_LABELS,
} from "@/lib/utils";

type ApiRecord = Record<string, unknown>;
export type SourcesInitialLicenseFilter = "" | "unknown";

function valueText(value: unknown, fallback = "—") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function scoreLabel(score: unknown) {
  if (typeof score !== "number") return "brak oceny";
  return `${score}/5`;
}

function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
}: {
  label: string;
  value: number;
  detail: string;
  icon: typeof BookOpenText;
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
}: {
  initialLicenseFilter: SourcesInitialLicenseFilter;
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
          <p className="admin-label">Źródła i dane</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Źródła i media</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Bibliografia, źródła historyczne, obrazy i dokumenty powiązane z rekordami.
          </p>
        </div>
        <button
          type="button"
          onClick={refreshAll}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-border px-4 text-sm font-semibold hover:bg-accent"
        >
          <RefreshCw className="h-4 w-4" /> Odśwież dane
        </button>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Podsumowanie źródeł">
        <MetricCard
          label="Bibliografia"
          value={bibliographyTotal}
          detail={`${websiteCount.toLocaleString("pl-PL")} pozycji pochodzi z adresów URL`}
          icon={BookOpenText}
        />
        <MetricCard
          label="Źródła historyczne"
          value={historicalTotal}
          detail={`${digitizedCount.toLocaleString("pl-PL")} pozycji ma digitalizację`}
          icon={Archive}
        />
        <MetricCard
          label="Media"
          value={imagesTotal}
          detail={`${unknownLicenseCount.toLocaleString("pl-PL")} obrazów wymaga licencji`}
          icon={ImageIcon}
        />
        <MetricCard
          label="Dokumenty"
          value={documentsTotal}
          detail={`${documents.filter((doc) => doc.is_public).length.toLocaleString("pl-PL")} dokumentów publicznych`}
          icon={FileText}
        />
      </section>

      <section className="admin-card p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-sm font-semibold">Wyszukiwanie źródeł tekstowych</h2>
            <p className="mt-1 text-xs text-muted-foreground">Przeszukuje bibliografię i źródła historyczne.</p>
          </div>
          <div className="relative w-full sm:max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Szukaj po tytule, autorze lub repozytorium..."
              className="w-full rounded-lg border border-input bg-background py-2 pl-9 pr-3 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
        </div>
      </section>

      {unknownLicenseCount > 0 && (
        <div className="flex flex-col gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/20 dark:text-amber-200 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-4 w-4" />
            <span>{unknownLicenseCount} obrazów ma nieznaną licencję i wymaga weryfikacji przed publikacją profilu.</span>
          </div>
          {licenseFilter === "unknown" ? (
            <Link href="/dashboard/sources#media" className="font-semibold text-amber-950 underline-offset-4 hover:underline dark:text-amber-100">
              Pokaż wszystkie media
            </Link>
          ) : (
            <Link href="/dashboard/sources?license=unknown#media" className="font-semibold text-amber-950 underline-offset-4 hover:underline dark:text-amber-100">
              Pokaż obrazy do sprawdzenia
            </Link>
          )}
        </div>
      )}

      <section className="grid gap-5 xl:grid-cols-2">
        <article id="bibliography" className="admin-card scroll-mt-6 overflow-hidden">
          <div className="border-b border-border px-5 py-4">
            <h2 className="text-sm font-semibold">Bibliografia</h2>
            <p className="mt-1 text-xs text-muted-foreground">Opracowania, artykuły, strony WWW i pozycje encyklopedyczne.</p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-[760px] w-full text-sm">
              <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">Tytuł</th>
                  <th className="px-4 py-3">Typ</th>
                  <th className="px-4 py-3">Rok</th>
                  <th className="px-4 py-3">Ocena</th>
                  <th className="px-4 py-3">Aktualizacja</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {bibliographyQuery.isLoading ? (
                  <EmptyRow colSpan={5} label="Ładowanie bibliografii..." />
                ) : bibliography.length === 0 ? (
                  <EmptyRow colSpan={5} label="Brak pozycji bibliograficznych" />
                ) : (
                  bibliography.map((source) => (
                    <tr key={String(source.id)} className="hover:bg-muted/30">
                      <td className="px-4 py-3">
                        <p className="font-medium text-foreground">{valueText(source.title)}</p>
                        <p className="mt-1 truncate text-xs text-muted-foreground">
                          {valueText(source.authors, "Autor nieuzupełniony")}
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
                        {SOURCE_TYPE_LABELS[String(source.source_type)] ?? valueText(source.source_type)}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">{valueText(source.year)}</td>
                      <td className="px-4 py-3">
                        <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                          {scoreLabel(source.reliability_score)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {formatDateTime(source.updated_at as string)}
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
            <h2 className="text-sm font-semibold">Źródła historyczne</h2>
            <p className="mt-1 text-xs text-muted-foreground">Rękopisy, archiwa, repozytoria i pierwotne świadectwa.</p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-[760px] w-full text-sm">
              <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">Źródło</th>
                  <th className="px-4 py-3">Repozytorium</th>
                  <th className="px-4 py-3">Datowanie</th>
                  <th className="px-4 py-3">Digitalizacja</th>
                  <th className="px-4 py-3">Aktualizacja</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {historicalQuery.isLoading ? (
                  <EmptyRow colSpan={5} label="Ładowanie źródeł historycznych..." />
                ) : historicalSources.length === 0 ? (
                  <EmptyRow colSpan={5} label="Brak źródeł historycznych" />
                ) : (
                  historicalSources.map((source) => (
                    <tr key={String(source.id)} className="hover:bg-muted/30">
                      <td className="px-4 py-3">
                        <p className="font-medium text-foreground">{valueText(source.title)}</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {SOURCE_TYPE_LABELS[String(source.source_type)] ?? valueText(source.source_type)}
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
                            <BadgeCheck className="h-3 w-3" /> Tak
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground">Nie</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {formatDateTime(source.updated_at as string)}
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
                {licenseFilter === "unknown" ? "Media bez zweryfikowanej licencji" : "Media"}
              </h2>
              <p className="mt-1 text-xs text-muted-foreground">
                {licenseFilter === "unknown"
                  ? "Obrazy, które blokują publikację powiązanych profili do czasu weryfikacji licencji."
                  : "Obrazy, avatary i ikonografia powiązana z osobami."}
              </p>
            </div>
            {licenseFilter === "unknown" && (
              <Link href="/dashboard/sources#media" className="text-xs font-semibold text-primary">
                Wyczyść filtr
              </Link>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-[720px] w-full text-sm">
              <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">Obraz</th>
                  <th className="px-4 py-3">Licencja</th>
                  <th className="px-4 py-3">Źródło</th>
                  <th className="px-4 py-3">Rozmiar</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {imagesQuery.isLoading ? (
                  <EmptyRow colSpan={4} label="Ładowanie mediów..." />
                ) : mediaRows.length === 0 ? (
                  <EmptyRow
                    colSpan={4}
                    label={licenseFilter === "unknown" ? "Brak obrazów z nieznaną licencją" : "Brak mediów"}
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
                            <p className="truncate font-medium text-foreground">{valueText(image.title, "Obraz bez tytułu")}</p>
                            <p className="text-xs text-muted-foreground">{valueText(image.image_type, "image")}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                          {IMAGE_LICENSE_LABELS[String(image.license)] ?? valueText(image.license)}
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
            <h2 className="text-sm font-semibold">Dokumenty</h2>
            <p className="mt-1 text-xs text-muted-foreground">Dekrety, biografie, procesy i pliki pomocnicze.</p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-[680px] w-full text-sm">
              <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">Tytuł</th>
                  <th className="px-4 py-3">Typ</th>
                  <th className="px-4 py-3">Język</th>
                  <th className="px-4 py-3">Widoczność</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {documentsQuery.isLoading ? (
                  <EmptyRow colSpan={4} label="Ładowanie dokumentów..." />
                ) : documents.length === 0 ? (
                  <EmptyRow colSpan={4} label="Brak dokumentów" />
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
                        {DOCUMENT_TYPE_LABELS[String(document.document_type)] ?? valueText(document.document_type)}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {valueText(document.language_code)}
                      </td>
                      <td className="px-4 py-3">
                        {document.is_public ? (
                          <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300">
                            Publiczny
                          </span>
                        ) : (
                          <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                            Roboczy
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
        <p className="text-xs text-muted-foreground">Część danych może się jeszcze odświeżać z API.</p>
      )}
    </div>
  );
}
