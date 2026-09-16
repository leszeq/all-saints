# Szczegółowy plan implementacji — 40 funkcji

Uzupełnienie sekcji 12 i 31 raportu. Wszystkie endpointy/tabele opisane jako „dodać” są propozycjami. Zachować obecne kontrakty i migracje, a nazwy finalizować przy implementacji. Faza jest docelowym horyzontem; w fazie 0 wdrażamy minimalne zabezpieczenia dużych epików.

Dla każdej funkcji podano konkretne acceptance criteria i zakres wszystkich warstw. Po discovery duże epiki należy rozbić na pionowe przyrosty. Reach i wartość są hipotezami; nie są wynikami analityki produkcyjnej.

## FEATURE-001 — Uczciwe statusy jakości i obietnice produktu

**Grupa:** Trust / UX. **Faza:** 0. **Priorytet:** P1. **Priority Score:** 57.72.

**Product — problem**

Homepage przypisuje wszystkim kartom verified, obiecuje NLP i przypisy do informacji; topbar ma martwe kontrolki.

**User Story**

**As a** czytelnik i redaktor  
**I want** rozpoznawać, co jest opublikowane, opracowane i rzeczywiście zweryfikowane  
**So that** Rozumiem zakres danych i funkcji, zanim oprę się na wyniku.

**Wartość i złożoność**

Rozumiem zakres danych i funkcji, zanim oprę się na wyniku.

Techniczna: **2/10 (niska)**; dane: **2/10**; utrzymanie: **1/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Żaden badge nie wynika wyłącznie ze statusu publikacji.
- [ ] tekst wyszukiwarki odpowiada funkcjom.
- [ ] wszystkie widoczne przyciski mają działanie.
- [ ] źródła i status są nazwane jednoznacznie.

**Backend — endpointy, serwisy, schemas, permissions**

W minimum bez nowego API; następnie QualitySummary DTO z source_count i last_reviewed_at z rzeczywistej recenzji; nie wyprowadzać verified z published. Health/info powinien opisywać wdrożoną capability, a nie sam config flag.

**Database — tabele, relacje, indeksy, migracje**

Bez migracji w minimum; jeśli dodajemy last_reviewed_at, przechowywać zdarzenie recenzji z revision_id zamiast aktualizować datę przy każdym zapisie.

**Frontend — strony, komponenty, stan, integracja API**

apps/web/app/page.tsx i słownik pl: poprawić verified/NLP/metodologię; footer: usunąć nieudowodnione zapewnienia; topbar admin: link do listy osób zamiast pustego search, ukryć nieaktywny dzwonek. State: brak nowego globalnego store.

**Tests — backend, frontend, E2E**

Backend: kontrakt capability i jakości; Frontend: warunkowy badge dla danych z/bez recenzji; E2E: opublikowany profil bez źródła nie ma etykiety zweryfikowany.

**Infrastructure**

Brak nowych usług.

**Dependencies**

Brak; uzgodnienie słownika pojęć redakcyjnych.

**Risk**

Utrata pozornego wrażenia kompletności; zaakceptować ją jako poprawę zaufania.

## FEATURE-002 — Publiczna bibliografia profilu

**Grupa:** Sources. **Faza:** 1. **Priorytet:** P1. **Priority Score:** 57.37.

**Product — problem**

PersonSource dostępny jest w panelu, ale nie na publicznym profilu.

**User Story**

**As a** czytelnik weryfikujący informację  
**I want** otworzyć bibliografię bezpośrednio z profilu osoby  
**So that** Mogę odnaleźć materiał stanowiący podstawę opracowania.

**Wartość i złożoność**

Mogę odnaleźć materiał stanowiący podstawę opracowania.

Techniczna: **3/10 (niska)**; dane: **3/10**; utrzymanie: **2/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Źródła widoczne na profilu bez logowania.
- [ ] każdy wpis wskazuje istniejący rekord.
- [ ] brak prywatnych metadanych w HTML/JSON.
- [ ] książka offline pozostaje użyteczna.

**Backend — endpointy, serwisy, schemas, permissions**

Dodać GET /api/v1/persons/{id_or_slug}/sources przez publiczny router; PublicCitationSchema bez editor_notes/reviewer email; PersonSourceService/public query sprawdza published oraz aktywność linku i źródła. Zachować chroniony /sources/person-links.

**Database — tabele, relacje, indeksy, migracje**

Wykorzystać Bibliography, HistoricalSource i PersonSource; nowe tabele niepotrzebne; istniejący indeks person_id; nie zmieniać schematu tylko dla wyświetlenia.

**Frontend — strony, komponenty, stan, integracja API**

apps/web/lib/api.ts: fetchPersonSources; profil: SourcesSection z tytułem, autorami, rokiem, stroną i URL; SSR, wspólne pobranie profilu/źródeł; stan pusty bez zmyślonego przypisu.

**Tests — backend, frontend, E2E**

Backend: published 200, draft/deleted 404, usunięte źródło pominięte, prywatne notes nieobecne; Frontend: książka bez URL i archiwalium; E2E: profil→przypis→lokalizator źródła.

**Infrastructure**

Cache zgodny z rewizją osoby; brak nowej usługi.

**Dependencies**

001 dla terminologii; 004 dla docelowej spójności wersji.

**Risk**

Wycieki notes i pokazanie źródła jako potwierdzenia wszystkich zdań.

## FEATURE-003 — Źródłowa bramka publikacji

**Grupa:** Editorial / Quality. **Faza:** 0. **Priorytet:** P1. **Priority Score:** 48.09.

**Product — problem**

Publikacja wymaga tekstów i licencji, ale nie wymaga źródła; can_publish ma odrębną listę blockerów.

**User Story**

**As a** recenzent  
**I want** sprawdzić wymagane źródła przed dopuszczeniem treści do publikacji  
**So that** Publikuję wyłącznie profil spełniający jawne minimum redakcyjne.

**Wartość i złożoność**

Publikuję wyłącznie profil spełniający jawne minimum redakcyjne.

Techniczna: **4/10 (średnia)**; dane: **5/10**; utrzymanie: **3/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Jedna polityka dla badge, kolejki i API.
- [ ] legacy ma listę naprawczą i właściciela.
- [ ] wyjątek jawny z powodem.
- [ ] test nie pozwala ominąć bramki alternatywną mutacją.

**Backend — endpointy, serwisy, schemas, permissions**

Wydzielić PublicationPolicy używaną przez EditorialWorkflowService i EditorialQualityPolicy; sprawdzać aktywne źródło oraz treść/licencję; POST /editorial/queue/{id}/transition zwraca typed blockers. Weryfikować także alternatywne ścieżki import/AI; permission review/publish zgodnie z istniejącą macierzą.

**Database — tabele, relacje, indeksy, migracje**

V1 bez migracji; raport 34 profili bez linku; docelowo PublicationException(revision_id,reason,approver,expires_at), FK i indeks open exceptions. Brak automatycznego unpublish legacy.

**Frontend — strony, komponenty, stan, integracja API**

Kolejka i detail: ten sam zestaw blockerów, odnośnik do sekcji Źródła; React Query invalidation quality/person po przypisaniu.

**Tests — backend, frontend, E2E**

Backend: publikacja bez aktywnego źródła odrzucona; usunięty link nie spełnia bramki; Frontend: can_publish i API zgodne; E2E: draft→source→review→published.

**Infrastructure**

Brak nowych usług.

**Dependencies**

001, 002; przed 004 ustalić politykę bieżącej edycji.

**Risk**

Formalne dodanie dowolnego linku zamiast merytorycznej recenzji.

## FEATURE-004 — Izolowane rewizje opublikowanych treści

**Grupa:** Editorial foundation. **Faza:** 0. **Priorytet:** P0. **Priority Score:** 37.39.

**Product — problem**

PATCH treści osoby published może zmienić live bez ponownej recenzji; tłumaczenia wymagają draft całej osoby.

**User Story**

**As a** redaktor aktualizujący publiczny profil  
**I want** przygotować i zrecenzować nową wersję bez modyfikowania wersji publicznej  
**So that** Przygotowuję poprawki bez zmiany przeczytanej już wersji publicznej.

**Wartość i złożoność**

Przygotowuję poprawki bez zmiany przeczytanej już wersji publicznej.

Techniczna: **8/10 (wysoka)**; dane: **6/10**; utrzymanie: **5/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Publiczny profil wskazuje jednoznaczną wersję.
- [ ] draft nie przecieka w źródłach, mediach ani search.
- [ ] publikacja atomowa.
- [ ] rollback tworzy nową wersję.
- [ ] legacy response zachowany w okresie migracji.

**Backend — endpointy, serwisy, schemas, permissions**

Minimum: blokada niedozwolonych zapisów do published i audyt wszystkich writerów. Docelowo RevisionService, POST /persons/{id}/revisions, PATCH /revisions/{id}, POST /revisions/{id}/submit i /publish; RevisionCommand z expected_version; public query czyta published_revision_id. Ta sama reguła dla sources/orders/AI.

**Database — tabele, relacje, indeksy, migracje**

PublicationRevision(id,person_id,revision_number,status,payload,base_revision_id,author_id,created_at); Person.published_revision_id FK; UNIQUE(person_id,revision_number), indeks kolejki; backfill opublikowanych rekordów do pierwszej rewizji, parity test projekcji. Typed relacje rewizji dla źródeł; payload ma wersję schema.

**Frontend — strony, komponenty, stan, integracja API**

EditPersonClient: draft revision, ostrzeżenie o wersji bazowej; podgląd i diff; stan RHF lokalny, React Query według revision_id; UI 409 nie kasuje wpisanych zmian.

**Tests — backend, frontend, E2E**

Backend: publiczne read nie zmienia się po zapisie draftu; wszystkie write paths respektują granicę; Frontend: konflikt zachowuje formularz; E2E: dwie osoby edytują, tylko jedna publikuje zatwierdzoną rewizję.

**Infrastructure**

Po publikacji invalidacja cache; outbox 036 gdy pojawiają się async projekcje.

**Dependencies**

003 i przegląd wszystkich serwisów zapisujących Person.

**Risk**

Największe ryzyko regresji modelu; najpierw mała blokada, następnie migracja rewizji z shadow reads.

## FEATURE-005 — Bezpieczne renderowanie JSON-LD

**Grupa:** Security. **Faza:** 0. **Priorytet:** P0. **Priority Score:** 60.85.

**Product — problem**

JSON.stringify w script dangerouslySetInnerHTML nie neutralizuje zamknięcia znacznika przez treść rekordu.

**User Story**

**As a** czytelnik publicznego profilu  
**I want** bezpiecznie otwierać profile zawierające treści importowane i redagowane  
**So that** Otwieram treść redakcyjną bez wykonywania wstrzykniętego skryptu.

**Wartość i złożoność**

Otwieram treść redakcyjną bez wykonywania wstrzykniętego skryptu.

Techniczna: **2/10 (niska)**; dane: **1/10**; utrzymanie: **1/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Serializator poprawnie obsługuje niebezpieczny fragment i zwykłe nazwy.
- [ ] JSON po odczycie zachowuje oryginalną wartość.
- [ ] żadna ścieżka nie osadza surowego JSON.stringify.

**Backend — endpointy, serwisy, schemas, permissions**

API bez zmian; walidacja treści pomocnicza nie zastępuje bezpiecznego renderera.

**Database — tabele, relacje, indeksy, migracje**

Brak migracji ani masowej zmiany danych.

