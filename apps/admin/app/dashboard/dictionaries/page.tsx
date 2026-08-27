"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BadgeCheck,
  BriefcaseBusiness,
  Crown,
  Layers3,
  RefreshCw,
  Search,
  Tags,
  UsersRound,
} from "lucide-react";
import { popesApi, taxonomyApi } from "@/lib/api";
import { cn, formatDateTime } from "@/lib/utils";

type ApiRecord = Record<string, unknown>;
type DictionaryView = "categories" | "tags" | "states" | "occupations" | "popes";

const views: Array<{ key: DictionaryView; label: string }> = [
  { key: "categories", label: "Kategorie" },
  { key: "tags", label: "Tagi" },
  { key: "states", label: "Stany życia" },
  { key: "occupations", label: "Zawody" },
  { key: "popes", label: "Papieże" },
];

function valueText(value: unknown, fallback = "—") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
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
  icon: typeof Tags;
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

export default function DictionariesPage() {
  const [activeView, setActiveView] = useState<DictionaryView>("categories");
  const [search, setSearch] = useState("");

  const categoriesQuery = useQuery({
    queryKey: ["taxonomy", "categories"],
    queryFn: () => taxonomyApi.categories(),
  });
  const tagsQuery = useQuery({
    queryKey: ["taxonomy", "tags"],
    queryFn: () => taxonomyApi.tags(),
  });
  const statesQuery = useQuery({
    queryKey: ["taxonomy", "states-of-life"],
    queryFn: () => taxonomyApi.statesOfLife(),
  });
  const occupationsQuery = useQuery({
    queryKey: ["taxonomy", "occupations"],
    queryFn: () => taxonomyApi.occupations(),
  });
  const popesQuery = useQuery({
    queryKey: ["popes"],
    queryFn: () => popesApi.list(),
  });

  const categories = useMemo(
    () => (categoriesQuery.data?.data ?? []) as ApiRecord[],
    [categoriesQuery.data?.data],
  );
  const tagsList = useMemo(
    () => (tagsQuery.data?.data ?? []) as ApiRecord[],
    [tagsQuery.data?.data],
  );
  const states = useMemo(
    () => (statesQuery.data?.data ?? []) as ApiRecord[],
    [statesQuery.data?.data],
  );
  const occupations = useMemo(
    () => (occupationsQuery.data?.data ?? []) as ApiRecord[],
    [occupationsQuery.data?.data],
  );
  const popes = useMemo(
    () => (popesQuery.data?.data ?? []) as ApiRecord[],
    [popesQuery.data?.data],
  );
  const categoryNames = useMemo(
    () => new Map(categories.map((category) => [String(category.id), valueText(category.name_pl)])),
    [categories],
  );
  const activeRows = {
    categories: categories.filter((row) => matchesSearch(row, ["name_pl", "name_en", "description"], search)),
    tags: tagsList.filter((row) => matchesSearch(row, ["name_pl", "name_en"], search)),
    states: states.filter((row) => matchesSearch(row, ["name_pl", "name_en", "name_la", "description"], search)),
    occupations: occupations.filter((row) => matchesSearch(row, ["name_pl", "name_en", "name_la", "description"], search)),
    popes: popes.filter((row) => matchesSearch(row, ["papal_name", "birth_name", "description"], search)),
  }[activeView];
  const isLoading =
    categoriesQuery.isLoading ||
    tagsQuery.isLoading ||
    statesQuery.isLoading ||
    occupationsQuery.isLoading ||
    popesQuery.isLoading;

  const refreshAll = () => {
    void Promise.all([
      categoriesQuery.refetch(),
      tagsQuery.refetch(),
      statesQuery.refetch(),
      occupationsQuery.refetch(),
      popesQuery.refetch(),
    ]);
  };

  return (
    <div className="mx-auto max-w-[1500px] space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="admin-label">Źródła i dane</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Słowniki</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Dane kontrolowane używane w formularzach, filtrach i profilach publicznych.
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

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5" aria-label="Podsumowanie słowników">
        <MetricCard
          label="Kategorie"
          value={categories.length}
          detail={`${categories.filter((category) => category.parent_id).length.toLocaleString("pl-PL")} podkategorii`}
          icon={Layers3}
        />
        <MetricCard
          label="Tagi"
          value={tagsList.length}
          detail={`${tagsList.filter((tag) => tag.color).length.toLocaleString("pl-PL")} z kolorem`}
          icon={Tags}
        />
        <MetricCard
          label="Stany życia"
          value={states.length}
          detail={`${states.filter((state) => state.name_la).length.toLocaleString("pl-PL")} z nazwą łacińską`}
          icon={UsersRound}
        />
        <MetricCard
          label="Zawody"
          value={occupations.length}
          detail={`${occupations.filter((occupation) => occupation.description).length.toLocaleString("pl-PL")} z opisem`}
          icon={BriefcaseBusiness}
        />
        <MetricCard
          label="Papieże"
          value={popes.length}
          detail={`${popes.filter((pope) => pope.person_id).length.toLocaleString("pl-PL")} powiązanych z osobą`}
          icon={Crown}
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
              placeholder="Szukaj w aktywnym słowniku..."
              className="w-full rounded-lg border border-input bg-background py-2 pl-9 pr-3 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          {activeView === "categories" && (
            <table className="min-w-[900px] w-full text-sm">
              <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">Kategoria</th>
                  <th className="px-4 py-3">Slug</th>
                  <th className="px-4 py-3">Rodzic</th>
                  <th className="px-4 py-3">Sortowanie</th>
                  <th className="px-4 py-3">Aktualizacja</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {categoriesQuery.isLoading ? (
                  <EmptyRow colSpan={5} label="Ładowanie kategorii..." />
                ) : activeRows.length === 0 ? (
                  <EmptyRow colSpan={5} label="Brak kategorii dla tych kryteriów" />
                ) : (
                  activeRows.map((category) => (
                    <tr key={String(category.id)} className="hover:bg-muted/30">
                      <td className="px-4 py-3">
                        <p className="font-medium text-foreground">{valueText(category.name_pl)}</p>
                        <p className="mt-1 text-xs text-muted-foreground">{valueText(category.name_en)}</p>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{valueText(category.slug)}</td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {categoryNames.get(String(category.parent_id)) ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">{valueText(category.sort_order)}</td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {formatDateTime(category.updated_at as string)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}

          {activeView === "tags" && (
            <table className="min-w-[760px] w-full text-sm">
              <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">Tag</th>
                  <th className="px-4 py-3">Slug</th>
                  <th className="px-4 py-3">Kolor</th>
                  <th className="px-4 py-3">Aktualizacja</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {tagsQuery.isLoading ? (
                  <EmptyRow colSpan={4} label="Ładowanie tagów..." />
                ) : activeRows.length === 0 ? (
                  <EmptyRow colSpan={4} label="Brak tagów dla tych kryteriów" />
                ) : (
                  activeRows.map((tag) => (
                    <tr key={String(tag.id)} className="hover:bg-muted/30">
                      <td className="px-4 py-3">
                        <p className="font-medium text-foreground">{valueText(tag.name_pl)}</p>
                        <p className="mt-1 text-xs text-muted-foreground">{valueText(tag.name_en)}</p>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{valueText(tag.slug)}</td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center gap-2 text-xs text-muted-foreground">
                          <span
                            className="h-3 w-3 rounded-full border border-border"
                            style={{ backgroundColor: valueText(tag.color, "#d4d4d4") }}
                          />
                          {valueText(tag.color)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {formatDateTime(tag.updated_at as string)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}

          {activeView === "states" && (
            <table className="min-w-[820px] w-full text-sm">
              <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">Stan życia</th>
                  <th className="px-4 py-3">Łacina</th>
                  <th className="px-4 py-3">Opis</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {statesQuery.isLoading ? (
                  <EmptyRow colSpan={3} label="Ładowanie stanów życia..." />
                ) : activeRows.length === 0 ? (
                  <EmptyRow colSpan={3} label="Brak stanów życia dla tych kryteriów" />
                ) : (
                  activeRows.map((state) => (
                    <tr key={String(state.id)} className="hover:bg-muted/30">
                      <td className="px-4 py-3">
                        <p className="font-medium text-foreground">{valueText(state.name_pl)}</p>
                        <p className="mt-1 text-xs text-muted-foreground">{valueText(state.name_en)}</p>
                      </td>
                      <td className="px-4 py-3 italic text-muted-foreground">{valueText(state.name_la)}</td>
                      <td className="px-4 py-3 text-muted-foreground">{valueText(state.description)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}

          {activeView === "occupations" && (
            <table className="min-w-[820px] w-full text-sm">
              <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">Zawód / funkcja</th>
                  <th className="px-4 py-3">Łacina</th>
                  <th className="px-4 py-3">Opis</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {occupationsQuery.isLoading ? (
                  <EmptyRow colSpan={3} label="Ładowanie zawodów..." />
                ) : activeRows.length === 0 ? (
                  <EmptyRow colSpan={3} label="Brak zawodów dla tych kryteriów" />
                ) : (
                  activeRows.map((occupation) => (
                    <tr key={String(occupation.id)} className="hover:bg-muted/30">
                      <td className="px-4 py-3">
                        <p className="font-medium text-foreground">{valueText(occupation.name_pl)}</p>
                        <p className="mt-1 text-xs text-muted-foreground">{valueText(occupation.name_en)}</p>
                      </td>
                      <td className="px-4 py-3 italic text-muted-foreground">{valueText(occupation.name_la)}</td>
                      <td className="px-4 py-3 text-muted-foreground">{valueText(occupation.description)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}

          {activeView === "popes" && (
            <table className="min-w-[860px] w-full text-sm">
              <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">Papież</th>
                  <th className="px-4 py-3">Pontyfikat</th>
                  <th className="px-4 py-3">Numer</th>
                  <th className="px-4 py-3">Powiązanie</th>
                  <th className="px-4 py-3">Aktualizacja</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {popesQuery.isLoading ? (
                  <EmptyRow colSpan={5} label="Ładowanie papieży..." />
                ) : activeRows.length === 0 ? (
                  <EmptyRow colSpan={5} label="Brak papieży dla tych kryteriów" />
                ) : (
                  activeRows.map((pope) => (
                    <tr key={String(pope.id)} className="hover:bg-muted/30">
                      <td className="px-4 py-3">
                        <p className="font-medium text-foreground">{valueText(pope.papal_name)}</p>
                        <p className="mt-1 text-xs text-muted-foreground">{valueText(pope.birth_name, "Imię świeckie nieuzupełnione")}</p>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {valueText(pope.pontificate_start_year)} - {valueText(pope.pontificate_end_year, "obecnie")}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">{valueText(pope.regnal_number)}</td>
                      <td className="px-4 py-3">
                        {pope.person_id ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300">
                            <BadgeCheck className="h-3 w-3" /> Osoba
                          </span>
                        ) : (
                          <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                            Tylko słownik
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {formatDateTime(pope.updated_at as string)}
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
        <p className="text-xs text-muted-foreground">Część słowników może się jeszcze odświeżać z API.</p>
      )}
    </div>
  );
}
