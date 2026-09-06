export type AdminSystemRoleKey =
  | "super_admin"
  | "admin"
  | "editor"
  | "reviewer"
  | "translator"
  | "reader"
  | "guest";

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
    };
  };
}

export type AdminSidebarDictionary = Pick<AdminDictionary, "brand" | "sidebar">;
export type AdminTopbarDictionary = AdminDictionary["topbar"];
export type AdminSystemDictionary = AdminDictionary["system"];