**Frontend — strony, komponenty, stan, integracja API**

Profil swieci/[slug]: wspólny serializeJsonLd neutralizujący < do sekwencji Unicode; zastosować do każdego JSON-LD; utrzymać poprawny JSON i odczyt przez parser danych strukturalnych.

**Tests — backend, frontend, E2E**

Backend: bez nowych testów gdy kontrakt bez zmian; Frontend: payload zawierający zamknięcie script, Unicode i cudzysłowy; E2E na fixture izolowanym: jedno script JSON-LD, brak dodatkowego elementu/wykonania.

**Infrastructure**

CSP jest dodatkową ochroną FEATURE-038; nie uzależniać szybkiego fixu od wdrożenia CSP.

**Dependencies**

Brak.

**Risk**

Niewłaściwe HTML escaping może zepsuć JSON-LD; test parsowania obok testu bezpieczeństwa.

## FEATURE-006 — SEO i cykl życia adresów

**Grupa:** SEO. **Faza:** 1. **Priorytet:** P1. **Priority Score:** 48.60.

**Product — problem**

Brak kompletnego canonical/sitemap/robots; profil może działać pod slug i UUID.

**User Story**

**As a** osoba trafiająca z wyszukiwarki  
**I want** trafiać z wyszukiwarki na trwały i jednoznaczny adres profilu  
**So that** Trafiam do jednej aktualnej, indeksowalnej strony tematu.

**Wartość i złożoność**

Trafiam do jednej aktualnej, indeksowalnej strony tematu.

Techniczna: **5/10 (średnia)**; dane: **3/10**; utrzymanie: **3/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Jedno kanoniczne URL na profil.
- [ ] sitemap tylko publiczne wartościowe strony.
- [ ] zmiana sluga zachowuje wejścia.
- [ ] polityka faset opisana i testowana.

**Backend — endpointy, serwisy, schemas, permissions**

GET /public-index/persons?cursor z lekkim PublicIndexItem(id,slug,updated_at); tylko published. Obsługa aliasu sluga/redirect target; nie używać pełnych biografii do sitemap.

**Database — tabele, relacje, indeksy, migracje**

V1 bez nowych tabel; v2 PersonSlugRedirect(old_slug UNIQUE,person_id,created_at), FK i indeks; migration/backfill tylko przy udokumentowanej zmianie sluga.

**Frontend — strony, komponenty, stan, integracja API**

web metadataBase z env; canonical i OG; sitemap.ts / robots.ts; 301 UUID/old_slug; BreadcrumbList; noindex wyszukiwania, kontrola stron tematycznych i paginacji; state URL.

**Tests — backend, frontend, E2E**

Backend: brak draftów w indeksie; Frontend: absolutne canonical/OG; E2E crawler fixture: brak pętli redirect, sitemap zawiera canonical i poprawne statusy, publikacja/usunięcie odświeża indeks.

**Infrastructure**

Cache sitemap, ewentualne shardowanie; domena produkcyjna z konfiguracji.

**Dependencies**

005, 002; pełna invalidacja zależy od 004.

**Risk**

Thin content i crawl explosion przy zbyt szerokim indeksowaniu faset.

## FEATURE-007 — Fasety relacyjne i precyzyjne filtry

**Grupa:** Discovery. **Faza:** 1. **Priorytet:** P1. **Priority Score:** 42.69.

**Product — problem**

Portal nie obsługuje kraju, zakonu, zawodu, dokładnego wieku ani męczeństwa jako pełnego przecięcia.

**User Story**

**As a** czytelnik szukający określonej grupy osób  
**I want** łączyć kryteria zakonu, dat, miejsca i patronatu  
**So that** Znajduję dokładnie określoną grupę i rozumiem znaczenie filtrów.

**Wartość i złożoność**

Znajduję dokładnie określoną grupę i rozumiem znaczenie filtrów.

Techniczna: **6/10 (średnia)**; dane: **6/10**; utrzymanie: **4/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Każda faseta ma opis semantyki.
- [ ] counts zgodne z wynikami i zasadą self-excluding jeśli zastosowana.
- [ ] filtr nie zwraca osoby wyłącznie na podstawie słowa w biografii.

**Backend — endpointy, serwisy, schemas, permissions**

Rozszerzyć PersonQueryService i GET /persons o order_id, occupation_id, nationality_id oraz zakres dat po 015; GET /persons/facets lub osobny search router z FacetCountsSchema. Country filter rozbić na typed geography; zapytania EXISTS, whitelist enum, published_only.

**Database — tabele, relacje, indeksy, migracje**

Wykorzystać PersonOrder/PersonOccupation i kraje; indeksy FK po obu stronach relacji; nowe role miejsca zależą od 017, martyrdom od 015; brak fikcyjnego backfillu z tekstu.

**Frontend — strony, komponenty, stan, integracja API**

web/swieci: URL jako źródło filtrów, FacetPanel, licznik, chips remove; select kraj z precyzyjną nazwą już w v1; mobile drawer; stabilny back/forward.

**Tests — backend, frontend, E2E**

Backend: OR wewnątrz/AND między fasetami, właściwe counts bez draftów; Frontend: normalizacja page/URL, reset; E2E: dominikanie+okres, patronat+zawód, 0 results.

**Infrastructure**

Bez nowego silnika wyszukiwania.

**Dependencies**

008 benchmark; 014/015/017 dla pełnego zestawu, obecne order/country dostępne wcześniej.

**Risk**

Niekompletne dane dają pozornie kompletną listę; pokazać zakres opracowania.

## FEATURE-008 — Benchmark i jakość rankingu wyszukiwania

**Grupa:** Discovery. **Faza:** 1. **Priorytet:** P1. **Priority Score:** 46.76.

**Product — problem**

Dobre mechanizmy SQL nie mają produktu jakościowego mierzonego na realnych pytaniach.

**User Story**

**As a** czytelnik wpisujący nazwę lub temat  
**I want** znaleźć poprawną osobę pomimo aliasu, odmiany lub literówki  
**So that** Poprawna osoba znajduje się wysoko również przy aliasie i literówce.

**Wartość i złożoność**

Poprawna osoba znajduje się wysoko również przy aliasie i literówce.

Techniczna: **5/10 (średnia)**; dane: **4/10**; utrzymanie: **3/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] 100–200 ocenionych pytań, udokumentowany baseline.
- [ ] brak regresji exact-name.
- [ ] ustalony próg task success/top5.
- [ ] wyniki z powodami, bez nieopublikowanych danych.

**Backend — endpointy, serwisy, schemas, permissions**

Wydzielić SearchPolicy w istniejącym PersonQueryService; exact canonical/alias boost, tie-breaker ID, reason code w SearchHitSchema; API GET /persons zachować kompatybilne; kontrolować krótkie zapytania i max długość.

**Database — tabele, relacje, indeksy, migracje**

Zachować FTS/trigram indeksy z migracji 0010/0016/0018; modyfikować dopiero po EXPLAIN; gold queries i expected IDs jako wersjonowane fixture, nie tabela produkcyjna.

**Frontend — strony, komponenty, stan, integracja API**

Komunikat powodów dopasowania, wyróżnienie dopasowanego aliasu; zero-results z przykładami i linkiem do korekty; nie generować odpowiedzi NLP.

**Tests — backend, frontend, E2E**

Backend: ranking exact/alias/transliteration/typo i polskie formy; Frontend: bezpieczne highlight, puste wyniki; E2E: realny query set + ręczna ocena MRR/nDCG przed/po.

**Infrastructure**

Powtarzalny benchmark offline w CI lub release check; brak nowej usługi.

**Dependencies**

013 dla realnych klas zapytań; można rozpocząć wywiadami.

**Risk**

Optymalizacja pod małą próbkę; rozdzielić zestaw do strojenia i walidacji.

## FEATURE-009 — Profil jako centrum odpowiedzi i eksploracji

**Grupa:** UX / Discovery. **Faza:** 1. **Priorytet:** P1. **Priority Score:** 52.07.

**Product — problem**

Długie aliasy i teksty utrudniają znalezienie daty, wspomnienia lub źródła.

**User Story**

**As a** czytelnik długiej biografii  
**I want** szybko przejść do właściwej sekcji profilu i powiązanego tematu  
**So that** Docieram do właściwej sekcji i przechodzę do powiązanego kontekstu.

**Wartość i złożoność**

Docieram do właściwej sekcji i przechodzę do powiązanego kontekstu.

Techniczna: **4/10 (średnia)**; dane: **3/10**; utrzymanie: **3/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Najważniejsze fakty widoczne wcześniej niż pełna lista aliasów.
- [ ] TOC działa klawiaturą.
- [ ] cytowany profil ma ID wersji.
- [ ] brak udawanych pustych sekcji mapy/grafu.

**Backend — endpointy, serwisy, schemas, permissions**

PersonPublicProfileSchema z lekkimi sekcjami i quality/source summary; agregację rozszerzać przez public query, bez surowych ORM relacji w payloadzie; v1 używa istniejących danych.

**Database — tabele, relacje, indeksy, migracje**

V1 brak migracji; późniejsza struktura bloków biografii związana z 016 i rewizją. Nie przepisywać wszystkich biografii tylko dla TOC.

**Frontend — strony, komponenty, stan, integracja API**

web/swieci/[slug]: TableOfContents, FactsPanel, SourcesSection, collapsible aliases, linki do kalendarza/zakonu, przycisk cytowania; SSR z małymi client islands; stan anchor w URL.

**Tests — backend, frontend, E2E**

Backend: zgodność pól i widoczności; Frontend: warunkowe sekcje i brak pustych anchorów; E2E mobile: przejście do źródeł w ≤2 działaniach, back do wyników zachowuje filtry.

**Infrastructure**

Brak nowej infrastruktury.

**Dependencies**

002, 010, 012; 018 dla related.

**Risk**

Rozbudowanie profilu do dashboardu; mierzyć czas znalezienia odpowiedzi.

## FEATURE-010 — Wspomnienia osoby i jawne pokrycie kalendarza

**Grupa:** Calendar. **Faza:** 1. **Priorytet:** P1. **Priority Score:** 47.81.

**Product — problem**

Osoba nie ma publicznej listy swoich obchodów; pusty dzień i niepełny katalog mogą być mylone z brakiem obchodu.

**User Story**

**As a** czytelnik sprawdzający datę wspomnienia  
**I want** sprawdzić wspomnienie osoby wraz z kalendarzem i zakresem opracowania  
**So that** Wiem, w jakim kalendarzu i zakresie występuje wpis.

**Wartość i złożoność**

Wiem, w jakim kalendarzu i zakresie występuje wpis.

Techniczna: **4/10 (średnia)**; dane: **5/10**; utrzymanie: **3/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Publiczny profil pokazuje wszystkie aktywne stałe wspomnienia z pochodzeniem.
- [ ] komunikat fixed-only widoczny.
- [ ] daty strefy Europe/Warsaw spójne z today.

**Backend — endpointy, serwisy, schemas, permissions**

GET /persons/{id}/commemorations jako public query; CalendarCoverageSchema w /calendar/calendars lub osobnym endpointcie: coverage_status, fixed_only, edition/description; filtrować published i active. Nie otwierać surowego editorial entries endpointu.

**Database — tabele, relacje, indeksy, migracje**

Wykorzystać Feast/LiturgicalCalendar; początkowo metadane opisowe zakresu; jeśli utrwalane, coverage_status i coverage_note, nie procent oparty tylko na liczbie wpisów.

