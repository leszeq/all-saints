export type AdminSystemRoleKey =
  | "super_admin"
  | "admin"
  | "editor"
  | "reviewer"
  | "translator"
  | "reader"
  | "guest";

export type AdminPublicationStatusKey = "draft" | "review" | "published" | "archived";
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
export type AdminEditorialIssueKey =
  | "missing_biography"
  | "missing_summary"
  | "missing_sources"
  | "missing_image"
  | "unknown_image_license"
  | "missing_dates"
  | "missing_state_of_life";

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
    editorialPriorityLabels: Record<AdminEditorialPriorityKey, string>;
    completionLabels: Record<AdminCompletionKey, string>;
    completenessCriterionLabels: Record<AdminCompletenessCriterionKey, string>;
    editorialIssueLabels: Record<AdminEditorialIssueKey, string>;
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
}

export type AdminSidebarDictionary = Pick<AdminDictionary, "brand" | "sidebar">;
export type AdminTopbarDictionary = AdminDictionary["topbar"];
export type AdminSystemDictionary = AdminDictionary["system"];
export type AdminLoginDictionary = Pick<AdminDictionary, "brand" | "login">;
export type AdminDashboardDictionary = AdminDictionary["dashboard"];
export type AdminDomainDictionary = AdminDictionary["domain"];
export type AdminReviewDictionary = AdminDictionary["review"];
