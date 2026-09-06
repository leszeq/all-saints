# Audyt architektury i gotowości produkcyjnej

Projekt: **All Saints / Encyklopedia Świętych**  
Data pomiaru: **2026-08-29**  
Zakres: backend FastAPI, baza danych, API, panel administracyjny, portal publiczny,
Docker, narzędzia developerskie, testy i bezpieczeństwo.

## Executive summary

Projekt ma dobry fundament domenowy i produktowy, ale nie jest jeszcze gotowy do
wdrożenia produkcyjnego. Największą wartością jest spójny monorepo, rzeczywisty
workflow redakcyjny, oddzielenie obchodów liturgicznych od osób, publiczne filtry
widoczności, relacyjny model źródeł oraz działające buildy obu aplikacji Next.js.

Najpoważniejsze ryzyka dotyczą bezpieczeństwa i integralności procesu redakcyjnego:

- status publikacji można zmienić zwykłym endpointem edycji, omijając workflow i
  uprawnienie `persons:publish`;
- publiczne endpointy mediów ujawniają również metadane zasobów roboczych;
- środowisko backendu zawiera znane podatności w bibliotekach obsługujących HTTP,
  upload i obrazy;
- deklarowane full-text search nie jest utrzymywane ani używane;
- wersjonowanie nie zapewnia optimistic locking, więc równoległe edycje mogą się
  nadpisywać;
- aktualny zestaw testów nie przechodzi i nie spełnia zadeklarowanego progu 80%.

Nie znaleziono aktywnego P0 (potwierdzonej utraty danych, przejęcia uwierzytelnienia
lub niedziałającej aplikacji). Zidentyfikowane P1 muszą jednak zostać zamknięte przed
udostępnieniem systemu w Internecie.

## Status po refaktoryzacji

Poniższy status jest aktualizacją wykonawczą do historycznego pomiaru bazowego.
Nie zmienia pierwotnych findings ani ocen, dzięki czemu dokument zachowuje wartość
porównawczą.

Stan na 2026-09-06 po kolejnych etapach refaktoryzacji:

| Kontrola | Wynik po zmianach |
| --- | --- |
| Backend pytest | **218 passed**, 0 failures, 0 errors, 0 warnings |
| Backend coverage | **82.82%**, wymagany próg 80% spełniony |
| Testy integracyjne | izolowany PostgreSQL z realnymi JSONB, TSVECTOR i pgvector |
| `alembic current` / heads | `0016_person_names`, jeden head |
| Nowa pusta baza | upgrade 0001 → 0016 oraz downgrade/re-upgrade 0016: PASS |
| `alembic check` | PASS na bazie developerskiej i świeżej bazie |
| `pip-audit` | 0 znanych podatności |
| `npm audit` | 0 znanych podatności w panelu i portalu |
| Ruff / strict mypy | PASS, mypy analizuje 109 plików źródłowych |
| Admin i web | ESLint, TypeScript, produkcyjne buildy Webpack i krytyczne E2E: PASS |
| Kontrakt błędów API | wspólny envelope z kodem, komunikatem, `detail`, `details` i `request_id` |
| Granice tras Next.js | spójne `error`, `loading`, `not-found`; 404 odróżnione od awarii API |
| Sesja panelu | access token tylko w pamięci, rotowany refresh w cookie HttpOnly, bramka chronionego layoutu |
| Formularz osoby | 379-liniowy orkiestrator, osobne sekcje UI, schema i mapper payloadu |
| Produkcyjny stack | świeża baza, migracje, API, web, admin i Nginx: PASS; procesy aplikacyjne non-root |
| Backup/restore PostgreSQL | format custom, restore 43 tabel, Alembic 0016: PASS |
| Obserwowalność | poprawny JSON logging, request ID, Prometheus i opcjonalny Sentry |
| Pydantic / Alembic / Ruff config | zdeprecjonowane konfiguracje usunięte |
| Hashowanie haseł | bezpośredni bcrypt, zgodny z istniejącymi hashami Passlib |
| Granice warstw backendu | PASS; application, domain i infrastructure nie importują warstwy HTTP |

Zamknięte zostały wszystkie P1 z listy Top 10:

- publikacja jest dostępna wyłącznie przez workflow i osobne uprawnienie;
- katalogi prywatnych mediów wymagają autoryzacji;
- refresh tokeny są rotowane i unieważniane, a login ma rate limiting;
- zależności backendu są zablokowane lockfile'em i nie mają znanych podatności;
- edycja osób ma optimistic locking;
- wyszukiwanie korzysta z utrzymywanego, ważonego PostgreSQL FTS;
- integracje działają na PostgreSQL, a pełny suite przekracza próg coverage;
- modele i migracje są zgodne, w tym indeksy częściowe i server defaults.

Moduł AI otrzymał dodatkowe testy providerów oraz integracje z pgvector. Przy okazji
naprawiono obsługę embeddingów zwracanych jako tablice NumPy i licznik rekordów z
tagami AI, który wcześniej traktował JSON `null` jak faktyczną listę tagów.

Powstał automatyczny CI z lintem, strict mypy, testami/coverage, audytem zależności,
kontrolą migracji, buildami frontendów oraz smoke testem całego stosu produkcyjnego.
Obrazy backendu i Next.js działają jako użytkownicy nie-root; DB i Redis są w
prywatnej sieci, migracja jest osobnym krokiem, storage ma kontrolowanego właściciela,
a Nginx wystawia tylko portal, panel i API. Produkcja odrzuca placeholderowe lub
współdzielone sekrety, niebezpieczne wildcardy host/CORS i niezabezpieczone cookies.

Najważniejsze otwarte ryzyka są teraz klasy P2/P3: brak zewnętrznego TLS i
platformowego zarządzania sekretami, skonfigurowanych reguł alertów, testu
obciążenia oraz zautomatyzowanego release/CD do konkretnego środowiska.
Kod udostępnia poprawne logi JSON, Prometheus i opcjonalny Sentry, ale odbiorniki i
alerty są zadaniem platformowym. Backup PostgreSQL ma działający restore drill,
lecz nadal wymaga harmonogramu, retencji, szyfrowania, kopii poza hostem i objęcia
storage plikowego. Granice warstw backendu są egzekwowane bez wyjątków; w kodzie
pozostają duże routery oraz brak docelowej warstwy i18n. Bieżąca gotowość wykonawcza to
**BETA**; przed publicznym wdrożeniem nadal trzeba zamknąć wymienione kroki
operacyjne.

## Repository discovery

```text
all-saints/
├── apps/
│   ├── backend/
│   │   ├── alembic/              # migracje 0001–0009
│   │   ├── src/
│   │   │   ├── application/      # serwisy przypadków użycia i AI
│   │   │   ├── core/             # konfiguracja, JWT, middleware
│   │   │   ├── domain/           # modele SQLAlchemy i enumy domenowe
│   │   │   ├── infrastructure/   # DB, Redis, storage, importy
│   │   │   ├── presentation/     # FastAPI i /api/v1
│   │   │   └── workers/          # Celery
│   │   └── tests/                # unit + integration
│   ├── admin/                    # Next.js App Router, panel redakcyjny
│   └── web/                      # Next.js App Router, portal publiczny
├── design/mockups/               # materiały projektowe
├── infrastructure/
│   ├── docker/                   # development compose
│   ├── nginx/                    # konfiguracja reverse proxy
│   └── monitoring/               # Prometheus + Grafana
└── Makefile                      # komendy developerskie, część nieaktualna
```

### Odpowiedzialności i zależności

```text
Browser
  ├─> apps/admin (Next.js) ─┐
  └─> apps/web   (Next.js) ─┴─> FastAPI /api/v1
                                  ├─> application services
                                  ├─> SQLAlchemy async ─> PostgreSQL + pgvector
                                  ├─> Redis / Celery
                                  ├─> MinIO / S3
                                  └─> OpenAI albo Ollama
```

Podział na `presentation → application → domain/infrastructure` jest rozsądny i nie
wymaga przepisywania do pełnego DDD. Granica jest jednak niekonsekwentna: część
routerów zawiera bezpośrednie operacje SQL, a serwisy aplikacyjne importują schematy
warstwy prezentacji. Docelowo schematy przypadków użycia powinny należeć do warstwy
application albo być zastąpione małymi typami wejścia/wyjścia.

## Rzeczywisty stack

### Backend

