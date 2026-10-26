# Zdarzenia analityczne produktu

Pierwsza wersja analityki zapisuje wyłącznie małe, allowlistowane zdarzenia potrzebne
do pomiaru lejka odkrywania katalogu. Endpoint `POST /api/v1/events` nie wymaga
logowania i zwraca `202 {"accepted": true}` po przyjęciu zdarzenia.

Dozwolone nazwy zdarzeń to: `search_submitted`, `search_results`, `profile_opened`,
`source_opened`, `relation_opened`, `filter_applied` i `feedback_submitted`.
`query_class` przyjmuje tylko klasy `name`, `patronage`, `occupation`, `order`,
`country`, `period` i `filter`.

Właściwości są ograniczone do `result_count`, `filter_name`, `source_kind`,
`relation_kind` i `feedback`. Nie przyjmujemy surowego tekstu wyszukiwania, adresów
URL, tytułów, komentarzy ani identyfikatora konta. Klient przesyła losowy UUID sesji;
serwer przechowuje wyłącznie HMAC-SHA256 związany z sekretem aplikacji.

Surowy wiersz ma retencję 90 dni (`retention_until`) i indeks po czasie oraz typie
zdarzenia. Agregaty i mechanizm okresowego usuwania będą kolejnym krokiem FEATURE-013.

## Instrumentacja portalu

Portal emituje zdarzenia przez jedną delegowaną warstwę klientową zamontowaną przy providerach aplikacji. Rejestrowane są:

- wysłanie wyszukiwania albo zastosowanie filtra (z klasą zapytania, bez wartości zapytania),
- wyświetlenie wyników (z ograniczoną liczbą wyników),
- otwarcie profilu, relacji do zakonu i zewnętrznego źródła.
- dobrowolna ocena pomocności profilu (`helpful` albo `not_helpful`).

Sesja jest tworzona w `sessionStorage`, a wysyłka używa `sendBeacon` z nieblokującym fallbackiem do `fetch`. Listener jest instalowany raz na cykl życia providerów, więc hydration nie duplikuje zdarzeń.

## Agregaty i panel

`POST /api/v1/events/aggregates/rebuild` materializuje maksymalnie 31 dni agregatów i wymaga uprawnienia redakcyjnego `persons:read`. `GET /api/v1/events/aggregates` zwraca wyłącznie dzienne wiersze z liczbą zdarzeń, unikalnych sesji, wyników, pustych wyników i niepustych wyników. Panel `/dashboard/analytics` korzysta z rebuildu dla ostatnich 28 dni i nie ma dostępu do surowych wierszy.

„Wynik niepusty” jest proxy sukcesu zadania: oznacza `search_results` z `result_count > 0`. Nie jest to potwierdzenie, że czytelnik znalazł poprawną informację; tę granicę opisuje panel i pozostaje ona częścią baseline'u do walidacji badaniami.
