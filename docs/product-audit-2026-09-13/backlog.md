# Backlog — 16 priorytetowych epików

Gotowe do przeniesienia do issue trackera. Kolejność odpowiada zależnościom i ryzyku, nie samemu Priority Score. Przy FEATURE-004/037/038 faza 0 obejmuje minimum opisane w planie; późniejsze zakresy nie blokują małych poprawek. Nie utworzono zewnętrznych zgłoszeń.

## FEATURE-005 — Bezpieczne renderowanie JSON-LD

**Goal**

Otwieram treść redakcyjną bez wykonywania wstrzykniętego skryptu.

**Why**

JSON.stringify w script dangerouslySetInnerHTML nie neutralizuje zamknięcia znacznika przez treść rekordu.

**User Story**

**As a** czytelnik publicznego profilu  
**I want** bezpiecznie otwierać profile zawierające treści importowane i redagowane  
**So that** Otwieram treść redakcyjną bez wykonywania wstrzykniętego skryptu.

**Backend**

- [ ] API bez zmian.
- [ ] walidacja treści pomocnicza nie zastępuje bezpiecznego renderera.

**Database**

- [ ] Brak migracji ani masowej zmiany danych.

**Frontend**

- [ ] Profil swieci/[slug]: wspólny serializeJsonLd neutralizujący < do sekwencji Unicode.
- [ ] zastosować do każdego JSON-LD.
- [ ] utrzymać poprawny JSON i odczyt przez parser danych strukturalnych.

**Tests**

- [ ] Backend: bez nowych testów gdy kontrakt bez zmian.
- [ ] Frontend: payload zawierający zamknięcie script, Unicode i cudzysłowy.
- [ ] E2E na fixture izolowanym: jedno script JSON-LD, brak dodatkowego elementu/wykonania.

**Infrastructure**

- [ ] CSP jest dodatkową ochroną FEATURE-038.
- [ ] nie uzależniać szybkiego fixu od wdrożenia CSP.

**Definition of Done**

- [ ] Serializator poprawnie obsługuje niebezpieczny fragment i zwykłe nazwy.
- [ ] JSON po odczycie zachowuje oryginalną wartość.
- [ ] żadna ścieżka nie osadza surowego JSON.stringify.

**Dependencies**

Brak.

**Risk**

Niewłaściwe HTML escaping może zepsuć JSON-LD; test parsowania obok testu bezpieczeństwa.

**Priority**

P0; faza 0; Priority Score 60.85. Techniczna: **2/10 (niska)**; dane: **1/10**; utrzymanie: **1/10**. Są to koszty względne, nie obietnica liczby dni.

## FEATURE-001 — Uczciwe statusy jakości i obietnice produktu

**Goal**

Rozumiem zakres danych i funkcji, zanim oprę się na wyniku.

**Why**

Homepage przypisuje wszystkim kartom verified, obiecuje NLP i przypisy do informacji; topbar ma martwe kontrolki.

**User Story**

**As a** czytelnik i redaktor  
**I want** rozpoznawać, co jest opublikowane, opracowane i rzeczywiście zweryfikowane  
**So that** Rozumiem zakres danych i funkcji, zanim oprę się na wyniku.

**Backend**

- [ ] W minimum bez nowego API.
- [ ] następnie QualitySummary DTO z source_count i last_reviewed_at z rzeczywistej recenzji.
- [ ] nie wyprowadzać verified z published. Health/info powinien opisywać wdrożoną capability, a nie sam config flag.

**Database**

- [ ] Bez migracji w minimum.
- [ ] jeśli dodajemy last_reviewed_at, przechowywać zdarzenie recenzji z revision_id zamiast aktualizować datę przy każdym zapisie.

**Frontend**

- [ ] apps/web/app/page.tsx i słownik pl: poprawić verified/NLP/metodologię.
- [ ] footer: usunąć nieudowodnione zapewnienia.
- [ ] topbar admin: link do listy osób zamiast pustego search, ukryć nieaktywny dzwonek. State: brak nowego globalnego store.

**Tests**

- [ ] Backend: kontrakt capability i jakości.
- [ ] Frontend: warunkowy badge dla danych z/bez recenzji.
- [ ] E2E: opublikowany profil bez źródła nie ma etykiety zweryfikowany.

**Infrastructure**

- [ ] Brak nowych usług.

**Definition of Done**

- [ ] Żaden badge nie wynika wyłącznie ze statusu publikacji.
- [ ] tekst wyszukiwarki odpowiada funkcjom.
- [ ] wszystkie widoczne przyciski mają działanie.
- [ ] źródła i status są nazwane jednoznacznie.

**Dependencies**

Brak; uzgodnienie słownika pojęć redakcyjnych.

**Risk**

Utrata pozornego wrażenia kompletności; zaakceptować ją jako poprawę zaufania.

**Priority**