- Python 3.12, FastAPI 0.111, Uvicorn/Gunicorn.
- SQLAlchemy 2 async, asyncpg, PostgreSQL 16, pgvector, Alembic.
- Pydantic v2 i pydantic-settings.
- JWT przez `python-jose`, Passlib/bcrypt, refresh tokeny hashowane w DB.
- Redis, Celery, MinIO/S3, OpenAI/Ollama.
- Loguru, Prometheus, zależność Sentry (bez inicjalizacji).
- Eksporty przez openpyxl, python-docx i WeasyPrint.

### Frontend

- Next.js 16.3.1 App Router, React 19.2.8, TypeScript strict.
- Tailwind CSS 4, Radix/Shadcn-style primitives.
- Axios, TanStack Query/Table, Zustand, React Hook Form, Zod.
- Brak biblioteki i warstwy i18n; UI jest obecnie przede wszystkim po polsku.

### Infrastructure i data

- Development Docker Compose: PostgreSQL/pgvector, Redis, backend, opcjonalny
  profil AI z Celery/Flower, MinIO, Mailhog, Prometheus i Grafana.
- Nginx istnieje, ale odwołuje się do usług admin/web wyłączonych w compose.
- Brak production compose, frontendowych Dockerfile, `.dockerignore` i CI/CD.
- Redis jest skonfigurowany, ale cache i rate limiting nie są wpięte w główne flow.

## Baseline

Wyniki są zapisane przed refactoringiem. Nie obejmują wymyślonych metryk.

| Kontrola | Wynik bazowy |
| --- | --- |
| Admin ESLint | PASS |
| Admin TypeScript `tsc --noEmit` | PASS |
| Web ESLint | PASS |
| Web TypeScript `tsc --noEmit` | PASS |
| Admin `next build --webpack` | PASS, 19 tras |
| Web `next build --webpack` | PASS |
| Domyślny Turbopack build | FAIL w sandboxie + błędne wykrycie root lockfile |
| Backend pytest | 69 passed, 4 failed, 10 errors |
| Backend coverage | 65.2%, wymagane 80% |
| Ruff | 150 błędów, 141 automatycznie naprawialnych |
| Black check | 43 pliki wymagają formatowania |
| mypy | FAIL przed analizą: duplikat modułu `models` przez brak `__init__.py` |
| `pip check` | PASS |
| npm audit, produkcyjne zależności | 0 podatności w obu aplikacjach |
| pip-audit, zainstalowane środowisko | 62 wpisy w 10 pakietach |
| `alembic current` | `0009_expand_countries (head)` |
| `alembic heads` | jeden head |
| Nowa pusta baza: upgrade | PASS 0001 → 0009 |
| Nowa pusta baza: downgrade -1 → upgrade | PASS |
| `alembic check` | FAIL, duży drift modeli względem migracji |

### Przyczyny niedziałających testów

- fixture integracyjna używa SQLite in-memory, podczas gdy modele zawierają typy
  PostgreSQL (`INET`, `JSONB`, `TSVECTOR`, pgvector);
- dwa testy oczekują domyślnych wartości Pythona przed flush, chociaż wartości są
  realizowane przez mechanizm SQLAlchemy;
- mock restore nie zawiera nowej relacji `orders`;
- test migracji oczekuje starego heada `0004`, podczas gdy repo ma `0009`.

## Co wykonano dobrze

1. Publiczne listy i szczegóły osób wymuszają `published` i `deleted_at IS NULL`.
2. Kalendarz, zakony i wyniki AI również filtrują osoby nieopublikowane.
3. RBAC jest ładowane z bazy przy każdym requestcie; role z JWT nie są bezkrytycznie
   uznawane za źródło uprawnień.
4. Refresh tokeny są hashowane w bazie i przesyłane przez HttpOnly cookie.
5. Upload obrazu waliduje format po dekodowaniu, limity rozmiaru/pikseli, generuje
   bezpieczny klucz i ponownie koduje plik do WebP.
6. Model `Feast` wymusza dokładnie jeden target i posiada użyteczne częściowe unique
   indeksy dla daty, kalendarza i wpisu primary.
7. `LiturgicalObservance` poprawnie oddziela tytuły maryjne i święta Pańskie od
   encji osoby.
8. Schematy Pydantic dobrze walidują enumy, UUID, limity i większość pól wejściowych.
9. Oba frontendowe projekty przechodzą strict typecheck, lint i build Webpack.
10. Projekt ma działające health/readiness, request ID, metryki Prometheus i
    sensowne punkty rozszerzeń dla storage oraz AI.

## Findings P0/P1

### SEC-001

- **Severity:** P1
- **Category:** Authorization / workflow
- **File:** `apps/backend/src/presentation/api/v1/persons/router.py`
- **Lines:** 173–195, 221–244
- **Problem:** Create i zwykły PATCH akceptują pole `status`. Redaktor posiada
  `persons:create/update`, ale nie `persons:publish`, więc może bezpośrednio zapisać
  `published` i ominąć przejścia oraz warunki kolejki redakcyjnej.
- **Why it matters:** Jest to mass assignment i eskalacja uprawnień w krytycznym
  procesie publikacji.
- **Suggested fix:** Zachować pola kontraktu dla kompatybilności, ale create wymusić
  jako `draft`, a zmianę statusu odrzucać w zwykłym PATCH. Publikacja wyłącznie przez
  endpoint transition; target `published` wymaga `persons:publish`.
- **Risk:** Medium; zaostrza dotychczasowe niebezpieczne zachowanie API.
- **Estimated complexity:** Small.

### SEC-002

- **Severity:** P1
- **Category:** Information disclosure
- **File:** `apps/backend/src/presentation/api/v1/sources/router.py`
- **Lines:** 491–505, 536–546
- **Problem:** Listy obrazów i dokumentów są publiczne. Dokumenty nie filtrują
  `is_public`, a obrazy mogą należeć do szkiców i rekordów w recenzji.
- **Why it matters:** Ujawnia tytuły, URL-e, storage keys, licencje i metadane treści,
  które nie przeszły publikacji.
- **Suggested fix:** Traktować obecne katalogowe endpointy jako zasoby admina i
  wymagać `images:read` / `sources:read`. Publiczne obrazy zwracać przez opublikowane
  profile; ewentualny publiczny katalog dokumentów zbudować osobno z `is_public` i
  kontrolą statusu osoby.
- **Risk:** Medium; może wpłynąć na nieznanych zewnętrznych klientów.
- **Estimated complexity:** Small.

### SEC-003

- **Severity:** P1
- **Category:** Dependencies
- **File:** `apps/backend/pyproject.toml`
- **Lines:** sekcje authentication, HTTP/storage i exports
- **Problem:** `pip-audit` dla faktycznie zainstalowanego środowiska zgłosił 62
  wpisy w 10 pakietach, m.in. Starlette, python-multipart, Pillow, cryptography,
  lxml i WeasyPrint.
- **Why it matters:** Najbardziej istotne pakiety przetwarzają niezaufane requesty,
  multipart i obrazy.
- **Suggested fix:** Aktualizować kompatybilnymi grupami, zaczynając od FastAPI /
  Starlette / multipart i Pillow; po każdej grupie uruchomić API, upload i eksporty.
  Dodać automatyczny audit zależności.
- **Risk:** Medium/High z powodu zmian transitive dependencies.
- **Estimated complexity:** Medium.

### AUTH-001

- **Severity:** P1
- **Category:** Authentication
- **File:** `apps/backend/src/presentation/api/v1/auth/router.py`
- **Lines:** login, refresh i change-password
- **Problem:** Refresh token nie jest rotowany przy użyciu, a zmiana hasła nie
  unieważnia istniejących sesji. Access token nie zawiera znacznika pozwalającego
  odrzucić token wystawiony przed zmianą hasła.
- **Why it matters:** Skradziona sesja pozostaje użyteczna po zmianie hasła.
- **Suggested fix:** Atomowa rotacja refresh tokenu, wykrywanie reuse, revocation
  wszystkich sesji przy zmianie hasła i walidacja `iat` względem
  `password_changed_at`.
- **Risk:** Medium; wymaga testów cookie i współbieżności.
- **Estimated complexity:** Medium.

### AUTH-002

- **Severity:** P1
- **Category:** Abuse prevention
- **File:** `apps/backend/src/infrastructure/cache/redis_client.py`,
  `apps/backend/src/presentation/api/v1/auth/router.py`
- **Lines:** `RateLimiter`, `login`
- **Problem:** Istnieje klasa rate limitera i odpowiedź 429 w OpenAPI, ale limiter
  nie jest nigdzie używany. Ochrona konta jest tylko per-account.
