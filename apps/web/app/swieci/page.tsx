import Link from "next/link";
import { BookOpen, ChevronRight, Search } from "lucide-react";
import {
  fetchCountries,
  fetchOccupations,
  fetchOrders,
  fetchPersonFacets,
  fetchPersons,
} from "@/lib/api";
import { SaintAvatar, type SaintAvatarData } from "@/components/saint-avatar";
import { DEFAULT_WEB_UI_LOCALE } from "@/lib/i18n/config";
import { getWebDictionary } from "@/lib/i18n/dictionaries";
import { resolveDictionaryLabel, resolveDictionaryValue } from "@/lib/i18n/labels";
import { readPublicPersonContent } from "@/lib/person-content";
import { LEGACY_ERA_PERIODS, LEGACY_SEARCH_PATRONAGES } from "@/lib/person-filters";
import type { ReligiousOrder } from "@/lib/orders";

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
    order_id?: SearchParamValue;
    occupation_id?: SearchParamValue;
    birth_country_id?: SearchParamValue;
    death_country_id?: SearchParamValue;
    nationality_id?: SearchParamValue;
    page?: SearchParamValue;
  }>;
}

type FacetCount = { id: string; count: number };
type PersonFacets = {
  orders?: FacetCount[];
  occupations?: FacetCount[];
  birth_countries?: FacetCount[];
  death_countries?: FacetCount[];
  nationalities?: FacetCount[];
};
type OccupationRecord = { id: string; name_pl: string };
type CountryRecord = { id: string; name_pl: string };

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
  orderId,
  occupationId,
  birthCountryId,
  deathCountryId,
  nationalityId,
  page,
}: {
  search: string;
  typeFilters: string[];
  genderFilters: string[];
  periodFilters: string[];
  eraFilters: string[];
  patronageFilters: string[];
  orderId?: string;
  occupationId?: string;
  birthCountryId?: string;
  deathCountryId?: string;
  nationalityId?: string;
  page?: number;
}) {
  const query = new URLSearchParams();

  if (search) query.set("search", search);
  typeFilters.forEach((value) => query.append("type", value));
  genderFilters.forEach((value) => query.append("gender", value));
  periodFilters.forEach((value) => query.append("period", value));
  eraFilters.forEach((value) => query.append("era", value));
  patronageFilters.forEach((value) => query.append("patronage", value));
  if (orderId) query.set("order_id", orderId);
  if (occupationId) query.set("occupation_id", occupationId);
  if (birthCountryId) query.set("birth_country_id", birthCountryId);
  if (deathCountryId) query.set("death_country_id", deathCountryId);
  if (nationalityId) query.set("nationality_id", nationalityId);
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

function RelationalSelect({
  name,
  label,
  value,
  options,
  allLabel,
}: {
  name: string;
  label: string;
  value: string;
  options: Array<{ id: string; label: string; count: number }>;
  allLabel: string;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-xs font-semibold text-stone-600">
      <span>{label}</span>
      <select
        name={name}
        defaultValue={value}
        className="rounded-xl border border-gold-500/30 bg-gray-50/50 px-3 py-2.5 text-sm font-normal text-gray-900 focus:border-gold-500 focus:outline-none focus:ring-2 focus:ring-gold-400/20"
      >
        <option value="">{allLabel}</option>
        {options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label} ({option.count})
          </option>
        ))}
      </select>
    </label>
  );
}

