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

Sesja jest tworzona w `sessionStorage`, a wysyłka używa `sendBeacon` z nieblokującym fallbackiem do `fetch`. Listener jest instalowany raz na cykl życia providerów, więc hydration nie duplikuje zdarzeń.
