export interface NavigationLink {
  href: string;
  label: string;
}

export interface FooterGroup {
  title: string;
  links: NavigationLink[];
}

export type GenderKey = "male" | "female" | "unknown";
export type PersonTypeKey =
  | "saint"
  | "blessed"
  | "venerable"
  | "servant_of_god"
  | "candidate";
export type EraKey =
  | "apostolic"
  | "early_church"
  | "late_antiquity"
  | "medieval"
  | "early_modern"
  | "modern"
  | "contemporary"
  | "unknown";
export type HistoricalPeriodKey = "early_witnesses" | "medieval" | "renewal" | "modern";
export type PatronageGroupKey = "health" | "family" | "work" | "travel";
export type PatronageTypeKey =
  | "illness"
  | "healthcare"
  | "family"
  | "profession"
  | "work"
  | "travel"
  | "country"
  | "city"
  | "diocese"
  | "group"
  | "cause"
  | "other";
export type ReligiousCommunityTypeKey =
  | "religious_order"
  | "congregation"
  | "monastic_family"
  | "society_apostolic_life"
  | "secular_institute"
  | "federation"
  | "other";
export type OrderCharismKey =
  | "contemplative"
  | "apostolic"
  | "mendicant"
  | "monastic"
  | "missionary"
  | "educational"
  | "charitable"
  | "military"
  | "other";
export type OrderMembershipTypeKey =
  | "founder"
  | "monk"
  | "friar"
  | "nun"
  | "sister"
  | "lay_member"
  | "spiritual_patron"
  | "member";

export interface WebDictionary {
  metadata: {
    defaultTitle: string;
    titleTemplate: string;
    description: string;
    keywords: string[];
    author: string;
    openGraphLocale: string;
    openGraphTitle: string;
    openGraphDescription: string;
  };
  brand: {
    name: string;
    product: string;
  };
  header: {
    homeAriaLabel: string;
    navigationAriaLabel: string;
    mobileNavigationAriaLabel: string;
    searchAriaLabel: string;
    searchPlaceholder: string;
    mobileSearchPlaceholder: string;
    searchButton: string;
    openMenuAriaLabel: string;
    closeMenuAriaLabel: string;
    navigation: NavigationLink[];
  };
  footer: {
    description: string;
    disclaimer: string;
    groups: FooterGroup[];
    rightsReserved: string;
  };
  domain: {
    personTypes: Record<PersonTypeKey, { label: string; description: string }>;
    eras: Record<EraKey, string>;
    historicalPeriods: Record<HistoricalPeriodKey, { range: string; title: string }>;
    patronageGroups: Record<PatronageGroupKey, { title: string; detail: string }>;
    religiousCommunities: {
      communityTypes: Record<ReligiousCommunityTypeKey, string>;
      charisms: Record<OrderCharismKey, string>;
      spiritualFamilies: Record<string, string>;
      membershipTypes: Record<OrderMembershipTypeKey, string>;
    };
  };
  saintsDirectory: {
    title: string;
    description: string;
    searchPlaceholder: string;
    personTypeLegend: string;
    genderLegend: string;
    patronageLegend: string;
    historicalPeriodLegend: string;
    genderContext: string;
    eraContext: string;
    searchScope: string;
    clear: string;
    submit: string;
    activeFilters: string;
    clearFilters: string;
    resultsPrefix: string;
    resultsSuffix: string;
    emptyTitle: string;
    emptyDescription: string;
    summaryFallback: string;
    primaryPatronages: string;
    patronages: string;
    secondaryPatronages: string;
    deathAbbreviation: string;
    biographyLink: string;
    genderLabels: Record<GenderKey, string>;
    patronageTypeLabels: Record<PatronageTypeKey, string>;
  };
  personProfile: {
    notFoundTitle: string;
    metadataTitleSuffix: string;
    metadataDescriptionPrefix: string;
    metadataBiographyPrefix: string;
    portraitPrefix: string;
    backToDirectory: string;
    eraPrefix: string;
    aliasesPrefix: string;
    birthYear: string;
    deathYear: string;
    gender: string;
    genderLabels: Record<GenderKey, string>;
    stateOfLife: string;
    summary: string;
    recognitionTitle: string;
    recognitionDescription: string;
    beatification: string;
    canonization: string;
    biographyTitle: string;
    biographyMissing: string;
    patronages: string;
    orders: string;
    prayer: string;
    prayerMissing: string;
    iconographicAttributes: string;
    iconographicAttributesMissing: string;
  };
}

export type WebHeaderDictionary = Pick<WebDictionary, "brand" | "header">;
export type WebFooterDictionary = Pick<WebDictionary, "brand" | "footer">;
