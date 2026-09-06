import type { AdminDictionary } from "@/lib/i18n/types";

const dictionary = {
  metadata: {
    defaultTitle: "Admin – Encyklopedia Świętych",
    titleTemplate: "%s | Admin Encyklopedia Świętych",
    description: "Panel administracyjny Encyklopedii Świętych Kościoła Katolickiego",
  },
  brand: {
    name: "Encyklopedia Świętych",
    product: "Panel redakcyjny",
  },
  sidebar: {
    navigationAriaLabel: "Nawigacja panelu",
    modulePlannedTitle: "Moduł przewidziany w kolejnym etapie",
    sections: {
      editorial: "Redakcja",
      quality: "Jakość danych",
      ai: "AI",
      sources: "Źródła i dane",
      administration: "Administracja",
    },
    items: {
      dashboard: "Pulpit",
      persons: "Osoby i święci",
      review: "Kolejka redakcyjna",
      qualityIssues: "Problemy jakości",
      duplicates: "Duplikaty",
      sourceVerification: "Weryfikacja źródeł",
      aiCenter: "Centrum AI",
      aiSuggestions: "Sugestie",
      sourcesAndMedia: "Źródła i media",
      geography: "Geografia",
      orders: "Zakony",
      dictionaries: "Słowniki",
      usersAndRoles: "Użytkownicy i role",
      apiDocumentation: "Dokumentacja API",
      settings: "Ustawienia",
    },
    status: {
      unavailable: "API niedostępne",
      connected: "API połączone",
      connecting: "Łączenie z API…",
      environment: "v1.0 · środowisko lokalne",
    },
  },
  topbar: {
    globalSearchAriaLabel: "Otwórz wyszukiwanie globalne",
    globalSearchPlaceholder: "Szukaj w panelu…",
    changeThemeAriaLabel: "Zmień motyw",
    notificationsAriaLabel: "Powiadomienia",
    userFallback: "Użytkownik",
    noRoleFallback: "Brak roli",
    logoutAriaLabel: "Wyloguj",
  },
} satisfies AdminDictionary;

export default dictionary;
