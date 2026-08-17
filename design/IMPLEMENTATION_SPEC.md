# Encyklopedia Świętych — specyfikacja UI

## 1. Zasady systemu

Portal ma charakter redakcyjny i książkowy; panel administracyjny jest narzędziem operacyjnym. Oba produkty łączy rytm 8 px, cienkie obramowania, oszczędne złoto i ten sam znak, ale nie współdzielą identycznych powierzchni ani gęstości.

| Token | Portal | Admin |
|---|---|---|
| Tło | `#F7F3EA` | `#F7F7F5` |
| Tekst | `#24211E` | `#202225` |
| Akcent | `#A8843D` | `#6B2033` |
| Sidebar | — | `#15171A` |
| Nagłówki | Literata 600–700 | Geist 600; Literata tylko redakcyjnie |
| UI / tekst | Geist 400–600 | Geist 400–600 |
| Promień | 12 px | 10 px |
| Obramowanie | 1 px `#DED8CD` | 1 px `#E1E2E0` |

Kontrolki mają minimum 44 px wysokości, focus ring 2 px i kontrast co najmniej WCAG AA. Złoto nie komunikuje stanu. Stany operacyjne: zielony — verified/sukces, niebieski — review/informacja, bursztynowy — brak/ostrzeżenie, czerwony — blokada/odrzucenie.

## 2. Architektura informacji

### Portal publiczny

| Trasa | Wzorzec |
|---|---|
| `/` | hero wyszukiwania + karta dnia + pięć sekcji odkrywania |
| `/swieci` | katalog: lewy filtr, sticky toolbar, grid/list, zapisany widok |
| `/swieci/[slug]` | artykuł redakcyjny + sticky TOC + metryka + źródła + podobni |
| `/wyszukiwarka` | hybrydowe wyniki z „Dlaczego pasuje”, źródłami i filtrem klasycznym |
| `/odkrywaj` | hub ścieżek tematycznych |
| `/kalendarz`, `/kalendarz/[data]` | miesiąc + panel dnia; pełny dzień używa tego samego modelu listy |
| `/patronaty`, `/patronaty/[slug]` | wspólny master–detail indeksu i strony tematu |
| `/zakony`, `/zakony/[slug]` | wspólny katalog badawczy i detal organizacji |
| `/kraje`, `/kraje/[slug]` | mapa + dostępna lista + panel kraju |
| `/epoki` | oś czasu z histogramem i zakresem |
| `/papieze` | katalog badawczy z grupowaniem kanonizacji |
| `/zrodla` | bibliografia/źródła z filtrowaniem i cytowaniem |
| `/o-projekcie`, `/metodologia`, `/kontakt` | jeden szablon treści instytucjonalnej |

### Panel administracyjny

| Trasa / grupa | Wzorzec |
|---|---|
| `/admin/login` | dzielony ekran logowania, komunikaty bezpieczeństwa |
| `/admin` | pulpit operacyjny: kolejki, jakość, zadania, obciążenie |
| `/admin/persons` | TanStack Table, saved views, bulk actions, kolumny użytkownika |
| `/admin/persons/new`, `/edit` | formularz sekcyjny, autosave, walidacja, sticky actions |
| `/admin/persons/[id]` | rekord + workflow + kompletność + problemy jakości |
| `/admin/persons/[id]/versions` | porównanie wersji i historia decyzji |
| `/admin/review`, `/duplicates` | kolejka + inspection Sheet + diff i decyzja |
| `/admin/ai/*` | centrum usług i ręczne kolejki sugestii |
| `/admin/sources`, `/media` | biblioteka zasobów + prawa/licencje + powiązania |
| słowniki geografii, Kościoła i taksonomii | tabela master + szybka edycja w Sheet |
| `/admin/users`, `/roles`, `/audit-log` | użytkownicy, macierz uprawnień, niezmienny audyt |
| `/admin/import`, `/export`, `/settings` | walidowany kreator i zakładki systemowe |

## 3. Komponenty do odwzorowania

- `PublicHeader`, `EditorialHero`, `SemanticSearchBox`, `SaintCard`, `SaintOfDayCard`, `FilterRail`, `ResultsToolbar`, `ArticleToc`, `PersonFactSheet`, `CitationPopover`, `RelatedPersons`.
- `AdminShell`, `CommandMenu`, `SavedViewSelect`, `DataTableToolbar`, `StatusBadge`, `CompletenessMeter`, `WorkflowStepper`, `SectionFormNav`, `AutosaveIndicator`, `ReviewDrawer`, `VersionDiff`.
- `AiDisclosure`, `ConfidenceBar`, `EvidencePanel`, `SuggestionDiff`, `ModelHealthCard`, `QualityIssueTable`, `RelationshipGraph`, `ClaimSourcePanel`.
- Wspólne stany: skeleton zachowujący layout, pusty stan z jednym CTA, błąd z retry i identyfikatorem, blokada uprawnień bez ukrywania kontekstu.

## 4. Reguły AI i jakości

1. AI zapisuje wyłącznie propozycję; nigdy nie nadpisuje wartości ani nie publikuje.
2. Sugestia pokazuje model/wersję, confidence, fragment uzasadniający, źródła i diff.
3. Decyzje `Zatwierdź / Edytuj / Odrzuć` trafiają do audytu; bulk approve wymaga jawnego zaznaczenia.
4. Workflow rekordu: `draft → review → verified → published → archived`, z właścicielem, recenzentem, kompletnością i datą weryfikacji.
5. Źródła można przypinać do twierdzenia/akapitu/pola, z numerem strony, wiarygodnością i konfliktem źródeł.

## 5. Kolejność wdrożenia

1. Tokeny, fonty i oba shelle.
2. Wspólne katalogi: toolbar, FilterRail, DataTable, master–detail.
3. Profil publiczny i rekord admina na jednym kontrakcie danych.
4. Workflow redakcyjny oraz Centrum jakości.
5. SuggestionDiff i kolejki AI.
6. Kalendarz, mapa, oś czasu i graf relacji ładowane dynamicznie.

## 6. Najważniejsze usprawnienia względem obecnej wersji

- Zastąpić fiolet admina burgundem i semantycznymi kolorami statusów; ograniczyć glassmorphism portalu do wyszukiwarki.
- Nie traktować dashboardu jako zestawu KPI: główne metryki powinny prowadzić do kolejki roboczej.
- Dodać źródła na poziomie twierdzeń, prawa do mediów, saved views, command palette, autosave i działania masowe.
- Ujednolicić route shell: w kodzie admin jest obecnie pod `/dashboard`, a mapa docelowa pod `/admin`; warto zdecydować o jednym publicznym prefiksie przed rozbudową.
- Portal projektować mobile-first; panel desktop-first z kontrolowanym wariantem tabletowym od 1024 px.

