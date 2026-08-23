import Link from "next/link";
import { BookOpen, ChevronRight, Search } from "lucide-react";
import { fetchPersons } from "@/lib/api";
import {
  LEGACY_ERA_PERIODS,
  LEGACY_SEARCH_PATRONAGES,
  PATRONAGE_GROUPS,
  PERSON_TYPE_LABELS,
  TIME_PERIODS,
} from "@/lib/utils";
import { SaintAvatar, type SaintAvatarData } from "@/components/saint-avatar";

export const revalidate = 30;

interface PageProps {
  searchParams: Promise<{
    search?: string;
    type?: string;
    era?: string;
    period?: string;
    patronage?: string;
    gender?: string;
    page?: string;
  }>;
}

export default async function SaintsDirectoryPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const requestedPatronage = params.patronage || LEGACY_SEARCH_PATRONAGES[params.search || ""] || "";
  const patronageFilter = requestedPatronage in PATRONAGE_GROUPS ? requestedPatronage : "";
  const search = patronageFilter ? "" : params.search || "";
  const typeFilter = params.type || "";
  const requestedPeriod = params.period || LEGACY_ERA_PERIODS[params.era || ""] || "";
  const periodFilter = requestedPeriod in TIME_PERIODS ? requestedPeriod : "";
  const eraFilter = periodFilter ? "" : params.era || "";
  const activePeriod = periodFilter
    ? TIME_PERIODS[periodFilter as keyof typeof TIME_PERIODS]
    : null;
  const activePatronage = patronageFilter
    ? PATRONAGE_GROUPS[patronageFilter as keyof typeof PATRONAGE_GROUPS]
    : null;
  const page = Number(params.page || "1");

  let persons: Array<Record<string, unknown>> = [];
  let total = 0;
  let totalPages = 1;

  try {
    const res = await fetchPersons({
      page,
      per_page: 18,
      ...(search && { search }),
      ...(typeFilter && { person_type: typeFilter }),
      ...(periodFilter && { period: periodFilter }),
      ...(patronageFilter && { patronage: patronageFilter }),
      ...(eraFilter && { era: eraFilter }),
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
      <form method="GET" className="rounded-2xl border border-gold-500/20 bg-white p-4 shadow-sm space-y-4 md:space-y-0 md:flex md:items-center md:gap-4">
        {/* Search Input */}
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gold-600" />
          <input
            type="text"
            name="search"
            defaultValue={search}
            placeholder="Szukaj po imieniu, nazwisku lub atrybucie..."
            className="w-full rounded-xl border border-gold-500/30 bg-gray-50/50 py-2.5 pl-10 pr-4 text-sm text-gray-900 focus:border-gold-500 focus:outline-none focus:ring-2 focus:ring-gold-400/20"
          />
        </div>

        {/* Type Select */}
        <select
          name="type"
          defaultValue={typeFilter}
          className="w-full md:w-48 rounded-xl border border-gold-500/30 bg-gray-50/50 px-3 py-2.5 text-sm text-gray-900 focus:border-gold-500 focus:outline-none"
        >
          <option value="">Wszystkie typy</option>
          <option value="saint">Święci</option>
          <option value="blessed">Błogosławieni</option>
          <option value="venerable">Czcigodni Boży</option>
          <option value="servant_of_god">Słudzy Boży</option>
          <option value="candidate">Kandydaci</option>
        </select>

        <select
          name="patronage"
          defaultValue={patronageFilter}
          className="w-full rounded-xl border border-gold-500/30 bg-gray-50/50 px-3 py-2.5 text-sm text-gray-900 focus:border-gold-500 focus:outline-none md:w-48"
        >
          <option value="">Wszystkie patronaty</option>
          {Object.entries(PATRONAGE_GROUPS).map(([value, group]) => (
            <option key={value} value={value}>{group.title}</option>
          ))}
        </select>

        {/* Timeline Period Select */}
        <select
          name="period"
          defaultValue={periodFilter}
          className="w-full md:w-48 rounded-xl border border-gold-500/30 bg-gray-50/50 px-3 py-2.5 text-sm text-gray-900 focus:border-gold-500 focus:outline-none"
        >
          <option value="">Wszystkie okresy</option>
          {Object.entries(TIME_PERIODS).map(([value, period]) => (
            <option key={value} value={value}>{period.range}</option>
          ))}
        </select>

        <button
          type="submit"
          className="w-full md:w-auto rounded-xl bg-burgundy-900 px-6 py-2.5 text-sm font-semibold text-white hover:bg-burgundy-800 transition-colors"
        >
          Filtruj
        </button>
      </form>

      {activePeriod && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-gold-500/25 bg-gold-50/60 px-4 py-3">
          <p className="text-sm text-burgundy-900">
            <span className="font-semibold">{activePeriod.range}</span>
            <span className="mx-2 text-gold-500">·</span>
            {activePeriod.title}
          </p>
          <Link href="/swieci" className="text-xs font-semibold text-burgundy-700 hover:underline">
            Wyczyść okres
          </Link>
        </div>
      )}

      {activePatronage && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-burgundy-500/15 bg-burgundy-50/70 px-4 py-3">
          <p className="text-sm text-burgundy-900">
            <span className="font-semibold">{activePatronage.title}</span>
            <span className="mx-2 text-gold-500">·</span>
            {activePatronage.detail}
          </p>
          <Link href="/swieci" className="text-xs font-semibold text-burgundy-700 hover:underline">
            Wyczyść patronat
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
          {persons.map((p) => (
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

                <h2 className="font-serif text-xl font-bold text-burgundy-900 group-hover:text-gold-700 transition-colors">
                  {p.canonical_name as string}
                </h2>

                {Boolean(p.latin_name) && (
                  <p className="text-xs text-gray-400 italic mt-0.5">
                    {String(p.latin_name)}
                  </p>
                )}

                <p className="mt-3 text-xs text-gray-600 line-clamp-3 leading-relaxed">
                  {(p.summary_pl as string) || "Brak szczegółowego streszczenia w bazie."}
                </p>
              </div>

              <div className="mt-4 flex items-center justify-between border-t border-gray-100 pt-3 text-xs">
                <span className="text-gray-500 font-medium">
                  {p.birth_year ? `zm. ${p.death_year ?? "—"}` : "—"}
                </span>
                <span className="font-semibold text-gold-700 flex items-center gap-1 group-hover:translate-x-1 transition-transform">
                  Życiorys <ChevronRight className="h-3.5 w-3.5" />
                </span>
              </div>
            </Link>
          ))}
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
                href={`/swieci?page=${pageNum}${search ? `&search=${encodeURIComponent(search)}` : ""}${typeFilter ? `&type=${typeFilter}` : ""}${periodFilter ? `&period=${periodFilter}` : ""}${patronageFilter ? `&patronage=${patronageFilter}` : ""}${eraFilter ? `&era=${eraFilter}` : ""}`}
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
