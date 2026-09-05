# Testy E2E krytycznych ścieżek

Smoke testy Playwright obejmują cztery granice, których nie pokrywają same testy
backendu: logowanie w panelu, przejście `draft → review → published`, ukrycie szkicu
w portalu publicznym oraz upload i odczyt obrazu.

## Uruchomienie lokalne

```bash
make test-e2e
```

Polecenie uruchamia wymagane usługi Docker, wykonuje migracje, synchronizuje
dedykowane konta demonstracyjne i uruchamia oba frontendy na portach 3000 i 3001.
Istniejące serwery developerskie na tych portach zostaną wykorzystane ponownie.
Playwright instaluje wyłącznie Chromium wymagane przez ten zestaw testów.

Domyślne hasło `DemoE2E123!` dotyczy tylko kont demonstracyjnych poza produkcją.
Można je zastąpić bez ujawniania prywatnych danych z lokalnego `.env`:

```bash
make test-e2e E2E_PASSWORD='inne-mocne-haslo'
```

Scenariusze korzystają z kont:

- `redaktor.test@encyklopedia.pl` — tworzenie rekordu, wysłanie do recenzji i upload;
- `recenzent.test@encyklopedia.pl` — publikacja kompletnego szkicu;
- `admin.test@encyklopedia.pl` — posprzątanie testowego rekordu.

Rekord osoby jest usuwany miękko po teście nawet wtedy, gdy asercja po utworzeniu
rekordu nie powiedzie się. Wygenerowane, minimalne obrazy pozostają w developerskim
storage; w CI cały wolumen jest usuwany po zakończeniu zadania.

## Uruchomienie interaktywne

Po jednorazowym przygotowaniu usług i kont można uruchomić przeglądarkę z widocznym
oknem:

```bash
cd apps/admin
E2E_PASSWORD='DemoE2E123!' npm run test:e2e:headed
```

Adresy można nadpisać zmiennymi `E2E_ADMIN_URL`, `E2E_WEB_URL` i `E2E_API_URL`.