P1; faza 0; Priority Score 57.72. Techniczna: **2/10 (niska)**; dane: **2/10**; utrzymanie: **1/10**. Są to koszty względne, nie obietnica liczby dni.

## FEATURE-002 — Publiczna bibliografia profilu

**Goal**

Mogę odnaleźć materiał stanowiący podstawę opracowania.

**Why**

PersonSource dostępny jest w panelu, ale nie na publicznym profilu.

**User Story**

**As a** czytelnik weryfikujący informację  
**I want** otworzyć bibliografię bezpośrednio z profilu osoby  
**So that** Mogę odnaleźć materiał stanowiący podstawę opracowania.

**Backend**

- [ ] Dodać GET /api/v1/persons/{id_or_slug}/sources przez publiczny router.
- [ ] PublicCitationSchema bez editor_notes/reviewer email.
- [ ] PersonSourceService/public query sprawdza published oraz aktywność linku i źródła. Zachować chroniony /sources/person-links.

**Database**

- [ ] Wykorzystać Bibliography, HistoricalSource i PersonSource.
- [ ] nowe tabele niepotrzebne.
- [ ] istniejący indeks person_id.
- [ ] nie zmieniać schematu tylko dla wyświetlenia.

**Frontend**

- [ ] apps/web/lib/api.ts: fetchPersonSources.
- [ ] profil: SourcesSection z tytułem, autorami, rokiem, stroną i URL.
- [ ] SSR, wspólne pobranie profilu/źródeł.
- [ ] stan pusty bez zmyślonego przypisu.

**Tests**

- [ ] Backend: published 200, draft/deleted 404, usunięte źródło pominięte, prywatne notes nieobecne.
- [ ] Frontend: książka bez URL i archiwalium.
- [ ] E2E: profil→przypis→lokalizator źródła.

**Infrastructure**

- [ ] Cache zgodny z rewizją osoby.
- [ ] brak nowej usługi.

**Definition of Done**

- [ ] Źródła widoczne na profilu bez logowania.
- [ ] każdy wpis wskazuje istniejący rekord.
- [ ] brak prywatnych metadanych w HTML/JSON.
- [ ] książka offline pozostaje użyteczna.

**Dependencies**

001 dla terminologii; 004 dla docelowej spójności wersji.

**Risk**

Wycieki notes i pokazanie źródła jako potwierdzenia wszystkich zdań.

**Priority**

P1; faza 1; Priority Score 57.37. Techniczna: **3/10 (niska)**; dane: **3/10**; utrzymanie: **2/10**. Są to koszty względne, nie obietnica liczby dni.

## FEATURE-003 — Źródłowa bramka publikacji

**Goal**

Publikuję wyłącznie profil spełniający jawne minimum redakcyjne.

**Why**

Publikacja wymaga tekstów i licencji, ale nie wymaga źródła; can_publish ma odrębną listę blockerów.

**User Story**

**As a** recenzent  
**I want** sprawdzić wymagane źródła przed dopuszczeniem treści do publikacji  
**So that** Publikuję wyłącznie profil spełniający jawne minimum redakcyjne.

**Backend**

- [ ] Wydzielić PublicationPolicy używaną przez EditorialWorkflowService i EditorialQualityPolicy.
- [ ] sprawdzać aktywne źródło oraz treść/licencję.
- [ ] POST /editorial/queue/{id}/transition zwraca typed blockers. Weryfikować także alternatywne ścieżki import/AI.
- [ ] permission review/publish zgodnie z istniejącą macierzą.

**Database**

- [ ] V1 bez migracji.
- [ ] raport 34 profili bez linku.
- [ ] docelowo PublicationException(revision_id,reason,approver,expires_at), FK i indeks open exceptions. Brak automatycznego unpublish legacy.

**Frontend**

- [ ] Kolejka i detail: ten sam zestaw blockerów, odnośnik do sekcji Źródła.
- [ ] React Query invalidation quality/person po przypisaniu.

**Tests**

- [ ] Backend: publikacja bez aktywnego źródła odrzucona.
- [ ] usunięty link nie spełnia bramki.
- [ ] Frontend: can_publish i API zgodne.
- [ ] E2E: draft→source→review→published.

**Infrastructure**

- [ ] Brak nowych usług.

**Definition of Done**

- [ ] Jedna polityka dla badge, kolejki i API.
- [ ] legacy ma listę naprawczą i właściciela.
- [ ] wyjątek jawny z powodem.
- [ ] test nie pozwala ominąć bramki alternatywną mutacją.

**Dependencies**

001, 002; przed 004 ustalić politykę bieżącej edycji.

**Risk**

Formalne dodanie dowolnego linku zamiast merytorycznej recenzji.

**Priority**

P1; faza 0; Priority Score 48.09. Techniczna: **4/10 (średnia)**; dane: **5/10**; utrzymanie: **3/10**. Są to koszty względne, nie obietnica liczby dni.

## FEATURE-004 — Izolowane rewizje opublikowanych treści

