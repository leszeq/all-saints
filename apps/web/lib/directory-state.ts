export type SaintsDirectoryState = {
  search?: string;
  typeFilters?: readonly string[];
  genderFilters?: readonly string[];
  periodFilters?: readonly string[];
  eraFilters?: readonly string[];
  patronageFilters?: readonly string[];
  orderId?: string;
  occupationId?: string;
  birthCountryId?: string;
  deathCountryId?: string;
  nationalityId?: string;
  page?: number;
};

/**
 * Keep catalogue state shareable and reversible by making the URL the single
 * source of truth for filters and pagination.
 */
export function buildSaintsDirectoryHref(state: SaintsDirectoryState): string {
  const query = new URLSearchParams();

  if (state.search) query.set("search", state.search);
  state.typeFilters?.forEach((value) => query.append("type", value));
  state.genderFilters?.forEach((value) => query.append("gender", value));
  state.periodFilters?.forEach((value) => query.append("period", value));
  state.eraFilters?.forEach((value) => query.append("era", value));
  state.patronageFilters?.forEach((value) => query.append("patronage", value));
  if (state.orderId) query.set("order_id", state.orderId);
  if (state.occupationId) query.set("occupation_id", state.occupationId);
  if (state.birthCountryId) query.set("birth_country_id", state.birthCountryId);
  if (state.deathCountryId) query.set("death_country_id", state.deathCountryId);
  if (state.nationalityId) query.set("nationality_id", state.nationalityId);
  if (state.page && state.page > 1) query.set("page", String(state.page));

  const serialized = query.toString();
  return serialized ? `/swieci?${serialized}` : "/swieci";
}
