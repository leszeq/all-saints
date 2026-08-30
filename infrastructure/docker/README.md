# Wdrożenie produkcyjne

Stos produkcyjny uruchamia PostgreSQL z pgvector, Redis, jednorazową migrację
Alembic, API FastAPI/Gunicorn, dwa samodzielne obrazy Next.js oraz Nginx. Baza i
Redis działają wyłącznie w prywatnej sieci Compose.

## Konfiguracja

1. Skopiuj `.env.production.example` do `.env.production`.
2. Ustaw niezależne wartości `APP_SECRET_KEY`, `JWT_SECRET_KEY` i
   `POSTGRES_PASSWORD`. Sekrety aplikacji powinny mieć co najmniej 32 losowe
   bajty; można je wygenerować poleceniem `openssl rand -hex 32`.
3. Zastąp domeny `*.example` rzeczywistymi publicznymi adresami portalu i panelu.
4. Pozostaw `SECURE_COOKIES=true`, gdy ruch użytkowników korzysta z HTTPS.
5. Dla storage S3 ustaw `STORAGE_BACKEND=s3` oraz komplet zmiennych `AWS_*`.

Plik `.env.production` jest ignorowany przez Git i nie może być commitowany.

## Uruchomienie

```bash
make prod-check
make prod-build
make prod-up
```

Status i podstawowy healthcheck:

```bash
docker compose --env-file infrastructure/docker/.env.production \
  -f infrastructure/docker/docker-compose.prod.yml ps
curl --fail http://localhost/health
```

Zatrzymanie usług bez usuwania danych:

```bash
make prod-down
```

`prod-down` zachowuje nazwane wolumeny PostgreSQL, Redis i lokalnego storage.
Usunięcie wolumenów jest operacją destrukcyjną i nie jest częścią standardowego
runbooka.

## TLS i sieć

Nginx wystawia portal na `PUBLIC_PORT` (domyślnie 80) i panel na `ADMIN_PORT`
(domyślnie 8080). W środowisku publicznym należy umieścić przed nim terminator TLS
(np. load balancer lub reverse proxy), przekierować HTTP do HTTPS i ograniczyć
dostęp do panelu administracyjnego zgodnie z polityką organizacji. PostgreSQL i
Redis nie powinny otrzymywać mapowania portów hosta.

## Kopie zapasowe

Przed wdrożeniem wymagany jest automatyczny backup PostgreSQL i storage oraz
udokumentowana próba odtworzenia. Sam wolumen Dockera nie jest kopią zapasową.
