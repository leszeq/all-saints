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
export type FeastRankKey =
  | "solemnity"
  | "feast"
  | "memorial"
  | "opt_memorial"
  | "commemoration";
export type ObservanceTypeKey = "lord" | "marian" | "church" | "mystery" | "other";

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
  system: {
    notFound: {
      kicker: string;
      title: string;
      description: string;
      catalogueAction: string;
      homeAction: string;
    };
    error: {
      kicker: string;
      title: string;
      description: string;
      digestPrefix: string;
      retryAction: string;
      homeAction: string;
    };
    loading: {
      labels: {
        default: string;
        saintsDirectory: string;
        calendar: string;
        ordersDirectory: string;
      };
      screenReaderLabel: string;
    };
    avatar: {
      fallbackLabelPrefix: string;
      portraitLabelPrefix: string;
      honorificPrefixes: string[];
    };
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
      memberCount: {
        one: string;
        few: string;
        many: string;
      };
    };
  };
  home: {
    heroKicker: string;
    heroTitlePrefix: string;
    heroTitleAccent: string;
    heroDescription: string;
    searchAriaLabel: string;
    searchPlaceholder: string;
    searchButton: string;
    searchHint: string;
    projectAriaLabel: string;
    projectTitle: string;
    projectDescription: string;
    peopleStat: string;
    sourcesStat: string;
    featuredCommemoration: string;
    defaultCalendarName: string;
    pendingDayTitle: string;
    pendingEntrySummary: string;
    missingTodaySummary: string;
    viewWholeDay: string;
    discoverKicker: string;
    discoverTitle: string;
    viewCatalogue: string;
    browse: string;
    calendarKicker: string;
    todayTitle: string;
    openCalendarAriaLabel: string;
    emptyCalendar: string;
    fullDayList: string;
    timelineKicker: string;
    timelineTitle: string;
    ordersKicker: string;
    ordersTitle: string;
    ordersDescription: string;
    ordersCatalogue: string;
    ordersEmpty: string;
    editorialKicker: string;
    recentTitle: string;
    allProfiles: string;
    verified: string;
    datesPending: string;
    profilePending: string;
    recentEmpty: string;
    methodologyKicker: string;
    methodologyDescription: string;
    methodologyAction: string;
  };
  calendar: {
    unknownObservance: string;
    feastRanks: Record<FeastRankKey, string>;
    feastRankShortLabels: Record<FeastRankKey, string>;
    observanceTypes: Record<ObservanceTypeKey, string>;
    entryCount: {
      one: string;
      few: string;
      many: string;
    };
    month: {
      metadataTitle: string;
      metadataDescription: string;
      ritePrefix: string;
      title: string;
      withUniversalDescription: string;
      selectedOnlyDescription: string;
      withMartyrologyDescription: string;
      multipleEntriesDescription: string;
      populatedDays: string;
      commemorations: string;
      baseCalendar: string;
      polishCalendar: string;
      universalCalendar: string;
      apply: string;
      previousMonthAriaLabel: string;
      nextMonthAriaLabel: string;
      weekdays: string[];
      emptyDay: string;
      fullYearTitle: string;
      fullYearDescription: string;
      layersTitle: string;
      layersDescription: string;
      sourceTitle: string;
      sourceDescription: string;
    };
    day: {
      invalidDateTitle: string;
      metadataTitlePrefix: string;
      metadataTitleSuffix: string;
      metadataDescriptionPrefix: string;
      metadataDescriptionSuffix: string;
      backToMonth: string;
      calendarKicker: string;
      todayTitle: string;
      dayTitle: string;
      previousDayAriaLabel: string;
      nextDayAriaLabel: string;
      primary: string;
      pendingDescription: string;
      fullProfile: string;
      discoverObservance: string;
      fullListKicker: string;
      remainingTitle: string;
      pendingListDescription: string;
      profile: string;
      observance: string;
      onlyEntry: string;
      scopeTitle: string;
      universalSuffix: string;
      martyrologySuffix: string;
      sourceTitle: string;
      sourceFallback: string;
      emptyTitle: string;
      emptyDescription: string;
      wholeMonth: string;
    };
    observance: {
      metadataFallbackTitle: string;
      metadataTitleSuffix: string;
      metadataDescriptionPrefix: string;
      backToCalendar: string;
      separateProfileNotice: string;
      summaryFallback: string;
      historyKicker: string;
      iconographicAttributes: string;
      pending: string;
      viewCalendar: string;
    };
  };
  ordersDirectory: {
    metadataTitle: string;
    metadataDescription: string;
    familyPrefix: string;
    communityFallback: string;
    descriptionFallback: string;
    cardAction: string;
    heroKicker: string;
    title: string;
    description: string;
    communitiesStat: string;
    spiritualFamiliesStat: string;
    linkedPeopleStat: string;
    searchAriaLabel: string;
    searchPlaceholder: string;
    familyAriaLabel: string;
    allFamilies: string;
    charismAriaLabel: string;
    allCharisms: string;
    typeAriaLabel: string;
    allTypes: string;
    filter: string;
    resultsPrefix: string;
    clearFilters: string;
    featuredKicker: string;
    featuredTitle: string;
    filteredKicker: string;
    catalogueKicker: string;
    filteredTitle: string;
    catalogueTitle: string;
    catalogueDescription: string;
    emptyTitle: string;
    emptyDescription: string;
    familyFeatureTitle: string;
    familyFeatureDescription: string;
    membershipFeatureTitle: string;
    membershipFeatureDescription: string;
    sourceFeatureTitle: string;
    sourceFeatureDescription: string;
  };
  orderProfile: {
    notFoundTitle: string;
    metadataTitleSuffix: string;
    metadataDescriptionPrefix: string;
    backToDirectory: string;
    familyPrefix: string;
    descriptionFallback: string;
    origins: string;
    originsFallback: string;
    founder: string;
    founderFallback: string;
    linkedPeople: string;
    legacyKicker: string;
    history: string;
    historyFallback: string;
    mission: string;
    missionFallback: string;
    motto: string;
    foundedYear: string;
    papalApproval: string;
    abbreviation: string;
    sources: string;
    historySource: string;
    officialWebsite: string;
    membersKicker: string;
    membersTitle: string;
    memberProfileFallback: string;
    fullProfile: string;
    membersEmpty: string;
    relatedKicker: string;
    relatedTitle: string;
    viewProfile: string;
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
    relationalFilters: string;
    orderFilter: string;
    occupationFilter: string;
    birthCountryFilter: string;
    deathCountryFilter: string;
    nationalityFilter: string;
    allValues: string;
    facetCount: string;
    searchReasonLabels: Record<string, string>;
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
    sources: {
      title: string;
      description: string;
      empty: string;
      primary: string;
      editor: string;
      edition: string;
      volume: string;
      pages: string;
      reference: string;
      accessed: string;
      repository: string;
      callNumber: string;
      dateRange: string;
      open: string;
      digitization: string;
      openDoi: string;
      newTab: string;
      offline: string;
    };
  };
}

export type WebHeaderDictionary = Pick<WebDictionary, "brand" | "header">;
export type WebFooterDictionary = Pick<WebDictionary, "brand" | "footer">;