**Frontend — strony, komponenty, stan, integracja API**

Profil: tabela wspomnień według kalendarzy; dzień/miesiąc: nazwa zakresu i empty state „brak opracowanych wpisów”; rozdzielić martyrologium od normatywnej odpowiedzi.

**Tests — backend, frontend, E2E**

Backend: wiele kalendarzy jednej osoby i wpis nieosobowy; Frontend: pusta data nie oznacza „nikt”; E2E: profil→dzień→profil bez zmiany kalendarza.

**Infrastructure**

Cache per calendar/date i wersja danych; bez silnika reguł w tym przyroście.

**Dependencies**

002, 009; resolver 021 niezależnie później.

**Risk**

Odbiorca może nadal traktować listę jako ordo; test z użytkownikiem liturgicznym.

## FEATURE-011 — Budżety wydajności, paginacja i cache

**Grupa:** Platform. **Faza:** 1. **Priorytet:** P1. **Priority Score:** 39.89.

**Product — problem**

Listy zakonów/historii i szerokie ORM payloady nie mają spójnych granic; Axios nie ma deadline.

**User Story**

**As a** czytelnik i operator  
**I want** otrzymać ograniczoną, szybką odpowiedź także przy dużym katalogu  
**So that** Portal pozostaje responsywny i przewidywalny przy wzroście katalogu.

**Wartość i złożoność**

Portal pozostaje responsywny i przewidywalny przy wzroście katalogu.

Techniczna: **6/10 (średnia)**; dane: **2/10**; utrzymanie: **5/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Wynik load testu i EXPLAIN zapisany.
- [ ] brak wzrostu liczby SQL per karta.
- [ ] bounded lists.
- [ ] stare publiczne dane odświeżone w zadanym budżecie po publikacji.

**Backend — endpointy, serwisy, schemas, permissions**

Paginować członków zakonów, historię i inne nieograniczone kolekcje; list DTO z projekcją pól; deduplikować pobranie profilu metadata/page; timestamp/version cache keys; timeout per outbound call.

**Database — tabele, relacje, indeksy, migracje**

Indeksy tylko z EXPLAIN; stabilny sort po nazwie+id; keyset do eksportu; opcjonalny SearchDocument read model po benchmarku. Pool budget obejmuje wszystkie procesy.

**Frontend — strony, komponenty, stan, integracja API**

API clients web/admin timeout i retry policy tylko dla bezpiecznych read; lazy load historii; React Query invalidation; nie maskować awarii jako pustego katalogu.

**Tests — backend, frontend, E2E**

Backend: query-count 1/20/100, payload budget, query timeout; Frontend: skeleton/error/empty osobno; E2E/load staging: SLO p95 z realistycznym zbiorem i publikacją invalidującą cache.

**Infrastructure**

HTTP/CDN cache; oddzielny cache Redis od brokera gdy trwałość jobów wymagana.

**Dependencies**

008, 004 dla wersjonowanej invalidacji; nie blokować prostego timeoutu.

**Risk**

Przedwczesna optymalizacja; cache leak między admin i public.

## FEATURE-012 — Dostępność i mobilne wykonanie zadań

**Grupa:** UX. **Faza:** 1. **Priorytet:** P1. **Priority Score:** 49.03.

**Product — problem**

Filtry i hero opóźniają dostęp do treści; część pól ma tylko tekst obok, focus bywa niewidoczny.

**User Story**

**As a** czytelnik używający telefonu lub klawiatury  
**I want** wykonać wyszukiwanie i odczyt treści na telefonie oraz klawiaturą  
**So that** Mogę samodzielnie wyszukać i przeczytać profil bez bariery interfejsu.

**Wartość i złożoność**

Mogę samodzielnie wyszukać i przeczytać profil bez bariery interfejsu.

Techniczna: **4/10 (średnia)**; dane: **1/10**; utrzymanie: **3/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Zero krytycznych naruszeń w objętych ekranach.
- [ ] kompletna obsługa klawiaturą.
- [ ] focus widoczny.
- [ ] brak poziomego przewijania w testowanych breakpointach.
- [ ] wynik nie znika pod drawerem.

**Backend — endpointy, serwisy, schemas, permissions**

Bez nowych endpointów; zachować semantyczne błędy walidacji i nazwy pól.

**Database — tabele, relacje, indeksy, migracje**

Bez zmian DB.

**Frontend — strony, komponenty, stan, integracja API**

Skip link i jeden main w web; label wyszukiwania; peer-focus-visible dla checkboxów; mobile filter drawer; label/id/aria-describedby w admin; zarządzanie focus w dialogach i błędach; prefers-reduced-motion.

**Tests — backend, frontend, E2E**

Backend: bez nowych testów dla CSS; Frontend: axe lub równoważny check, kontrast i semantyka etykiet; E2E: keyboard-only i 390 px, 200% zoom, czytnik ekranu dla formularza i listy.

**Infrastructure**

Brak nowych usług; automatyczny accessibility smoke w CI.

**Dependencies**

009 i 007 dla docelowego układu, proste label/focus niezależne.

**Risk**

Automatyczny test nie dowodzi pełnego WCAG; potrzebna próba manualna.

## FEATURE-013 — Analityka sukcesu użytkownika

**Grupa:** Analytics. **Faza:** 0. **Priorytet:** P1. **Priority Score:** 47.59.

**Product — problem**

Brak danych o sukcesie wyszukiwania, zero-results i korzystaniu ze źródeł.

**User Story**

**As a** właściciel produktu  
**I want** mierzyć, czy czytelnik rozwiązał swoje zadanie  
**So that** Podejmuję decyzje na podstawie wykonanych zadań, nie tylko wizyt.

**Wartość i złożoność**

Podejmuję decyzje na podstawie wykonanych zadań, nie tylko wizyt.

Techniczna: **4/10 (średnia)**; dane: **2/10**; utrzymanie: **4/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Baseline 4 tygodnie.
- [ ] zdarzenia udokumentowane.
- [ ] North Star rozróżnia proxy i potwierdzony sukces.
- [ ] dane prywatne nie są wymagane do statystyk.

**Backend — endpointy, serwisy, schemas, permissions**

Event ingestion (własny POST /events lub wybrany produkt) z allowlist schema, anon session_id, event/query class; nie zbierać domyślnie raw text i PII; agregaty search success i zero-results.

**Database — tabele, relacje, indeksy, migracje**

Jeśli własny collector: ProductEvent z datą/typem/małym payload i retencją, indeks time+event; agregaty dzienne. Nie zapisywać pełnych danych użytkownika w domenowej Person DB.

**Frontend — strony, komponenty, stan, integracja API**

Instrumentacja search submitted/results/opened, filters, source click, relation, feedback; session state ograniczony i opisany; panel baseline dla PM.

**Tests — backend, frontend, E2E**

Backend: walidacja eventów, redakcja i retencja; Frontend: jeden event na działanie, bez duplikacji hydration; E2E: ścieżka search→profile→source składa się w poprawny funnel.

**Infrastructure**

Lekki collector/analytics; limit kosztu i dostęp do agregatów, nie szerokich surowych logów.

**Dependencies**

001; krótka decyzja polityki danych.

**Risk**

Proxy może nagradzać długi czas zagubienia; walidacja w badaniach.

## FEATURE-014 — Słowniki patronatów, ikonografii i zawodów

**Grupa:** Knowledge Graph. **Faza:** 2. **Priorytet:** P2. **Priority Score:** 41.03.

**Product — problem**

Patronaty i atrybuty powtarzają się jako tekst; grupy są zbyt szerokie.

**User Story**

**As a** czytelnik szukający patrona lub symbolu  
**I want** wyszukiwać osoby po jednoznacznym patronacie, zawodzie lub atrybucie  
**So that** Odkrywam osoby po spójnym pojęciu i jego synonimach.

**Wartość i złożoność**

Odkrywam osoby po spójnym pojęciu i jego synonimach.

Techniczna: **6/10 (średnia)**; dane: **7/10**; utrzymanie: **5/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Każdy migrowany patronat zachowuje tekst/ID źródłowy.
- [ ] niewyjaśnione mapowania trafiają do review.
- [ ] strony pojęć nie są puste.
- [ ] filtr działa po relacji.

**Backend — endpointy, serwisy, schemas, permissions**

ConceptService; GET /patronages oraz /patronages/{slug}/persons; admin create/update z taxonomy permissions; ConceptSchema i PersonConceptAssignmentCommand z evidence reference; wykorzystać istniejące Occupation.

**Database — tabele, relacje, indeksy, migracje**

PatronageConcept(id,slug,type,labels), ConceptAlias, PersonPatronage; AttributeConcept i PersonAttribute; FK i unique aktywnego assignment; backfill obecnych Patronage do mapowania, nie merge po nazwie bez review.

**Frontend — strony, komponenty, stan, integracja API**

Strony /patronaty/[slug], słownik w admin, wybór po ID zamiast swobodnego powielania; URL query i React Query dla edytora; profile linkują do pojęć.

**Tests — backend, frontend, E2E**

Backend: synonimy, oficjalny vs zwyczajowy i relacje M:N; Frontend: rozróżnianie homonimów; E2E: patron lekarzy→osoba→źródło przypisania.

**Infrastructure**

PostgreSQL; brak nowego silnika.

**Dependencies**

002; schema pojęć odblokowuje pełne fasety 007. Evidence 016 docelowo; w v1 zachować istniejące źródła.

**Risk**

Nadmierna normalizacja i utrata lokalnej tradycji; dopuszczać kwalifikatory.

## FEATURE-015 — Historyczne daty, męczeństwo i uznanie kultu

**Grupa:** Data / Timeline. **Faza:** 2. **Priorytet:** P2. **Priority Score:** 36.40.

**Product — problem**

Tekstowe daty i pojedyncza kanonizacja nie oddają niepewności, dawnych trybów kultu ani męczeństwa.

**User Story**

**As a** badacz i czytelnik zaawansowany  
**I want** odróżniać dokładne i przybliżone daty oraz rodzaje uznania kultu  
**So that** Mogę filtrować daty i rozumieć podstawę uznania bez fałszywej precyzji.

**Wartość i złożoność**

Mogę filtrować daty i rozumieć podstawę uznania bez fałszywej precyzji.

Techniczna: **7/10 (wysoka)**; dane: **8/10**; utrzymanie: **5/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Żaden backfill nie dopowiada precyzji.
- [ ] stare odpowiedzi API pozostają spójne.
- [ ] męczeństwo ma źródło i kwalifikację.
- [ ] rozbieżności nie są nadpisywane.

**Backend — endpointy, serwisy, schemas, permissions**

HistoricalEventService i HistoricalDateSchema; GET /persons/{id}/events; admin commands dla recognition/martyrdom z persons:update/review; walidacja przedziałów i rodzaju zdarzenia; kompatybilne projekcje Canonization/Beatification.

**Database — tabele, relacje, indeksy, migracje**

HistoricalEvent, PersonEvent(role), HistoricalDate(earliest/latest,precision,calendar,label); RecognitionEvent subtype lub kontrolowane pola; FK source/evidence, indeks zakresów; backfill exact/year bez zgadywania dni.

**Frontend — strony, komponenty, stan, integracja API**

FactDate z etykietą „około/przed/po”; editor dat przedziałowych i uznań; profil sekcja Kult; stan RHF, query cache zdarzeń.

**Tests — backend, frontend, E2E**

