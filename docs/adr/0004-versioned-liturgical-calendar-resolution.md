# ADR-004: Wersjonowane reguły i rozstrzyganie kalendarza liturgicznego

- Status: zaakceptowane architektonicznie
- Data: 2026-09-05
- Zakres: kalendarz rzymski powszechny oraz kalendarze własne

## Kontekst

Obecny model `Feast` poprawnie przechowuje przypisania do dat stałych, ale pola
`is_moveable` i `date_note` nie stanowią reguły obliczeniowej. Publiczne zapytania
celowo zwracają wyłącznie wpisy stałe. Sam `FeastRank` nie wystarcza do rozstrzygania
kolizji: pierwszeństwo zależy również od rodzaju dnia, okresu liturgicznego oraz tego,
czy obchód jest powszechny albo własny dla miejsca, diecezji lub wspólnoty.

Normy powszechne definiują hierarchiczną tabelę dni liturgicznych oraz nakazują przy
zbiegu obchodów stosować jej kolejność. Przewidują też transfer niektórych
uroczystości i pominięcie innych obchodów w konkretnym roku. Kalendarze własne
uzupełniają kalendarz powszechny, podlegają zatwierdzeniu i mogą zmieniać stopień
obchodu. Dekrety mogą ponadto dodawać reguły względne, na przykład poniedziałek po
Pięćdziesiątnicy, albo wyjątki obowiązujące od określonego momentu.

## Decyzja

Nie będziemy kodować świąt ruchomych jako tekstu ani wykonywalnego wyrażenia w
`Feast.date_note`. Docelowy resolver będzie oparty na zamkniętym zestawie typowanych
reguł i rozdzieli pięć odpowiedzialności:

1. `LiturgicalObservance` pozostaje tożsamością i treścią obchodu, niezależną od daty.
2. `CalendarEdition` opisze zatwierdzoną wersję kalendarza, zakres terytorialny lub
   zakonny, przedział obowiązywania, źródło oraz edycję zastępowaną.
3. `ObservanceRule` przypisze obchód do edycji. Obsłuży jawne warianty, początkowo:
   `fixed_date`, `easter_offset`, `pentecost_offset`, `advent_weekday` i
   `nth_weekday`. Reguła przechowa własne źródło i kod pozycji w tabeli pierwszeństwa.
4. `CalendarException` zapisze udokumentowane przeniesienie, pominięcie albo zmianę
   stopnia dla konkretnej daty lub roku, bez modyfikowania reguły bazowej.
5. `ResolvedOccurrence` będzie odtwarzalną projekcją dla daty cywilnej. Zachowa datę
   wyliczoną, datę po transferze, wynik (`observed`, `transferred`, `omitted`) oraz
   pełną proweniencję reguły, edycji i wyjątku.

`FeastRank` pozostanie nazwą stopnia obchodu widoczną dla użytkownika. Osobne pole
`precedence_code` będzie wskazywać pozycję w wersjonowanej tabeli pierwszeństwa; nie
będziemy wyprowadzać pierwszeństwa wyłącznie z rangi.

Edycja zatwierdzona i użyta publicznie będzie niemutowalna. Zmiana normy, dekretu lub
kalendarza lokalnego utworzy nową edycję z przedziałem obowiązywania. Resolver dla
daty historycznej zawsze wybierze edycję obowiązującą w tej dacie. Nakładające się
edycje tego samego kalendarza będą zabronione.

## Algorytm rozstrzygania

1. Wybrać edycje obowiązujące dla daty i żądanego zakresu.
2. Wyliczyć cykl okresowy oraz daty z typowanych reguł.
3. Nałożyć kolejno kalendarz powszechny i właściwe kalendarze własne.
4. Zastosować tabelę pierwszeństwa oraz udokumentowane reguły transferu.
5. Zastosować wyjątki roczne/dekrety i zapisać proweniencję wyniku.
6. Przerwać publikację wyniku przy nierozstrzygniętej kolizji zamiast wybierać obchód
   heurystycznie. `is_primary` pozostaje wyborem redakcyjnym prezentacji, a nie
   substytutem prawa pierwszeństwa.

## Granica obecnego wydania

Do czasu wdrożenia resolvera API tworzy i aktualizuje tylko wpisy stałe z miesiącem i
dniem. Nieznane pola, w tym `is_moveable` i `date_note`, są odrzucane zamiast cicho
ignorowane. Rekordy oznaczone `is_moveable=true` nie trafiają do publicznych widoków
dnia ani miesiąca. Obecne pola pozostają w bazie wyłącznie dla kompatybilności; nie są
deklaracją działającej funkcji.

Martyrologium pozostaje warstwą katalogową. Jego wpisy mogą być prezentowane obok
oficjalnych obchodów jako dodatkowa lista hagiograficzna, ale nie uczestniczą w
obliczaniu pierwszeństwa ani transferów kalendarza liturgicznego.

## Plan migracji

1. Uzgodnić z redakcją oficjalne wydania źródłowe dla kalendarza powszechnego,
   polskiego oraz pierwszych kalendarzy własnych.
2. Dodać tabele edycji, reguł, wyjątków i wersji tabeli pierwszeństwa w osobnej
   migracji; nie zmieniać zastosowanych migracji historycznych.
3. Przenieść istniejące wpisy stałe do reguł `fixed_date`, zachowując identyfikatory,
   źródła i publiczne odpowiedzi kompatybilnościowe.
4. Wdrożyć czysty, deterministyczny resolver z testami lat przestępnych, Wielkanocy,
   granicy roku liturgicznego, nakładania zakresów, kolizji i transferów.
5. Porównać wygenerowany rok z zatwierdzonym ordo przed uruchomieniem publicznym.
6. Dopiero po okresie zgodności usunąć lub zdeprecjonować legacy `is_moveable`,
   `date_note` i `day_of_year` jako źródła danych.

## Konsekwencje

- Wynik dla dowolnego roku będzie odtwarzalny i audytowalny.
- Kalendarz polski, diecezjalny i zakonny będzie rozszerzeniem właściwej edycji, a nie
  nadpisaniem wspólnej tabeli.
- Model jest większy niż pojedyncza tabela `feasts`, ale nie miesza treści, norm,
  wyjątków i wyliczonego wyniku.
- Do czasu wdrożenia całego resolvera produkt uczciwie obsługuje tylko daty stałe.

## Źródła normatywne i przykłady

- [Universal Norms on the Liturgical Year and the Calendar](https://www.cbcew.org.uk/wp-content/uploads/sites/13/2015/06/GNLY.pdf), szczególnie numery 49–61 i tabela pierwszeństwa.
- [Wskazania o kalendarzach własnych](https://www.vatican.va/content/dam/wss/roman_curia/congregations/ccdds/documents/rc_con_ccdds_doc_20000628_calendari_it.html), Kongregacja ds. Kultu Bożego, 2000.
- [Dekret wykonawczy do kan. 838](https://www.vatican.va/roman_curia/congregations/ccdds/documents/rc_con_ccdds_doc_20211022_decreto-can838-cdc_it.html), numery 51–55 o zatwierdzaniu kalendarzy własnych.
- [Notyfikacja o wspomnieniu NMP Matki Kościoła](https://www.vatican.va/roman_curia/congregations/ccdds/documents/rc_con_ccdds_doc_20180324_notificazione-mater-ecclesiae_sp.html), przykład reguły względnej i kolizji wspomnień.
