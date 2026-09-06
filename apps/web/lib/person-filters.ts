import type { HistoricalPeriodKey, PatronageGroupKey } from "@/lib/i18n/types";

/** Compatibility aliases for links emitted before structured filter keys existed. */
export const LEGACY_ERA_PERIODS: Record<string, HistoricalPeriodKey> = {
  "Starożytność": "early_witnesses",
  "Średniowiecze": "medieval",
  "Nowożytność": "renewal",
  "Współczesność": "modern",
};

export const LEGACY_SEARCH_PATRONAGES: Record<string, PatronageGroupKey> = {
  chorzy: "health",
  rodzina: "family",
  praca: "work",
  "podróżni": "travel",
};