Backend: nieznane/przybliżone daty, konflikty, rok bez dnia, kilka tradycji; Frontend: display bez 1 stycznia; E2E: filtr męczennicy XX wieku na zatwierdzonych zdarzeniach.

**Infrastructure**

PostgreSQL; opcjonalne range indexes według pomiaru.

**Dependencies**

003; w fazie 2 wystarczy źródło istniejące i referencja zdarzenia. Minimalne Evidence 016 wdrożyć przed pełną normalizacją dat; pełny UI twierdzeń może powstać w fazie 3.

**Risk**

Błędna semantyka historyczna i narzucenie współczesnej procedury dawnym kultom.

## FEATURE-016 — Twierdzenia, cytowania i rozbieżności

**Grupa:** Sources / Knowledge Graph. **Faza:** 3. **Priorytet:** P2. **Priority Score:** 35.55.

**Product — problem**

PersonSource dokumentuje rekord, ale nie konkretne zdanie ani relację.

**User Story**

**As a** badacz weryfikujący konkretny fakt  
**I want** sprawdzić źródło konkretnej informacji i porównać rozbieżne wersje  
**So that** Wiem, które źródło wspiera datę, patronat lub opis i gdzie źródła się różnią.

**Wartość i złożoność**

Wiem, które źródło wspiera datę, patronat lub opis i gdzie źródła się różnią.

Techniczna: **8/10 (wysoka)**; dane: **9/10**; utrzymanie: **7/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Pilotaż 20 profili: daty, patronaty i uznanie mają evidence.
- [ ] brak przypisu do nieistniejącego bloku.
- [ ] status pewności ma kryteria, a nie stały procent.
- [ ] export zachowuje provenance.

**Backend — endpointy, serwisy, schemas, permissions**

AssertionService i EvidenceService; GET /persons/{id}/assertions, /assertions/{id}/evidence; chronione commands create/review z revision i predicate whitelist; public DTO bez editor_notes; supports/contradicts/mentions.

**Database — tabele, relacje, indeksy, migracje**

Assertion(person_id,predicate,typed_value,qualifiers,status,revision_id), Evidence(source_id,assertion_id,locator,quote,relation,reviewed_at), ContentCitation(block_id,revision_id,evidence_id); Source identity/fasada dla Bibliography/HistoricalSource; CHECK typu wartości, FK i indeks assertion/person.

**Frontend — strony, komponenty, stan, integracja API**

Inline citation anchors i drawer ze źródłem; porównanie wariantów dat; edytor przypisu przy polu/bloku, source picker; query keyed by revision; SSR public.

**Tests — backend, frontend, E2E**

Backend: public/private i FK, alternatywne wartości, publikacja tylko review; Frontend: stabilność anchor po edycji; E2E: fakt→dwa sprzeczne źródła→cytowanie konkretnej wersji.

**Infrastructure**

Bez graph DB; opcjonalny link checker jako job po 037.

**Dependencies**

002, 004, 003.

**Risk**

Koszt redakcyjny i licencje cytatów; zacząć od kilku predykatów.

## FEATURE-017 — Miejsca i historyczne role geograficzne

**Grupa:** Geography / Knowledge Graph. **Faza:** 3. **Priorytet:** P2. **Priority Score:** 35.27.

**Product — problem**

Place istnieje, ale lokalnie brak danych i relacji działalności/pochówku.

**User Story**

**As a** badacz lokalny i pielgrzym  
**I want** odnaleźć osoby związane z miejscem w określonej roli i czasie  
**So that** Odkrywam ludzi związanych z miejscem z opisem rodzaju i czasu związku.

**Wartość i złożoność**

Odkrywam ludzi związanych z miejscem z opisem rodzaju i czasu związku.

Techniczna: **6/10 (średnia)**; dane: **9/10**; utrzymanie: **6/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Pilotaż co najmniej 30 zweryfikowanych powiązań dla jednej kolekcji.
- [ ] narodowość oddzielona od geografii.
- [ ] źródło i dokładność każdego publikowanego punktu.

**Backend — endpointy, serwisy, schemas, permissions**

Rozszerzyć GeographyService; GET /places/{slug} i /places/{id}/persons z role filters; PersonPlaceRoleCommand z evidence/date; permissions geography:create/update i persons:update.

**Database — tabele, relacje, indeksy, migracje**

Place slug i external IDs, PlaceName z okresem, PersonPlaceRole(person_id,place_id,role,date_range,evidence_id); FK i unique relacji z kwalifikacją; koordynaty z accuracy/source. Backfill birth/death FK bez zgadywania.

**Frontend — strony, komponenty, stan, integracja API**

Publiczny profil miejsca, lista powiązań; admin picker z nazwą historyczną/obecną i source; state URL roli/okresu, SSR. Mapa nie jest wymagana w v1.

**Tests — backend, frontend, E2E**

Backend: typ roli, data, konflikty identyfikacji miejsc o tej samej nazwie; Frontend: brak koordynatów; E2E: osoba→miejsce→inne osoby według roli.

**Infrastructure**

Geokoder opcjonalny do sugestii; manual review, bez automatycznego geocoding-to-publish.

**Dependencies**

015, 016, 023 dla importu skali.

**Risk**

Anachronizmy granic i pomylenie miejsc; nie przypisywać współczesnego kraju jako narodowości.

## FEATURE-018 — Powiązane osoby i eksplorator relacji

**Grupa:** Discovery / Graph. **Faza:** 2. **Priorytet:** P2. **Priority Score:** 43.84.

**Product — problem**

Osoba→zakon działa, ale relacje z innymi osobami i wyjaśnione podobieństwo nie.

**User Story**

**As a** czytelnik pogłębiający temat  
**I want** odkrywać powiązane osoby z wyjaśnieniem relacji  
**So that** Przechodzę do kolejnego użytecznego profilu i widzę przyczynę powiązania.

**Wartość i złożoność**

Przechodzę do kolejnego użytecznego profilu i widzę przyczynę powiązania.

Techniczna: **5/10 (średnia)**; dane: **6/10**; utrzymanie: **4/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Każde jawne powiązanie ma rodzaj i źródło.
- [ ] podobieństwo jest oznaczone jako rekomendacja.
- [ ] limit 50 nodes i depth2.
- [ ] lista dostępna bez grafiki.

**Backend — endpointy, serwisy, schemas, permissions**

GET /persons/{id}/related?type&limit oraz /persons/{id}/relations; RelationQueryService używa PersonRelationship/Order/Concept, published filter obu końców; RelatedHit z reason/evidence, nie tylko cosine.

**Database — tabele, relacje, indeksy, migracje**

Wykorzystać PersonRelationship; dodać evidence_id/date zakres gdy wymagane; indeks obu końców i typu; CHECK brak self relation dla zakazanych typów; nie materializować all contemporary pairs.

**Frontend — strony, komponenty, stan, integracja API**

Profil: 3–6 kart „powiązany przez zakon/patronat/nauczyciela”; /odkrywaj/relacje opcjonalnie listowy explorer z max depth2; URL przechowuje wybrane typy.

**Tests — backend, frontend, E2E**

Backend: directionality/bidirectional, draft na dowolnym końcu, bounds; Frontend: widoczne reason; E2E: dwa skoki i powrót bez utraty kontekstu.

**Infrastructure**

PostgreSQL; żadnej bazy grafowej.

**Dependencies**

014, 016; v1 wspólny zakon z istniejących danych.

**Risk**

Mylenie współczesności/podobieństwa z historyczną znajomością.

## FEATURE-019 — Historyczna oś czasu

**Grupa:** Timeline. **Faza:** 3. **Priorytet:** P3. **Priority Score:** 32.83.

**Product — problem**

Linki epok nie pokazują wydarzeń i współczesności postaci.

**User Story**

**As a** uczeń i badacz  
**I want** zobaczyć wydarzenia i osoby na wspólnej osi czasu  
**So that** Rozumiem życie osoby w kontekście zdarzeń i powstawania wspólnot.

**Wartość i złożoność**

Rozumiem życie osoby w kontekście zdarzeń i powstawania wspólnot.

Techniczna: **6/10 (średnia)**; dane: **8/10**; utrzymanie: **5/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Co najmniej jedna kuratorowana oś gotowa merytorycznie.
- [ ] „contemporary” nie znaczy spotkanie.
- [ ] keyboard/list equivalence.
- [ ] bounded payload.

**Backend — endpointy, serwisy, schemas, permissions**

GET /timeline?from&to&person/order/place z bounded range; TimelineQueryService i TimelineItem(type,date_range,uncertainty,source); tylko opublikowane zdarzenia.

**Database — tabele, relacje, indeksy, migracje**

Wykorzystać HistoricalEvent/PersonEvent i daty z 015; indeks zakresów/roku; nie tworzyć kopii Person na każdy widok osi.

**Frontend — strony, komponenty, stan, integracja API**

/os-czasu: zoom okresu, lista alternatywna, legendy niepewności; stan zakresu/filtrów w URL; lazy client visualization nad SSR listą.

**Tests — backend, frontend, E2E**

Backend: overlap dat i duże zakresy; Frontend: przedziały niepewne i nakładanie etykiet; E2E: filtrowanie okresu i przejście do źródła zdarzenia.

**Infrastructure**

Brak nowych usług; limit liczby zdarzeń, agregacja przy szerokim zakresie.

**Dependencies**

015, 016, 018.

**Risk**

Efektowna wizualizacja bez danych i pozorna dokładność.

## FEATURE-020 — Mapa źródłowa miejsc i pielgrzymek

**Grupa:** Maps. **Faza:** 3. **Priorytet:** P3. **Priority Score:** 31.10.

**Product — problem**

Brak miejsc/geokodowania uniemożliwia wartościową mapę.

**User Story**

**As a** pielgrzym i czytelnik historii  
**I want** przejrzeć udokumentowane miejsca na mapie i w dostępnej liście  
**So that** Widzę miejsca związane z osobą i wiem, na czym opiera się lokalizacja.

**Wartość i złożoność**

Widzę miejsca związane z osobą i wiem, na czym opiera się lokalizacja.

Techniczna: **7/10 (wysoka)**; dane: **9/10**; utrzymanie: **7/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Mapa nie startuje na pustym katalogu.
- [ ] pilotaż geograficzny ma źródła i listową alternatywę.
- [ ] nie sugeruje aktualnej dostępności sanktuarium na podstawie samej relacji.

**Backend — endpointy, serwisy, schemas, permissions**

GET /places/map?bbox&role&person/order z limitami i GeoPointSchema; cluster projection w GeographyQueryService; miejsca wyłącznie z reviewed coordinates; nie prosić o geolokalizację w podstawowym użyciu.

**Database — tabele, relacje, indeksy, migracje**

Wykorzystać 017 coordinates/accuracy/source; indeks bbox lub PostGIS tylko jeśli pomiar i zakres tego wymagają; information_checked_at dla danych odwiedzin, nie utożsamiać z datą związku historycznego.

**Frontend — strony, komponenty, stan, integracja API**

/mapa: mapa+synchroniczna lista, filtry roli, profil miejsca; URL bbox/filters; panel wyjaśnia dokładność i datę weryfikacji. Trasy najpierw kuratorowane, bez własnego routingu.

**Tests — backend, frontend, E2E**

Backend: bbox bounds, osoby draft nie widoczne; Frontend: mapa bez współrzędnych i keyboard list; E2E: punkt→źródło miejsca→profil osoby.

**Infrastructure**