**Goal**

Przygotowuję poprawki bez zmiany przeczytanej już wersji publicznej.

**Why**

PATCH treści osoby published może zmienić live bez ponownej recenzji; tłumaczenia wymagają draft całej osoby.

**User Story**

**As a** redaktor aktualizujący publiczny profil  
**I want** przygotować i zrecenzować nową wersję bez modyfikowania wersji publicznej  
**So that** Przygotowuję poprawki bez zmiany przeczytanej już wersji publicznej.

**Backend**

- [ ] Minimum: blokada niedozwolonych zapisów do published i audyt wszystkich writerów. Docelowo RevisionService, POST /persons/{id}/revisions, PATCH /revisions/{id}, POST /revisions/{id}/submit i /publish.
- [ ] RevisionCommand z expected_version.
- [ ] public query czyta published_revision_id. Ta sama reguła dla sources/orders/AI.

**Database**

- [ ] PublicationRevision(id,person_id,revision_number,status,payload,base_revision_id,author_id,created_at).
- [ ] Person.published_revision_id FK.
- [ ] UNIQUE(person_id,revision_number), indeks kolejki.
- [ ] backfill opublikowanych rekordów do pierwszej rewizji, parity test projekcji. Typed relacje rewizji dla źródeł.
- [ ] payload ma wersję schema.

**Frontend**

- [ ] EditPersonClient: draft revision, ostrzeżenie o wersji bazowej.
- [ ] podgląd i diff.
- [ ] stan RHF lokalny, React Query według revision_id.
- [ ] UI 409 nie kasuje wpisanych zmian.

**Tests**

- [ ] Backend: publiczne read nie zmienia się po zapisie draftu.
- [ ] wszystkie write paths respektują granicę.
- [ ] Frontend: konflikt zachowuje formularz.
- [ ] E2E: dwie osoby edytują, tylko jedna publikuje zatwierdzoną rewizję.

**Infrastructure**

- [ ] Po publikacji invalidacja cache.
- [ ] outbox 036 gdy pojawiają się async projekcje.

**Definition of Done**

- [ ] Publiczny profil wskazuje jednoznaczną wersję.
- [ ] draft nie przecieka w źródłach, mediach ani search.
- [ ] publikacja atomowa.
- [ ] rollback tworzy nową wersję.
- [ ] legacy response zachowany w okresie migracji.

**Dependencies**

003 i przegląd wszystkich serwisów zapisujących Person.

**Risk**

Największe ryzyko regresji modelu; najpierw mała blokada, następnie migracja rewizji z shadow reads.

**Priority**

P0; faza 0; Priority Score 37.39. Techniczna: **8/10 (wysoka)**; dane: **6/10**; utrzymanie: **5/10**. Są to koszty względne, nie obietnica liczby dni.

## FEATURE-006 — SEO i cykl życia adresów

**Goal**

Trafiam do jednej aktualnej, indeksowalnej strony tematu.

**Why**

Brak kompletnego canonical/sitemap/robots; profil może działać pod slug i UUID.

**User Story**

**As a** osoba trafiająca z wyszukiwarki  
**I want** trafiać z wyszukiwarki na trwały i jednoznaczny adres profilu  
**So that** Trafiam do jednej aktualnej, indeksowalnej strony tematu.

**Backend**

- [ ] GET /public-index/persons?cursor z lekkim PublicIndexItem(id,slug,updated_at).
- [ ] tylko published. Obsługa aliasu sluga/redirect target.
- [ ] nie używać pełnych biografii do sitemap.

**Database**

- [ ] V1 bez nowych tabel.
- [ ] v2 PersonSlugRedirect(old_slug UNIQUE,person_id,created_at), FK i indeks.
- [ ] migration/backfill tylko przy udokumentowanej zmianie sluga.

**Frontend**

- [ ] web metadataBase z env.
- [ ] canonical i OG.
- [ ] sitemap.ts / robots.ts.
- [ ] 301 UUID/old_slug.
- [ ] BreadcrumbList.
- [ ] noindex wyszukiwania, kontrola stron tematycznych i paginacji.
- [ ] state URL.

**Tests**

- [ ] Backend: brak draftów w indeksie.
- [ ] Frontend: absolutne canonical/OG.
- [ ] E2E crawler fixture: brak pętli redirect, sitemap zawiera canonical i poprawne statusy, publikacja/usunięcie odświeża indeks.

**Infrastructure**

- [ ] Cache sitemap, ewentualne shardowanie.
- [ ] domena produkcyjna z konfiguracji.

**Definition of Done**

- [ ] Jedno kanoniczne URL na profil.
- [ ] sitemap tylko publiczne wartościowe strony.
- [ ] zmiana sluga zachowuje wejścia.
- [ ] polityka faset opisana i testowana.

**Dependencies**

005, 002; pełna invalidacja zależy od 004.

**Risk**

