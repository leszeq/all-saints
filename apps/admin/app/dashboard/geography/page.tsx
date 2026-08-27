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
import { CHURCH_TYPE_LABELS, formatDateTime, cn } from "@/lib/utils";

type ApiRecord = Record<string, unknown>;
type GeographyView = "countries" | "places" | "dioceses" | "churches";

const views: Array<{ key: GeographyView; label: string }> = [
  { key: "countries", label: "Państwa" },
  { key: "places", label: "Miejsca" },
  { key: "dioceses", label: "Diecezje" },
  { key: "churches", label: "Kościoły" },
];

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
}: {
  label: string;
  value: number;
  detail: string;
  icon: typeof Globe2;
}) {
  return (
    <article className="admin-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-muted-foreground">{label}</p>
          <p className="mt-2 text-3xl font-semibold tracking-tight">{value.toLocaleString("pl-PL")}</p>
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

export default function GeographyPage() {
  const [activeView, setActiveView] = useState<GeographyView>("countries");
  const [search, setSearch] = useState("");

  const countriesQuery = useQuery({
    queryKey: ["countries"],
    queryFn: () => geographyApi.countries(),
  });
  const placesQuery = useQuery({
    queryKey: ["geography", "places"],
    queryFn: () => geographyApi.places(),
  });
  const diocesesQuery = useQuery({
    queryKey: ["geography", "dioceses"],
    queryFn: () => geographyApi.dioceses(),
  });
  const churchesQuery = useQuery({
    queryKey: ["geography", "churches"],
    queryFn: () => geographyApi.churches(),
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
          <p className="admin-label">Źródła i dane</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Geografia</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Państwa, miejsca, diecezje oraz obiekty kultu używane w profilach świętych.
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

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Podsumowanie geografii">
        <MetricCard
          label="Państwa i terytoria"
          value={countries.length}
          detail={`${countries.filter((country) => country.is_historical).length.toLocaleString("pl-PL")} wpisów historycznych`}
          icon={Flag}
        />
        <MetricCard
          label="Miejsca"
          value={places.length}
          detail={`${places.filter((place) => place.latitude && place.longitude).length.toLocaleString("pl-PL")} z koordynatami`}
          icon={MapPin}
        />
        <MetricCard
          label="Diecezje"
          value={dioceses.length}
          detail={`${dioceses.filter((diocese) => diocese.is_archdiocese).length.toLocaleString("pl-PL")} archidiecezji`}
          icon={Building2}
        />
        <MetricCard
          label="Kościoły i sanktuaria"
          value={churches.length}
          detail={`${sanctuaryCount.toLocaleString("pl-PL")} miejsc pielgrzymkowych`}
          icon={Church}
        />
      </section>

      <section className="admin-card overflow-hidden">
        <div className="flex flex-col gap-4 border-b border-border px-5 py-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-wrap gap-1 rounded-lg border border-border bg-background p-1">
            {views.map((view) => (
              <button
                key={view.key}
                type="button"
                onClick={() => setActiveView(view.key)}
                className={cn(
                  "h-9 rounded-md px-3 text-sm font-medium transition-colors",
                  activeView === view.key
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {view.label}
              </button>
            ))}
          </div>
          <div className="relative w-full xl:max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Szukaj w aktywnym widoku..."
              className="w-full rounded-lg border border-input bg-background py-2 pl-9 pr-3 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          {activeView === "countries" && (
            <table className="min-w-[900px] w-full text-sm">
              <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">Państwo</th>
                  <th className="px-4 py-3">ISO</th>
                  <th className="px-4 py-3">Stolica</th>
                  <th className="px-4 py-3">Kontynent</th>
                  <th className="px-4 py-3">Typ</th>
                  <th className="px-4 py-3">Aktualizacja</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {countriesQuery.isLoading ? (
                  <EmptyRow colSpan={6} label="Ładowanie państw..." />
                ) : activeRows.length === 0 ? (
                  <EmptyRow colSpan={6} label="Brak państw dla tych kryteriów" />
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
                          {country.is_historical ? "Historyczne" : "Współczesne"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {formatDateTime(country.updated_at as string)}
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
                  <th className="px-4 py-3">Miejsce</th>
                  <th className="px-4 py-3">Państwo</th>
                  <th className="px-4 py-3">Diecezja</th>
                  <th className="px-4 py-3">Koordynaty</th>
                  <th className="px-4 py-3">Aktualizacja</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {placesQuery.isLoading ? (
                  <EmptyRow colSpan={5} label="Ładowanie miejsc..." />
                ) : activeRows.length === 0 ? (
                  <EmptyRow colSpan={5} label="Brak miejsc dla tych kryteriów" />
                ) : (
                  activeRows.map((place) => (
                    <tr key={String(place.id)} className="hover:bg-muted/30">
                      <td className="px-4 py-3">
                        <p className="font-medium text-foreground">{valueText(place.name)}</p>
                        <p className="mt-1 truncate text-xs text-muted-foreground">
                          {valueText(place.name_la || place.name_local, "Nazwa lokalna nieuzupełniona")}
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
                        {formatDateTime(place.updated_at as string)}
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
                  <th className="px-4 py-3">Diecezja</th>
                  <th className="px-4 py-3">Państwo</th>
                  <th className="px-4 py-3">Typ</th>
                  <th className="px-4 py-3">Lata</th>
                  <th className="px-4 py-3">Aktualizacja</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {diocesesQuery.isLoading ? (
                  <EmptyRow colSpan={5} label="Ładowanie diecezji..." />
                ) : activeRows.length === 0 ? (
                  <EmptyRow colSpan={5} label="Brak diecezji dla tych kryteriów" />
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
                          {diocese.is_archdiocese ? "Archidiecezja" : "Diecezja"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {valueText(diocese.founded_year)} - {valueText(diocese.suppressed_year, "obecnie")}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {formatDateTime(diocese.updated_at as string)}
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
                  <th className="px-4 py-3">Kościół</th>
                  <th className="px-4 py-3">Typ</th>
                  <th className="px-4 py-3">Miejsce</th>
                  <th className="px-4 py-3">Diecezja</th>
                  <th className="px-4 py-3">Status kultu</th>
                  <th className="px-4 py-3">Aktualizacja</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {churchesQuery.isLoading ? (
                  <EmptyRow colSpan={6} label="Ładowanie kościołów..." />
                ) : activeRows.length === 0 ? (
                  <EmptyRow colSpan={6} label="Brak kościołów dla tych kryteriów" />
                ) : (
                  activeRows.map((churchItem) => (
                    <tr key={String(churchItem.id)} className="hover:bg-muted/30">
                      <td className="px-4 py-3">
                        <p className="font-medium text-foreground">{valueText(churchItem.name)}</p>
                        <p className="mt-1 truncate text-xs text-muted-foreground">{valueText(churchItem.address)}</p>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {CHURCH_TYPE_LABELS[String(churchItem.church_type)] ?? valueText(churchItem.church_type)}
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
                            ? "Sanktuarium narodowe"
                            : churchItem.is_pilgrimage_site
                              ? "Pielgrzymkowe"
                              : "Lokalne"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {formatDateTime(churchItem.updated_at as string)}
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
        <p className="text-xs text-muted-foreground">Część danych może się jeszcze odświeżać z API.</p>
      )}
    </div>
  );
}
