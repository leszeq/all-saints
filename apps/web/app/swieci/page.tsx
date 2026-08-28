import Link from "next/link";
import { BookOpen, ChevronRight, Search } from "lucide-react";
import { fetchPersons } from "@/lib/api";
import {
  ERA_LABELS,
  LEGACY_ERA_PERIODS,
  LEGACY_SEARCH_PATRONAGES,
  PATRONAGE_GROUPS,
  PERSON_TYPE_DESCRIPTIONS,
  PERSON_TYPE_LABELS,
  TIME_PERIODS,
} from "@/lib/utils";
import { SaintAvatar, type SaintAvatarData } from "@/components/saint-avatar";

export const revalidate = 30;

type SearchParamValue = string | string[] | undefined;

interface PageProps {
  searchParams: Promise<{
    search?: SearchParamValue;
    type?: SearchParamValue;
    era?: SearchParamValue;
    period?: SearchParamValue;
    patronage?: SearchParamValue;
    gender?: SearchParamValue;
    page?: SearchParamValue;
  }>;
}

const GENDER_LABELS: Record<string, string> = {
  male: "Mężczyźni",
  female: "Kobiety",
  unknown: "Nieustalone",
};

const PATRONAGE_TYPE_LABELS: Record<string, string> = {
  illness: "choroba",
  healthcare: "opieka",
  family: "rodzina",
  profession: "zawód",
  work: "praca",
  travel: "droga",
  country: "kraj",
  city: "miasto",
  diocese: "diecezja",
  other: "inne",
};

type PatronageRecord = {
  id?: string;
  patronage_type?: string;
  name_pl?: string;
  description?: string | null;
  is_official?: boolean;
};

function normalizeParamValues(value: SearchParamValue | SearchParamValue[]): string[] {
  const values = Array.isArray(value) ? value : [value];

  return values
    .flatMap((item) => (Array.isArray(item) ? item : [item]))
    .map((item) => item?.trim() ?? "")
    .filter(Boolean);
}

function firstParamValue(value: SearchParamValue): string {
  return normalizeParamValues(value)[0] ?? "";
}

function validParamValues(
  value: SearchParamValue | SearchParamValue[],
  dictionary: Record<string, unknown>,
): string[] {
  return Array.from(
    new Set(normalizeParamValues(value).filter((item) => item in dictionary)),
  );
}

function buildDirectoryHref({
  search,
  typeFilters,
  genderFilters,
  periodFilters,
  eraFilters,
  patronageFilters,
  page,
}: {
  search: string;
  typeFilters: string[];
  genderFilters: string[];
  periodFilters: string[];
  eraFilters: string[];
  patronageFilters: string[];
  page?: number;
}) {
  const query = new URLSearchParams();

  if (search) query.set("search", search);
  typeFilters.forEach((value) => query.append("type", value));
  genderFilters.forEach((value) => query.append("gender", value));
  periodFilters.forEach((value) => query.append("period", value));
  eraFilters.forEach((value) => query.append("era", value));
  patronageFilters.forEach((value) => query.append("patronage", value));
  if (page && page > 1) query.set("page", String(page));

  const serialized = query.toString();
  return serialized ? `/swieci?${serialized}` : "/swieci";
}

function getPersonPatronages(person: Record<string, unknown>): PatronageRecord[] {
  const rawPatronages = person.patronages;
  if (!Array.isArray(rawPatronages)) return [];

  return rawPatronages
    .filter((item): item is PatronageRecord => {
      return Boolean(item && typeof item === "object" && "name_pl" in item);
    })
    .sort((a, b) => {
      const officialDifference = Number(Boolean(b.is_official)) - Number(Boolean(a.is_official));
      if (officialDifference !== 0) return officialDifference;
      return String(a.name_pl ?? "").localeCompare(String(b.name_pl ?? ""), "pl");
    });
}

function splitAttributes(value: unknown): string[] {
  if (typeof value !== "string") return [];
  return value
    .split(/[;\n]/)
    .map((attribute) => attribute.trim())
    .filter(Boolean)
    .slice(0, 4);
}

