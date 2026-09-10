export type AdminSystemRoleKey =
  | "super_admin"
  | "admin"
  | "editor"
  | "reviewer"
  | "translator"
  | "reader"
  | "guest";

export type AdminPublicationStatusKey = "draft" | "review" | "published" | "archived";
export type AdminGenderKey = "male" | "female" | "unknown";
export type AdminFeastRankKey =
  | "solemnity"
  | "feast"
  | "memorial"
  | "opt_memorial"
  | "commemoration";
export type AdminLiturgicalColorKey =
  | "white"
  | "red"
  | "green"
  | "violet"
  | "rose"
  | "black"
  | "gold";
export type AdminPatronageTypeKey =
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
export type AdminPersonAliasKindKey =
  | "birth_name"
  | "religious_name"
  | "alias"
  | "abbreviation"
  | "transliteration";
export type AdminAvatarLicenseKey =
  | "public_domain"
  | "cc_by"
  | "cc_by_sa"
  | "cc_by_nc"
  | "cc_by_nc_sa"
  | "all_rights_reserved"
  | "fair_use"
  | "unknown";
export type AdminOrderMembershipTypeKey =
  | "founder"
  | "monk"
  | "friar"
  | "nun"
  | "sister"
  | "lay_member"
  | "spiritual_patron"
  | "member";
export type AdminCommunityTypeKey =
  | "religious_order"
  | "congregation"
  | "monastic_family"
  | "society_apostolic_life"
  | "secular_institute"
  | "federation"
  | "other";
export type AdminOrderCharismKey =
  | "contemplative"
  | "apostolic"
  | "mendicant"
  | "monastic"
  | "missionary"
  | "educational"
  | "charitable"
  | "military"
  | "other";
export type AdminChurchTypeKey =
  | "parish"
  | "cathedral"
  | "basilica"
  | "chapel"
  | "monastery"
  | "sanctuary"
  | "shrine"
  | "pilgrimage_site"
  | "other";
export type AdminSourceTypeKey =
  | "book"
  | "article"
  | "encyclopedia"
  | "website"
  | "manuscript"
  | "archive"
  | "document"
  | "hagiography"
  | "vita"
  | "other";
export type AdminDocumentTypeKey =
  | "decree"
  | "bull"
  | "encyclical"
  | "biography"
  | "letter"
  | "vita"
  | "process"
  | "other";
export type AdminEraKey =
  | "apostolic"
  | "early_church"
  | "late_antiquity"
  | "medieval"
  | "early_modern"
  | "modern"
  | "contemporary"
  | "unknown";
export type AdminCompletionKey = "complete" | "partial" | "low" | "critical";
export type AdminPersonTypeKey =
  | "saint"
  | "blessed"
  | "venerable"
  | "servant_of_god"
  | "candidate";
export type AdminEditorialPriorityKey = "urgent" | "high" | "normal";
export type AdminCompletenessCriterionKey =
  | "basic_data"
  | "summary"
  | "biography"
  | "life_dates"
  | "state_of_life"
  | "sources"
  | "image"
  | "image_license";
export type AdminSeverityKey = "critical" | "warning";
export type AdminSourceVerificationTypeKey =
  | "bibliography"
  | "historical_source"
  | "image"
  | "person_source";
export type AdminSourceVerificationIssueKey =
  | "missing_reliability_score"
  | "missing_website_url"
  | "missing_website_access_date"
  | "missing_digitization_url"
  | "unknown_image_license"
  | "missing_image_source_url"
  | "orphan_person_source";
export type AdminDuplicateReasonKey =
  | "same_normalized_name_and_life_years"
  | "same_normalized_name_different_life_years";
export type AdminEditorialIssueKey =
  | "missing_biography"
  | "missing_summary"
  | "missing_sources"
  | "missing_image"
  | "unknown_image_license"
  | "missing_dates"
  | "missing_state_of_life";
export type AdminAiSuggestionKindKey = "embedding" | "summary" | "tags";
export type AdminAiSuggestionStatusKey =
  | "pending_review"
  | "ready_to_generate"
  | "blocked";
export type AdminAiFeatureStatusKey = "ready" | "disabled" | "needs_data" | "fallback";
export type AdminAiFeatureKey = "embeddings" | "semantic_search" | "summaries" | "tagging";
export type AdminApplicationFeatureKey = "ai_search" | "maps" | "timeline" | "exports";
export type AdminEnvironmentKey = "development" | "staging" | "production" | "testing";
export type AdminUserStatusKey = "active" | "inactive" | "banned" | "pending_verification";
export type AdminPermissionGroupKey =
  | "persons"
  | "editorial_workflow"
  | "sources_media"
  | "geography"
  | "orders"
  | "calendar"
  | "translations"
  | "import_export"
  | "administration";