- **Why it matters:** Endpoint login można bombardować z wielu adresów; można też
  celowo blokować znane konta.
- **Suggested fix:** Limit IP + znormalizowany email, z bezpiecznym fallbackiem przy
  niedostępnym Redis i spójną odpowiedzią 429.
- **Risk:** Medium; zły limit może blokować legalnych użytkowników.
- **Estimated complexity:** Medium.

### DB-001

- **Severity:** P1
- **Category:** Concurrency / data integrity
- **File:** `apps/backend/src/application/services/person_service.py`
- **Lines:** 473–540
- **Problem:** Pole `version` jest zwiększane tylko w pamięci. Brak
  `version_id_col`, oczekiwanej wersji w request lub blokady wiersza.
- **Why it matters:** Dwie równoległe edycje mogą się nadpisać; unique snapshot może
  zamienić utratę zmiany w nieprzewidywalny konflikt transakcji.
- **Suggested fix:** Optimistic locking SQLAlchemy i kontrakt `expected_version`
  (początkowo opcjonalny/deprecacyjny), mapowany na HTTP 409.
- **Risk:** Medium; wpływa na update i workflow.
- **Estimated complexity:** Medium.

### SEARCH-001

- **Severity:** P1
- **Category:** Performance / correctness
- **File:** `apps/backend/src/application/services/person_service.py`,
  `apps/backend/src/workers/tasks/maintenance.py`
- **Lines:** `list_persons`, `refresh_search_vectors`
- **Problem:** Model i indeks GIN deklarują `search_vector`, ale nie ma triggera ani
  aktualizacji wartości. Zapytanie używa `%term% ILIKE` także na pełnym biogramie,
  a task odświeżający jest stubem.
- **Why it matters:** Indeks jest martwy, ranking nie istnieje, a przy kilkunastu
  tysiącach długich biografii wyszukiwanie będzie skanować tabelę.
- **Suggested fix:** Nowa migracja z funkcją/triggerem, ważonym `tsvector`, unaccent
  i GIN; fallback trigram dla literówek; zapytanie używające ranking.
- **Risk:** Medium; językowa normalizacja wymaga testów polskich nazw.
- **Estimated complexity:** Medium/Large.

### DB-002

- **Severity:** P1
- **Category:** Schema drift
- **File:** `apps/backend/alembic`, modele domenowe
- **Lines:** cały metadata diff
- **Problem:** `alembic check` zgłasza setki różnic: indeksy, komentarze, defaulty i
  constrainty. Część to szum konfiguracyjny, część rzeczywisty drift.
- **Why it matters:** Kolejna automatyczna migracja może wygenerować ogromny,
  ryzykowny i trudny do review diff.
- **Suggested fix:** Najpierw ujednolicić naming/default metadata i konfigurację
  compare, potem utworzyć jedną nową, ręcznie sprawdzoną migrację naprawczą. Nie
  zmieniać migracji 0001–0009.
- **Risk:** High, jeżeli poprawka zostanie wygenerowana bez analizy.
- **Estimated complexity:** Large.

### TEST-001

- **Severity:** P1
- **Category:** Regression safety
- **File:** `apps/backend/tests/conftest.py`, testy unit/integration
- **Lines:** fixture `TEST_DATABASE_URL` i cztery nieaktualne asercje/mocki
- **Problem:** Główny test suite ma 4 failures, 10 errors i 65.2% coverage przy
  progu 80%. Testy integracyjne uruchamiają PostgreSQL-only metadata na SQLite.
- **Why it matters:** Nie ma wiarygodnej bramki regresji dla auth, RBAC i CRUD.
- **Suggested fix:** Integracje uruchamiać na izolowanej bazie PostgreSQL, unit testy
  pozostawić bez DB albo na świadomie przenośnym podzbiorze modeli; naprawić stare
  oczekiwania i podnieść coverage krytycznych flow.
- **Risk:** Low/Medium.
- **Estimated complexity:** Medium.

## Findings P2/P3

### DX-001

- **Severity:** P2
- **Status po refaktoryzacji:** Zamknięte 2026-09-06. `apps/backend/poetry.lock`
  jest wersjonowany, kopiowany do deterministycznych etapów obrazu i sprawdzany przez
  `poetry check --lock`; instalacja developerska oraz produkcyjna korzysta z lockfile.
  Dependabot aktualizuje zależności kontrolowanymi pull requestami, a CI wykonuje
  `pip-audit` na zablokowanym zestawie.
- **Category:** Reproducibility
- **File:** `.gitignore`, `apps/backend/pyproject.toml`
- **Lines:** reguła `poetry.lock`
- **Problem:** Backend nie ma lockfile, a `.gitignore` jawnie go ignoruje.
- **Why it matters:** Developerzy i obrazy mogą instalować różne wersje, co już
  wpływa na audit bezpieczeństwa.
- **Suggested fix:** Wersjonować `poetry.lock`; aktualizacje robić kontrolowanie.
- **Risk:** Low.
- **Estimated complexity:** Small.

### OPS-001

- **Severity:** P2
- **Status po refaktoryzacji:** Zamknięte 2026-09-06. Produkcyjny Compose uruchamia
  migrator, backend, dwa samodzielne obrazy Next.js i Nginx; PostgreSQL i Redis nie
  publikują portów i działają w sieci wewnętrznej. Obrazy aplikacyjne są non-root,
  usługi mają healthchecki, a pełny smoke test świeżego projektu potwierdził routing,
  ukrycie dokumentacji, migrację do `0016_person_names` oraz backup/restore 43 tabel.
  `PROD_PROJECT` umożliwia izolowane uruchomienia, a runbook opisuje bezpieczną rotację
  hasła istniejącego wolumenu PostgreSQL.
- **Category:** Deployment
- **File:** `infrastructure/docker`, `Makefile`
- **Lines:** prod targets i zakomentowane frontend services
- **Problem:** Brak production compose i Dockerfile dla frontendów. Nginx wskazuje
  usługi, których compose nie uruchamia. Brak `.dockerignore`.
- **Why it matters:** Nie istnieje powtarzalna ścieżka wdrożenia całego produktu.
- **Suggested fix:** Multi-stage, non-root obrazy, prywatna sieć dla DB/Redis,
  sekrety poza compose i healthchecki całego stacku.
- **Risk:** Medium.
- **Estimated complexity:** Medium.

### CI-001

- **Severity:** P2
- **Status po refaktoryzacji:** Zamknięte 2026-09-05. CI wykonuje kontrolę migracji,
  Ruff, strict mypy, pytest z progiem coverage, `pip-audit`, `npm audit` dla obu
  frontendów, lint, typecheck, buildy, krytyczne E2E oraz smoke całego stosu
  produkcyjnego z próbą backup/restore. Dependabot co tydzień proponuje grupowane
  aktualizacje minor/patch dla Poetry, obu lockfile'ów npm i GitHub Actions.
- **Category:** CI/CD
- **File:** repo root
- **Lines:** brak `.github/workflows`
- **Problem:** Brak CI dla lint, typecheck, testów, buildów, migracji i skanowania.
- **Why it matters:** Main nie ma automatycznej quality gate.
- **Suggested fix:** Minimalny workflow z PostgreSQL/Redis service containers,
  backend checks, oba buildy i dependency audit.
- **Risk:** Low.
- **Estimated complexity:** Medium.

### DX-002

- **Severity:** P2
- **Status po refaktoryzacji:** Zamknięte 2026-09-04. `make install` korzysta z
  deterministycznego obrazu backendu i `npm ci`, polecenia testów/lint/type-check
  wskazują rzeczywisty workdir `/app`, a konfiguracja produkcyjna istnieje i jest
  walidowana przez `prod-check`. Usunięto cele MkDocs bez konfiguracji. Eksporty
  XLSX/PDF są jawnie oznaczone jako planowane, E2E uruchamiają rzeczywiste smoke
  testy Playwright, a `openapi-export` generuje aktualny kontrakt bezpośrednio z
  aplikacji FastAPI.
- **Category:** Developer experience
- **File:** `Makefile`
- **Lines:** test, format, type-check, prod, export
- **Problem:** Komendy wskazują ścieżki nieistniejące wewnątrz kontenera, brakujące
  skrypty npm, nieistniejący compose prod i moduły export.
- **Why it matters:** Dokumentowana ścieżka pracy nie jest wykonywalna.
- **Suggested fix:** Uzgodnić Makefile z faktycznymi workdir i package scripts;
  nieistniejące funkcje oznaczyć jako planowane albo usunąć.