Thin content i crawl explosion przy zbyt szerokim indeksowaniu faset.

**Priority**

P1; faza 1; Priority Score 48.60. Techniczna: **5/10 (średnia)**; dane: **3/10**; utrzymanie: **3/10**. Są to koszty względne, nie obietnica liczby dni.

## FEATURE-009 — Profil jako centrum odpowiedzi i eksploracji

**Goal**

Docieram do właściwej sekcji i przechodzę do powiązanego kontekstu.

**Why**

Długie aliasy i teksty utrudniają znalezienie daty, wspomnienia lub źródła.

**User Story**

**As a** czytelnik długiej biografii  
**I want** szybko przejść do właściwej sekcji profilu i powiązanego tematu  
**So that** Docieram do właściwej sekcji i przechodzę do powiązanego kontekstu.

**Backend**

- [ ] PersonPublicProfileSchema z lekkimi sekcjami i quality/source summary.
- [ ] agregację rozszerzać przez public query, bez surowych ORM relacji w payloadzie.
- [ ] v1 używa istniejących danych.

**Database**

- [ ] V1 brak migracji.
- [ ] późniejsza struktura bloków biografii związana z 016 i rewizją. Nie przepisywać wszystkich biografii tylko dla TOC.

**Frontend**

- [ ] web/swieci/[slug]: TableOfContents, FactsPanel, SourcesSection, collapsible aliases, linki do kalendarza/zakonu, przycisk cytowania.
- [ ] SSR z małymi client islands.
- [ ] stan anchor w URL.

**Tests**

- [ ] Backend: zgodność pól i widoczności.
- [ ] Frontend: warunkowe sekcje i brak pustych anchorów.
- [ ] E2E mobile: przejście do źródeł w ≤2 działaniach, back do wyników zachowuje filtry.

**Infrastructure**

- [ ] Brak nowej infrastruktury.

**Definition of Done**

- [ ] Najważniejsze fakty widoczne wcześniej niż pełna lista aliasów.
- [ ] TOC działa klawiaturą.
- [ ] cytowany profil ma ID wersji.
- [ ] brak udawanych pustych sekcji mapy/grafu.

**Dependencies**

002, 010, 012; 018 dla related.

**Risk**

Rozbudowanie profilu do dashboardu; mierzyć czas znalezienia odpowiedzi.

**Priority**

P1; faza 1; Priority Score 52.07. Techniczna: **4/10 (średnia)**; dane: **3/10**; utrzymanie: **3/10**. Są to koszty względne, nie obietnica liczby dni.

## FEATURE-007 — Fasety relacyjne i precyzyjne filtry

**Goal**

Znajduję dokładnie określoną grupę i rozumiem znaczenie filtrów.

**Why**

Portal nie obsługuje kraju, zakonu, zawodu, dokładnego wieku ani męczeństwa jako pełnego przecięcia.

**User Story**

**As a** czytelnik szukający określonej grupy osób  
**I want** łączyć kryteria zakonu, dat, miejsca i patronatu  
**So that** Znajduję dokładnie określoną grupę i rozumiem znaczenie filtrów.

**Backend**

- [ ] Rozszerzyć PersonQueryService i GET /persons o order_id, occupation_id, nationality_id oraz zakres dat po 015.
- [ ] GET /persons/facets lub osobny search router z FacetCountsSchema. Country filter rozbić na typed geography.
- [ ] zapytania EXISTS, whitelist enum, published_only.

**Database**

- [ ] Wykorzystać PersonOrder/PersonOccupation i kraje.
- [ ] indeksy FK po obu stronach relacji.
- [ ] nowe role miejsca zależą od 017, martyrdom od 015.
- [ ] brak fikcyjnego backfillu z tekstu.

**Frontend**

- [ ] web/swieci: URL jako źródło filtrów, FacetPanel, licznik, chips remove.
- [ ] select kraj z precyzyjną nazwą już w v1.
- [ ] mobile drawer.
- [ ] stabilny back/forward.

**Tests**

- [ ] Backend: OR wewnątrz/AND między fasetami, właściwe counts bez draftów.
- [ ] Frontend: normalizacja page/URL, reset.
- [ ] E2E: dominikanie+okres, patronat+zawód, 0 results.

**Infrastructure**

- [ ] Bez nowego silnika wyszukiwania.

**Definition of Done**

- [ ] Każda faseta ma opis semantyki.
- [ ] counts zgodne z wynikami i zasadą self-excluding jeśli zastosowana.
- [ ] filtr nie zwraca osoby wyłącznie na podstawie słowa w biografii.

**Dependencies**

008 benchmark; 014/015/017 dla pełnego zestawu, obecne order/country dostępne wcześniej.

**Risk**

Niekompletne dane dają pozornie kompletną listę; pokazać zakres opracowania.

**Priority**

