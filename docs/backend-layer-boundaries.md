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

Drugim wydzielonym pionem jest kalendarz liturgiczny. Komendy obchodów i stałych
wpisów kalendarza, razem z walidacją daty i rodzaju celu, znajdują się w
`application.commands.liturgical_calendar`. Warstwa HTTP zachowuje dotychczasowe
nazwy schematów i publiczny kontrakt.

Trzecim wydzielonym pionem są osoby. Walidowane dane osoby, avatara, aliasów,
patronatów, beatyfikacji i kanonizacji należą do `application.commands.persons`.
Zachowano dotychczasowe nazwy klas wejściowych, aby publiczne komponenty OpenAPI i
importy klientów Pythona nie zmieniły się. `PersonService` oraz workflow redakcyjny
nie importują już schematów HTTP osoby.

Pozostały zastany dług dotyczy modeli wynikowych trzech modułów redakcyjnych.
