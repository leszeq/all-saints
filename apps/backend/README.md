# All Saints Backend

API platformy **All Saints / Encyklopedia Świętych**. Aplikacja wykorzystuje
FastAPI, SQLAlchemy 2, PostgreSQL/pgvector, Alembic, Redis i Celery.

## Uruchomienie developerskie

Z katalogu głównego repozytorium:

```bash
docker compose -f infrastructure/docker/docker-compose.yml up -d db redis backend
docker compose -f infrastructure/docker/docker-compose.yml exec backend alembic upgrade head
```

API jest dostępne pod `http://localhost:8000`, a Swagger UI pod
`http://localhost:8000/docs` poza środowiskiem produkcyjnym.

Redis jest krytyczną zależnością instancji API: zapewnia współdzielony limiter
logowania, pośredniczy w zadaniach Celery i opcjonalnie cache'uje embeddingi.
Dlatego `/health/ready` zwraca `503`, gdy niedostępna jest baza albo Redis.
Ogólny cache odpowiedzi HTTP nie jest włączony — należy go dodawać dopiero po
pomiarze konkretnego endpointu wraz z jawną strategią unieważniania.

## Testy

Integracje wymagają PostgreSQL. Development compose przekazuje bezpieczny adres
dedykowanej bazy `all_saints_test`; fixture odmawia pracy z bazą bez sufiksu
`_test`, tworzy ją przed sesją i usuwa po zakończeniu.

```bash
docker compose -f infrastructure/docker/docker-compose.yml exec backend pytest
```

Szybkie przebiegi bez raportu coverage:

```bash
docker compose -f infrastructure/docker/docker-compose.yml exec backend \
  pytest -q -o addopts='' tests/unit
docker compose -f infrastructure/docker/docker-compose.yml exec backend \
  pytest -q -o addopts='' tests/integration
```

## Bezpieczeństwo zależności

`poetry.lock` jest częścią repozytorium i źródłem wersji dla obrazu Docker.

```bash
docker compose -f infrastructure/docker/docker-compose.yml exec backend \
  poetry run pip-audit
```

Nie zapisuj sekretów w repozytorium. Lokalne wartości konfiguracyjne należą do
`infrastructure/docker/.env`, utworzonego na podstawie `.env.example`.