P1; faza 1; Priority Score 42.69. Techniczna: **6/10 (średnia)**; dane: **6/10**; utrzymanie: **4/10**. Są to koszty względne, nie obietnica liczby dni.

## FEATURE-008 — Benchmark i jakość rankingu wyszukiwania

**Goal**

Poprawna osoba znajduje się wysoko również przy aliasie i literówce.

**Why**

Dobre mechanizmy SQL nie mają produktu jakościowego mierzonego na realnych pytaniach.

**User Story**

**As a** czytelnik wpisujący nazwę lub temat  
**I want** znaleźć poprawną osobę pomimo aliasu, odmiany lub literówki  
**So that** Poprawna osoba znajduje się wysoko również przy aliasie i literówce.

**Backend**

- [x] Wydzielić SearchPolicy w istniejącym PersonQueryService.
- [x] exact canonical/alias boost, tie-breaker ID, reason code w SearchHitSchema.
- [x] API GET /persons zachować kompatybilne.
- [x] kontrolować krótkie zapytania i max długość.

**Database**

- [ ] Zachować FTS/trigram indeksy z migracji 0010/0016/0018.
- [ ] modyfikować dopiero po EXPLAIN.
- [x] gold queries i expected IDs jako wersjonowane fixture, nie tabela produkcyjna.

**Frontend**

- [ ] Komunikat powodów dopasowania, wyróżnienie dopasowanego aliasu.
- [ ] zero-results z przykładami i linkiem do korekty.
- [ ] nie generować odpowiedzi NLP.

**Tests**

- [ ] Backend: ranking exact/alias/transliteration/typo i polskie formy.
- [ ] Frontend: bezpieczne highlight, puste wyniki.
- [ ] E2E: realny query set + ręczna ocena MRR/nDCG przed/po.

**Infrastructure**

- [x] Powtarzalny benchmark offline w CI lub release check.
- [x] brak nowej usługi.

**Stan implementacji (2026-10-19)**

Starter fixture `apps/backend/data/search/search_gold_v1.json` zawiera 100
przypadków z opublikowanych slugów. Evaluator raportuje top-k, MRR@10,
nDCG@10 i puste wyniki; `make search-benchmark SEARCH_RESULTS=...` uruchamia
go/no-go. Ręczna ocena pytań i zapis baseline'u pozostają wymagane przed
traktowaniem progów jako release gate.

**Definition of Done**

- [ ] 100–200 ocenionych pytań, udokumentowany baseline.
- [ ] brak regresji exact-name.
- [ ] ustalony próg task success/top5.
- [ ] wyniki z powodami, bez nieopublikowanych danych.

**Dependencies**

013 dla realnych klas zapytań; można rozpocząć wywiadami.

**Risk**

Optymalizacja pod małą próbkę; rozdzielić zestaw do strojenia i walidacji.

**Priority**

P1; faza 1; Priority Score 46.76. Techniczna: **5/10 (średnia)**; dane: **4/10**; utrzymanie: **3/10**. Są to koszty względne, nie obietnica liczby dni.

## FEATURE-010 — Wspomnienia osoby i jawne pokrycie kalendarza

**Goal**

Wiem, w jakim kalendarzu i zakresie występuje wpis.

**Why**

Osoba nie ma publicznej listy swoich obchodów; pusty dzień i niepełny katalog mogą być mylone z brakiem obchodu.

**User Story**

**As a** czytelnik sprawdzający datę wspomnienia  
**I want** sprawdzić wspomnienie osoby wraz z kalendarzem i zakresem opracowania  
**So that** Wiem, w jakim kalendarzu i zakresie występuje wpis.

**Backend**

- [ ] GET /persons/{id}/commemorations jako public query.
- [ ] CalendarCoverageSchema w /calendar/calendars lub osobnym endpointcie: coverage_status, fixed_only, edition/description.
- [ ] filtrować published i active. Nie otwierać surowego editorial entries endpointu.

**Database**

- [ ] Wykorzystać Feast/LiturgicalCalendar.
- [ ] początkowo metadane opisowe zakresu.
- [ ] jeśli utrwalane, coverage_status i coverage_note, nie procent oparty tylko na liczbie wpisów.

**Frontend**

- [ ] Profil: tabela wspomnień według kalendarzy.
- [ ] dzień/miesiąc: nazwa zakresu i empty state „brak opracowanych wpisów”.
- [ ] rozdzielić martyrologium od normatywnej odpowiedzi.

**Tests**

- [ ] Backend: wiele kalendarzy jednej osoby i wpis nieosobowy.
- [ ] Frontend: pusta data nie oznacza „nikt”.
- [ ] E2E: profil→dzień→profil bez zmiany kalendarza.

**Infrastructure**

- [ ] Cache per calendar/date i wersja danych.
- [ ] bez silnika reguł w tym przyroście.

**Definition of Done**

- [ ] Publiczny profil pokazuje wszystkie aktywne stałe wspomnienia z pochodzeniem.
- [ ] komunikat fixed-only widoczny.
- [ ] daty strefy Europe/Warsaw spójne z today.

