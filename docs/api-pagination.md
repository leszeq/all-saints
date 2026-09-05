# Stronicowanie list API

Rosnące zasoby API v1 używają wspólnego kontraktu `page` / `per_page`, zachowując
tablicę JSON jako ciało odpowiedzi. Pozwala to stronicować nowe klienty bez zerwania
kompatybilności ze starszym panelem administracyjnym.

## Parametry

- `page` — numer strony liczony od 1; domyślnie `1`;
- `per_page` — liczba rekordów od 1 do 500; domyślnie `100`.

Nieprawidłowe wartości zwracają standardowy błąd walidacji HTTP 422.

## Metadane odpowiedzi

- `X-Total-Count` — liczba wszystkich rekordów pasujących do filtrów;
- `X-Page` — bieżąca strona;
- `X-Per-Page` — użyty rozmiar strony;
- `X-Total-Pages` — liczba stron, `0` dla pustego wyniku.

Nagłówki są udokumentowane w OpenAPI i dostępne dla klientów przeglądarkowych
przez CORS. Przykład:

```http
GET /api/v1/geography/places?page=2&per_page=50

HTTP/1.1 200 OK
X-Total-Count: 127
X-Page: 2
X-Per-Page: 50
X-Total-Pages: 3

[{ ... }]
```

Kontrakt obejmuje miejsca, diecezje, kościoły, bibliografię, źródła historyczne,
obrazy, dokumenty, tagi i zawody. Małe, zamknięte słowniki — państwa, kategorie
i stany życia — nadal zwracają pełną listę.

Endpoint obrazów przejściowo akceptuje również starszy parametr `limit`. Jest on
oznaczony w OpenAPI jako deprecated i ma pierwszeństwo przed `per_page`, aby nie
przerywać działania istniejących integracji w okresie migracji klientów.