- **Risk:** Low.
- **Estimated complexity:** Small.

### ARCH-001

- **Severity:** P2
- **Status po refaktoryzacji:** Zamknięte 2026-09-04. Zamknięto część frontendową
  oraz wydzielono
  z `EditorialService` stabilną politykę kompletności, priorytetów, problemów jakości
  i wykrywania duplikatów, a także osobny reader statystyk i weryfikacji źródeł.
  Serwis redakcyjny zmniejszył się z ok. 1154 do 552 linii, zachowując dotychczasowe
  sygnatury i kontrakty. Z `AIService` wydzielono modele wynikowe i deterministyczny
  mapper kolejki sugestii; serwis zmniejszył się z 881 do 592 linii. Nie wprowadzono
  ogólnego `BaseService` ani zmian publicznego kontraktu API.
- **Category:** Maintainability / SRP
- **File:** `editorial_service.py`, `ai_service.py`, `person-form.tsx`
- **Lines:** odpowiednio 552, 592 i 379 linii po podziale
- **Problem:** Moduły agregują wiele niezależnych odpowiedzialności i reguł.
- **Why it matters:** Zmiany mają duży blast radius i utrudniają testy.
- **Suggested fix:** Wydzielać tylko stabilne pionowe fragmenty: quality queries,
  workflow policy, AI queue mapper oraz sekcje formularza. Bez BaseService.
- **Risk:** Medium.
- **Estimated complexity:** Medium/Large.

### ARCH-002

- **Severity:** P2
- **Status po refaktoryzacji:** Zamknięte 2026-09-05. Ustalono i udokumentowano
  jedną politykę unit-of-work: serwisy flushują, a granica requestu lub workera
  commit/rollbackuje. Osiem pionów — zakony wraz z członkostwami, kalendarz
  liturgiczny wraz z obchodami, osoby z wersjonowaniem, audytem i workflow
  redakcyjnym, kontrola dostępu użytkowników, ról i uprawnień oraz źródła i media
  z wersjonowaniem relacji, geografia, taksonomia i papieże, a także zapis wyników
  AI i uwierzytelnianie — nie wykonują już przypadkowych commitów wewnątrz
  przypadków użycia HTTP. Workery AI są jawnymi właścicielami transakcji i
  commitują każdy udany element batcha osobno. Odmowy logowania zapisuje
  `AuthenticationSecurityRecorder` w izolowanej transakcji, dzięki czemu audit,
  licznik prób i blokada konta przeżywają rollback odpowiedzi `401/403`. Testy
  integracyjne potwierdzają obie ścieżki, a bezpośrednie commity pozostały tylko
  w udokumentowanych granicach unit-of-work.
- **Category:** Transactions
- **File:** `apps/backend/src/infrastructure/db/session.py` i serwisy
- **Lines:** `get_db_session` oraz jawne `commit()` w service/router
- **Problem:** Dependency commit/rollback i serwisy jednocześnie posiadają
  transakcję, co daje podwójny commit i niejasną atomowość.
- **Why it matters:** Trudno składać kilka operacji w jeden przypadek użycia.
- **Suggested fix:** Jedna polityka: application service flushuje, a granica requestu
  commit/rollback; wyjątkowe transakcje jawne przez `session.begin()`.
- **Risk:** High przy zmianie masowej; wdrażać przypadek po przypadku.
- **Estimated complexity:** Large.

### ARCH-003

- **Severity:** P2
- **Status po refaktoryzacji:** Zamknięte 2026-09-05. Komendy pionów zakonów,
  kalendarza i osób oraz modele wynikowe redakcji należą do warstwy application;
  enum członkostwa zakonnego należy do domeny. Serwisy i importery nie zależą już od
  schematów HTTP. Moduły presentation zachowują kompatybilne re-eksporty dla
  istniejących importów i nazw OpenAPI. Test architektury ma pustą listę wyjątków i
  blokuje każdą zależność `application/domain/infrastructure -> presentation`.
- **Category:** Architecture / dependency direction
- **File:** `apps/backend/src/application`, `apps/backend/src/infrastructure`
- **Problem:** Serwisy przypadków użycia i importer danych importują schematy z
  warstwy prezentacji, przez co zależność biegnie od logiki do HTTP.
- **Why it matters:** Przypadki użycia są trudniejsze do testowania i ponownego użycia,
  a zmiana kontraktu transportowego może wymuszać zmianę logiki aplikacyjnej.
- **Suggested fix:** Wydzielać komendy i typy domenowe pion po pionie, utrzymując
  schematy transportowe jako cienkie adaptery kompatybilne z OpenAPI.
- **Risk:** Medium; migracja szeroka, dlatego wykonywana przyrostowo.
- **Estimated complexity:** Large.

### VER-001

- **Severity:** P2
- **Status po refaktoryzacji:** Zamknięte 2026-09-04. Jeden wersjonowany serializer
  zachowuje zgodny wstecznie zestaw pól osoby oraz aktywne patronaty, źródła, obrazy,
  przynależności zakonne, beatyfikację i kanonizację. Snapshot ma jawny numer schematu.
  Tworzenie, edycja, soft delete i restore oraz zmiany źródeł, obrazów i członkostw
  zapisują nową wersję z autorem; patronaty i avatar są wersjonowane w operacji edycji
  osoby. Wersje pozostają bezterminowo jako nieusuwalna historia redakcyjna — nie ma
  automatycznego pruningu.
- **Category:** Versioning / audit
- **File:** `apps/backend/src/application/services/person_service.py`
- **Lines:** snapshot create/update/delete/restore
- **Problem:** Snapshot zawiera tylko skalarne kolumny `Person`, bez patronatów,
  źródeł, obrazów i zakonów. Soft delete nie tworzy wersji ani nie używa `user_id`.
- **Why it matters:** Historia nie pozwala wiernie odtworzyć ani wyjaśnić rekordu.
- **Suggested fix:** Jawny serializer kompletnego snapshotu i wersje dla delete,
  restore oraz zmian relacji; określić politykę retencji.
- **Risk:** Medium.
- **Estimated complexity:** Medium.

### VER-002

- **Severity:** P2
- **Status po refaktoryzacji:** Zamknięte 2026-09-04. `changed_at` używa teraz
  timezone-aware `datetime` w modelu i kontrakcie API oraz `TIMESTAMPTZ` w PostgreSQL.
  Migracja przed zmianą typu jawnie waliduje wszystkie istniejące wartości i przerywa
  się przy błędnym formacie; downgrade zachowuje reprezentację czasu jako tekst.
- **Category:** Data model
- **File:** `apps/backend/src/domain/hagiography/models.py`
- **Lines:** `PersonVersion.changed_at`
- **Problem:** Czas zmiany jest tekstem zamiast timezone-aware datetime.
- **Why it matters:** Walidacja, sortowanie po czasie i zapytania zakresowe są
  zależne od formatu stringa.
- **Suggested fix:** Nowa kolumna datetime lub bezpieczna migracja typu z walidacją.
- **Risk:** Medium.
- **Estimated complexity:** Small/Medium.

### DATA-001

- **Severity:** P2
- **Status po refaktoryzacji:** Zamknięte 2026-09-05. Globalnie unikalny slug jest
  celowo rezerwowany również przez rekord usunięty miękko. Generator uwzględnia takie
  rekordy, przywrócenie zachowuje kanoniczny URL, a nowy rekord o tej samej nazwie
  otrzymuje sufiks. Decyzję i konsekwencje opisuje
  `docs/adr/0002-person-slug-after-soft-delete.md`, a pełny cykl chroni test
  integracyjny.
- **Category:** Soft delete
- **File:** `Person.slug`, restore flow
- **Lines:** unique slug i `_generate_unique_slug`
- **Problem:** Soft-deleted rekord nadal zajmuje globalnie unikalny slug. Nowy rekord
  dostaje suffix, a restore starego działa; oczekiwane zachowanie nie jest opisane.
- **Why it matters:** URL-e i canonical SEO mogą zmieniać się bez jasnej polityki.
- **Suggested fix:** Zachować obecne bezpieczne zachowanie jako ADR: slug nigdy nie
  jest ponownie używany. Alternatywa z partial unique wymaga jawnej obsługi konfliktu
  przy restore.
- **Risk:** Low dla dokumentacji, High dla zmiany polityki.
- **Estimated complexity:** Small/Large zależnie od decyzji.