**Dependencies**

002, 009; resolver 021 niezależnie później.

**Risk**

Odbiorca może nadal traktować listę jako ordo; test z użytkownikiem liturgicznym.

**Priority**

P1; faza 1; Priority Score 47.81. Techniczna: **4/10 (średnia)**; dane: **5/10**; utrzymanie: **3/10**. Są to koszty względne, nie obietnica liczby dni.

## FEATURE-012 — Dostępność i mobilne wykonanie zadań

**Goal**

Mogę samodzielnie wyszukać i przeczytać profil bez bariery interfejsu.

**Why**

Filtry i hero opóźniają dostęp do treści; część pól ma tylko tekst obok, focus bywa niewidoczny.

**User Story**

**As a** czytelnik używający telefonu lub klawiatury  
**I want** wykonać wyszukiwanie i odczyt treści na telefonie oraz klawiaturą  
**So that** Mogę samodzielnie wyszukać i przeczytać profil bez bariery interfejsu.

**Backend**

- [ ] Bez nowych endpointów.
- [ ] zachować semantyczne błędy walidacji i nazwy pól.

**Database**

- [ ] Bez zmian DB.

**Frontend**

- [ ] Skip link i jeden main w web.
- [ ] label wyszukiwania.
- [ ] peer-focus-visible dla checkboxów.
- [ ] mobile filter drawer.
- [ ] label/id/aria-describedby w admin.
- [ ] zarządzanie focus w dialogach i błędach.
- [ ] prefers-reduced-motion.

**Tests**

- [ ] Backend: bez nowych testów dla CSS.
- [ ] Frontend: axe lub równoważny check, kontrast i semantyka etykiet.
- [ ] E2E: keyboard-only i 390 px, 200% zoom, czytnik ekranu dla formularza i listy.

**Infrastructure**

- [ ] Brak nowych usług.
- [ ] automatyczny accessibility smoke w CI.

**Definition of Done**

- [ ] Zero krytycznych naruszeń w objętych ekranach.
- [ ] kompletna obsługa klawiaturą.
- [ ] focus widoczny.
- [ ] brak poziomego przewijania w testowanych breakpointach.
- [ ] wynik nie znika pod drawerem.

**Dependencies**

009 i 007 dla docelowego układu, proste label/focus niezależne.

**Risk**

Automatyczny test nie dowodzi pełnego WCAG; potrzebna próba manualna.

**Priority**

P1; faza 1; Priority Score 49.03. Techniczna: **4/10 (średnia)**; dane: **1/10**; utrzymanie: **3/10**. Są to koszty względne, nie obietnica liczby dni.

## FEATURE-013 — Analityka sukcesu użytkownika

**Goal**

Podejmuję decyzje na podstawie wykonanych zadań, nie tylko wizyt.

**Why**

Brak danych o sukcesie wyszukiwania, zero-results i korzystaniu ze źródeł.

**User Story**

**As a** właściciel produktu  
**I want** mierzyć, czy czytelnik rozwiązał swoje zadanie  
**So that** Podejmuję decyzje na podstawie wykonanych zadań, nie tylko wizyt.

**Backend**

- [ ] Event ingestion (własny POST /events lub wybrany produkt) z allowlist schema, anon session_id, event/query class.
- [ ] nie zbierać domyślnie raw text i PII.
- [ ] agregaty search success i zero-results.

**Database**

- [ ] Jeśli własny collector: ProductEvent z datą/typem/małym payload i retencją, indeks time+event.
- [ ] agregaty dzienne. Nie zapisywać pełnych danych użytkownika w domenowej Person DB.

**Frontend**

- [ ] Instrumentacja search submitted/results/opened, filters, source click, relation, feedback.
- [ ] session state ograniczony i opisany.
- [ ] panel baseline dla PM.

**Tests**

- [ ] Backend: walidacja eventów, redakcja i retencja.
- [ ] Frontend: jeden event na działanie, bez duplikacji hydration.
- [ ] E2E: ścieżka search→profile→source składa się w poprawny funnel.

**Infrastructure**

- [ ] Lekki collector/analytics.
- [ ] limit kosztu i dostęp do agregatów, nie szerokich surowych logów.

**Definition of Done**

- [ ] Baseline 4 tygodnie.
- [ ] zdarzenia udokumentowane.
- [ ] North Star rozróżnia proxy i potwierdzony sukces.
- [ ] dane prywatne nie są wymagane do statystyk.

**Dependencies**

001; krótka decyzja polityki danych.

**Risk**

Proxy może nagradzać długi czas zagubienia; walidacja w badaniach.

**Priority**

P1; faza 0; Priority Score 47.59. Techniczna: **4/10 (średnia)**; dane: **2/10**; utrzymanie: **4/10**. Są to koszty względne, nie obietnica liczby dni.

