"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Building2,
  Church,
  Flag,
  Globe2,
  MapPin,
  RefreshCw,
  Search,
} from "lucide-react";
import { geographyApi } from "@/lib/api";
import { formatAdminDateTime } from "@/lib/i18n/format";
import type {
  AdminChurchTypeKey,
  AdminDomainDictionary,
  AdminGeographyDictionary,
} from "@/lib/i18n/types";
import { cn } from "@/lib/utils";

type ApiRecord = Record<string, unknown>;
type GeographyView = "countries" | "places" | "dioceses" | "churches";

const VIEW_KEYS: GeographyView[] = ["countries", "places", "dioceses", "churches"];

function valueText(value: unknown, fallback = "—") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function shortId(value: unknown) {
  const id = valueText(value, "");
  return id ? `${id.slice(0, 8)}…` : "—";
}

function matchesSearch(row: ApiRecord, fields: string[], search: string) {
  const normalized = search.trim().toLowerCase();
  if (!normalized) return true;
  return fields.some((field) =>
    String(row[field] ?? "").toLowerCase().includes(normalized),
  );
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
  icon: typeof Globe2;
  locale: string;
}) {
  return (
    <article className="admin-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-muted-foreground">{label}</p>
          <p className="mt-2 text-3xl font-semibold tracking-tight">{new Intl.NumberFormat(locale).format(value)}</p>
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

interface GeographyClientProps {
  copy: AdminGeographyDictionary;
  domainCopy: AdminDomainDictionary;
  locale: string;
}

export function GeographyClient({ copy, domainCopy, locale }: GeographyClientProps) {
  const [activeView, setActiveView] = useState<GeographyView>("countries");
  const [search, setSearch] = useState("");

  const countriesQuery = useQuery({
    queryKey: ["countries"],
    queryFn: () => geographyApi.countries(),
  });
  const placesQuery = useQuery({
    queryKey: ["geography", "places"],
    queryFn: () => geographyApi.places({ per_page: 500 }),
  });
  const diocesesQuery = useQuery({
    queryKey: ["geography", "dioceses"],
    queryFn: () => geographyApi.dioceses({ per_page: 500 }),
  });
  const churchesQuery = useQuery({
    queryKey: ["geography", "churches"],
    queryFn: () => geographyApi.churches({ per_page: 500 }),
  });

  const countries = useMemo(
    () => (countriesQuery.data?.data ?? []) as ApiRecord[],
    [countriesQuery.data?.data],
  );
  const places = useMemo(
    () => (placesQuery.data?.data ?? []) as ApiRecord[],
    [placesQuery.data?.data],
  );
  const dioceses = useMemo(
    () => (diocesesQuery.data?.data ?? []) as ApiRecord[],
    [diocesesQuery.data?.data],
  );
  const churches = useMemo(
    () => (churchesQuery.data?.data ?? []) as ApiRecord[],
    [churchesQuery.data?.data],
  );
  const placesTotal = Number(placesQuery.data?.headers["x-total-count"] ?? places.length);
  const diocesesTotal = Number(
    diocesesQuery.data?.headers["x-total-count"] ?? dioceses.length,
  );
  const churchesTotal = Number(
    churchesQuery.data?.headers["x-total-count"] ?? churches.length,
  );
  const countryNames = useMemo(
    () => new Map(countries.map((country) => [String(country.id), valueText(country.name_pl)])),
    [countries],
  );
  const placeNames = useMemo(
    () => new Map(places.map((place) => [String(place.id), valueText(place.name)])),
    [places],
  );
  const dioceseNames = useMemo(
    () => new Map(dioceses.map((diocese) => [String(diocese.id), valueText(diocese.name)])),
    [dioceses],
  );

  const activeRows = {
    countries: countries.filter((row) => matchesSearch(row, ["name_pl", "name_en", "capital", "continent"], search)),
    places: places.filter((row) => matchesSearch(row, ["name", "name_la", "name_local", "description"], search)),
    dioceses: dioceses.filter((row) => matchesSearch(row, ["name", "name_la"], search)),
    churches: churches.filter((row) => matchesSearch(row, ["name", "name_la", "address", "description"], search)),
  }[activeView];
  const isLoading =
    countriesQuery.isLoading ||
    placesQuery.isLoading ||
    diocesesQuery.isLoading ||
    churchesQuery.isLoading;
  const sanctuaryCount = churches.filter(
    (churchItem) =>
      churchItem.is_national_sanctuary ||
      churchItem.is_pilgrimage_site ||
      churchItem.church_type === "sanctuary",
  ).length;
  const numberFormatter = new Intl.NumberFormat(locale);

  const refreshAll = () => {
    void Promise.all([
      countriesQuery.refetch(),
      placesQuery.refetch(),
      diocesesQuery.refetch(),
      churchesQuery.refetch(),
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
          label={copy.metrics.countries}
          value={countries.length}
          detail={`${numberFormatter.format(countries.filter((country) => country.is_historical).length)} ${copy.metrics.historicalSuffix}`}
          icon={Flag}
          locale={locale}
        />
        <MetricCard
          label={copy.metrics.places}
          value={placesTotal}
          detail={`${numberFormatter.format(places.filter((place) => place.latitude && place.longitude).length)} ${copy.metrics.coordinatesSuffix}`}
          icon={MapPin}
          locale={locale}
        />
        <MetricCard
          label={copy.metrics.dioceses}
          value={diocesesTotal}
          detail={`${numberFormatter.format(dioceses.filter((diocese) => diocese.is_archdiocese).length)} ${copy.metrics.archdiocesesSuffix}`}
          icon={Building2}
          locale={locale}
        />
        <MetricCard
          label={copy.metrics.churches}
          value={churchesTotal}
          detail={`${numberFormatter.format(sanctuaryCount)} ${copy.metrics.pilgrimageSuffix}`}
          icon={Church}
          locale={locale}
        />
      </section>

      <section className="admin-card overflow-hidden">
        <div className="flex flex-col gap-4 border-b border-border px-5 py-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-wrap gap-1 rounded-lg border border-border bg-background p-1">
            {VIEW_KEYS.map((viewKey) => (
              <button
                key={viewKey}
                type="button"
                onClick={() => setActiveView(viewKey)}
                className={cn(
                  "h-9 rounded-md px-3 text-sm font-medium transition-colors",
                  activeView === viewKey
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {copy.views[viewKey]}
              </button>
            ))}
          </div>
          <div className="relative w-full xl:max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              aria-label={copy.searchAriaLabel}
              placeholder={copy.searchPlaceholder}
              className="w-full rounded-lg border border-input bg-background py-2 pl-9 pr-3 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          {activeView === "countries" && (
            <table className="min-w-[900px] w-full text-sm">
              <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">{copy.columns.country}</th>
                  <th className="px-4 py-3">{copy.columns.iso}</th>
                  <th className="px-4 py-3">{copy.columns.capital}</th>
                  <th className="px-4 py-3">{copy.columns.continent}</th>
                  <th className="px-4 py-3">{copy.columns.type}</th>
                  <th className="px-4 py-3">{copy.columns.updated}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {countriesQuery.isLoading ? (
                  <EmptyRow colSpan={6} label={copy.states.loadingCountries} />
                ) : activeRows.length === 0 ? (
                  <EmptyRow colSpan={6} label={copy.states.emptyCountries} />
                ) : (
                  activeRows.map((country) => (
                    <tr key={String(country.id)} className="hover:bg-muted/30">
                      <td className="px-4 py-3">
                        <span className="mr-2">{valueText(country.flag_emoji, "🌐")}</span>
                        <span className="font-medium text-foreground">{valueText(country.name_pl)}</span>
                        <span className="ml-2 text-xs text-muted-foreground">{valueText(country.name_en)}</span>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                        {valueText(country.iso_code_alpha2)} / {valueText(country.iso_code_alpha3)}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">{valueText(country.capital)}</td>
                      <td className="px-4 py-3 text-muted-foreground">{valueText(country.continent)}</td>
                      <td className="px-4 py-3">
                        <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                          {country.is_historical ? copy.labels.historical : copy.labels.current}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {formatAdminDateTime(country.updated_at as string, locale)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}

          {activeView === "places" && (
            <table className="min-w-[900px] w-full text-sm">
              <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">{copy.columns.place}</th>
                  <th className="px-4 py-3">{copy.columns.country}</th>
                  <th className="px-4 py-3">{copy.columns.diocese}</th>
                  <th className="px-4 py-3">{copy.columns.coordinates}</th>
                  <th className="px-4 py-3">{copy.columns.updated}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {placesQuery.isLoading ? (
                  <EmptyRow colSpan={5} label={copy.states.loadingPlaces} />
                ) : activeRows.length === 0 ? (
                  <EmptyRow colSpan={5} label={copy.states.emptyPlaces} />
                ) : (
                  activeRows.map((place) => (
                    <tr key={String(place.id)} className="hover:bg-muted/30">
                      <td className="px-4 py-3">
                        <p className="font-medium text-foreground">{valueText(place.name)}</p>
                        <p className="mt-1 truncate text-xs text-muted-foreground">
                          {valueText(place.name_la || place.name_local, copy.labels.localNameMissing)}
                        </p>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {countryNames.get(String(place.country_id)) ?? shortId(place.country_id)}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {dioceseNames.get(String(place.diocese_id)) ?? shortId(place.diocese_id)}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {place.latitude && place.longitude ? `${place.latitude}, ${place.longitude}` : "—"}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {formatAdminDateTime(place.updated_at as string, locale)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}

          {activeView === "dioceses" && (
            <table className="min-w-[860px] w-full text-sm">
              <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">{copy.columns.diocese}</th>
                  <th className="px-4 py-3">{copy.columns.country}</th>
                  <th className="px-4 py-3">{copy.columns.type}</th>
                  <th className="px-4 py-3">{copy.columns.years}</th>
                  <th className="px-4 py-3">{copy.columns.updated}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {diocesesQuery.isLoading ? (
                  <EmptyRow colSpan={5} label={copy.states.loadingDioceses} />
                ) : activeRows.length === 0 ? (
                  <EmptyRow colSpan={5} label={copy.states.emptyDioceses} />
                ) : (
                  activeRows.map((diocese) => (
                    <tr key={String(diocese.id)} className="hover:bg-muted/30">
                      <td className="px-4 py-3">
                        <p className="font-medium text-foreground">{valueText(diocese.name)}</p>
                        <p className="mt-1 text-xs italic text-muted-foreground">{valueText(diocese.name_la)}</p>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {countryNames.get(String(diocese.country_id)) ?? shortId(diocese.country_id)}
                      </td>
                      <td className="px-4 py-3">
                        <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                          {diocese.is_archdiocese ? copy.labels.archdiocese : copy.labels.diocese}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {valueText(diocese.founded_year)} - {valueText(diocese.suppressed_year, copy.labels.present)}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {formatAdminDateTime(diocese.updated_at as string, locale)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}

          {activeView === "churches" && (
            <table className="min-w-[920px] w-full text-sm">
              <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">{copy.columns.church}</th>
                  <th className="px-4 py-3">{copy.columns.type}</th>
                  <th className="px-4 py-3">{copy.columns.place}</th>
                  <th className="px-4 py-3">{copy.columns.diocese}</th>
                  <th className="px-4 py-3">{copy.columns.cultStatus}</th>
                  <th className="px-4 py-3">{copy.columns.updated}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {churchesQuery.isLoading ? (
                  <EmptyRow colSpan={6} label={copy.states.loadingChurches} />
                ) : activeRows.length === 0 ? (
                  <EmptyRow colSpan={6} label={copy.states.emptyChurches} />
                ) : (
                  activeRows.map((churchItem) => (
                    <tr key={String(churchItem.id)} className="hover:bg-muted/30">
                      <td className="px-4 py-3">
                        <p className="font-medium text-foreground">{valueText(churchItem.name)}</p>
                        <p className="mt-1 truncate text-xs text-muted-foreground">{valueText(churchItem.address)}</p>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {domainCopy.churchTypeLabels[String(churchItem.church_type) as AdminChurchTypeKey] ?? valueText(churchItem.church_type)}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {placeNames.get(String(churchItem.place_id)) ?? shortId(churchItem.place_id)}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {dioceseNames.get(String(churchItem.diocese_id)) ?? shortId(churchItem.diocese_id)}
                      </td>
                      <td className="px-4 py-3">
                        <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                          {churchItem.is_national_sanctuary
                            ? copy.labels.nationalSanctuary
                            : churchItem.is_pilgrimage_site
                              ? copy.labels.pilgrimage
                              : copy.labels.local}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {formatAdminDateTime(churchItem.updated_at as string, locale)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </div>
      </section>

      {isLoading && (
        <p className="text-xs text-muted-foreground">{copy.states.partialRefresh}</p>
      )}
    </div>
  );
}
