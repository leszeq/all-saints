# All Saints — Encyklopedia Świętych

Projekt zawiera API FastAPI, panel administracyjny i portal publiczny Next.js.
Lokalnie backend oraz PostgreSQL, Redis i usługi pomocnicze działają w Dockerze,
a oba frontendy uruchamiamy przez npm na komputerze.

## Wymagania

- Uruchomiony Docker Desktop z Docker Compose v2.
- Node.js 22 i npm (środowisko zweryfikowano z Node.js 22.14.0 i npm 10.9.2).
- `make` oraz trzy zakładki terminala.

Polecenia poniżej wykonuj z katalogu głównego sklonowanego repozytorium
`all-saints`, chyba że wskazano inaczej.

## Codzienne uruchamianie

Jeśli to pierwsze uruchomienie na komputerze, najpierw wykonaj konfigurację
z następnej sekcji.

W pierwszej zakładce terminala:

```bash
docker compose -f infrastructure/docker/docker-compose.yml up -d --wait
make migrate
```

Compose uruchamia API i usługi pomocnicze w tle. **Nie uruchamia frontendów**;
`make dev` i `make dev-detach` również obejmują tylko usługi Dockera.

W drugiej zakładce terminala uruchom panel i pozostaw proces działający:

```bash
npm --prefix apps/admin run dev -- --hostname localhost --port 3000
```

W trzeciej zakładce uruchom portal i pozostaw proces działający:

```bash
npm --prefix apps/web run dev -- --hostname localhost --port 3001
```

| Aplikacja | Adres |
| --- | --- |
| Panel administracyjny | http://localhost:3000/login |
| Portal publiczny | http://localhost:3001 |
| Dokumentacja API (Swagger) | http://localhost:8000/docs |
| Gotowość API, PostgreSQL i Redis | http://localhost:8000/health/ready |
| Poczta testowa MailHog | http://localhost:8025 |
| Konsola MinIO | http://localhost:9001 |
| Grafana | http://localhost:3002 |

Używaj `localhost` konsekwentnie w obu frontendach, zgodnie z lokalną konfiguracją
CORS i cookies. Domyślny adres API w aplikacjach to `http://localhost:8000`.
Jeśli go zmieniasz, ustaw `NEXT_PUBLIC_API_URL` w `.env.local` każdej aplikacji
(`apps/admin` i `apps/web`), bez końcowego `/api/v1`, i uruchom frontendy ponownie.

## Pierwsze uruchomienie na nowym komputerze

1. Przygotuj konfigurację:

   ```bash
   make setup
   ```

   Polecenie tworzy główny `.env` z `.env.example`, jeśli plik jeszcze nie istnieje.
   Uzupełnij w nim `APP_SECRET_KEY`, `JWT_SECRET_KEY`, `POSTGRES_PASSWORD`,
   `MINIO_SECRET_KEY` oraz `INITIAL_ADMIN_EMAIL` i `INITIAL_ADMIN_PASSWORD`.
   Pozostaw `APP_ENV=development`, `SECURE_COOKIES=false` i `AI_PROVIDER=none`
   dla lokalnego startu bez zewnętrznego dostawcy AI.

2. Przygotuj drugi plik konfiguracyjny, jeśli jeszcze go nie ma:

   ```bash
   test -f infrastructure/docker/.env || cp .env infrastructure/docker/.env
   ```

   Główny `.env` dostarcza wartości podstawiane przez Compose, natomiast
   `infrastructure/docker/.env` jest wczytywany do kontenera backendu.
   Na nowym środowisku użyj zgodnej konfiguracji w obu plikach. Przy późniejszych
   zmianach aktualizuj odpowiednie wartości w obu miejscach; powyższe polecenie
   nie nadpisuje istniejącego pliku. Nie commituj plików z sekretami.

3. Zbuduj backend i zainstaluj zależności frontendów:

   ```bash
   make install
   ```

4. Uruchom Docker i migracje według sekcji „Codzienne uruchamianie”, a następnie
   zainicjalizuj słowniki, role i konto administratora:

   ```bash
   make seed
   ```

   Zaloguj się danymi `INITIAL_ADMIN_EMAIL` i `INITIAL_ADMIN_PASSWORD`
   z `infrastructure/docker/.env`. Seed nie resetuje hasła istniejącego
   superadministratora. Konta demonstracyjne nie są potrzebne do zwykłego startu.

5. Uruchom panel i portal w osobnych zakładkach, jak opisano powyżej.

## Sprawdzenie działania i logi

```bash
make ps
curl --fail http://localhost:8000/health/ready
curl --fail -I http://localhost:3000/login
curl --fail -I http://localhost:3001/
make logs-backend
```

`/health` sprawdza sam proces API, a `/health/ready` także połączenia z bazą
i Redis. Logi frontendów są widoczne w ich zakładkach terminala.
Jeśli port 3000 lub 3001 jest zajęty, sprawdź, czy aplikacja już pod nim działa,
zanim uruchomisz drugi proces.

## Opcjonalne zadania AI

Workery, scheduler Celery i Flower są w profilu `ai`:

```bash
docker compose -f infrastructure/docker/docker-compose.yml --profile ai up -d --wait
```

Generowanie AI wymaga dodatkowo skonfigurowanego dostawcy w plikach środowiska.
Flower jest dostępny pod `http://localhost:5555`, z danymi `FLOWER_BASIC_AUTH`.

## Zatrzymanie

W zakładkach panelu i portalu naciśnij `Ctrl+C`. Następnie zatrzymaj kontenery:

```bash
docker compose -f infrastructure/docker/docker-compose.yml --profile ai down
```

Polecenie zachowuje dane w wolumenach. Nie używaj `make clean`, `make reset-db`
ani `down -v` do zwykłego zatrzymania — te operacje usuwają dane lub wolumeny.

## Dalsza dokumentacja

- [Backend i testy](apps/backend/README.md)
- [Testy end-to-end](docs/e2e-testing.md)
- [Wdrożenie produkcyjne i backupy](infrastructure/docker/README.md)
- [Audyt architektury i postęp prac](docs/architecture-audit-2026-08-29.md)

Lista dostępnych poleceń projektu: `make help`.