## FEATURE-025 — Kolejki jakości i odpowiedzialność za dane

**Goal**

Widzę konkretne problemy, zakres pokrycia i kolejność pracy.

**Why**

Kompletność i stałe confidence mogą być odczytywane jako prawdziwość, a braki nie mają właściciela.

**User Story**

**As a** redaktor prowadzący  
**I want** przypisać właściciela konkretnemu problemowi jakości i śledzić naprawę  
**So that** Widzę konkretne problemy, zakres pokrycia i kolejność pracy.

**Backend**

- [ ] Rozwinąć EditorialQualityPolicy: source completeness osobno od content completeness.
- [ ] QualityIssueSchema z rule_version, field, evidence i severity.
- [ ] GET /quality/issues paginated, PATCH assignment/status.
- [ ] nie mieszać rule score z AI probability.

**Database**

- [ ] QualityIssue przy potrzebie trwałego assignment, resolution i waivers.
- [ ] indeks status/owner/severity.
- [ ] reguły obliczalne nie wymagają utrwalania każdej oceny przy każdym odczycie.

**Frontend**

- [ ] Quality dashboard: kategoria, właściciel, wyjaśnienie reguły, zakres danych.
- [ ] usunąć fałszywy confidence.
- [ ] stan filtrów URL, revalidate po poprawce.

**Tests**

- [ ] Backend: te same blockery co publish policy, source deleted, conflict dat.
- [ ] Frontend: etykiety kompletność/recenzja.
- [ ] E2E: problem→poprawka→zniknięcie issue i zachowanie audit trail.

**Infrastructure**

- [ ] Ciężkie walidacje okresowe przez job.
- [ ] v1 zapytania SQL.

**Definition of Done**

- [ ] 34 legacy braki mają listę i właściciela.
- [ ] każda ocena ma wersję reguły i wyjaśnienie.
- [ ] ręczne zamknięcie nie ukrywa niepoprawionego źródła bez powodu.

**Dependencies**

001, 003, 013; 016 dla reguł twierdzeń.

**Risk**

Goodhart: dopisywanie treści tylko dla wyniku; mierzyć próbki jakości merytorycznej.

**Priority**

P1; faza 2; Priority Score 42.09. Techniczna: **5/10 (średnia)**; dane: **5/10**; utrzymanie: **4/10**. Są to koszty względne, nie obietnica liczby dni.

## FEATURE-037 — Gotowość operacyjna, backup i monitoring

**Goal**

Mogę wykryć awarię, ograniczyć jej skutki i odtworzyć usługę z danymi.

**Why**

Są fundamenty CI/health/backup, ale prod Compose nie uruchamia workerów i pełnego monitoringu.

**User Story**

**As a** operator aplikacji  
**I want** wykryć awarię i odtworzyć działanie aplikacji wraz z danymi  
**So that** Mogę wykryć awarię, ograniczyć jej skutki i odtworzyć usługę z danymi.

**Backend**

- [ ] Health readiness per required capability, metrics job age/search lag/publication failure, structured logs z redakcją PII.
- [ ] implementować cleanup tokens zamiast stub lub wyłączyć harmonogram.
- [ ] release ID w błędach.

**Database**

- [ ] Backup DB+storage manifest.
- [ ] retencja AuditLog/RefreshToken.
- [ ] indeksy cleanup według pomiaru.
- [ ] restore do izolowanego środowiska, brak zmian aplikacyjnych tylko dla dashboardu.

**Frontend**

- [ ] Błędy API z request_id i jasnym stanem ponów.
- [ ] error tracking web/admin.
- [ ] status funkcji dla operatora, nie fałszywe flagi.

**Tests**

- [ ] Backend: health dependency failure, cleanup bounds.
- [ ] Frontend: awaria i recovery.
- [ ] E2E/ops: restore danych i plików, worker crash/retry, smoke prod routes i migracja.

**Infrastructure**

- [ ] Prod worker/beat gdy włączone joby, monitoring backend+FE, alert routing, TLS, prywatne sieci, memory/CPU budgets.
- [ ] rozdzielić durable queue od evicting cache.

**Definition of Done**

- [ ] Udokumentowany test RPO/RTO, działający alert z właścicielem, test przywrócenia pliku+rekordu.
- [ ] niewdrożone capability wyłączone.
- [ ] brak fałszywych success tasków.

**Dependencies**

Przegląd istniejących Compose i scripts; kolejne moduły według faz.

**Risk**

Zbyt dużo infrastruktury przed obciążeniem; utrzymać minimalny produkcyjny zestaw.

**Priority**

P1; faza 0; Priority Score 37.69. Techniczna: **6/10 (średnia)**; dane: **3/10**; utrzymanie: **6/10**. Są to koszty względne, nie obietnica liczby dni.

## FEATURE-038 — Ochrona dostępu, zasobów i sesji

**Goal**

Konto i usługa mają realne zabezpieczenia odpowiadające sposobowi wdrożenia.