Provider map tiles z ograniczeniem kosztu i atrybucją; cache zgodny z warunkami wybranego dostawcy.

**Dependencies**

017, 016, 012.

**Risk**

Koszt danych, błędna lokalizacja oraz starzenie praktycznych informacji podróżniczych.

## FEATURE-021 — Wersjonowany resolver roku liturgicznego

**Grupa:** Calendar. **Faza:** 4. **Priorytet:** P2. **Priority Score:** 33.75.

**Product — problem**

Feast z datą stałą i rank nie rozstrzyga roku, przeniesień i kalendarzy własnych.

**User Story**

**As a** osoba przygotowująca liturgię  
**I want** otrzymać rozstrzygnięty obchód dla konkretnego roku i zakresu kalendarza  
**So that** Otrzymuję wynik dla konkretnej daty, edycji i zakresu z wyjaśnieniem.

**Wartość i złożoność**

Otrzymuję wynik dla konkretnej daty, edycji i zakresu z wyjaśnieniem.

Techniczna: **9/10 (wysoka)**; dane: **10/10**; utrzymanie: **8/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Każda reguła ma źródło, edycję i test.
- [ ] brak heurystycznego rozstrzygania konfliktów.
- [ ] nierozstrzygnięty dzień wstrzymuje odpowiedź normatywną.
- [ ] stare fixed API kompatybilne.

**Backend — endpointy, serwisy, schemas, permissions**

Zrealizować ADR-004: CalendarResolver czysty/deterministyczny; GET /calendar/resolved/day/{date}?calendar_code&edition; CalendarResolutionSchema z observed/transferred/omitted i provenance; edycję/reguły zatwierdza uprawniony recenzent.

**Database — tabele, relacje, indeksy, migracje**

CalendarEdition, ObservanceRule(kind,typed_params,precedence_code,source), CalendarException, ResolvedOccurrence; FK i zakaz nakładających się obowiązujących edycji; migration Feast fixed_date z zachowaniem ID i źródeł.

**Frontend — strony, komponenty, stan, integracja API**

Kalendarz: wybór zakresu/edycji, wyjaśnienie transferu i status nierozstrzygnięty; panel redakcyjny wersji reguł; state URL year/calendar. Martyrologium jako odrębna lista.

**Tests — backend, frontend, E2E**

Backend: golden corpus zatwierdzony przez liturgistę, lata przestępne, Wielkanoc, kolizje/transfery; Frontend: brak mylenia katalogu z ordo; E2E: ten sam rok+edition zawsze ten sam wynik.

**Infrastructure**

Job precompute roku i cache według immutable edition; nie wykonywać dowolnych formuł wpisanych przez redaktora.

**Dependencies**

010, 015, 016, 022 i recenzent liturgiczny.

**Risk**

Wysokie ryzyko domenowe; nie wyprowadzać pierwszeństwa wyłącznie z FeastRank.

## FEATURE-022 — Przydziały recenzji, diff, rollback i planowanie

**Grupa:** Editorial. **Faza:** 4. **Priorytet:** P2. **Priority Score:** 36.26.

**Product — problem**

Kolejka nie ma pełnego assignment i komentarzy do zmian; historia nie jest przeglądem rewizji.

**User Story**

**As a** recenzent i wydawca  
**I want** przydzielić recenzję, obejrzeć diff i bezpiecznie opublikować wybraną wersję  
**So that** Wiem, co sprawdzić, komu zwrócić poprawki i jak odtworzyć wcześniejsze wydanie.

**Wartość i złożoność**

Wiem, co sprawdzić, komu zwrócić poprawki i jak odtworzyć wcześniejsze wydanie.

Techniczna: **7/10 (wysoka)**; dane: **4/10**; utrzymanie: **5/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Żadna recenzja nie przeskakuje między wersjami.
- [ ] wszystkie decyzje audytowane.
- [ ] rollback nie kasuje historii.
- [ ] harmonogram powtarzalny i anulowalny.

**Backend — endpointy, serwisy, schemas, permissions**

ReviewService; POST /revisions/{id}/assign, /comments, /approve, /schedule, /rollback; GET /revisions/{id}/diff?base; ReviewCommand z expected_version, persons:review/publish; return-to-author wymaga komentarza.

**Database — tabele, relacje, indeksy, migracje**

ReviewAssignment, ReviewComment(block/field_path), ReviewDecision, ScheduledPublication; UNIQUE aktywnego assignment w ustalonym zakresie, indeks deadline/status; FK revision; immutable decyzja wskazuje konkretną wersję.

**Frontend — strony, komponenty, stan, integracja API**

Queue: moje zadania, przeterminowane, diff przed/po z przypisami; dialog rollback preview; state filters URL, mutation cache invalidation; kalendarz terminu publikacji z timezone.

**Tests — backend, frontend, E2E**

Backend: autor/recenzent/uprawnienia, approval konkretnej wersji, idempotent schedule; Frontend: komentarz do właściwej wersji; E2E: return→poprawka→approve→publish→rollback nowa rewizja.

**Infrastructure**

Worker planowanych publikacji dopiero z 037; retry i outbox 036.

**Dependencies**

004, 003, 037; 036 przed automatycznym schedule.

**Risk**

Biurokratyzacja pracy małego zespołu; zapewnić prosty tryb jednoosobowy.

## FEATURE-023 — Staging i idempotentny pipeline importu

**Grupa:** Data platform. **Faza:** 4. **Priorytet:** P2. **Priority Score:** 32.51.

**Product — problem**

Istnieją różne importy JSON/CLI, lecz brak wspólnej kwarantanny i trwałego raportu joba.

**User Story**

**As a** redaktor importujący materiał  
**I want** obejrzeć plan importu i ponowić go bez tworzenia duplikatów  
**So that** Sprawdzam zmiany przed zastosowaniem i bezpiecznie ponawiam import.

**Wartość i złożoność**

Sprawdzam zmiany przed zastosowaniem i bezpiecznie ponawiam import.

Techniczna: **7/10 (wysoka)**; dane: **8/10**; utrzymanie: **6/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Ponowiony identyczny batch nie tworzy nowych osób.
- [ ] każda zmiana ma pochodzenie i wynik walidacji.
- [ ] import nie publikuje automatycznie.
- [ ] da się odtworzyć przebieg po awarii.

**Backend — endpointy, serwisy, schemas, permissions**

ImportService: POST /imports/validate, /imports, /imports/{id}/apply; GET /imports/{id}; ImportManifestSchema z format_version/hash/source/license, record result i candidate matches; import permissions; apply tylko zatwierdzone wiersze do draft revisions.

**Database — tabele, relacje, indeksy, migracje**

ImportJob, ImportItem, ImportMapping, ImportError; unique idempotency_key+source scope, FK do target/revision; staging raw minimalny z retencją; transakcja per logiczny agregat, nie tysiące rekordów w jednym request.

**Frontend — strony, komponenty, stan, integracja API**

Admin import wizard: preview diff, nierozstrzygnięte ID, errors download, retry tylko nieudanych; state job ID z polling; reuse istniejący validator profilu i zakonów.

**Tests — backend, frontend, E2E**

Backend: dry-run zero domain writes, ponowienie bez duplikatów, częściowa porażka i rollback agregatu; Frontend: brak utraty raportu po reload; E2E: import→review→publish.

**Infrastructure**

Celery lub prosty worker, durable queue, storage manifestu; limits i cancellation.

**Dependencies**

004, minimalne źródła 016 i 037; sugestie 024 są opcjonalne dla pierwszego stagingu, nierozstrzygnięte rekordy można mapować ręcznie.

**Risk**

Masowe utrwalenie błędów i praw do treści; review przed apply.

## FEATURE-024 — Deduplikacja i bezpieczne scalanie tożsamości

**Grupa:** Data quality. **Faza:** 4. **Priorytet:** P2. **Priority Score:** 30.82.

**Product — problem**

Obecne wykrywanie to heurystyka znormalizowanych nazw, bez pełnego entity resolution i merge.

**User Story**

**As a** redaktor danych  
**I want** porównać i scalić potwierdzone duplikaty z zachowaniem źródeł  
**So that** Rozróżniam homonimy i łączę tylko potwierdzone duplikaty z historią decyzji.

**Wartość i złożoność**

Rozróżniam homonimy i łączę tylko potwierdzone duplikaty z historią decyzji.

Techniczna: **7/10 (wysoka)**; dane: **7/10**; utrzymanie: **5/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Każdy merge ma jawne uzasadnienie.
- [ ] żadne źródło nie znika.
- [ ] preview odpowiada wynikowi lub zwraca conflict.
- [ ] możliwe odtworzenie mapowania.

**Backend — endpointy, serwisy, schemas, permissions**

EntityResolutionService: GET /quality/duplicate-candidates, POST /persons/merge/preview, /merge; evidence features name/date/order/external ID; MergeCommand z expected versions i wybranym survivor; permission osobne persons:merge.

**Database — tabele, relacje, indeksy, migracje**

MergeDecision, EntityRedirect; unique external_id namespace/value po sprawdzeniu zakresu; transakcyjne przepięcie relacji z zachowaniem wersji; archiwum mapowania, brak hard delete.

**Frontend — strony, komponenty, stan, integracja API**

ComparePersons: różnice, źródła, powiązania i plan kolizji; ręczny wybór pól; React Query preview przed commit; linki do historycznych ID działają.

**Tests — backend, frontend, E2E**

Backend: kolizje relacji, idempotent merge, równoczesny zapis; Frontend: homonimy z różnych epok; E2E: duplikat→preview→merge→stary URL→survivor, dowód zachowany.

**Infrastructure**

Batch kandydatów jako job dla dużego zbioru; AI tylko opcjonalny scorer.

**Dependencies**

004, 016; niezależny preview/merge może powstać przed 023 i być później użyty przez importer.

**Risk**

Fałszywe scalenie dwóch osób jest droższe niż pozostawienie duplikatu.

## FEATURE-025 — Kolejki jakości i odpowiedzialność za dane

**Grupa:** Data quality. **Faza:** 2. **Priorytet:** P1. **Priority Score:** 42.09.

**Product — problem**

Kompletność i stałe confidence mogą być odczytywane jako prawdziwość, a braki nie mają właściciela.

**User Story**

**As a** redaktor prowadzący  
**I want** przypisać właściciela konkretnemu problemowi jakości i śledzić naprawę  
**So that** Widzę konkretne problemy, zakres pokrycia i kolejność pracy.

**Wartość i złożoność**

Widzę konkretne problemy, zakres pokrycia i kolejność pracy.

Techniczna: **5/10 (średnia)**; dane: **5/10**; utrzymanie: **4/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] 34 legacy braki mają listę i właściciela.
- [ ] każda ocena ma wersję reguły i wyjaśnienie.
- [ ] ręczne zamknięcie nie ukrywa niepoprawionego źródła bez powodu.

**Backend — endpointy, serwisy, schemas, permissions**

Rozwinąć EditorialQualityPolicy: source completeness osobno od content completeness; QualityIssueSchema z rule_version, field, evidence i severity; GET /quality/issues paginated, PATCH assignment/status; nie mieszać rule score z AI probability.

**Database — tabele, relacje, indeksy, migracje**

QualityIssue przy potrzebie trwałego assignment, resolution i waivers; indeks status/owner/severity; reguły obliczalne nie wymagają utrwalania każdej oceny przy każdym odczycie.

**Frontend — strony, komponenty, stan, integracja API**