export type AdminPermissionKey =
  | "persons:read"
  | "persons:create"
  | "persons:update"
  | "persons:delete"
  | "persons:submit"
  | "persons:review"
  | "persons:publish"
  | "persons:restore"
  | "sources:read"
  | "sources:create"
  | "sources:update"
  | "sources:delete"
  | "geography:read"
  | "geography:create"
  | "geography:update"
  | "geography:delete"
  | "orders:read"
  | "orders:create"
  | "orders:update"
  | "orders:delete"
  | "images:read"
  | "images:create"
  | "images:update"
  | "images:delete"
  | "calendar:read"
  | "calendar:create"
  | "calendar:update"
  | "calendar:delete"
  | "translations:read"
  | "translations:create"
  | "translations:update"
  | "translations:delete"
  | "export:read"
  | "export:create"
  | "import:create"
  | "audit:read"
  | "users:read"
  | "users:create"
  | "users:update"
  | "users:delete"
  | "roles:read"
  | "roles:create"
  | "roles:update"
  | "roles:delete";

export interface AdminDictionary {
  metadata: {
    defaultTitle: string;
    titleTemplate: string;
    description: string;
  };
  brand: {
    name: string;
    product: string;
  };
  domain: {
    personStatusLabels: Record<AdminPublicationStatusKey, string>;
    personTypeLabels: Record<AdminPersonTypeKey, string>;
    eraLabels: Record<AdminEraKey, string>;
    genderLabels: Record<AdminGenderKey, string>;
    feastRankLabels: Record<AdminFeastRankKey, string>;
    liturgicalColorLabels: Record<AdminLiturgicalColorKey, string>;
    patronageTypeLabels: Record<AdminPatronageTypeKey, string>;
    personAliasKindLabels: Record<AdminPersonAliasKindKey, string>;
    avatarLicenseLabels: Record<AdminAvatarLicenseKey, string>;
    orderMembershipTypeLabels: Record<AdminOrderMembershipTypeKey, string>;
    communityTypeLabels: Record<AdminCommunityTypeKey, string>;
    orderCharismLabels: Record<AdminOrderCharismKey, string>;
    churchTypeLabels: Record<AdminChurchTypeKey, string>;
    sourceTypeLabels: Record<AdminSourceTypeKey, string>;
    documentTypeLabels: Record<AdminDocumentTypeKey, string>;
    editorialPriorityLabels: Record<AdminEditorialPriorityKey, string>;
    completionLabels: Record<AdminCompletionKey, string>;
    completenessCriterionLabels: Record<AdminCompletenessCriterionKey, string>;
    editorialIssueLabels: Record<AdminEditorialIssueKey, string>;
    severityLabels: Record<AdminSeverityKey, string>;
    sourceVerificationTypeLabels: Record<AdminSourceVerificationTypeKey, string>;
    sourceVerificationIssueLabels: Record<AdminSourceVerificationIssueKey, string>;
    duplicateReasonLabels: Record<AdminDuplicateReasonKey, string>;
    aiSuggestionKindLabels: Record<AdminAiSuggestionKindKey, string>;
    aiSuggestionStatusLabels: Record<AdminAiSuggestionStatusKey, string>;
    aiFeatureStatusLabels: Record<AdminAiFeatureStatusKey, string>;
    applicationFeatureLabels: Record<AdminApplicationFeatureKey, string>;
    environmentLabels: Record<AdminEnvironmentKey, string>;
  };
  sidebar: {
    navigationAriaLabel: string;
    modulePlannedTitle: string;
    sections: {
      editorial: string;
      quality: string;
      ai: string;
      sources: string;
      administration: string;
    };
    items: {
      dashboard: string;
      persons: string;
      review: string;
      qualityIssues: string;
      duplicates: string;
      sourceVerification: string;
      aiCenter: string;
      aiSuggestions: string;
      sourcesAndMedia: string;
      geography: string;
      orders: string;
      dictionaries: string;
      usersAndRoles: string;
      apiDocumentation: string;
      settings: string;
    };
    status: {
      unavailable: string;
      connected: string;
      connecting: string;
      environment: string;
    };
  };
  topbar: {
    globalSearchAriaLabel: string;
    globalSearchPlaceholder: string;
    changeThemeAriaLabel: string;
    notificationsAriaLabel: string;
    userFallback: string;
    noRoleFallback: string;
    roleLabels: Record<AdminSystemRoleKey, string>;
    logoutAriaLabel: string;
  };
  system: {
    notFound: {
      kicker: string;
      title: string;
      description: string;
      dashboardAction: string;
    };
    error: {
      kicker: string;
      title: string;
      description: string;
      digestPrefix: string;
      retryAction: string;
      dashboardAction: string;
    };
    loading: {
      application: string;
      dashboard: string;
      sessionVerification: string;
    };
    apiErrors: {
      unauthorized: string;
      forbidden: string;
      notFound: string;
      conflict: string;
      validation: string;
      rateLimited: string;
      server: string;
      unexpected: string;
      invalidValue: string;
      invalidData: string;
      network: string;
      requestFailedPrefix: string;
      requestFailedSuffix: string;
    };
  };
  login: {
    metadataTitle: string;
    metadataDescription: string;
    editorialPanelAriaLabel: string;
    quote: string;
    quoteDescription: string;
    securityStatement: string;
    accessKicker: string;
    title: string;
    description: string;
    emailLabel: string;
    emailPlaceholder: string;
    passwordLabel: string;
    passwordRecovery: string;
    hidePasswordAriaLabel: string;
    showPasswordAriaLabel: string;
    sessionStorageNotice: string;
    submitting: string;
    submit: string;
    auditNotice: string;
    validation: {
      invalidEmail: string;
      requiredPassword: string;
    };
    errors: {
      unauthorized: string;
      forbidden: string;
      rateLimited: string;
      validation: string;
      server: string;
      unexpected: string;
      invalidValue: string;
      invalidData: string;
      network: string;
      requestFailedPrefix: string;
      requestFailedSuffix: string;
    };
  };
  dashboard: {
    metadataTitle: string;
    metadataDescription: string;
    loading: string;
    loadError: {
      title: string;
      description: string;
      refreshAction: string;
    };
    header: {
      title: string;
      recordsDescriptionPrefix: string;
      recordsDescriptionSuffix: string;
      queueAction: string;
      addPersonAction: string;
    };
    operationalQueuesAriaLabel: string;
    metricOpenAriaLabelSuffix: string;
    metrics: {
      review: { label: string; detail: string };
      draft: { label: string; detail: string };
      quality: { label: string; detail: string };
      license: { label: string; detail: string };
    };
    activity: {
      title: string;
      description: string;
      currentData: string;
    };
    queue: {
      title: string;
      recordsSuffix: string;
      openAction: string;
      empty: string;
      readyForNextStage: string;
      completenessPrefix: string;
    };
    recent: {
      title: string;
      description: string;
      personsAction: string;
      systemActor: string;
    };
    completion: {
      title: string;
      description: string;
    };
    resources: {
      title: string;
      description: string;
      labels: {
        users: string;
        countries: string;
        orders: string;
        bibliography: string;
      };
      synchronized: string;
    };
    licenseAlert: {
      prefix: string;
      suffix: string;
    };
  };
  review: {
    metadataTitle: string;
    metadataDescription: string;
    kicker: string;
    title: string;
    description: string;
    addRecordAction: string;
    queueStateAriaLabel: string;
    summary: {
      all: string;
      drafts: string;
      inReview: string;
      attention: string;
      urgent: string;
      highPriority: string;
    };
    searchPlaceholder: string;
    stageFilterAriaLabel: string;
    priorityFilterAriaLabel: string;
    filters: {
      allStages: string;
      drafts: string;
      inReview: string;
      everyPriority: string;
    };
    refreshAction: string;
    table: {
      record: string;
      stageAndPriority: string;
      completeness: string;
      issues: string;
      lastChange: string;
      decision: string;
    };
    states: {
      loading: string;
      loadError: string;
      emptyTitle: string;
      emptyDescription: string;
    };
    completenessExplanation: string;
    noDetectedIssues: string;
    systemActor: string;
    actions: {
      edit: string;
      submitForReview: string;
      return: string;
      approve: string;
      viewOnly: string;
      publishBlockedTitle: string;
      publishReadyTitle: string;
    };
    pagination: {
      displayedPrefix: string;
      of: string;
      recordsSuffix: string;
      previous: string;
      pagePrefix: string;
      pageSeparator: string;
      next: string;
    };
    returnDialog: {
      title: string;
      descriptionPrefix: string;
      closeAriaLabel: string;
      noteLabel: string;
      notePlaceholder: string;
      noteRequirement: string;
      cancelAction: string;
      confirmAction: string;
    };
    errors: {
      unauthorized: string;
      forbidden: string;
      notFound: string;
      conflict: string;
      validation: string;
      server: string;
      unexpected: string;
      invalidValue: string;
      invalidData: string;
      network: string;
      requestFailedPrefix: string;
      requestFailedSuffix: string;
    };
  };
  quality: {
    metadataTitle: string;
    metadataDescription: string;
    tabsAriaLabel: string;
    tabs: {
      issues: string;
      duplicates: string;
      sources: string;
    };
    header: {
      kicker: string;
      title: string;
      description: string;
      refreshAction: string;
    };
    states: {
      loading: string;
      loadErrorTitle: string;
      loadErrorDescription: string;
      refreshAction: string;
    };
    summaryAriaLabel: string;
    summary: {
      recordsWithIssues: { label: string; detail: string };
      totalIssues: { label: string; detail: string };
      duplicateGroups: { label: string; recordsSuffix: string };
      sourcesToReview: { label: string; detail: string };
      undocumentedProfiles: { label: string; documentedSuffix: string };
    };
    issues: {
      typesAriaLabel: string;
      emptyTitle: string;
      emptyDescription: string;
      recordsTitle: string;
      shownPrefix: string;
      shownSeparator: string;
      shownSuffix: string;
      openAttentionQueue: string;
      table: {
        record: string;
        status: string;
        completeness: string;
        documentation: string;
        issues: string;
        actions: string;
      };
      attachedSourcesSuffix: string;
      imagesSuffix: string;
      licensesToReviewSuffix: string;
      editAction: string;
    };
    duplicates: {
      emptyTitle: string;
      emptyDescription: string;
      suspicionPrefix: string;
      confidencePrefix: string;
      unknownLifeDates: string;
      sourcesSuffix: string;
      openAction: string;
    };
    sources: {
      explanationTitle: string;
      explanationDescription: string;
      statisticsAriaLabel: string;
      metrics: {
        bibliography: { label: string; detail: string };
        historical: { label: string; detail: string };
        assignments: { label: string; detail: string };
        documented: { label: string; detail: string };
        undocumented: { label: string; detail: string };
        unknownLicenses: { label: string; detailPrefix: string; detailSuffix: string };
      };
      emptyTitle: string;
      emptyDescription: string;
      itemsTitle: string;
      shownPrefix: string;
      shownSuffix: string;
      mediaWithoutLicense: string;
      table: {
        item: string;
        issue: string;
        relatedPerson: string;
        sourceUrl: string;
        destination: string;
      };
      noUrl: string;
      personSourceTitlePrefix: string;
      targets: {
        editAvatar: { label: string; hint: string };
        editSources: { label: string; hint: string };
        checkMedia: { label: string; hint: string };
        openSection: { label: string; hint: string };
      };
    };
  };
  settings: {
    metadataTitle: string;
    metadataDescription: string;
    loading: string;
    loadError: {
      title: string;
      description: string;
      refreshAction: string;
    };
    header: {
      kicker: string;
      title: string;
      description: string;
      refreshAction: string;
    };
    common: {
      enabled: string;
      disabled: string;
      notAvailable: string;
    };
    application: {
      title: string;
      description: string;
      name: string;
      version: string;
      environment: string;
      apiDocumentation: string;
      swagger: string;
      openApi: string;
      schemaJson: string;
    };
    features: {
      title: string;
      descriptionMiddle: string;
      descriptionSuffix: string;
      environmentNotice: string;
    };
    ai: {
      title: string;
      description: string;
      provider: string;
      openAiApi: string;
      keyConfigured: string;
      keyMissing: string;
      embeddingModel: string;
      completionModel: string;
      ollama: string;
      ollamaInactive: string;
      embeddingDimensions: string;
    };
    storageAndSecurity: {
      title: string;
      description: string;
      storageBackend: string;
      imagesBucket: string;
      documentsBucket: string;
      exportsBucket: string;
      publicEndpoint: string;
      accessToken: string;
      refreshToken: string;
      minutesSuffix: string;
      daysSuffix: string;
      secureCookies: string;
      cors: string;
    };
    profile: {
      title: string;
      description: string;
      fullName: string;
      fullNamePlaceholder: string;
      preferredLanguage: string;
      languages: {
        pl: string;
        en: string;
        la: string;
      };
      email: string;
      roles: string;
      lastLogin: string;
      profileSaved: string;
      saveAction: string;
    };
    appearance: {
      title: string;
      description: string;
      light: string;
      lightDescription: string;
      dark: string;
      darkDescription: string;
    };
    password: {
      title: string;
      description: string;
      current: string;
      next: string;
      confirm: string;
      hideAriaLabel: string;
      showAriaLabel: string;
      changed: string;
      tooShort: string;
      mismatch: string;
      changeAction: string;
    };
    environment: {
      title: string;
      description: string;
      explanationTitle: string;
      explanation: string;
    };
  };
  accessControl: {
    metadataTitle: string;
    metadataDescription: string;
    closeDialogAriaLabel: string;
    sessionVerifying: string;
    forbidden: {
      title: string;
      description: string;
    };
    header: {
      kicker: string;
      title: string;
      description: string;
      addUserAction: string;
      addRoleAction: string;
    };
    summaryAriaLabel: string;
    summary: {
      accounts: string;
      activeRoles: string;
      permissions: string;
    };
    tabs: {
      ariaLabel: string;
      users: string;
      matrix: string;
    };
    users: {
      searchPlaceholder: string;
      table: {
        user: string;
        role: string;
        status: string;
        lastLogin: string;
        actions: string;
      };
      loading: string;
      loadError: string;
      empty: string;
      noRole: string;
      neverLoggedIn: string;
      editAction: string;
      editProtectedTitle: string;
      editTitle: string;
      deactivateAction: string;
      deactivateTitle: string;
      deactivateConfirmPrefix: string;
    };
    roles: {
      loading: string;
      loadError: string;
      retryAction: string;
      empty: string;
      systemBadge: string;
      customBadge: string;
      noDescription: string;
      usersSuffix: string;
      permissionsSuffix: string;
      editAction: string;
      deleteTitle: string;
      deleteBlockedTitle: string;
      deleteConfirmPrefix: string;
      matrixTitle: string;
      matrixDescription: string;
      operation: string;
      allowedAriaLabel: string;
      deniedAriaLabel: string;
      systemDescriptions: Record<AdminSystemRoleKey, string>;
    };
    userDialog: {
      createTitle: string;
      editTitle: string;
      createDescription: string;
      editDescription: string;
      fullName: string;
      role: string;
      chooseRole: string;
      email: string;
      temporaryPassword: string;
      passwordHelp: string;
      status: string;
      cancelAction: string;
      createAction: string;
      saveAction: string;
    };
    roleDialog: {
      createTitle: string;
      editTitle: string;
      description: string;
      identifier: string;
      identifierPlaceholder: string;
      identifierHelp: string;
      displayName: string;
      responsibility: string;
      permissionsLegend: string;
      permissionsHelp: string;
      cancelAction: string;
      createAction: string;
      saveAction: string;
    };
    userStatusLabels: Record<AdminUserStatusKey, string>;
    permissionGroupLabels: Record<AdminPermissionGroupKey, string>;
    permissionLabels: Record<AdminPermissionKey, string>;
    errors: {
      unauthorized: string;
      forbidden: string;
      notFound: string;
      conflict: string;
      validation: string;
      server: string;
      unexpected: string;
      invalidValue: string;
      invalidData: string;
      network: string;
      requestFailedPrefix: string;
      requestFailedSuffix: string;
    };
  };
  aiCenter: {
    metadataTitle: string;
    metadataDescription: string;
    loading: string;
    loadError: {
      title: string;
      description: string;
      refreshAction: string;
    };
    kicker: string;
    title: string;
    description: string;
    refreshAction: string;
    suggestionsAction: string;
    metricsAriaLabel: string;
    metrics: {
      coverage: { label: string; profilesSuffix: string };
      missing: { label: string; detail: string };
      suggestions: { label: string; detail: string };
      blocked: { label: string; detail: string };
    };
    modules: {
      title: string;
      configuration: {
        prefix: string;
        embeddings: string;
        model: string;
        summaries: string;
      };
      lastEmbeddingPrefix: string;
      noEmbedding: string;
      progress: string;
      features: Record<
        AdminAiFeatureKey,
        {
          label: string;
          description: string;
        }
      >;
      details: {
        embeddingsMiddle: string;
        embeddingsSuffix: string;
        semanticReady: string;
        semanticNeedsData: string;
        summariesPrefix: string;
        summariesFallback: string;
        taggingPrefix: string;
        taggingDisabled: string;
      };
    };
    operations: {
      title: string;
      description: string;
      embeddingsAction: string;
      embeddingsDisabled: string;
      embeddingsEnabled: string;
      tagsAction: string;
      tagsDisabled: string;
      tagsEnabled: string;
      safetyNotice: string;
    };
    recent: {
      title: string;
      description: string;
      allAction: string;
      openAction: string;
      empty: string;
    };
  };
  aiSuggestions: {
    metadataTitle: string;
    metadataDescription: string;
    backAction: string;
    kicker: string;
    title: string;
    description: string;
    refreshAction: string;
    statusAriaLabel: string;
    statusCards: {
      all: string;
      pending: string;
      ready: string;
      blocked: string;
    };
    filters: {
      searchAriaLabel: string;
      searchPlaceholder: string;
      allKinds: string;
    };
    actions: {
      blocked: string;
      generateEmbedding: string;
      generateSummary: string;
      generateTags: string;
      openDecision: string;
      editPerson: string;
      manualRequired: string;
    };
    successPrefix: string;
    successSuffix: string;
    card: {
      currentValue: string;
      currentValueEmpty: string;
      suggestion: string;
      suggestionEmpty: string;
      confidence: string;
      updatedPrefix: string;
    };
    decisionDialog: {
      summaryTitle: string;
      tagsTitle: string;
      description: string;
      currentLabel: string;
      currentEmpty: string;
      summaryLabel: string;
      summaryHelp: string;
      tagsLabel: string;
      tagsHelp: string;
      rejectionLabel: string;
      rejectionPlaceholder: string;
      rejectionHelp: string;
      cancelAction: string;
      rejectAction: string;
      acceptAction: string;
      savingAction: string;
      closeAriaLabel: string;
      summaryRequired: string;
      tagsRequired: string;
      rejectionRequired: string;
      acceptedMessage: string;
      rejectedMessage: string;
    };
    states: {
      loading: string;
      loadErrorTitle: string;
      loadErrorDescription: string;
      emptyTitle: string;
      emptyDescription: string;
    };
  };
  ordersWorkspace: {
    metadataTitle: string;
    metadataDescription: string;
    kicker: string;
    title: string;
    description: string;
    refreshAction: string;
    addAction: string;
    importAction: string;
    importSuccessPrefix: string;
    importSuccessSuffix: string;
    summaryAriaLabel: string;
    metrics: {
      communities: string;
      activeSuffix: string;
      featured: string;
      featuredDetail: string;
      members: string;
      membersDetail: string;
      documented: string;
      documentedDetail: string;
    };
    filters: {
      all: string;
      featured: string;
      active: string;
      suppressed: string;
      members: string;
    };
    searchAriaLabel: string;
    searchPlaceholder: string;
    table: {
      community: string;
      type: string;
      charism: string;
      foundation: string;
      missionHistory: string;
      persons: string;
      status: string;
      updated: string;
      actions: string;
    };
    states: {
      loading: string;
      empty: string;
    };
    labels: {
      descriptionMissing: string;
      source: string;
      suppressed: string;
      active: string;
    };
    actions: {
      edit: string;
      deleteAriaPrefix: string;
      deleteBlockedTitle: string;
      deleteTitle: string;
      deleteConfirmPrefix: string;
      deleteConfirmSuffix: string;
    };
    dialog: {
      editTitle: string;
      createTitle: string;
      description: string;
      closeAriaLabel: string;
      sections: {
        identity: string;
        institutionalHistory: string;
        editorialDescription: string;
        sourcesAndPublication: string;
      };
      fields: {
        name: string;
        slug: string;
        abbreviation: string;
        latinName: string;
        localName: string;
        communityType: string;
        spiritualFamily: string;
        spiritualFamilyPlaceholder: string;
        charism: string;
        unspecified: string;
        sortOrder: string;
        foundedYear: string;
        founder: string;
        papalApprovalYear: string;
        suppressedYear: string;
        shortDescription: string;
        mission: string;
        history: string;
        englishDescription: string;
        motto: string;
        website: string;
        sourceTitle: string;
        sourceUrl: string;
        featured: string;
        suppressed: string;
      };
      cancelAction: string;
      saveAction: string;
      createAction: string;
    };
    importDialog: {
      title: string;
      description: string;
      closeAriaLabel: string;
      chooseFile: string;
      fileHint: string;
      downloadTemplate: string;
      maxSizeError: string;
      invalidRootError: string;
      invalidJsonPrefix: string;
      readError: string;
      invalidFormat: string;
      validating: string;
      batchTitle: string;
      schemaVersionPrefix: string;
      communitiesCount: string;
      warningsTitle: string;
      errorsTitle: string;
      ready: string;
      cancelAction: string;
      importAction: string;
      importingAction: string;
    };
  };
  dictionariesWorkspace: {
    metadataTitle: string;
    metadataDescription: string;
    kicker: string;
    title: string;
    description: string;
    refreshAction: string;
    summaryAriaLabel: string;
    metrics: {
      categories: string;
      subcategoriesSuffix: string;
      tags: string;
      coloredSuffix: string;
      states: string;
      latinNamesSuffix: string;
      occupations: string;
      describedSuffix: string;
      popes: string;
      linkedPersonsSuffix: string;
    };
    views: {
      categories: string;
      tags: string;
      states: string;
      occupations: string;
      popes: string;
    };
    searchAriaLabel: string;
    searchPlaceholder: string;
    columns: {
      category: string;
      slug: string;
      parent: string;
      sortOrder: string;
      updated: string;
      tag: string;
      color: string;
      state: string;
      latin: string;
      description: string;
      occupation: string;
      pope: string;
      pontificate: string;
      number: string;
      relation: string;
    };
    states: {
      loadingCategories: string;
      emptyCategories: string;
      loadingTags: string;
      emptyTags: string;
      loadingStates: string;
      emptyStates: string;
      loadingOccupations: string;
      emptyOccupations: string;
      loadingPopes: string;
      emptyPopes: string;
      partialRefresh: string;
    };
    labels: {
      layNameMissing: string;
      present: string;
      linkedPerson: string;
      dictionaryOnly: string;
    };
  };
  geography: {
    metadataTitle: string;
    metadataDescription: string;
    kicker: string;
    title: string;
    description: string;
    refreshAction: string;
    summaryAriaLabel: string;
    metrics: {
      countries: string;
      historicalSuffix: string;
      places: string;
      coordinatesSuffix: string;
      dioceses: string;
      archdiocesesSuffix: string;
      churches: string;
      pilgrimageSuffix: string;
    };
    views: {
      countries: string;
      places: string;
      dioceses: string;
      churches: string;
    };
    searchAriaLabel: string;
    searchPlaceholder: string;
    columns: {
      country: string;
      iso: string;
      capital: string;
      continent: string;
      type: string;
      updated: string;
      place: string;
      diocese: string;
      coordinates: string;
      years: string;
      church: string;
      cultStatus: string;
    };
    states: {
      loadingCountries: string;
      emptyCountries: string;
      loadingPlaces: string;
      emptyPlaces: string;
      loadingDioceses: string;
      emptyDioceses: string;
      loadingChurches: string;
      emptyChurches: string;
      partialRefresh: string;
    };
    labels: {
      historical: string;
      current: string;
      localNameMissing: string;
      archdiocese: string;
      diocese: string;
      present: string;
      nationalSanctuary: string;
      pilgrimage: string;
      local: string;
    };
  };
  sourcesHub: {
    metadataTitle: string;
    metadataDescription: string;
    kicker: string;
    title: string;
    description: string;
    refreshAction: string;
    summaryAriaLabel: string;
    metrics: {
      bibliography: string;
      websiteSuffix: string;
      historical: string;
      digitizedSuffix: string;
      media: string;
      unknownLicenseSuffix: string;
      documents: string;
      publicDocumentsSuffix: string;
    };
    search: {
      title: string;
      description: string;
      ariaLabel: string;
      placeholder: string;
    };
    licenseAlert: {
      prefix: string;
      suffix: string;
      showAll: string;
      showReview: string;
    };
    bibliography: {
      title: string;
      description: string;
      columns: {
        title: string;
        type: string;
        year: string;
        score: string;
        updated: string;
      };
      loading: string;
      empty: string;
      authorMissing: string;
      noScore: string;
    };
    historical: {
      title: string;
      description: string;
      columns: {
        source: string;
        repository: string;
        dating: string;
        digitization: string;
        updated: string;
      };
      loading: string;
      empty: string;
      yes: string;
      no: string;
    };
    media: {
      title: string;
      filteredTitle: string;
      description: string;
      filteredDescription: string;
      clearFilter: string;
      columns: {
        image: string;
        license: string;
        source: string;
        size: string;
      };
      loading: string;
      empty: string;
      filteredEmpty: string;
      untitled: string;
      imageTypeFallback: string;
    };
    documents: {
      title: string;
      description: string;
      columns: {
        title: string;
        type: string;
        language: string;
        visibility: string;
      };
      loading: string;
      empty: string;
      public: string;
      draft: string;
    };
    partialRefresh: string;
  };
  persons: {
    metadataTitle: string;
    metadataDescription: string;
    header: {
      title: string;
      description: string;
      importAction: string;
      addAction: string;
    };
    filters: {
      searchPlaceholder: string;
      searchAriaLabel: string;
      typeAriaLabel: string;
      allTypes: string;
      statusAriaLabel: string;
      allStatuses: string;
      refreshAction: string;
    };
    resultsPrefix: string;
    resultsSuffix: string;
    table: {
      ariaLabel: string;
      name: string;
      type: string;
      status: string;
      era: string;
      lastModified: string;
      modifiedBy: string;
      createdAt: string;
      actions: string;
    };
    states: {
      loadError: string;
      empty: string;
    };
    systemActor: string;
    editAction: string;
    pagination: {
      pagePrefix: string;
      pageSeparator: string;
      previous: string;
      next: string;
    };
    importDialog: {
      title: string;
      description: string;
      closeAriaLabel: string;
      chooseFile: string;
      fileHint: string;
      maxSizeError: string;
      invalidRootError: string;
      invalidJsonPrefix: string;
      readError: string;
      validating: string;
      invalidFormat: string;
      profileWithoutName: string;
      typePrefix: string;
      schemaVersionPrefix: string;
      counts: {
        orders: string;
        feasts: string;
        sources: string;
      };
      warningsTitle: string;
      errorsTitle: string;
      ready: string;
      cancelAction: string;
      importAction: string;
    };
  };
  personEditor: {
    metadata: {
      newTitle: string;
      newDescription: string;
      editTitle: string;
      editDescription: string;
    };
    permissions: {
      createTitle: string;
      createDescription: string;
      readOnlyTitle: string;
      readOnlyDescription: string;
    };
    notFound: string;
    backToListAction: string;
    header: {
      newTitle: string;
      newDescription: string;
      editTitlePrefix: string;
      editDescription: string;
    };
    tabs: {
      basic: string;
      aliases: string;
      dates: string;
      biography: string;
      patronages: string;
      devotion: string;
      orders: string;
      sources: string;
      avatar: string;
    };
    prerequisites: {
      ordersTitle: string;
      ordersDescription: string;
      sourcesTitle: string;
      sourcesDescription: string;
    };
    avatarValidation: {
      invalidType: string;
      maxSize: string;
    };
    actions: {
      cancel: string;
      saveChanges: string;
      createPerson: string;
    };
    basic: {
      canonicalName: string;
      canonicalNamePlaceholder: string;
      canonicalNameEn: string;
      canonicalNameEnPlaceholder: string;
      latinName: string;
      latinNamePlaceholder: string;
      personType: string;
      publicationStatus: string;
      publicationStatusHint: string;
      gender: string;
      era: string;
      stateOfLife: string;
      loadingData: string;
      dataLoadError: string;
      noDictionaryData: string;
      retryData: string;
      featured: string;
      feast: {
        title: string;
        description: string;
        clearAction: string;
        loading: string;
        multipleEntriesPrefix: string;
        multipleEntriesSuffix: string;
        calendar: string;
        fallbackCalendars: {
          romanPl: string;
          romanUniversal: string;
          romanMartyrology: string;
        };
        retryCalendars: string;
        month: string;
        day: string;
        dayPlaceholder: string;
        rank: string;
        color: string;
        primary: string;
        sourceTitle: string;
        sourceTitlePlaceholder: string;
        sourceUrl: string;
        sourceUrlPlaceholder: string;
        notes: string;
        notesPlaceholder: string;
      };
    };
    dates: {
      birthYear: string;
      birthYearPlaceholder: string;
      deathYear: string;
      deathYearPlaceholder: string;
      birthCountry: string;
      deathCountry: string;
      loadingCountries: string;
      countriesLoadError: string;
      noCountries: string;
      retryCountries: string;
      recognitionTitle: string;
      recognitionDescription: string;
      beatification: string;
      beatificationYearPlaceholder: string;
      canonization: string;
      canonizationYearPlaceholder: string;
      exactDate: string;
      yearOnly: string;
    };
    biography: {
      summary: string;
      summaryPlaceholder: string;
      biography: string;
      biographyPlaceholder: string;
      changeSummary: string;
      changeSummaryPlaceholder: string;
    };
    devotion: {
      prayer: string;
      prayerPlaceholder: string;
      prayerHint: string;
      iconography: string;
      iconographyPlaceholder: string;
      iconographyHint: string;
    };
    aliases: {
      title: string;
      description: string;
      emptyTitle: string;
      emptyDescription: string;
      itemPrefix: string;
      removeAction: string;
      name: string;
      namePlaceholder: string;
      kind: string;
      language: string;
      languagePlaceholder: string;
      addAction: string;
    };
    patronages: {
      title: string;
      description: string;
      emptyTitle: string;
      emptyDescription: string;
      itemPrefix: string;
      itemHint: string;
      removeAction: string;
      type: string;
      name: string;
      namePlaceholder: string;
      nameEn: string;
      nameEnPlaceholder: string;
      official: string;
      notes: string;
      notesPlaceholder: string;
      addAction: string;
    };
    avatar: {
      newPersonFallback: string;
      previewTitle: string;
      previewDescription: string;
      diskFile: string;
      chooseFile: string;
      fileHint: string;
      removeFileAriaLabel: string;
      orUseAddress: string;
      imageUrl: string;
      imageUrlPlaceholder: string;
      fileOverridesUrl: string;
      thumbnailUrl: string;
      thumbnailUrlPlaceholder: string;
      altText: string;
      altTextPrefix: string;
      license: string;
      photographer: string;
      photographerPlaceholder: string;
      sourceUrl: string;
      sourceUrlPlaceholder: string;
      processingHint: string;
    };
    orders: {
      title: string;
      description: string;
      community: string;
      selectCommunity: string;
      membershipType: string;
      founder: string;
      entry: string;
      entryPlaceholder: string;
      exit: string;
      exitPlaceholder: string;
      notes: string;
      notesPlaceholder: string;
      catalogueHint: string;
      assignAction: string;
      assignedPrefix: string;
      empty: string;
      fromPrefix: string;
      toPrefix: string;
      removeConfirmPrefix: string;
      removeConfirmSuffix: string;
      removeAction: string;
      selectRequired: string;
    };
    sources: {
      completenessPrefix: string;
      completenessPoints: string;
      completenessSuffix: string;
      addLinkMode: string;
      catalogueMode: string;
      title: string;
      titlePlaceholder: string;
      url: string;
      urlPlaceholder: string;
      invalidUrl: string;
      author: string;
      authorPlaceholder: string;
      kind: string;
      bibliographyKind: string;
      historicalKind: string;
      position: string;
      selectSource: string;
      pageReference: string;
      pageReferencePlaceholder: string;
      notes: string;
      notesPlaceholder: string;
      primary: string;
      addWebAction: string;
      assignAction: string;
      assignedTitle: string;
      linksCountSuffix: string;
      loading: string;
      empty: string;
      unknown: string;
      primaryBadge: string;
      referencePrefix: string;
      removeAriaPrefix: string;
    };
    validation: {
      canonicalNameMin: string;
      mediaUrl: string;
      httpUrl: string;
      aliasRequired: string;
      aliasCharacters: string;
      languageCodeRequired: string;
      languageCodeMax: string;
      languageCodeFormat: string;
      duplicateAliases: string;
      patronageTypeRequired: string;
      patronageNameRequired: string;
      feastDateIncomplete: string;
      feastDateInvalid: string;
      feastCalendarRequired: string;
    };
  };
  personDetail: {
    metadataTitle: string;
    metadataDescription: string;
    backAriaLabel: string;
    exportAction: string;
    editAction: string;
    exportFileFallback: string;
    exportError: string;
    notFound: string;
    backToListAction: string;
    biography: {
      title: string;
      noSummary: string;
      noBiography: string;
    };
    prayer: {
      title: string;
      empty: string;
    };
    iconography: {
      title: string;
      empty: string;
    };
    patronages: {
      title: string;
      description: string;
      manageAction: string;
      official: string;
      empty: string;
    };
    sources: {
      title: string;
      description: string;
      manageAction: string;
      unknown: string;
      referencePrefix: string;
      empty: string;
    };
    hagiographicMetadata: {
      title: string;
      feast: string;
      noFeast: string;
      gender: string;
      era: string;
      stateOfLife: string;
      birthYear: string;
      deathYear: string;
      beatification: string;
      canonization: string;
    };
    history: {
      titlePrefix: string;
      empty: string;
      defaultChange: string;
    };
  };
}

