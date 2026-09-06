import type { WebDictionary } from "@/lib/i18n/types";

const dictionary = {
  metadata: {
    defaultTitle: "Encyklopedia Świętych Kościoła Katolickiego",
    titleTemplate: "%s | Encyklopedia Świętych",
    description:
      "Kompletny cyfrowy leksykon hagiograficzny Kościoła Katolickiego. Wyszukuj świętych, błogosławionych, patronów, kalendarz liturgiczny i modlitwy.",
    keywords: [
      "święci",
      "błogosławieni",
      "Kościół Katolicki",
      "patroni",
      "hagiografia",
      "kalendarz liturgiczny",
      "modlitwy",
      "sanktuaria",
    ],
    author: "Encyklopedia Świętych Team",
    openGraphLocale: "pl_PL",
    openGraphTitle: "Encyklopedia Świętych Kościoła Katolickiego",
    openGraphDescription:
      "Wyszukuj świętych, błogosławionych, patronów i kalendarz liturgiczny.",
  },
  brand: {
    name: "Encyklopedia Świętych",
    product: "Portal publiczny",
  },
  header: {
    homeAriaLabel: "Encyklopedia Świętych — strona główna",
    navigationAriaLabel: "Nawigacja główna",
    mobileNavigationAriaLabel: "Nawigacja mobilna",
    searchAriaLabel: "Szukaj w encyklopedii",
    searchPlaceholder: "Szukaj…",
    mobileSearchPlaceholder: "Szukaj świętego lub patronatu…",
    searchButton: "Szukaj",
    openMenuAriaLabel: "Otwórz menu",
    closeMenuAriaLabel: "Zamknij menu",
    navigation: [
      { href: "/swieci", label: "Katalog świętych" },
      { href: "/#odkrywaj", label: "Patronaty" },
      { href: "/kalendarz", label: "Kalendarz" },
      { href: "/zakony", label: "Zakony" },
      { href: "/#epoki", label: "Epoki" },
    ],
  },
  footer: {
    description:
      "Redakcyjna baza wiedzy o życiu, kulcie i dziedzictwie świętych. Każdy profil powstaje na podstawie udokumentowanych źródeł.",
    disclaimer: "Portal ma charakter informacyjno-edukacyjny.",
    groups: [
      {
        title: "Odkrywaj",
        links: [
          { label: "Katalog świętych", href: "/swieci" },
          { label: "Patronaty", href: "/#odkrywaj" },
          { label: "Kalendarz", href: "/kalendarz" },
          { label: "Zakony i zgromadzenia", href: "/zakony" },
          { label: "Epoki", href: "/#epoki" },
        ],
      },
      {
        title: "Projekt",
        links: [
          { label: "Metodologia", href: "/#metodologia" },
          { label: "Źródła i zasady", href: "/#zrodla" },
          { label: "Kontakt", href: "mailto:redakcja@encyklopediaswietych.pl" },
        ],
      },
    ],
    rightsReserved: "Wszelkie prawa zastrzeżone.",
  },
} satisfies WebDictionary;

export default dictionary;