Quality dashboard: kategoria, właściciel, wyjaśnienie reguły, zakres danych; usunąć fałszywy confidence; stan filtrów URL, revalidate po poprawce.

**Tests — backend, frontend, E2E**

Backend: te same blockery co publish policy, source deleted, conflict dat; Frontend: etykiety kompletność/recenzja; E2E: problem→poprawka→zniknięcie issue i zachowanie audit trail.

**Infrastructure**

Ciężkie walidacje okresowe przez job; v1 zapytania SQL.

**Dependencies**

001, 003, 013; 016 dla reguł twierdzeń.

**Risk**

Goodhart: dopisywanie treści tylko dla wyniku; mierzyć próbki jakości merytorycznej.

## FEATURE-026 — Trwałe propozycje AI i provenance

**Grupa:** AI / Editorial. **Faza:** 5. **Priorytet:** P2. **Priority Score:** 29.95.

**Product — problem**

Obecne ai_summary/ai_tags nie przechowują pełnej historii propozycji i wersji wejścia.

**User Story**

**As a** redaktor korzystający z asysty AI  
**I want** poznać pochodzenie sugestii AI i zatwierdzić ją względem właściwej wersji  
**So that** Wiem, jak powstała sugestia i czy nadal pasuje do aktualnego źródła.

**Wartość i złożoność**

Wiem, jak powstała sugestia i czy nadal pasuje do aktualnego źródła.

Techniczna: **6/10 (średnia)**; dane: **5/10**; utrzymanie: **7/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] 100% nowych propozycji ma provenance.
- [ ] decyzja zapisuje wynik i powód.
- [ ] tekst zewnętrzny nie może zmienić instrukcji/system tools.
- [ ] limity kosztu testowane.

**Backend — endpointy, serwisy, schemas, permissions**

AISuggestionService: generation tworzy record z input_revision/hash, model/prompt_version i kosztami; accept/reject wymaga expected revision; source excerpts traktować jako dane; public AI generation zablokowane; dotychczasowe endpointy kompatybilne.

**Database — tabele, relacje, indeksy, migracje**

AISuggestion(id,person_id,input_revision_id,kind,provider,model,prompt_version,output,status,cost_tokens,created_at,decided_by), AIJob; indeks pending/kind i unique dedup hash; stare pola jako adapter do czasu migracji.

**Frontend — strony, komponenty, stan, integracja API**

AI center: aktualna/stara propozycja, fragment źródła, diff, edytuj przed akceptacją; brak arbitralnego procentu; query keyed suggestion ID i job status.

**Tests — backend, frontend, E2E**

Backend: stale suggestion nie nadpisuje nowej treści, retry bez duplikatu, budget/disabled provider; Frontend: accept/reject i status stale; E2E: mock provider→review→draft revision, nigdy auto publish.

**Infrastructure**

Worker, durable queue, provider budget/timeouts i model allowlist.

**Dependencies**

004, 016 minimalne, 037/038.

**Risk**

Halucynacje i prompt injection; review i ograniczony scope narzędzi.

## FEATURE-027 — Wersjonowane hybrid search

**Grupa:** AI / Search. **Faza:** 5. **Priorytet:** P3. **Priority Score:** 31.04.

**Product — problem**

Semantic API istnieje, ale jedna przestrzeń 1536, brak wersji tekstu i połączenia z rankingiem publicznym.

**User Story**

**As a** czytelnik szukający po znaczeniu  
**I want** wyszukiwać po znaczeniu przy zachowaniu dokładności nazw i filtrów  
**So that** Znajduję relewantną postać nawet bez dokładnej nazwy.

**Wartość i złożoność**

Znajduję relewantną postać nawet bez dokładnej nazwy.

Techniczna: **7/10 (wysoka)**; dane: **7/10**; utrzymanie: **7/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Gold set pokazuje poprawę istotną dla produktu.
- [ ] identyczny model dla query i corpus.
- [ ] nowe publikacje aktualizowane w budżecie.
- [ ] awaria AI nie wyłącza keyword search.

**Backend — endpointy, serwisy, schemas, permissions**

AIVectorService filtrować model/version/locale i published revision; HybridSearchService łączy keyword+vector ranks; GET /search?mode=hybrid z bounded filters; fallback keyword przy awarii; query cost/rate limits.

**Database — tabele, relacje, indeksy, migracje**

PersonEmbedding rozszerzyć o revision_id,locale,content_hash,embedding_space_id,status; unique klucza przestrzeni i rewizji; model-specific table/index gdy wymiary inne; równoległy rebuild i cutover bez mieszania modeli.

**Frontend — strony, komponenty, stan, integracja API**

Wyniki publiczne ze wskazaniem dopasowania tematycznego; filtry egzekwowane jak keyword; URL mode, brak osobnego chat UI; obserwowalny fallback bez błędnego komunikatu.

**Tests — backend, frontend, E2E**

Backend: model/dimension mismatch, stale vectors, public visibility, filtered recall; Frontend: loading/error/fallback; E2E: benchmark gold przed/po, brak regresji exact-name.

**Infrastructure**

pgvector pozostaje; HNSW/IVFFlat tylko po benchmarku, nie automatycznie; job rebuild i lag metric.

**Dependencies**

008, 014, 016, 026, 037.

**Risk**

Wysoki koszt przy niskiej korzyści, nieświeże wektory i filtrowanie obniżające recall.

## FEATURE-028 — Natural language do jawnych filtrów

**Grupa:** AI / Discovery. **Faza:** 5. **Priorytet:** P3. **Priority Score:** 33.00.

**Product — problem**

FTS nie interpretuje „polscy męczennicy XX wieku” jako relacji i zakresu.

**User Story**

**As a** czytelnik z wielokryterialnym pytaniem  
**I want** przełożyć moje pytanie na widoczne i edytowalne kryteria wyszukiwania  
**So that** Widzę zrozumiałą interpretację zapytania i mogę ją poprawić.

**Wartość i złożoność**

Widzę zrozumiałą interpretację zapytania i mogę ją poprawić.

Techniczna: **7/10 (wysoka)**; dane: **8/10**; utrzymanie: **7/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Nigdy nie wykonuje model-generated SQL.
- [ ] każde kryterium widoczne i edytowalne.
- [ ] user nie otrzymuje listy jako kompletnej przy brakującym typie danych.

**Backend — endpointy, serwisy, schemas, permissions**

POST /search/interpret z NaturalLanguageQuery; wynik SearchIntentSchema zawiera tylko dozwolone country relation/order/occupation/event/date range i warnings. Model nie generuje SQL; normalny SearchService waliduje i wykonuje filtry.

**Database — tabele, relacje, indeksy, migracje**

Brak nowej domenowej tabeli; opcjonalny ephemeral cache interpretacji z wersją słownika; nie utrwalać prywatnych raw pytań domyślnie.

**Frontend — strony, komponenty, stan, integracja API**

Pod search input: „Rozumiem: …” z chips do edycji; niejednoznaczne „z Polski” wymaga doprecyzowania relacji; state URL zatwierdzonych filtrów, fallback do zwykłego search.

**Tests — backend, frontend, E2E**

Backend: nieznane enumy/ID, injection, niejednoznaczne daty, impossible filters; Frontend: korekta interpretacji; E2E: 50 ręcznie ocenionych pytań, jawne abstention dla brakujących danych.

**Infrastructure**

Provider z timeout/budget lub deterministyczny parser w pierwszym zakresie.

**Dependencies**

007, 014, 015, 017; 027 opcjonalne, parser nie wymaga embeddingów.

**Risk**

Błędna interpretacja przy pozornie trafnym wyniku; mierzyć precision intencji.

## FEATURE-029 — Źródłowe Q&A z odmową odpowiedzi

**Grupa:** AI / Research. **Faza:** 5. **Priorytet:** P3. **Priority Score:** 22.86.

**Product — problem**

Brak narzędzia odpowiedzi przekrojowej; sam chatbot mógłby generować niepoparte twierdzenia.

**User Story**

**As a** czytelnik porównujący informacje  
**I want** otrzymać odpowiedź opartą na fragmentach źródeł lub informację o braku podstaw  
**So that** Otrzymuję odpowiedź z cytowaniami lub jasną informacją o braku podstaw.

**Wartość i złożoność**

Otrzymuję odpowiedź z cytowaniami lub jasną informacją o braku podstaw.

Techniczna: **9/10 (wysoka)**; dane: **9/10**; utrzymanie: **9/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Każde istotne twierdzenie ma wskazany fragment.
- [ ] brak materiału powoduje abstention.
- [ ] pilot nie uruchamia się bez gold eval i ustalonego akceptowalnego odsetka błędów.

**Backend — endpointy, serwisy, schemas, permissions**

POST /research/questions, AnswerSchema(claims,citations,uncertainties,abstained); retrieval tylko published revisions i Evidence; validate citation IDs i support mapping; bez narzędzi zapisujących; scopes/rate/budget.

**Database — tabele, relacje, indeksy, migracje**

AnswerRun z minimalnymi audit metadata i wersją retrieval/model; citation revision IDs; bez domyślnego magazynowania pełnych prywatnych pytań; retencja.

**Frontend — strony, komponenty, stan, integracja API**

Pilotaż /badania: answer/citation pairs, alternatywne źródła i „nie wiem”; lista znalezionych materiałów zawsze dostępna; session state bez automatycznego public sharing.

**Tests — backend, frontend, E2E**

Backend: cited passage exists, private sources excluded, injection/abstention; Frontend: source passage navigation; E2E/eval: groundedness, attribution, unsupported claim rate i koszt na pytanie.

**Infrastructure**

Retrieval + provider worker/streaming z limitami; monitoring jakości i możliwością wyłączenia.

**Dependencies**

016, 026, 027 i potwierdzony popyt badawczy.

**Risk**

Wysokie ryzyko halucynacji i pozornych przypisów; ostatni etap AI.

## FEATURE-030 — Lokalizacja produktu i rewizje tłumaczeń

**Grupa:** Editorial / Internationalization. **Faza:** 4. **Priorytet:** P2. **Priority Score:** 29.83.

**Product — problem**

UI obsługuje tylko PL; tłumaczenia w API są, ale edycja zależy od draft całej osoby.

**User Story**

**As a** tłumacz i czytelnik EN  
**I want** opracować i czytać niezależną wersję językową powiązaną z oryginałem  
**So that** Czytam i tłumaczę spójną wersję językową bez wycofywania polskiej publikacji.

**Wartość i złożoność**

Czytam i tłumaczę spójną wersję językową bez wycofywania polskiej publikacji.

Techniczna: **6/10 (średnia)**; dane: **8/10**; utrzymanie: **7/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Tłumaczenie wskazuje wersję źródłową.
- [ ] fallback jawny.
- [ ] UI i treść nie mieszają się niekontrolowanie.
- [ ] „name_en” nie powstaje przez kopiowanie PL z AI tags.

**Backend — endpointy, serwisy, schemas, permissions**

Rozszerzyć PersonTranslationService do translation revision/source revision; locale negotiation i fallback metadata; translation permissions już istnieją; query może czytać wybrany published language.

**Database — tabele, relacje, indeksy, migracje**

TranslationRevision(source_revision_id,language,status,translated_by,reviewed_by), unique person/locale/revision; stopniowe wycofanie dual-write legacy pól po parity; brak automatycznego założenia pełności 116 rekordów.

**Frontend — strony, komponenty, stan, integracja API**

