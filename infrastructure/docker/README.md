# Wdrożenie produkcyjne

Stos produkcyjny uruchamia PostgreSQL z pgvector, Redis, jednorazową migrację
Alembic, API FastAPI/Gunicorn, dwa samodzielne obrazy Next.js oraz Nginx. Baza i
Redis działają wyłącznie w prywatnej sieci Compose.

## Konfiguracja

1. Skopiuj `.env.production.example` do `.env.production`.
2. Ustaw niezależne wartości `APP_SECRET_KEY`, `JWT_SECRET_KEY` i
   `POSTGRES_PASSWORD`. Sekrety aplikacji muszą mieć co najmniej 32 znaki, a
   hasło bazy co najmniej 16; losową wartość można wygenerować poleceniem
   `openssl rand -hex 32`.
3. Zastąp domeny `*.example` rzeczywistymi publicznymi adresami portalu i panelu.
4. Pozostaw `SECURE_COOKIES=true`, gdy ruch użytkowników korzysta z HTTPS.
5. Dla storage S3 ustaw `STORAGE_BACKEND=s3` oraz komplet zmiennych `AWS_*`.

Backend w trybie produkcyjnym odmawia startu dla placeholderów, współdzielonych
sekretów, `SECURE_COOKIES=false` oraz wildcardu `*` w `ALLOWED_HOSTS` lub CORS.

Plik `.env.production` jest ignorowany przez Git i nie może być commitowany.

## Uruchomienie

```bash
make prod-check
make prod-build
make prod-up
```

Domyślna nazwa projektu Compose to `all-saints-prod`. Można ją jawnie zmienić, na
przykład dla izolowanego smoke testu, bez współdzielenia kontenerów i wolumenów z
właściwym środowiskiem:

```bash
make prod-up PROD_PROJECT=all-saints-smoke PROD_ENV=infrastructure/docker/.env.production
make prod-down PROD_PROJECT=all-saints-smoke PROD_ENV=infrastructure/docker/.env.production
```

Status i podstawowy healthcheck:

```bash
docker compose --env-file infrastructure/docker/.env.production \
  -f infrastructure/docker/docker-compose.prod.yml ps
curl --fail http://localhost/health
```

Sonda `/health` sprawdza wyłącznie proces. Load balancer powinien używać
`/health/ready`, które wymaga działającego PostgreSQL i Redis; awaria którejkolwiek
z tych usług wycofuje instancję API z ruchu odpowiedzią `503`.

Zatrzymanie usług bez usuwania danych:

```bash
make prod-down
```

`prod-down` zachowuje nazwane wolumeny PostgreSQL, Redis i lokalnego storage.
Usunięcie wolumenów jest operacją destrukcyjną i nie jest częścią standardowego
runbooka.

### Zmiana hasła PostgreSQL

`POSTGRES_PASSWORD` inicjalizuje użytkownika tylko podczas tworzenia pustego wolumenu
PostgreSQL. Sama zmiana wartości w `.env.production` nie aktualizuje hasła roli w już
działającej bazie i spowoduje błąd uwierzytelnienia migratora przy kolejnym starcie.

Rotację należy wykonać jako kontrolowaną operację:

1. utworzyć i zweryfikować aktualny backup;
2. wygenerować nowe hasło w menedżerze sekretów;
3. połączyć się z bazą przy użyciu dotychczasowego sekretu i zmienić hasło roli;
4. atomowo zaktualizować sekret używany przez Compose;
5. uruchomić migrator i sprawdzić `/health/ready`;
6. zachować możliwość szybkiego rollbacku konfiguracji do czasu zakończenia smoke
   testu.

Nie należy naprawiać rozjazdu hasła przez usunięcie wolumenu. Dla lokalnych testów
lepiej użyć osobnego `PROD_PROJECT`; w środowisku rzeczywistym procedura rotacji musi
być dopasowana do używanego menedżera sekretów i platformy bazodanowej.

## TLS i sieć

Nginx wystawia portal na `PUBLIC_PORT` (domyślnie 80) i panel na `ADMIN_PORT`
(domyślnie 8080). W środowisku publicznym należy umieścić przed nim terminator TLS
(np. load balancer lub reverse proxy), przekierować HTTP do HTTPS i ograniczyć
dostęp do panelu administracyjnego zgodnie z polityką organizacji. PostgreSQL i
Redis nie powinny otrzymywać mapowania portów hosta.

## Monitoring

Ustawienie `SENTRY_DSN` włącza raportowanie błędów backendu. Pole
`SENTRY_TRACES_SAMPLE_RATE` przyjmuje wartość od `0.0` do `1.0`; bez świadomego
budżetu telemetrycznego należy pozostawić domyślne `0.0`. Integracja oznacza
zdarzenia nazwą środowiska i wersją aplikacji oraz nie wysyła domyślnie PII.

Endpoint Prometheus `/metrics` istnieje w backendzie, ale produkcyjny Nginx nie
wystawia go publicznie. Scraper powinien działać w zaufanej sieci wewnętrznej.

## Kopie zapasowe

Backup PostgreSQL jest zapisywany atomowo w formacie custom i weryfikowany przez
`pg_restore --list`:

```bash
make prod-backup
```

Każdy backup należy okresowo odtworzyć do izolowanej bazy testowej:

```bash
make prod-restore-check BACKUP_FILE=backups/all-saints-YYYYmmddTHHMMSSZ.dump
```

Restore check tworzy nową bazę o ściśle kontrolowanej nazwie, sprawdza tabele i
wersję Alembic, po czym usuwa wyłącznie tę bazę testową. Nie modyfikuje aktywnej
bazy aplikacji. Pliki z katalogu `backups/` są ignorowane przez Git.

Przed publicznym wdrożeniem nadal należy skonfigurować harmonogram, retencję,
szyfrowanie i kopię poza hostem oraz analogiczny backup storage. Sam wolumen
Dockera nie jest kopią zapasową.