### SEARCH-002

- **Severity:** P2
- **Status po refaktoryzacji:** Zamknięte 2026-09-04. Nazwy alternatywne są
  przechowywane w encji `PersonName` z językiem, rodzajem i wartością
  znormalizowaną bez znaków diakrytycznych. Formularz redakcyjny obsługuje aliasy,
  skróty, imiona świeckie/zakonne i transliteracje, a publiczny profil eksponuje je
  użytkownikowi i w `alternateName` JSON-LD. Wyszukiwanie PostgreSQL uwzględnia
  aliasy oraz nazwy z `PersonTranslation` przez dokładne dopasowanie wartości
  znormalizowanej i indeksowane podobieństwo trigramowe. Migracja zachowuje
  istniejące `original_name` i `religious_name` przez backfill.
- **Category:** Domain search
- **File:** modele Person/Translation i `list_persons`
- **Lines:** pola nazw i warunek search
- **Problem:** Brak encji aliasów; tłumaczenia nie uczestniczą w wyszukiwaniu.
- **Why it matters:** `Karol Wojtyła`, `Ioannes Paulus II` czy `JPII` nie są
  niezawodnie mapowane na ten sam rekord.
- **Suggested fix:** `PersonName`/alias z language, kind i normalized value, unikalny
  indeks oraz włączenie do FTS/trigram.
- **Risk:** Medium.
- **Estimated complexity:** Medium.

### DATA-002

- **Severity:** P2
- **Status po refaktoryzacji:** Zamknięte 2026-09-04. W całym kodzie nie było
  odczytów ani zapisów legacy `Person.embedding_vector`, a lokalna kolumna była pusta.
  Jedynym źródłem prawdy jest teraz `PersonEmbedding.embedding` typu pgvector.
  Migracja odmawia usunięcia starej kolumny, jeśli na innym środowisku zawiera ona
  dane; downgrade odtwarza nullable JSONB wyłącznie jako pole kompatybilności.
- **Category:** AI / schema
- **File:** model Person i `PersonEmbedding`
- **Lines:** legacy `embedding_vector` oraz tabela pgvector
- **Problem:** Istnieją dwa konkurencyjne miejsca na embedding: JSONB w Person i
  dedykowana tabela pgvector.
- **Why it matters:** Niejasne źródło prawdy i ryzyko rozjazdu danych.
- **Suggested fix:** Potwierdzić brak odczytów legacy, przestać zapisywać JSONB, a
  usunięcie kolumny odłożyć do osobnej migracji po okresie kompatybilności.
- **Risk:** Medium.
- **Estimated complexity:** Small/Medium.

### LIT-001

- **Severity:** P2
- **Status po refaktoryzacji:** Zamknięte decyzją architektoniczną 2026-09-05.
  `docs/adr/0004-versioned-liturgical-calendar-resolution.md` rozdziela obchód,
  wersję kalendarza, typowaną regułę, wyjątek i wynik dla konkretnego roku. Obecny
  kontrakt został jawnie ograniczony do dat stałych: odrzuca pozorne pola reguł
  ruchomych, a nierozstrzygnięte rekordy nie trafiają do publicznych widoków. Migracja
  modelu nastąpi dopiero po zatwierdzeniu źródeł dla kalendarza powszechnego, polskiego
  i pierwszych kalendarzy własnych.
- **Category:** Liturgical domain
- **File:** `apps/backend/src/domain/liturgy/models.py`
- **Lines:** `Feast.month/day/date_note/is_moveable`
- **Problem:** Model oznacza święto jako ruchome, lecz ma jedynie opis tekstowy; brak
  reguły obliczeniowej, transferu, pierwszeństwa i roku obowiązywania kalendarza.
- **Why it matters:** Nie da się automatycznie i audytowalnie wyznaczyć Wielkanocy,
  uroczystości zależnych ani zmian lokalnego kalendarza w konkretnym roku.
- **Suggested fix:** Nie zmieniać teraz modelu; przygotować osobny ADR dla reguł,
  wyjątków rocznych i wersjonowania kalendarzy.
- **Risk:** High domenowo.
- **Estimated complexity:** Large.

### API-001

- **Severity:** P2
- **Status po refaktoryzacji:** Zamknięte 2026-09-04. Handler obsługuje również
  `HTTPException`, zachowuje przejściowe pole `detail`, dodaje stabilny kod błędu,
  `message`, `details` i skorelowany `request_id`; pokrywają to testy kontraktowe i
  integracyjne.
- **Category:** Error handling
- **File:** FastAPI exception handlers i routery
- **Lines:** wiele `HTTPException(detail=...)`
- **Problem:** Globalne błędy mają `{error,message,details}`, a endpointy najczęściej
  zwracają `{detail}`; frontend musi obsługiwać oba formaty.
- **Why it matters:** Kontrakt błędów jest nieprzewidywalny i trudny do wersjonowania.
- **Suggested fix:** Jeden envelope i kody domenowe, z adapterem zachowującym
  `detail` przez okres przejściowy.
- **Risk:** Medium ze względu na kompatybilność.
- **Estimated complexity:** Medium.

### API-002

- **Severity:** P2
- **Status po refaktoryzacji:** Zamknięte 2026-09-05. Rosnące listy miejsc,
  diecezji, kościołów, bibliografii, źródeł historycznych, obrazów, dokumentów,
  tagów i zawodów mają wspólne, ograniczone parametry `page` / `per_page` oraz
  udokumentowane nagłówki `X-Total-Count`, `X-Page`, `X-Per-Page` i
  `X-Total-Pages`. Ciało pozostaje tablicą JSON dla kompatybilności ze starszymi
  klientami. Panel korzysta z jawnego limitu i pełnych liczników z nagłówków, a CORS
  je eksponuje. Małe słowniki kontrolowane nadal zwracają pełne listy.
- **Category:** Pagination
- **File:** geography/taxonomy/source routers
- **Lines:** list endpoints
- **Problem:** Kilka zasobów zwraca niepaginowane listy; dla krajów jest to małe,
  ale places, churches, sources i rosnące słowniki nie mają stabilnego limitu/cursora.
- **Why it matters:** Odpowiedzi i czas serializacji będą rosnąć z bazą.
- **Suggested fix:** Wspólny, jawny kontrakt page/per_page dla zasobów rosnących;
  małe zamknięte słowniki pozostawić jako pełne listy.
- **Risk:** Medium dla klientów.
- **Estimated complexity:** Medium.

### FE-001

- **Severity:** P2
- **Status po refaktoryzacji:** Zamknięte 2026-09-04. Access token nie jest już
  zapisywany w Web Storage i żyje wyłącznie w pamięci klienta. Pełny reload odbudowuje
  sesję przez rotowany cookie HttpOnly przed wyrenderowaniem chronionego layoutu;
  równoległe odpowiedzi 401 współdzielą jedno żądanie refresh. Pozostawiono możliwość
  dalszego hardeningu przez BFF, ale pierwotne ryzyko trwałego JWT zostało usunięte.
- **Category:** Frontend security
- **File:** `apps/admin/lib/api.ts`, auth store
- **Lines:** localStorage access token
- **Problem:** Access token jest przechowywany w localStorage.
- **Why it matters:** Udany XSS daje bezpośredni dostęp do tokenu administratora.
- **Suggested fix:** Preferować krótko żyjący token w pamięci + rotowany HttpOnly
  refresh; docelowo BFF/sesja HttpOnly. Równolegle CSP bez zbędnych wyjątków.
- **Risk:** Medium/High z uwagi na zmianę flow logowania.
- **Estimated complexity:** Medium.

### FE-002

- **Severity:** P2
- **Status po refaktoryzacji:** Zamknięte 2026-09-04. Obie aplikacje mają granice
  `error/loading/not-found` zgodne z Next.js 16, retry oraz bezpieczny identyfikator
  błędu. Publiczne profile mapują na 404 wyłącznie odpowiedź HTTP 404, a awarie API
  trafiają do error boundary. Naprawiono też hydratację menu zależnego od RBAC.
- **Category:** Resilience / UX
- **File:** `apps/admin/app`, `apps/web/app`
- **Lines:** brak route-level `loading.tsx`, `error.tsx`, `not-found.tsx`
- **Problem:** Brak systemowych granic błędu i spójnych stanów route. Publiczne detail
  pages w części mapują każdy błąd pobrania na `notFound()`.
- **Why it matters:** Awaria API może wyglądać jak brak treści, a użytkownik nie ma
  ścieżki ponowienia.