Dedykowana sekcja admin tłumaczeń; słownik UI en, routing locale i language switch; SSR metadata/hreflang tylko dla rzeczywiście opublikowanych przekładów; state revision i locale.

**Tests — backend, frontend, E2E**

Backend: fallback chain, source changed→stale translation, draft nie przecieka; Frontend: długość tłumaczeń/formaty dat; E2E: EN publish bez wycofania PL i poprawny hreflang.

**Infrastructure**

Brak nowych usług; asysta AI opcjonalna po 026.

**Dependencies**

004, 006, 022; pilotaż EN po ocenie popytu.

**Risk**

Dual source of truth i błędy terminologii; nie wdrażać wielu języków naraz.

## FEATURE-031 — Kuratorowane kolekcje tematyczne

**Grupa:** Education / Discovery. **Faza:** 2. **Priorytet:** P2. **Priority Score:** 43.04.

**Product — problem**

Brak wejścia do tematu bardziej znaczącego niż szeroka era lub grupa patronatów.

**User Story**

**As a** nauczyciel i zainteresowany historią  
**I want** poznawać temat przez uporządkowaną kolekcję profili  
**So that** Czytam uporządkowany zestaw osób z wprowadzeniem i źródłami.

**Wartość i złożoność**

Czytam uporządkowany zestaw osób z wprowadzeniem i źródłami.

Techniczna: **4/10 (średnia)**; dane: **6/10**; utrzymanie: **4/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Pilotaż 3–5 kolekcji z realnym odbiorcą.
- [ ] każda ma unikalne wprowadzenie i kuratora.
- [ ] brak automatycznych pustych landing pages.

**Backend — endpointy, serwisy, schemas, permissions**

CollectionService: GET /collections i /collections/{slug}; editorial CRUD draft/review/publish; CollectionSchema z ordered items i references; oddzielne permissions collections:update/publish.

**Database — tabele, relacje, indeksy, migracje**

Collection, CollectionRevision, CollectionItem(person_id,sort_order,commentary), source links; FK do osób i indeks slug/status; widoczność zależy od publikacji obu elementów.

**Frontend — strony, komponenty, stan, integracja API**

/kolekcje/[slug]: opis, kolejność czytania i powody wyboru; admin prosty editor listy; SSR, sort order zapisany w DB, URL jako tożsamość kolekcji.

**Tests — backend, frontend, E2E**

Backend: draft member visibility i atomowe publish; Frontend: lista z usuniętą osobą; E2E: 3 profile w ścieżce i źródła, sitemap tylko published collection.

**Infrastructure**

Brak nowej infrastruktury.

**Dependencies**

002, 006, 009.

**Risk**

Tanie tworzenie list bez wartości; mierzyć użycie i completion.

## FEATURE-032 — Ścieżki edukacyjne i quizy źródłowe

**Grupa:** Education. **Faza:** 6. **Priorytet:** P3. **Priority Score:** 31.33.

**Product — problem**

Brak materiałów z poziomem trudności, celem i czasem lekcji.

**User Story**

**As a** katecheta i uczeń  
**I want** przeprowadzić lekcję i sprawdzić zrozumienie za pomocą źródłowych pytań  
**So that** Mogę przeprowadzić lekcję i sprawdzić zrozumienie na podstawie źródeł.

**Wartość i złożoność**

Mogę przeprowadzić lekcję i sprawdzić zrozumienie na podstawie źródeł.

Techniczna: **5/10 (średnia)**; dane: **8/10**; utrzymanie: **6/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Pilotaż z nauczycielem.
- [ ] pytania sprawdzają zrozumienie, nie arbitralną pamięć.
- [ ] nie zbieramy kont dzieci dla prostego quizu.

**Backend — endpointy, serwisy, schemas, permissions**

LearningPathService; GET /learning-paths/{slug}, /quizzes/{id}; typed question/answer/explanation schema; authored publish permissions; wynik quizu może być lokalny, nie wymaga konta dziecka.

**Database — tabele, relacje, indeksy, migracje**

LearningPath, Lesson, QuizQuestion, QuizOption z answer explanation/source revision; żadnej tabeli danych ucznia w MVP; wersje pytań zależne od materiału.

**Frontend — strony, komponenty, stan, integracja API**

/edukacja: czas/poziom/cel, lekcja i dostępny quiz; odpowiedź pokazuje wyjaśnienie i źródło; state local, opcjonalny wydruk.

**Tests — backend, frontend, E2E**

Backend: każda odpowiedź ma source revision; Frontend: keyboard i reset; E2E: lekcja→quiz→wyjaśnienie, zmiana źródła oznacza pytanie do review.

**Infrastructure**

Brak nowej usługi; ewentualny eksport dopiero po 035.

**Dependencies**

031, 016, 012.

**Risk**

Utrzymanie materiału i odpowiedni poziom; nie generować masowo quizów AI.

## FEATURE-033 — Ulubione, prywatne listy i kontynuacja czytania

**Grupa:** Personalization. **Faza:** 6. **Priorytet:** P3. **Priority Score:** 38.55.

**Product — problem**

Nie można zapisać profilu i wrócić do własnego tematu.

**User Story**

**As a** powracający czytelnik  
**I want** zapisać profil i wrócić do własnej listy  
**So that** Zachowuję własną ścieżkę bez obowiązkowego rejestrowania konta.

**Wartość i złożoność**

Zachowuję własną ścieżkę bez obowiązkowego rejestrowania konta.

Techniczna: **4/10 (średnia)**; dane: **2/10**; utrzymanie: **4/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Podstawowe zapisy działają bez konta.
- [ ] czytelnik wie, że lista jest na urządzeniu.
- [ ] wersja sync zapewnia prywatność i usuwanie.

**Backend — endpointy, serwisy, schemas, permissions**

MVP bez API: local favorites; po potwierdzeniu potrzeby GET/PUT /me/collections i items, owner authorization; nie wykorzystywać kont redakcyjnych jako domyślnych publicznych profili.

**Database — tabele, relacje, indeksy, migracje**

MVP bez DB; sync później ReaderCollection/CollectionItem z owner_id i unique collection/person; prywatne domyślnie, brak publicznego slug bez jawnego udostępnienia.

**Frontend — strony, komponenty, stan, integracja API**

Przycisk zapisz, /zapisane, kontynuuj czytanie; versioned localStorage tylko niesekretne ID, obsługa niedostępnych osób; sync opt-in.

**Tests — backend, frontend, E2E**

Backend później: owner isolation; Frontend: storage unavailable, export/import własnej listy; E2E: zapis→reload→otwarcie, usunięta osoba nie łamie listy.

**Infrastructure**

MVP bez nowej infrastruktury; konto dopiero z flow recovery/security.

**Dependencies**

009, 013; 038 dla accounts.

**Risk**

Kolekcje mogą ujawniać przekonania użytkownika; minimalizować identyfikację.

## FEATURE-034 — Eksport ICS i obserwowane wspomnienia

**Grupa:** Calendar / Retention. **Faza:** 6. **Priorytet:** P3. **Priority Score:** 37.68.

**Product — problem**

Kalendarz wymaga ponownego odwiedzenia portalu; brak przeniesienia wybranych terminów.

**User Story**

**As a** czytelnik wracający do wspomnień  
**I want** dodać wybrane wspomnienia do kalendarza i otrzymywać zamówione przypomnienia  
**So that** Mam wybrane wspomnienia w swoim kalendarzu i rozumiem ich zakres.

**Wartość i złożoność**

Mam wybrane wspomnienia w swoim kalendarzu i rozumiem ich zakres.

Techniczna: **5/10 (średnia)**; dane: **6/10**; utrzymanie: **6/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Nie eksportuje niezweryfikowanego resolvera jako pełnej liturgii.
- [ ] stabilne identyfikatory i wersje.
- [ ] opt-in/wycofanie subskrypcji działa.

**Backend — endpointy, serwisy, schemas, permissions**

GET /calendar/export.ics?calendar&year&person; CalendarExportService z stable UID/SEQUENCE i źródłem; subskrypcje prywatne później z revoke token i bounded horizon; notifications tylko opt-in.

**Database — tabele, relacje, indeksy, migracje**

V1 ICS bez DB; później CalendarSubscription(owner,scope,token_hash,revoked_at), NotificationDelivery idempotency; wpisy pochodzą z Feast fixed-only albo ResolvedOccurrence po 021.

**Frontend — strony, komponenty, stan, integracja API**

Przycisk pobierz rok/wybrane wspomnienia, opis fixed-only lub edition; własny zakres w URL; potwierdzanie kanału i częstotliwości dopiero dla powiadomień.

**Tests — backend, frontend, E2E**

Backend: ICS escaping, all-day dates, leap day, stable UID/update/cancel; Frontend: poprawny zakres; E2E: plik parserem ICS i aktualizacja wpisu bez duplikatu.

**Infrastructure**

ICS bez workerów; przypomnienia dopiero worker+mail provider+unsubscribe.

**Dependencies**

010; 021 dla normatywnych terminów; 033/038 dla prywatnych kont.

**Risk**

Stare wydarzenia w kalendarzu odbiorcy i zła strefa; jawna wersja i horyzont.

## FEATURE-035 — Publiczne API, wydania danych i eksporty

**Grupa:** API / Platform. **Faza:** 6. **Priorytet:** P3. **Priority Score:** 27.46.

**Product — problem**

REST v1 jest aplikacyjne; brak developer portal, kluczy/quota i stabilnego eksportu zbioru.

**User Story**

**As a** developer partnera i badacz  
**I want** pobrać stabilne i udokumentowane wydanie danych z API  
**So that** Pobieram udokumentowane dane z wersją, licencją i pochodzeniem.

**Wartość i złożoność**

Pobieram udokumentowane dane z wersją, licencją i pochodzeniem.

Techniczna: **7/10 (wysoka)**; dane: **7/10**; utrzymanie: **8/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] 2–3 partnerów potwierdza use case.
- [ ] kontrakt wersjonowany, dane i obrazy mają jawne prawa.
- [ ] eksport zawiera citations.
- [ ] klucze odwoływalne i limitowane.

**Backend — endpointy, serwisy, schemas, permissions**

/developers docs publikowane niezależnie od admin; API key scopes read-only, quota; GET /datasets/releases i eksport JSON/CSV; POST /exports tylko jeśli zadanie długie, job/status/download. Zaczynać od istniejącego JSON profilu i public read DTO.

**Database — tabele, relacje, indeksy, migracje**

ApiClient, ApiKeyHash, UsageAggregate, DatasetRelease(manifest_hash,schema_version,created_at,license), ExportJob; klucze tylko hashed; immutable manifest i FK do wersji danych.

**Frontend — strony, komponenty, stan, integracja API**

/developers: OpenAPI, examples, changelog, deprecation; admin client management z minimalnymi scopes; ExportDialog wybiera format/zakres, polling job. PDF/XLSX dopiero z konkretnym use case.

**Tests — backend, frontend, E2E**

Backend: API compatibility, quota i brak private fields, dataset reproducibility; Frontend: download states; E2E: partner pobiera, cytuje revision i potrafi odtworzyć release.

**Infrastructure**

Object storage eksportów, worker dla dużych plików, limit czasu/rozmiaru i retencja.

**Dependencies**

006, 016, 023, 037, 038, 039.

**Risk**

Koszt supportu, obietnice SLA i prawa do redystrybucji; oddzielić metadane od plików.

## FEATURE-036 — Transactional outbox i webhooki