function FilterOption({
  name,
  value,
  label,
  checked,
}: {
  name: string;
  value: string;
  label: string;
  checked: boolean;
}) {
  return (
    <label className="cursor-pointer">
      <input
        type="checkbox"
        name={name}
        value={value}
        defaultChecked={checked}
        className="peer sr-only"
      />
      <span className="inline-flex rounded-full border border-gold-500/25 bg-white px-3 py-1.5 text-xs font-semibold text-stone-600 transition-colors hover:border-gold-500/60 hover:bg-gold-50 peer-checked:border-burgundy-900 peer-checked:bg-burgundy-900 peer-checked:text-white">
        {label}
      </span>
    </label>
  );
}

export default async function SaintsDirectoryPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const rawSearch = firstParamValue(params.search);
  const legacyPatronage = LEGACY_SEARCH_PATRONAGES[rawSearch]
    ? [LEGACY_SEARCH_PATRONAGES[rawSearch]]
    : [];
  const legacyPeriods = normalizeParamValues(params.era)
    .map((value) => LEGACY_ERA_PERIODS[value])
    .filter(Boolean);
  const patronageFilters = validParamValues(
    [params.patronage, legacyPatronage],
    PATRONAGE_GROUPS,
  );
  const search = legacyPatronage.length ? "" : rawSearch;
  const typeFilters = validParamValues(params.type, PERSON_TYPE_LABELS);
  const genderFilters = validParamValues(params.gender, GENDER_LABELS);
  const periodFilters = validParamValues([params.period, legacyPeriods], TIME_PERIODS);
  const eraFilters = periodFilters.length ? [] : validParamValues(params.era, ERA_LABELS);
  const page = Number(firstParamValue(params.page) || "1");
  const activeFilters = [
    ...typeFilters.map((value) => ({
      label: PERSON_TYPE_LABELS[value],
      context: PERSON_TYPE_DESCRIPTIONS[value],
    })),
    ...genderFilters.map((value) => ({
      label: GENDER_LABELS[value],
      context: "Płeć",
    })),
    ...periodFilters.map((value) => ({
      label: TIME_PERIODS[value as keyof typeof TIME_PERIODS].range,
      context: TIME_PERIODS[value as keyof typeof TIME_PERIODS].title,
    })),
    ...eraFilters.map((value) => ({
      label: ERA_LABELS[value],
      context: "Epoka",
    })),
    ...patronageFilters.map((value) => ({
      label: PATRONAGE_GROUPS[value as keyof typeof PATRONAGE_GROUPS].title,
      context: PATRONAGE_GROUPS[value as keyof typeof PATRONAGE_GROUPS].detail,
    })),
  ];

  let persons: Array<Record<string, unknown>> = [];
  let total = 0;
  let totalPages = 1;

  try {
    const res = await fetchPersons({
      page,
      per_page: 18,
      ...(search && { search }),
      ...(typeFilters.length && { person_type: typeFilters }),
      ...(genderFilters.length && { gender: genderFilters }),
      ...(periodFilters.length && { period: periodFilters }),
      ...(patronageFilters.length && { patronage: patronageFilters }),
      ...(eraFilters.length && { era: eraFilters }),
    });
    persons = res?.items ?? [];
    total = res?.total ?? 0;
    totalPages = res?.pages ?? 1;
  } catch {
    persons = [];
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8 space-y-8">
      {/* Page Title */}
      <div>
        <h1 className="font-serif text-3xl sm:text-4xl font-bold text-burgundy-900">
          Katalog Świętych i Błogosławionych
        </h1>
        <p className="mt-1 text-sm text-gray-600">
          Przeszukaj całą bazę hagiograficzną Kościoła Katolickiego
        </p>
      </div>

      {/* Search & Filter Bar */}
      <form method="GET" className="rounded-2xl border border-gold-500/20 bg-white p-4 shadow-sm">
        {/* Search Input */}
        <div className="relative">
          <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gold-600" />
          <input
            type="text"
            name="search"
            defaultValue={search}
            placeholder="Szukaj po imieniu, patronacie lub atrybucie ikonograficznym..."
            className="w-full rounded-xl border border-gold-500/30 bg-gray-50/50 py-2.5 pl-10 pr-4 text-sm text-gray-900 focus:border-gold-500 focus:outline-none focus:ring-2 focus:ring-gold-400/20"
          />
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <fieldset>
            <legend className="text-[11px] font-bold uppercase tracking-[0.16em] text-stone-500">
              Typ osoby
            </legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {Object.entries(PERSON_TYPE_LABELS).map(([value, label]) => (
                <FilterOption
                  key={value}
                  name="type"
                  value={value}
                  label={label}
                  checked={typeFilters.includes(value)}
                />
              ))}
            </div>
          </fieldset>

          <fieldset>
            <legend className="text-[11px] font-bold uppercase tracking-[0.16em] text-stone-500">
              Płeć
            </legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {Object.entries(GENDER_LABELS).map(([value, label]) => (
                <FilterOption
                  key={value}
                  name="gender"
                  value={value}
                  label={label}
                  checked={genderFilters.includes(value)}
                />
              ))}
            </div>
          </fieldset>

          <fieldset>
            <legend className="text-[11px] font-bold uppercase tracking-[0.16em] text-stone-500">
              Patronaty
            </legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {Object.entries(PATRONAGE_GROUPS).map(([value, group]) => (
                <FilterOption
                  key={value}
                  name="patronage"
                  value={value}
                  label={group.title}
                  checked={patronageFilters.includes(value)}
                />
              ))}
            </div>
          </fieldset>

          <fieldset>
            <legend className="text-[11px] font-bold uppercase tracking-[0.16em] text-stone-500">
              Okres historyczny
            </legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {Object.entries(TIME_PERIODS).map(([value, period]) => (
                <FilterOption
                  key={value}
                  name="period"
                  value={value}
                  label={period.range}
                  checked={periodFilters.includes(value)}
                />
              ))}
            </div>
          </fieldset>
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-gold-500/15 pt-4">
          <p className="text-xs text-stone-500">
            Wyszukiwanie obejmuje nazwy, streszczenia, patronaty oraz atrybuty ikonograficzne.
          </p>
          <div className="flex flex-wrap gap-2">
            <Link
              href="/swieci"
              className="rounded-xl border border-gold-500/30 px-5 py-2.5 text-sm font-semibold text-burgundy-800 transition-colors hover:bg-gold-50"
            >
              Wyczyść
            </Link>
            <button
              type="submit"
              className="rounded-xl bg-burgundy-900 px-6 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-burgundy-800"
            >
              Filtruj
            </button>
          </div>
        </div>
      </form>

      {activeFilters.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-gold-500/25 bg-gold-50/60 px-4 py-3">
          <div className="flex flex-wrap items-center gap-2 text-sm text-burgundy-900">
            <span className="font-semibold">Aktywne filtry:</span>
            {activeFilters.map((filter) => (
              <span
                key={`${filter.context}-${filter.label}`}
                title={filter.context}
                className="rounded-full border border-gold-500/30 bg-white px-3 py-1 text-xs font-semibold text-burgundy-800"
              >
                {filter.label}
              </span>
            ))}
          </div>
          <Link href="/swieci" className="text-xs font-semibold text-burgundy-700 hover:underline">
            Wyczyść filtry
          </Link>
        </div>
      )}

      {/* Results Counter */}
      <p className="text-xs font-medium text-gray-500">
        Znaleziono <strong className="text-burgundy-900">{total}</strong> postaci
      </p>

      {/* Directory Grid */}
      {persons.length === 0 ? (
        <div className="rounded-2xl border border-gold-500/20 bg-white p-12 text-center">
          <BookOpen className="mx-auto h-10 w-10 text-gold-600 mb-3" />
          <p className="text-base font-semibold text-burgundy-900">Brak wyników</p>
          <p className="mt-1 text-xs text-gray-500">Zmień kryteria wyszukiwania lub filtry.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {persons.map((p) => {
            const patronages = getPersonPatronages(p);
            const officialPatronages = patronages.filter((patronage) => patronage.is_official);
            const highlightedPatronages = officialPatronages.length
              ? officialPatronages.slice(0, 3)
              : patronages.slice(0, 3);
            const secondaryPatronages = officialPatronages.length
              ? patronages.filter((patronage) => !patronage.is_official)
              : patronages.slice(3);
            const attributes = splitAttributes(p.iconographic_attributes);

            return (
              <Link
                key={p.id as string}
                href={`/swieci/${p.slug as string}`}
                className="group flex flex-col justify-between rounded-2xl border border-gold-500/20 bg-white p-6 shadow-sm transition-all hover:border-gold-500/50 hover:shadow-md"
              >
                <div>
                  <div className="mb-5 flex items-start justify-between gap-4">
                    <SaintAvatar
                      name={p.canonical_name as string}
                      avatar={p.avatar as SaintAvatarData | null}
                      className="h-20 w-20 text-xl transition-transform duration-300 group-hover:scale-[1.03]"
                    />
                    <span className="inline-block rounded-full bg-gold-100 px-3 py-1 text-xs font-semibold text-gold-800">
                      {PERSON_TYPE_LABELS[p.person_type as string] ?? (p.person_type as string)}
                    </span>
                  </div>

                  <h2 className="font-serif text-xl font-bold text-burgundy-900 transition-colors group-hover:text-gold-700">
                    {p.canonical_name as string}
                  </h2>

                  {Boolean(p.latin_name) && (
                    <p className="mt-0.5 text-xs italic text-gray-500">
                      {String(p.latin_name)}
                    </p>
                  )}

                  <p className="mt-3 line-clamp-3 text-xs leading-relaxed text-gray-600">
                    {(p.summary_pl as string) || "Brak szczegółowego streszczenia w bazie."}
                  </p>

                  {highlightedPatronages.length > 0 && (
                    <div className="mt-4 space-y-2">
                      <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-stone-400">
                        {officialPatronages.length ? "Patronaty główne" : "Patronaty"}
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {highlightedPatronages.map((patronage) => (
                          <span
                            key={patronage.id ?? patronage.name_pl}
                            title={PATRONAGE_TYPE_LABELS[patronage.patronage_type ?? ""] ?? patronage.patronage_type}
                            className="rounded-full border border-gold-500/25 bg-gold-50 px-2.5 py-1 text-[11px] font-semibold text-gold-800"
                          >
                            {patronage.name_pl}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {secondaryPatronages.length > 0 && (
                    <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px] text-stone-500">
                      <span className="font-semibold text-stone-400">Rzadziej:</span>
                      {secondaryPatronages.slice(0, 2).map((patronage) => (
                        <span
                          key={patronage.id ?? patronage.name_pl}
                          title={PATRONAGE_TYPE_LABELS[patronage.patronage_type ?? ""] ?? patronage.patronage_type}
                          className="rounded-full border border-stone-200 bg-stone-50 px-2.5 py-1"
                        >
                          {patronage.name_pl}
                        </span>
                      ))}
                      {secondaryPatronages.length > 2 && (
                        <span
                          title={secondaryPatronages.map((patronage) => patronage.name_pl).join(", ")}
                          className="rounded-full border border-stone-200 bg-stone-50 px-2.5 py-1 font-semibold"
                        >
                          +{secondaryPatronages.length - 2}
                        </span>
                      )}
                    </div>
                  )}

                  {attributes.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {attributes.map((attribute) => (
                        <span
                          key={attribute}
                          className="rounded-full border border-burgundy-900/10 bg-burgundy-50 px-2.5 py-1 text-[11px] text-burgundy-800"
                        >
                          {attribute}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <div className="mt-4 flex items-center justify-between border-t border-gray-100 pt-3 text-xs">
                  <span className="font-medium text-gray-500">
                    {p.death_year ? `zm. ${p.death_year}` : "—"}
                  </span>
                  <span className="flex items-center gap-1 font-semibold text-gold-700 transition-transform group-hover:translate-x-1">
                    Życiorys <ChevronRight className="h-3.5 w-3.5" />
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-6">
          {Array.from({ length: totalPages }).map((_, i) => {
            const pageNum = i + 1;
            const active = pageNum === page;
            return (
              <Link
                key={pageNum}
                href={buildDirectoryHref({
                  search,
                  typeFilters,
                  genderFilters,
                  periodFilters,
                  eraFilters,
                  patronageFilters,
                  page: pageNum,
                })}
                className={`h-9 w-9 rounded-lg flex items-center justify-center text-sm font-semibold transition-all ${
                  active
                    ? "bg-burgundy-900 text-white shadow-md"
                    : "bg-white border border-gold-500/30 text-gray-700 hover:bg-gold-50"
                }`}
              >
                {pageNum}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