- **Suggested fix:** Segmentowe error/loading/not-found i rozróżnienie 404 od 5xx.
- **Risk:** Low.
- **Estimated complexity:** Small/Medium.

### FE-003

- **Severity:** P2
- **Status po refaktoryzacji:** Zamknięte 2026-09-04. Główny formularz ma 379
  linii i pełni rolę orkiestratora zapisu, zapytań oraz nawigacji. Schema Zod,
  mapper payloadu i typy domenowe są w osobnym module, a dane podstawowe, daty,
  biografia, patronaty, kult i avatar mają niezależne komponenty. React Hook Form
  pozostaje jednym właścicielem stanu i kontrakt API nie został zmieniony.
- **Category:** Frontend maintainability
- **File:** `apps/admin/components/persons/person-form.tsx`
- **Lines:** ok. 1341
- **Problem:** Formularz łączy fetch słowników, transformacje payloadu, upload,
  walidację, tabs i kilkanaście sekcji UI.
- **Why it matters:** Trudno izolować regresje i testować pola domenowe.
- **Suggested fix:** Wydzielić sekcje formularza i mapper API; React Hook Form
  pozostawić jednym właścicielem stanu.
- **Risk:** Medium.
- **Estimated complexity:** Medium.

### I18N-001

- **Severity:** P2
- **Status po refaktoryzacji:** W realizacji od 2026-09-06. ADR 0005 rozdziela
  lokalizację UI od wersji językowych treści, zabrania dokładania kolejnych kolumn
  `_xx` i wskazuje `PersonTranslation` jako docelowe źródło prawdy. Oba frontendy
  mają typowany rejestr obsługiwanych języków i ładowane po stronie serwera słowniki;
  do pierwszego pionu przeniesiono metadata oraz globalne powłoki nawigacyjne. Publiczne
  endpointy osób przyjmują teraz walidowany parametr `locale` i zwracają jawne
  `localized_content` z językiem żądanym, rozstrzygniętym, źródłem oraz informacją o
  fallbacku. Resolver preferuje aktywny `PersonTranslation`, obsługuje tag regionalny
  i nie miesza brakujących pól z innym językiem; katalog nie zwraca pełnego biogramu.
  Chronione API tłumaczeń egzekwuje osobne RBAC, blokadę optymistyczną i edycję tylko
  w szkicu, a każdą zmianę włącza do wersji osoby i dziennika audytu. Recenzent ma
  wyłącznie odczyt tłumaczeń i zatwierdza cały rekord w istniejącym workflow.
  Backfill PL/EN ma osobne, domyślnie suche narzędzie: tworzy tylko brakujące
  projekcje, jest idempotentny i raportuje istniejące, usunięte, rozbieżne lub
  nienormalizowane tłumaczenia bez nadpisywania. Aktywne tłumaczenia uczestniczą
  również w ważonym FTS przez indeks GIN; `EXISTS`/skorelowany ranking zachowuje
  jedną osobę w wynikach niezależnie od liczby pasujących języków, a usunięte
  tłumaczenia są wykluczone. Katalog i profil publiczny pobierają jawny język treści,
  renderują spójną projekcję `localized_content`, a ich teksty UI są częścią typowanego
  słownika; lekka projekcja katalogowa zawiera także lokalizowane atrybuty
  ikonograficzne, bez pełnego biogramu i modlitw. Wspólne etykiety typów osób, epok,
  okresów, patronatów i wspólnot są oddzielone od stabilnych kluczy API i pobierane
  z typowanego słownika przez stronę główną, katalog, profil, kalendarz oraz zakony;
  stare polskie wartości zapytań pozostają wyłącznie izolowaną warstwą zgodności.
  Cały tekst strony głównej jest już w słowniku, a brak API lub opublikowanych danych
  pokazuje jawny stan pusty zamiast fikcyjnych statystyk, osób i wspólnot. Miesięczny
  i dzienny kalendarz oraz profile obchodów niebędących osobami korzystają już z
  tego samego słownika dla treści UI, metadata, dostępności i etykiet domenowych;
  formatery dat wymagają jawnego locale. Katalog i profil wspólnoty mają również
  słownikowe metadata, filtry, karty, fallbacki, stany puste i etykiety ładowania,
  przy zachowaniu stabilnych kluczy klasyfikacji w API. Publiczne 404, granica błędu,
  wszystkie warianty ładowania i dostępność awatarów korzystają ze słownikowego
  kontekstu przekazującego do klienta wyłącznie serializowalny wycinek treści. Tym
  samym wszystkie obecnie istniejące trasy portalu mają kompletną granicę UI-copy;
  pozostają teksty panelu oraz routing uruchamiany dopiero z kompletnym drugim
  językiem.
- **Category:** Internationalization
- **File:** oba frontendy i modele Person/Translation
- **Lines:** setki hardcoded strings
- **Problem:** UI nie ma warstwy tłumaczeń, a dane łączą kolumny `_pl/_en` z
  generycznym modelem translation.
- **Why it matters:** Dodanie it/es/fr/de/la wymaga zmian w wielu komponentach i
  nie ma jasno określonego źródła prawdy treści.
- **Suggested fix:** ADR dla i18n UI i danych; nowe języki wyłącznie w tabeli
  tłumaczeń, istniejące kolumny migrować stopniowo.
- **Risk:** High przy migracji danych.
- **Estimated complexity:** Large.

### OBS-001

- **Severity:** P2
- **Status po refaktoryzacji:** Zamknięte 2026-09-04. Sentry jest inicjalizowany
  wyłącznie z DSN, bez domyślnego PII i z kontrolowanym samplingiem. Po poprawnym
  uwierzytelnieniu middleware wzbogaca końcowy log requestu o `user_id` i e-mail,
  a `request_id` pozostaje wspólnym identyfikatorem logu, odpowiedzi, błędu i wpisu
  audytowego. `AuditLog` jest zapisywany atomowo z tworzeniem, edycją, usuwaniem,
  przywracaniem i publikacją postaci oraz ze zdarzeniami logowania, wylogowania,
  zmiany profilu i hasła. Snapshoty uwierzytelniania nie zawierają haseł ani tokenów.
- **Category:** Observability / audit
- **File:** config, middleware, identity models
- **Lines:** `SENTRY_DSN`, request logging, `AuditLog`
- **Problem:** Sentry jest zależnością i settingiem bez inicjalizacji; request log
  nie zawiera user_id; model `AuditLog` nie jest zapisywany przez flow biznesowe.
- **Why it matters:** Incydentu lub zmiany uprzywilejowanej nie da się łatwo
  prześledzić poza snapshotami Person.
- **Suggested fix:** Najpierw audit create/update/delete/publish/auth i korelacja z
  request_id; Sentry włączyć tylko z filtrem danych wrażliwych.
- **Risk:** Low/Medium.
- **Estimated complexity:** Medium.

### CACHE-001

- **Severity:** P3
- **Status po refaktoryzacji:** Zamknięte 2026-09-05. Redis ma jawnie ograniczone
  odpowiedzialności: atomowy limiter logowania, broker Celery i cache embeddingów.
  Usunięto nieużywany ogólny `CacheService` oraz martwe ustawienia TTL. Redis został
  utrzymany jako krytyczna zależność sondy readiness, co pokrywają testy stanów
  zdrowych i awarii każdej zależności. Cache odpowiedzi wymaga wcześniejszego
  benchmarku oraz jawnej strategii unieważniania.
- **Category:** Dead code / consistency
- **File:** `apps/backend/src/infrastructure/cache`
- **Lines:** cache manager, TTL i limiter
- **Problem:** Infrastruktura istnieje, ale nie jest używana przez endpointy; opis
  opcjonalnego Redis nie odpowiada readiness, które traktuje go jako wymagany.
- **Why it matters:** Utrzymywany jest kod bez efektu i niejasny kontrakt operacyjny.
- **Suggested fix:** Zdecydować, czy Redis jest krytyczny. Wpiąć tylko limiter i
  jeden profilowany cache albo usunąć martwe settingi.
- **Risk:** Low.
- **Estimated complexity:** Small/Medium.

### TOOL-001

- **Severity:** P3
- **Status po refaktoryzacji:** Zamknięte 2026-09-06. Ruff korzysta z aktualnej
  sekcji `[tool.ruff.lint]`, mypy działa w trybie strict dla 109 plików źródłowych,
  a 161 plików backendu i testów jest zgodnych z Black. `make lint`,
  `make format-check` i `make type-check` rozdzielają kontrolę jakości od modyfikacji
  kodu; CI wykonuje formatter w trybie tylko do odczytu jako osobną bramkę.