**Why**

Limiter obejmuje logowanie, nie wszystkie kosztowne endpointy; MFA/CSRF config nie dowodzą ochrony; CSP nie obejmuje portalu.

**User Story**

**As a** administrator i czytelnik  
**I want** chronić konto i ograniczać nadużycia zasobów aplikacji  
**So that** Konto i usługa mają realne zabezpieczenia odpowiadające sposobowi wdrożenia.

**Backend**

- [ ] Public/API/AI/import/upload rate policies na Redis/edge.
- [ ] Origin check cookie auth, JWT/refresh regression.
- [ ] MFA enroll/verify/recovery z osobnymi commands i audit.
- [ ] permission checks na wszystkich nowych writes. Ustalić granicę logout access token lifetime.

**Database**

- [ ] MFA recovery hashes i szyfrowany secret jeśli feature aktywna.
- [ ] session family/revocation zależnie od polityki.
- [ ] indeksy cleanup.
- [ ] żadne plaintext recovery codes w DB.

**Frontend**

- [ ] Admin MFA setup/recovery i sessions UI dopiero po backend policy.
- [ ] CSP w Next/Nginx report-only→enforce.
- [ ] komunikaty 429 z Retry-After.
- [ ] bez tokenów w localStorage.

**Tests**

- [ ] Backend: rate limit race, Redis failure policy, CSRF Origin, MFA recovery reuse, permissions.
- [ ] Frontend: 429 i expired session.
- [ ] E2E izolowane: login/refresh/logout, nagłówki dokumentu web/admin, brak bypass publish.

**Infrastructure**

- [ ] Trusted proxy config, TLS i CSP.
- [ ] limit provider kosztów.
- [ ] bez publikowania danych/logów testowych.

**Definition of Done**

- [ ] Limity są egzekwowane w runtime.
- [ ] security settings mają testy działania.
- [ ] MFA działa end-to-end albo nie jest reklamowane.
- [ ] backup/recovery nie otwiera obejścia auth.

**Dependencies**

005, 037; istniejący RBAC i auth zachować.

**Risk**

Lockout administratora i CSP łamiący UI; etap report-only i test recovery.

**Priority**

P1; faza 0; Priority Score 39.58. Techniczna: **6/10 (średnia)**; dane: **2/10**; utrzymanie: **6/10**. Są to koszty względne, nie obietnica liczby dni.

## FEATURE-016 — Twierdzenia, cytowania i rozbieżności

**Goal**

Wiem, które źródło wspiera datę, patronat lub opis i gdzie źródła się różnią.

**Why**

PersonSource dokumentuje rekord, ale nie konkretne zdanie ani relację.

**User Story**

**As a** badacz weryfikujący konkretny fakt  
**I want** sprawdzić źródło konkretnej informacji i porównać rozbieżne wersje  
**So that** Wiem, które źródło wspiera datę, patronat lub opis i gdzie źródła się różnią.

**Backend**

- [ ] AssertionService i EvidenceService.
- [ ] GET /persons/{id}/assertions, /assertions/{id}/evidence.
- [ ] chronione commands create/review z revision i predicate whitelist.
- [ ] public DTO bez editor_notes.
- [ ] supports/contradicts/mentions.

**Database**

- [ ] Assertion(person_id,predicate,typed_value,qualifiers,status,revision_id), Evidence(source_id,assertion_id,locator,quote,relation,reviewed_at), ContentCitation(block_id,revision_id,evidence_id).
- [ ] Source identity/fasada dla Bibliography/HistoricalSource.
- [ ] CHECK typu wartości, FK i indeks assertion/person.

**Frontend**

- [ ] Inline citation anchors i drawer ze źródłem.
- [ ] porównanie wariantów dat.
- [ ] edytor przypisu przy polu/bloku, source picker.
- [ ] query keyed by revision.
- [ ] SSR public.

**Tests**

- [ ] Backend: public/private i FK, alternatywne wartości, publikacja tylko review.
- [ ] Frontend: stabilność anchor po edycji.
- [ ] E2E: fakt→dwa sprzeczne źródła→cytowanie konkretnej wersji.

**Infrastructure**

- [ ] Bez graph DB.
- [ ] opcjonalny link checker jako job po 037.

**Definition of Done**

- [ ] Pilotaż 20 profili: daty, patronaty i uznanie mają evidence.
- [ ] brak przypisu do nieistniejącego bloku.
- [ ] status pewności ma kryteria, a nie stały procent.
- [ ] export zachowuje provenance.

**Dependencies**

002, 004, 003.

**Risk**

Koszt redakcyjny i licencje cytatów; zacząć od kilku predykatów.

**Priority**

P2; faza 3; Priority Score 35.55. Techniczna: **8/10 (wysoka)**; dane: **9/10**; utrzymanie: **7/10**. Są to koszty względne, nie obietnica liczby dni.

