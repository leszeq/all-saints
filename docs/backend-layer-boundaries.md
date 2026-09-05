# Granice warstw backendu

## Kierunek zależności

Backend rozwijamy zgodnie z jednokierunkową zależnością:

```text
presentation -> application -> domain
                         \----> infrastructure (przez composition root)
```

- `presentation` odpowiada za HTTP, autoryzację, walidację transportową i mapowanie
  odpowiedzi;
- `application` opisuje przypadki użycia, komendy wejściowe i koordynuje domenę;
- `domain` zawiera modele oraz pojęcia biznesowe niezależne od FastAPI;
- `infrastructure` dostarcza bazę, cache, storage, integracje i importery.

Niższe warstwy nie mogą importować `src.presentation`. Automatyczny test architektury
blokuje nowe naruszenia. Tymczasowa lista wyjątków obejmuje wyłącznie zastany dług i
będzie zmniejszana pion po pionie.

## Pierwszy wydzielony pion: zakony

Komendy tworzenia i edycji wspólnot oraz dodawania członkostwa należą teraz do
`application.commands.religious_orders`. Schematy HTTP dziedziczą po tych komendach,
zachowując nazwy i kształt publicznego kontraktu OpenAPI. `OrderMembershipType` jest
pojęciem domenowym i znajduje się obok pozostałych enumów wspólnot religijnych.

`OrderService` oraz importer danych nie zależą już od routerów ani schematów HTTP.
Ten sam wzorzec należy zastosować kolejno do kalendarza, osób i redakcji.
