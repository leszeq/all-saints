# ADR-002: Slug osoby po soft-delete

- Status: zaakceptowane
- Data: 2026-09-05
- Zakres: osoby i publiczne adresy profili

## Kontekst

Profil osoby jest identyfikowany publicznym, kanonicznym adresem zawierającym
`Person.slug`. Usunięcie osoby jest miękkie: rekord może później zostać przywrócony.
Gdyby generator ignorował usunięte rekordy, inna osoba mogłaby w międzyczasie przejąć
ten sam adres, a przywrócenie pierwotnego rekordu powodowałoby konflikt albo zmianę
znaczenia istniejącego URL-a.

## Decyzja

Slug pozostaje globalnie unikalny dla wszystkich rekordów, także usuniętych miękko.
Generator sprawdza aktywne i usunięte osoby. Nowy rekord o tej samej nazwie otrzymuje
sufiks, natomiast przywrócony rekord zachowuje swój dotychczasowy slug.

Nie wprowadzamy częściowego indeksu unikalnego ograniczonego do aktywnych rekordów.
Nie zwalniamy ani nie przypisujemy automatycznie slugów należących do usuniętych osób.

## Konsekwencje

- Przywrócenie osoby nie zmienia jej kanonicznego URL-a.
- Usunięty rekord nadal rezerwuje slug; nowa osoba może otrzymać sufiks liczbowy.
- Baza danych i serwis stosują tę samą globalną regułę unikalności.
- Kontrolowane zmiany historycznych URL-i będą wymagały osobnego mechanizmu historii
  slugów i przekierowań HTTP.

## Weryfikacja

Test integracyjny wykonuje pełny cykl: utworzenie osoby, soft-delete, utworzenie
rekordu o tej samej nazwie oraz przywrócenie pierwotnej osoby. Sprawdza zachowanie
oryginalnego adresu i nadanie sufiksu nowemu rekordowi.