**Grupa:** API / Events. **Faza:** 6. **Priorytet:** P2. **Priority Score:** 30.90.

**Product — problem**

Publikacja i przyszłe indeksy/eksporty mogą się rozjechać po awarii; webhook wymaga trwałych zdarzeń.

**User Story**

**As a** operator projekcji i partner  
**I want** otrzymać zdarzenie publikacji i bezpiecznie ponowić nieudaną dostawę  
**So that** Zmiany publikacji docierają do projekcji i partnera z kontrolą ponowień.

**Wartość i złożoność**

Zmiany publikacji docierają do projekcji i partnera z kontrolą ponowień.

Techniczna: **7/10 (wysoka)**; dane: **3/10**; utrzymanie: **7/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] At-least-once jawne.
- [ ] consumer idempotentny.
- [ ] partner weryfikuje podpis.
- [ ] replay nie publikuje starej rewizji.
- [ ] sekret nie trafia do logów.

**Backend — endpointy, serwisy, schemas, permissions**

PublicationService zapisuje OutboxEvent w tej samej transakcji; dispatcher z idempotency; POST /webhook-subscriptions, delivery log/retry chronione API scopes; event envelope id,type,schema_version,entity_id,revision_id.

**Database — tabele, relacje, indeksy, migracje**

OutboxEvent, ProjectionCheckpoint, WebhookSubscription(secret ref,target,status), WebhookDelivery(event_id,attempt,result); unique consumer/event i indeks pending/next_attempt; retencja po potwierdzeniu.

**Frontend — strony, komponenty, stan, integracja API**

Admin status projekcji i delivery, manual retry z powodem; developer subscription panel dopiero po autoryzacji; public UI bez nowego state.

**Tests — backend, frontend, E2E**

Backend: crash commit/send boundary, duplicate/reordered delivery, HMAC signature, SSRF URL; Frontend: retry disabled/running; E2E: publish→projection→webhook i awaria→retry bez podwójnego skutku.

**Infrastructure**

Worker, durable broker lub DB polling; DLQ/retencja i bezpieczny egress do webhooków.

**Dependencies**

004, 037; webhooks dopiero 035.

**Risk**

Przesadna event architecture; outbox dla spójności, nie event sourcing całej aplikacji.

## FEATURE-037 — Gotowość operacyjna, backup i monitoring

**Grupa:** DevOps / SRE. **Faza:** 0. **Priorytet:** P1. **Priority Score:** 37.69.

**Product — problem**

Są fundamenty CI/health/backup, ale prod Compose nie uruchamia workerów i pełnego monitoringu.

**User Story**

**As a** operator aplikacji  
**I want** wykryć awarię i odtworzyć działanie aplikacji wraz z danymi  
**So that** Mogę wykryć awarię, ograniczyć jej skutki i odtworzyć usługę z danymi.

**Wartość i złożoność**

Mogę wykryć awarię, ograniczyć jej skutki i odtworzyć usługę z danymi.

Techniczna: **6/10 (średnia)**; dane: **3/10**; utrzymanie: **6/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Udokumentowany test RPO/RTO, działający alert z właścicielem, test przywrócenia pliku+rekordu.
- [ ] niewdrożone capability wyłączone.
- [ ] brak fałszywych success tasków.

**Backend — endpointy, serwisy, schemas, permissions**

Health readiness per required capability, metrics job age/search lag/publication failure, structured logs z redakcją PII; implementować cleanup tokens zamiast stub lub wyłączyć harmonogram; release ID w błędach.

**Database — tabele, relacje, indeksy, migracje**

Backup DB+storage manifest; retencja AuditLog/RefreshToken; indeksy cleanup według pomiaru; restore do izolowanego środowiska, brak zmian aplikacyjnych tylko dla dashboardu.

**Frontend — strony, komponenty, stan, integracja API**

Błędy API z request_id i jasnym stanem ponów; error tracking web/admin; status funkcji dla operatora, nie fałszywe flagi.

**Tests — backend, frontend, E2E**

Backend: health dependency failure, cleanup bounds; Frontend: awaria i recovery; E2E/ops: restore danych i plików, worker crash/retry, smoke prod routes i migracja.

**Infrastructure**

Prod worker/beat gdy włączone joby, monitoring backend+FE, alert routing, TLS, prywatne sieci, memory/CPU budgets; rozdzielić durable queue od evicting cache.

**Dependencies**

Przegląd istniejących Compose i scripts; kolejne moduły według faz.

**Risk**

Zbyt dużo infrastruktury przed obciążeniem; utrzymać minimalny produkcyjny zestaw.

## FEATURE-038 — Ochrona dostępu, zasobów i sesji

**Grupa:** Security. **Faza:** 0. **Priorytet:** P1. **Priority Score:** 39.58.

**Product — problem**

Limiter obejmuje logowanie, nie wszystkie kosztowne endpointy; MFA/CSRF config nie dowodzą ochrony; CSP nie obejmuje portalu.

**User Story**

**As a** administrator i czytelnik  
**I want** chronić konto i ograniczać nadużycia zasobów aplikacji  
**So that** Konto i usługa mają realne zabezpieczenia odpowiadające sposobowi wdrożenia.

**Wartość i złożoność**

Konto i usługa mają realne zabezpieczenia odpowiadające sposobowi wdrożenia.

Techniczna: **6/10 (średnia)**; dane: **2/10**; utrzymanie: **6/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Limity są egzekwowane w runtime.
- [ ] security settings mają testy działania.
- [ ] MFA działa end-to-end albo nie jest reklamowane.
- [ ] backup/recovery nie otwiera obejścia auth.

**Backend — endpointy, serwisy, schemas, permissions**

Public/API/AI/import/upload rate policies na Redis/edge; Origin check cookie auth, JWT/refresh regression; MFA enroll/verify/recovery z osobnymi commands i audit; permission checks na wszystkich nowych writes. Ustalić granicę logout access token lifetime.

**Database — tabele, relacje, indeksy, migracje**

MFA recovery hashes i szyfrowany secret jeśli feature aktywna; session family/revocation zależnie od polityki; indeksy cleanup; żadne plaintext recovery codes w DB.

**Frontend — strony, komponenty, stan, integracja API**

Admin MFA setup/recovery i sessions UI dopiero po backend policy; CSP w Next/Nginx report-only→enforce; komunikaty 429 z Retry-After; bez tokenów w localStorage.

**Tests — backend, frontend, E2E**

Backend: rate limit race, Redis failure policy, CSRF Origin, MFA recovery reuse, permissions; Frontend: 429 i expired session; E2E izolowane: login/refresh/logout, nagłówki dokumentu web/admin, brak bypass publish.

**Infrastructure**

Trusted proxy config, TLS i CSP; limit provider kosztów; bez publikowania danych/logów testowych.

**Dependencies**

005, 037; istniejący RBAC i auth zachować.

**Risk**

Lockout administratora i CSP łamiący UI; etap report-only i test recovery.

## FEATURE-039 — Typowane kontrakty i developer ergonomics

**Grupa:** Platform / Maintainability. **Faza:** 2. **Priorytet:** P2. **Priority Score:** 32.93.

**Product — problem**

Dwa klienty API mają ręczne typy i Record<string,unknown>; schemat może dryfować od UI.

**User Story**

**As a** developer projektu  
**I want** wykrywać niezgodność kontraktu API przed wdrożeniem  
**So that** Zmiana backendu daje wczesny błąd kompilacji, a nie błąd w przeglądarce.

**Wartość i złożoność**

Zmiana backendu daje wczesny błąd kompilacji, a nie błąd w przeglądarce.

Techniczna: **5/10 (średnia)**; dane: **1/10**; utrzymanie: **3/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Generacja powtarzalna, brak ręcznej edycji generated files.
- [ ] frontend build/types wykrywają breaking schema.
- [ ] migracja klienta po jednym module.

**Backend — endpointy, serwisy, schemas, permissions**

Generować OpenAPI z aktualnej app i porównywać breaking changes; error envelope i pagination contract konsekwentne; command/query boundaries utrzymać, nie wprowadzać repository boilerplate.

**Database — tabele, relacje, indeksy, migracje**

Bez migracji dla samego klienta; schema drift check pozostaje; kontrakt nie powinien serializować tabel 1:1.

**Frontend — strony, komponenty, stan, integracja API**

Mała paczka generated API types/client + osobne adapters web/admin; stopniowo zastąpić any/Record; wspólne domain labels tylko tam, gdzie identyczne; state obecny React Query/RHF pozostaje.

**Tests — backend, frontend, E2E**

Backend: OpenAPI diff i serialization; Frontend: typecheck kontraktów i mocked API errors; E2E: jedna krytyczna pionowa ścieżka po regeneracji klienta.

**Infrastructure**

Generacja deterministyczna w CI, pinned toolchain, brak nowego serwera.

**Dependencies**

011 ustalone DTO; można robić stopniowo z nowymi funkcjami.

**Risk**

Nadmierne monorepo tooling i wspólny UI wymuszony kosztem dwóch produktów.

## FEATURE-040 — Media z prawami, dostępnością i właściwą dystrybucją

**Grupa:** Media / UX. **Faza:** 1. **Priorytet:** P2. **Priority Score:** 37.92.

**Product — problem**

Upload jest walidowany, ale profil nie eksponuje pełnego podpisu/licencji; publiczny plik nie jest powiązany z widocznością draftu.

**User Story**

**As a** czytelnik i redaktor ilustracji  
**I want** poznać źródło i prawa ilustracji oraz otrzymać właściwy wariant obrazu  
**So that** Widzę pochodzenie ilustracji i korzystam z szybkiego, dostępnego obrazu.

**Wartość i złożoność**

Widzę pochodzenie ilustracji i korzystam z szybkiego, dostępnego obrazu.

Techniczna: **5/10 (średnia)**; dane: **6/10**; utrzymanie: **5/10**. Są to koszty względne, nie obietnica liczby dni.

**Acceptance Criteria**

- [ ] Każdy publiczny obraz ma jawne prawa/pochodzenie.
- [ ] brak nowego obrazu z unknown license.
- [ ] zmiana statusu usuwa dostęp zgodnie z polityką cache.
- [ ] test restore obejmuje plik.

**Backend — endpointy, serwisy, schemas, permissions**

PublicImageSchema z attribution/license/source; chronione draft image access lub podpisany URL; public endpoint opiera się na published relation, jeśli polityka wymaga prywatności; zachować existing prepare_avatar limits.

**Database — tabele, relacje, indeksy, migracje**

Wykorzystać Image title/license/photographer/source_url; dodać rights_reviewed_at/revision/published state gdy potrzebne; storage_key nadal nie jest autoryzacją; backfill unknown do review, nie do public_domain.

**Frontend — strony, komponenty, stan, integracja API**

Avatar/Figure: podpis, licencja i źródło, alt zależne od treści; sizes/srcset i odpowiedni wariant obrazu; admin rights checklist z zachowaniem provenance; fallback monogram istnieje.

**Tests — backend, frontend, E2E**

Backend: draft file exposure według ustalonej polityki, path traversal, format/size; Frontend: alt/fallback i layout stability; E2E: upload→review→publish→podpis, CDN cache po wycofaniu obrazu.

**Infrastructure**

Object storage + CDN dla publicznych; signed URLs dla prywatnych; backup obiektów i retencja orphan uploads.

**Dependencies**

002, 003, 004, 037.

**Risk**

Prawa do ilustracji i publiczne cache po wycofaniu; nie zakładać licencji z wieku postaci.