- **Category:** Code quality
- **File:** `apps/backend/pyproject.toml`, pakiety `src`
- **Lines:** Ruff config i brakujące `__init__.py`
- **Problem:** Konfiguracja Ruff używa zdeprecjonowanych kluczy, mypy nie startuje,
  Black zgłasza 43 pliki, Ruff 150 błędów.
- **Why it matters:** Narzędzia nie stanowią obecnie quality gate.
- **Suggested fix:** Najpierw naprawić konfigurację/package boundaries, następnie
  małymi partiami formatować i usuwać ostrzeżenia.
- **Risk:** Low, ale duży diff przy jednorazowym auto-fix.
- **Estimated complexity:** Medium.

### TEST-002

- **Severity:** P2
- **Status po refaktoryzacji:** Zamknięte 2026-09-05. Playwright sprawdza logowanie
  przez UI, pełne przejście `draft → review → published`, brak publicznej widoczności
  szkicu oraz upload i odczyt obrazu. `make test-e2e` przygotowuje bezpieczne konta
  demonstracyjne i wymagane usługi, a CI uruchamia ten sam zestaw w Chromium.
- **Category:** E2E
- **File:** `Makefile`, frontendy
- **Lines:** target `test-e2e`
- **Problem:** Makefile uruchamia Playwright, ale brak zależności, konfiguracji i
  testów E2E.
- **Why it matters:** Login, workflow publikacji, upload i public visibility nie są
  sprawdzane end-to-end.
- **Suggested fix:** Minimalne smoke E2E dla tych czterech ścieżek po ustabilizowaniu
  integracji backendowej.
- **Risk:** Low.
- **Estimated complexity:** Medium.

### AI-001

- **Severity:** P2
- **Status po refaktoryzacji:** Zamknięte 2026-09-04. Aktywne zadania AI wykonują
  rzeczywistą pracę i mają testy jednostkowe/integracyjne. Dwa niezaimplementowane
  zadania maintenance zwracają jawnie `status=disabled` i `reason=not_implemented`,
  a harmonogram Celery Beat jest pusty, więc monitoring nie raportuje pozornego
  sukcesu okresowych no-opów.
- **Category:** Background jobs
- **File:** `apps/backend/src/workers/tasks/maintenance.py` i taski AI
- **Lines:** task bodies
- **Problem:** Część tasków zwraca sukces, mimo że nie wykonuje deklarowanej pracy.
- **Why it matters:** Monitoring pokazuje pozornie zdrowy proces, a indeksy/dane nie
  są odświeżane.
- **Suggested fix:** Nieaktywne taski zgłaszać jako `not_implemented`/disabled i nie
  planować ich w beat; implementować wraz z testem integracyjnym.
- **Risk:** Low.
- **Estimated complexity:** Small.

## Security assessment

### Mocne strony

- parametry SQL są budowane przez SQLAlchemy;
- brak znalezionych śledzonych sekretów; `.env` jest ignorowany;
- hasła są hashowane, komunikat błędnego logowania jest ogólny;
- uprawnienia do mutacji są obecne na większości endpointów;
- upload nie ufa rozszerzeniu pliku i ma ochronę przed path traversal.

### Warunki bezpieczeństwa przed produkcją

1. Zamknąć SEC-001–003 oraz AUTH-001–002.
2. Nie wystawiać portów DB/Redis/MinIO/Prometheus/Flower publicznie.
3. Wymusić production secrets i `SECURE_COOKIES=true`.
4. Dodać TrustedHost i poprawną politykę proxy/CORS.
5. Dodać audit log dla zmian uprawnień, publikacji i sesji.
6. Przetestować upload fuzz/corrupted images oraz limity na poziomie proxy.

## Performance assessment

Historycznie największym potwierdzonym ryzykiem było wyszukiwanie `ILIKE` po długich
polach; zostało zastąpione ważonym FTS i trigramami. Listy osób nie pobierają pełnych
biografii, a relacje obrazów/patronatów są ładowane przez `selectinload`, co ogranicza
N+1. Dashboard redakcyjny nadal wykonuje wiele agregacji, a quality report mapuje do
150+ rekordów. Cache działa wyłącznie dla embeddingów. Przed cache'owaniem odpowiedzi
należy zebrać `EXPLAIN (ANALYZE, BUFFERS)` na reprezentatywnych 10–20 tys. osób i
zmierzyć p95.

## Database assessment

Model jest bogaty i zasadniczo odpowiada domenie. Dobre są constraints kalendarza,
oddzielenie źródeł oraz wiele relacji. Główne braki to schema drift, niepełne
snapshoty, brak concurrency control, niespójne defaulty model/migracja i brak
obliczalnych reguł świąt ruchomych. Nie należy edytować zastosowanych migracji
0001–0009. Fresh upgrade i pojedynczy downgrade zostały potwierdzone na bezpiecznej,
tymczasowej bazie audytowej.

## API assessment

Nazwy `/api/v1`, response models, filtrowanie i limity głównego katalogu są czytelne.
Public/admin rozdzielono w kilku miejscach, ale źródła/media wymagają domknięcia.
Najważniejszą korektą kontraktu jest uczynienie workflow jedyną drogą zmiany statusu.
Error envelope, paginacja zasobów rosnących oraz optimistic locking powinny być
wdrożone kompatybilnie i wersjonowane.

## Frontend assessment

Frontend ma dobry poziom typowania, nowoczesny stack i działające buildy. Dług
koncentruje się w dużych komponentach, obsłudze błędów, storage tokenu i hardcoded
Polish strings. Nie ma powodu przepisywać UI. Najbezpieczniej wydzielać komponenty
przy okazji testowanych zmian oraz dodać route boundaries i smoke E2E.

## Test assessment

Obecne unit testy pokrywają wiele reguł domenowych, ale cały suite jest czerwony.
Testy oznaczone jako integration nie mogą używać SQLite dla PostgreSQL-specific
metadata. Priorytetem nie jest sztuczne 100%, tylko działające testy auth/RBAC,
workflow, public visibility, upload, CRUD, versioning, soft-delete/restore i
constraints kalendarza.

## Ocena jakości

| Area | Score | Status |
| --- | ---: | --- |
| Architecture | 6.5/10 | dobry kierunek, nieszczelne granice |
| Backend | 5.5/10 | bogaty funkcjonalnie, wymaga stabilizacji |
| Database | 6.0/10 | dobry model, drift i concurrency |
| API | 6.0/10 | czytelne v1, niespójne błędy/workflow |
| Security | 4.5/10 | dobre podstawy, kilka P1 |
| Tests | 4.0/10 | sensowne testy unit, czerwony suite |
| Performance | 5.0/10 | bez pomiarów, martwe FTS/cache |
| Frontend | 7.0/10 | lint/type/build PASS |
| Type safety | 6.5/10 | TS mocny, mypy niedziałający |
| DevEx | 4.0/10 | brak lock/CI, zepsuty Makefile |
| Maintainability | 5.5/10 | duże serwisy i komponenty |
| Production readiness | 3.5/10 | brak bezpiecznej ścieżki deploy |

**Overall score: 5.4/10**  
**Technical debt: HIGH**  
**Production readiness: EARLY BETA**

Do poziomu BETA potrzebne są: zielone testy, zamknięte P1 security/workflow,
deterministyczne zależności i działający CI. Do `PRODUCTION WITH CONDITIONS` dodatkowo
potrzebne są obrazy produkcyjne, backup/restore drill, alerty, rate limiting,
rotacja sesji, test obciążenia search i przejrzany drift migracji.

## Top 10 najważniejszych problemów

| # | Problem | Severity | Impact | Effort |
| -: | --- | --- | --- | --- |
| 1 | Ominięcie workflow i `persons:publish` | P1 | privilege escalation | Small |
| 2 | Podatne zależności HTTP/upload/image | P1 | remote attack surface | Medium |
| 3 | Publiczne metadane prywatnych mediów | P1 | information disclosure | Small |
| 4 | Brak refresh rotation/revocation | P1 | przejęta sesja trwa po zmianie hasła | Medium |
| 5 | Brak skutecznego rate limit login | P1 | brute force / account DoS | Medium |
| 6 | Brak optimistic locking | P1 | utrata równoległych zmian | Medium |
| 7 | FTS nie działa, fallback skanuje biografie | P1 | correctness i skala | Medium/Large |
| 8 | Czerwony backend test suite | P1 | brak bezpiecznego refactoringu | Medium |
| 9 | Duży drift Alembic/model | P1 | ryzykowne przyszłe migracje | Large |
| 10 | Brak lockfile, CI i production deploy | P2 | niereprodukowalne wydania | Medium |