export default async function SaintsDirectoryPage({ searchParams }: PageProps) {
  const dictionary = await getWebDictionary(DEFAULT_WEB_UI_LOCALE);
  const copy = dictionary.saintsDirectory;
  const domain = dictionary.domain;
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
    domain.patronageGroups,
  );
  const search = legacyPatronage.length ? "" : rawSearch;
  const typeFilters = validParamValues(params.type, domain.personTypes);
  const genderFilters = validParamValues(params.gender, copy.genderLabels);
  const periodFilters = validParamValues(
    [params.period, legacyPeriods],
    domain.historicalPeriods,
  );
  const eraFilters = periodFilters.length
    ? []
    : validParamValues(params.era, domain.eras);
  const orderId = firstParamValue(params.order_id);
  const occupationId = firstParamValue(params.occupation_id);
  const birthCountryId = firstParamValue(params.birth_country_id);
  const deathCountryId = firstParamValue(params.death_country_id);
  const nationalityId = firstParamValue(params.nationality_id);
  const page = Number(firstParamValue(params.page) || "1");

  const discoveryParams = {
    ...(search && { search }),
    ...(typeFilters.length && { person_type: typeFilters }),
    ...(genderFilters.length && { gender: genderFilters }),
    ...(periodFilters.length && { period: periodFilters }),
    ...(patronageFilters.length && { patronage: patronageFilters }),
    ...(eraFilters.length && { era: eraFilters }),
    ...(orderId && { order_id: orderId }),
    ...(occupationId && { occupation_id: occupationId }),
    ...(birthCountryId && { birth_country_id: birthCountryId }),
    ...(deathCountryId && { death_country_id: deathCountryId }),
    ...(nationalityId && { nationality_id: nationalityId }),
  };
  const [res, facetResponse, orderResponse, occupationResponse, countryResponse] =
    await Promise.all([
      fetchPersons({ page, per_page: 18, ...discoveryParams }),
      fetchPersonFacets(discoveryParams),
      fetchOrders(),
      fetchOccupations(),
      fetchCountries(),
    ]);
  const orders = (Array.isArray(orderResponse) ? orderResponse : []) as ReligiousOrder[];
  const occupations = (Array.isArray(occupationResponse) ? occupationResponse : []) as OccupationRecord[];
  const countries = (Array.isArray(countryResponse) ? countryResponse : []) as CountryRecord[];
  const facets = (facetResponse ?? {}) as PersonFacets;
  const findLabel = (
    items: Array<{ id: string; name_pl?: string; name?: string }>,
    id: string,
    fallback: string,
  ) => {
    const item = items.find((candidate) => candidate.id === id);
    return item?.name_pl ?? item?.name ?? fallback;
  };
  const findCount = (items: FacetCount[] | undefined, id: string) =>
    items?.find((item) => item.id === id)?.count ?? 0;
  const activeFilters = [
    ...typeFilters.map((value) => ({
      label: resolveDictionaryValue(domain.personTypes, value)?.label ?? value,
      context: resolveDictionaryValue(domain.personTypes, value)?.description ?? value,
    })),
    ...genderFilters.map((value) => ({
      label: resolveDictionaryLabel(copy.genderLabels, value) ?? value,
      context: copy.genderContext,
    })),
    ...periodFilters.map((value) => ({
      label: resolveDictionaryValue(domain.historicalPeriods, value)?.range ?? value,
      context: resolveDictionaryValue(domain.historicalPeriods, value)?.title ?? value,
    })),
    ...eraFilters.map((value) => ({
      label: resolveDictionaryLabel(domain.eras, value) ?? value,
      context: copy.eraContext,
    })),
    ...patronageFilters.map((value) => ({
      label: resolveDictionaryValue(domain.patronageGroups, value)?.title ?? value,
      context: resolveDictionaryValue(domain.patronageGroups, value)?.detail ?? value,
    })),
    ...(orderId
      ? [{ label: findLabel(orders, orderId, copy.orderFilter), context: copy.orderFilter }]
      : []),
    ...(occupationId
      ? [{
          label: findLabel(occupations, occupationId, copy.occupationFilter),
          context: copy.occupationFilter,
        }]
      : []),
    ...(birthCountryId
      ? [{
          label: findLabel(countries, birthCountryId, copy.birthCountryFilter),
          context: copy.birthCountryFilter,
        }]
      : []),
    ...(deathCountryId
      ? [{
          label: findLabel(countries, deathCountryId, copy.deathCountryFilter),
          context: copy.deathCountryFilter,
        }]
      : []),
    ...(nationalityId
      ? [{
          label: findLabel(countries, nationalityId, copy.nationalityFilter),
          context: copy.nationalityFilter,
        }]
      : []),
  ];
  const persons: Array<Record<string, unknown>> = res?.items ?? [];
  const total = res?.total ?? 0;
  const totalPages = res?.pages ?? 1;
  const orderOptions = orders.map((order) => ({
    id: order.id,
    label: order.name,
    count: findCount(facets.orders, order.id),
  }));
  const occupationOptions = occupations.map((occupation) => ({
    id: occupation.id,
    label: occupation.name_pl,
    count: findCount(facets.occupations, occupation.id),
  }));
  const countryOptions = countries.map((country) => ({
    id: country.id,
    label: country.name_pl,
    count: findCount(facets.birth_countries, country.id),
  }));
  const deathCountryOptions = countries.map((country) => ({
    id: country.id,
    label: country.name_pl,
    count: findCount(facets.death_countries, country.id),
  }));
  const nationalityOptions = countries.map((country) => ({
    id: country.id,
    label: country.name_pl,
    count: findCount(facets.nationalities, country.id),
  }));

  return (
    <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8 space-y-8">
      {/* Page Title */}
      <div>
        <h1 className="font-serif text-3xl sm:text-4xl font-bold text-burgundy-900">
          {copy.title}
        </h1>
        <p className="mt-1 text-sm text-gray-600">
          {copy.description}
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
            placeholder={copy.searchPlaceholder}
            className="w-full rounded-xl border border-gold-500/30 bg-gray-50/50 py-2.5 pl-10 pr-4 text-sm text-gray-900 focus:border-gold-500 focus:outline-none focus:ring-2 focus:ring-gold-400/20"
          />
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <fieldset>
            <legend className="text-[11px] font-bold uppercase tracking-[0.16em] text-stone-500">
              {copy.personTypeLegend}
            </legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {Object.entries(domain.personTypes).map(([value, personType]) => (
                <FilterOption
                  key={value}
                  name="type"
                  value={value}
                  label={personType.label}
                  checked={typeFilters.includes(value)}
                />
              ))}
            </div>
          </fieldset>

          <fieldset>
            <legend className="text-[11px] font-bold uppercase tracking-[0.16em] text-stone-500">
              {copy.genderLegend}
            </legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {Object.entries(copy.genderLabels).map(([value, label]) => (
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
              {copy.patronageLegend}
            </legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {Object.entries(domain.patronageGroups).map(([value, group]) => (
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
              {copy.historicalPeriodLegend}
            </legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {Object.entries(domain.historicalPeriods).map(([value, period]) => (
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

        <div className="mt-5 border-t border-gold-500/15 pt-4">
          <h2 className="text-[11px] font-bold uppercase tracking-[0.16em] text-stone-500">
            {copy.relationalFilters}
          </h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <RelationalSelect
              name="order_id"
              label={copy.orderFilter}
              value={orderId}
              options={orderOptions}
              allLabel={copy.allValues}
            />
            <RelationalSelect
              name="occupation_id"
              label={copy.occupationFilter}
              value={occupationId}
              options={occupationOptions}
              allLabel={copy.allValues}
            />
            <RelationalSelect
              name="birth_country_id"
              label={copy.birthCountryFilter}
              value={birthCountryId}
              options={countryOptions}
              allLabel={copy.allValues}
            />
            <RelationalSelect
              name="death_country_id"
              label={copy.deathCountryFilter}
              value={deathCountryId}
              options={deathCountryOptions}
              allLabel={copy.allValues}
            />
            <RelationalSelect
              name="nationality_id"
              label={copy.nationalityFilter}
              value={nationalityId}
              options={nationalityOptions}
              allLabel={copy.allValues}
            />
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-gold-500/15 pt-4">
          <p className="text-xs text-stone-500">
            {copy.searchScope}
          </p>
          <div className="flex flex-wrap gap-2">
            <Link
              href="/swieci"
              className="rounded-xl border border-gold-500/30 px-5 py-2.5 text-sm font-semibold text-burgundy-800 transition-colors hover:bg-gold-50"
            >
              {copy.clear}
            </Link>
            <button
              type="submit"
              className="rounded-xl bg-burgundy-900 px-6 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-burgundy-800"
            >
              {copy.submit}
            </button>
          </div>
        </div>
      </form>

      {activeFilters.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-gold-500/25 bg-gold-50/60 px-4 py-3">
          <div className="flex flex-wrap items-center gap-2 text-sm text-burgundy-900">
            <span className="font-semibold">{copy.activeFilters}</span>
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
            {copy.clearFilters}
          </Link>
        </div>
      )}

      {/* Results Counter */}
      <p className="text-xs font-medium text-gray-500">
        {copy.resultsPrefix} <strong className="text-burgundy-900">{total}</strong>{" "}
        {copy.resultsSuffix}
      </p>

      {/* Directory Grid */}
      {persons.length === 0 ? (
        <div className="rounded-2xl border border-gold-500/20 bg-white p-12 text-center">
          <BookOpen className="mx-auto h-10 w-10 text-gold-600 mb-3" />
          <p className="text-base font-semibold text-burgundy-900">{copy.emptyTitle}</p>
          <p className="mt-1 text-xs text-gray-500">{copy.emptyDescription}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {persons.map((p) => {
            const content = readPublicPersonContent(p);
            const patronages = getPersonPatronages(p);
            const officialPatronages = patronages.filter((patronage) => patronage.is_official);
            const highlightedPatronages = officialPatronages.length
              ? officialPatronages.slice(0, 3)
              : patronages.slice(0, 3);
            const secondaryPatronages = officialPatronages.length
              ? patronages.filter((patronage) => !patronage.is_official)
              : patronages.slice(3);
            const attributes = splitAttributes(content.iconographicAttributes);

            return (
              <Link
                key={p.id as string}
                href={`/swieci/${p.slug as string}`}
                className="group flex flex-col justify-between rounded-2xl border border-gold-500/20 bg-white p-6 shadow-sm transition-all hover:border-gold-500/50 hover:shadow-md"
              >
                <div>
                  <div className="mb-5 flex items-start justify-between gap-4">
                    <SaintAvatar
                      name={content.canonicalName}
                      avatar={p.avatar as SaintAvatarData | null}
                      className="h-20 w-20 text-xl transition-transform duration-300 group-hover:scale-[1.03]"
                    />
                    <span className="inline-block rounded-full bg-gold-100 px-3 py-1 text-xs font-semibold text-gold-800">
                      {resolveDictionaryValue(domain.personTypes, p.person_type)?.label ??
                        String(p.person_type)}
                    </span>
                  </div>

                  <h2 className="font-serif text-xl font-bold text-burgundy-900 transition-colors group-hover:text-gold-700">
                    {content.canonicalName}
                  </h2>

                  {search && typeof p.search_reason === "string" && copy.searchReasonLabels[p.search_reason] && (
                    <p className="mt-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-gold-700">
                      {copy.searchReasonLabels[p.search_reason]}
                    </p>
                  )}

                  {Boolean(p.latin_name) && (
                    <p className="mt-0.5 text-xs italic text-gray-500">
                      {String(p.latin_name)}
                    </p>
                  )}

                  <p className="mt-3 line-clamp-3 text-xs leading-relaxed text-gray-600">
                    {content.summary || copy.summaryFallback}
                  </p>

                  {highlightedPatronages.length > 0 && (
                    <div className="mt-4 space-y-2">
                      <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-stone-400">
                        {officialPatronages.length
                          ? copy.primaryPatronages
                          : copy.patronages}
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {highlightedPatronages.map((patronage) => (
                          <span
                            key={patronage.id ?? patronage.name_pl}
                            title={
                              resolveDictionaryLabel(
                                copy.patronageTypeLabels,
                                patronage.patronage_type,
                              ) ??
                              patronage.patronage_type
                            }
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
                      <span className="font-semibold text-stone-400">
                        {copy.secondaryPatronages}
                      </span>
                      {secondaryPatronages.slice(0, 2).map((patronage) => (
                        <span
                          key={patronage.id ?? patronage.name_pl}
                          title={
                            resolveDictionaryLabel(
                              copy.patronageTypeLabels,
                              patronage.patronage_type,
                            ) ??
                            patronage.patronage_type
                          }
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
                    {p.death_year ? `${copy.deathAbbreviation} ${p.death_year}` : "—"}
                  </span>
                  <span className="flex items-center gap-1 font-semibold text-gold-700 transition-transform group-hover:translate-x-1">
                    {copy.biographyLink} <ChevronRight className="h-3.5 w-3.5" />
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
                  orderId,
                  occupationId,
                  birthCountryId,
                  deathCountryId,
                  nationalityId,
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