export type AdminSidebarDictionary = Pick<AdminDictionary, "brand" | "sidebar">;
export type AdminTopbarDictionary = AdminDictionary["topbar"];
export type AdminSystemDictionary = AdminDictionary["system"];
export type AdminApiErrorsDictionary = AdminSystemDictionary["apiErrors"];
export type AdminLoginDictionary = Pick<AdminDictionary, "brand" | "login">;
export type AdminDashboardDictionary = AdminDictionary["dashboard"];
export type AdminDomainDictionary = AdminDictionary["domain"];
export type AdminReviewDictionary = AdminDictionary["review"];
export type AdminQualityDictionary = AdminDictionary["quality"];
export type AdminSettingsDictionary = AdminDictionary["settings"];
export type AdminAccessControlDictionary = AdminDictionary["accessControl"];
export type AdminAiCenterDictionary = AdminDictionary["aiCenter"];
export type AdminAiSuggestionsDictionary = AdminDictionary["aiSuggestions"];
export type AdminOrdersDictionary = AdminDictionary["ordersWorkspace"];
export type AdminDictionariesDictionary = AdminDictionary["dictionariesWorkspace"];
export type AdminGeographyDictionary = AdminDictionary["geography"];
export type AdminSourcesHubDictionary = AdminDictionary["sourcesHub"];
export type AdminPersonsDictionary = AdminDictionary["persons"];
export type AdminPersonEditorDictionary = AdminDictionary["personEditor"];
export type AdminPersonDetailDictionary = AdminDictionary["personDetail"];