## Quick wins

1. Zablokować `status` w create/PATCH i wymusić workflow.
2. Wymagać `persons:publish` dla przejścia do published.
3. Zabezpieczyć listy images/documents.
4. Unieważniać wszystkie refresh tokeny po zmianie hasła.
5. Naprawić cztery nieaktualne unit testy.
6. Przenieść integracje z SQLite na PostgreSQL test DB.
7. Dodać `__init__.py`, aby mypy faktycznie analizował kod.
8. Zaktualizować Ruff config do `[tool.ruff.lint]`.
9. Dodać `type-check` scripts do obu package.json.
10. Naprawić ścieżki testów w Makefile.
11. Wersjonować `poetry.lock`.
12. Dodać route error/loading boundaries.
13. Wyłączyć stub tasks z Celery beat.
14. Dodać request/user/action do audytu zmian publikacji.
15. Ustawić jawny Next.js root, aby usunąć warning lockfile.

## Refactoring roadmap

### Phase 0 — Bugs & Security

| Priority | Files | Problem / solution | Risk | Dependencies | Benefit |
| --- | --- | --- | --- | --- | --- |
| P1 | persons/editorial routers | workflow-only status + publish permission | Medium | regresja API/RBAC | chroni publikację |
| P1 | sources router | auth dla katalogów mediów | Medium | frontend admin | brak wycieku |
| P1 | auth router | revocation + rotation + rate limit | Medium | Redis/DB | bezpieczne sesje |
| P1 | pyproject/lock | kompatybilne aktualizacje podatnych pakietów | Medium | testy | mniejszy attack surface |

### Phase 1 — Tests and safety net

| Priority | Files | Problem / solution | Risk | Dependencies | Benefit |
| --- | --- | --- | --- | --- | --- |
| P1 | tests/conftest | PostgreSQL integration DB | Medium | Docker CI | wiarygodne integracje |
| P1 | tests | regresje workflow/media/auth/concurrency | Low | Phase 0 | ochrona zmian |
| P2 | CI | automatyczne quality gates | Low | działające komendy | stabilny main |

### Phase 2 — Database and search

| Priority | Files | Problem / solution | Risk | Dependencies | Benefit |
| --- | --- | --- | --- | --- | --- |
| P1 | Alembic/models | sklasyfikować i naprawić drift | High | green tests/backup | bezpieczne migracje |
| P1 | Person/version | optimistic locking | Medium | API test | brak lost update |
| P1 | FTS migration/service | trigger + ranking + trigram | Medium | benchmark | skalowalne search |
| P2 | versions | pełny serializer snapshotów | Medium | storage policy | audytowalność |

### Phase 3 — Backend cleanup

| Priority | Files | Problem / solution | Risk | Dependencies | Benefit |
| --- | --- | --- | --- | --- | --- |
| P2 | session/services | jedna polityka transakcji | High | testy integracyjne | przewidywalność |
| P2 | editorial/AI services | pionowe, małe moduły | Medium | unit tests | SRP/testability |
| P2 | errors | wspólny envelope kompatybilny | Medium | frontend | prostsze klienty |
| P3 | package/config | Ruff, Black, mypy | Low | małe commity | działający lint |

### Phase 4 — Frontend cleanup

| Priority | Files | Problem / solution | Risk | Dependencies | Benefit |
| --- | --- | --- | --- | --- | --- |
| P2 | auth/api | token poza localStorage/BFF | High | auth backend | mniejszy XSS impact |
| P2 | app routes | error/loading/not-found | Low | API errors | poprawne UX |
| P2 | person-form | sekcje + mapper payload | Medium | component tests | maintainability |
| P2 | UI strings | i18n layer | Medium | ADR | kolejne języki |

### Phase 5–7 — Performance, operations, DevEx

- benchmark i profilowanie dashboard/search przed cache;
- produkcyjne obrazy i compose/orchestrator config;
- backup/restore test, monitoring i alerty;
- E2E smoke, dependency scanning, migration check;
- aktualny README/Makefile i reproducible onboarding.

## ADR-001 — Jedyna ścieżka publikacji

- **Decision:** Status osoby zmienia wyłącznie workflow endpoint; publikacja wymaga
  osobnego permission.
- **Context:** Obecny PATCH pozwala ominąć walidację kompletności.
- **Options:** status w CRUD; walidacja w każdym routerze; pojedyncza workflow policy.
- **Chosen approach:** pojedyncza policy + transition endpoint.
- **Advantages:** jeden audytowalny punkt reguł, brak mass assignment.
- **Disadvantages:** klienci używający bezpośredniego PATCH muszą przejść na
  istniejący endpoint transition.
- **Migration path:** pola pozostają w OpenAPI w pierwszym kroku, ale zwracają jasny
  konflikt; następnie oznaczenie deprecated i usunięcie dopiero w v2.

## ADR-002 — Polityka slug po soft delete

Pełny zapis decyzji: `docs/adr/0002-person-slug-after-soft-delete.md`.

- **Decision:** Zachować slug jako globalnie unikalny i nigdy go automatycznie nie
  przydzielać innemu rekordowi.
- **Context:** Restore ma zachować istniejące publiczne URL-e.
- **Options:** global unique; partial unique dla aktywnych; tabela rezerwacji URL.
- **Chosen approach:** global unique na obecnym etapie.
- **Advantages:** restore jest bezpieczny, brak przejęcia starego URL.
- **Disadvantages:** nowa osoba może dostać suffix po usuniętym rekordzie.
- **Migration path:** w przyszłości osobna tabela redirect/slug history, jeśli
  redakcja potrzebuje kontrolowanego ponownego użycia.

## ADR-003 — Integracyjne testy PostgreSQL

- **Decision:** Testy metadata/API uruchamiać na PostgreSQL, nie SQLite.
- **Context:** Produkcyjny model używa INET, JSONB, TSVECTOR, partial indexes i vector.
- **Options:** mock DB; SQLite adapters; PostgreSQL container/schema.
- **Chosen approach:** izolowana baza/schema PostgreSQL w Docker/CI.
- **Advantages:** testuje realne constraints, migrations i typy.
- **Disadvantages:** wolniejszy setup i wymagana usługa DB.
- **Migration path:** szybkie unit testy pozostają bez DB; integration ma osobny marker
  i fixture PostgreSQL.

## Architecture before / target after

```text
BEFORE
Router ─┬─> Service ─> SQLAlchemy ─> PostgreSQL
        └─> bezpośredni SQL/commit
Status: CRUD albo workflow
Search: ILIKE pełnych tekstów; nieużywany GIN
Tests: SQLite próbuje emulować PostgreSQL
Deploy: development backend compose
```

```text
TARGET AFTER (incrementalnie)
Router ─> use-case/service ─> SQLAlchemy unit of work ─> PostgreSQL
Status: jedna workflow policy + RBAC + audit
Search: aliasy + ważony FTS/trigram + zmierzony plan
Tests: unit bez DB + integration na PostgreSQL + E2E smoke
Deploy: deterministyczne, non-root obrazy + CI + backup/alerts
```

## Trzy decyzje wymagające właściciela produktu

1. Czy publiczny katalog dokumentów ma istnieć, czy dokumenty są wyłącznie
   narzędziem redakcyjnym? Pole `is_public` sugeruje przyszły publiczny use case.
2. Czy rola `reviewer` może publikować, czy publikacja jest wyłącznie dla
   administratora? Obecna macierz daje `persons:publish` tylko adminom.
3. Jakie oficjalne źródło i zasady pierwszeństwa mają obowiązywać dla kalendarza
   powszechnego, polskiego i lokalnego, zwłaszcza dla obchodów ruchomych?

## Definicja zakończenia całego programu refactoringu

Refactoring będzie ukończony dopiero, gdy: testy/lint/typecheck/build są zielone,
`alembic check` ma wyjaśniony i kontrolowany wynik, dependency audit nie zawiera
niezaakceptowanych podatności wysokiego ryzyka, migracja pustej oraz kopii bazy działa,
workflow i widoczność mają testy regresji, produkcyjny deploy jest powtarzalny, a
metryki i pozostały dług są zapisane w końcowym changelogu.
