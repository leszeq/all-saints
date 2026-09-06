export interface NavigationLink {
  href: string;
  label: string;
}

export interface FooterGroup {
  title: string;
  links: NavigationLink[];
}

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
}

export type WebHeaderDictionary = Pick<WebDictionary, "brand" | "header">;
export type WebFooterDictionary = Pick<WebDictionary, "brand" | "footer">;
