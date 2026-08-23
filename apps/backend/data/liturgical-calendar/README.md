# Dane kalendarza liturgicznego

Plik `feasts.csv` jest idempotentnym, wersjonowanym źródłem przypisań postaci do
stałych dat. Nie przechowujemy osobnych pustych rekordów dla każdego dnia:
endpoint miesiąca generuje pełny kalendarz cywilny, dzięki czemu obejmuje 365
lub 366 dni i poprawnie uwzględnia 29 lutego.

## Zakres danych

- `roman_universal` — Ogólny Kalendarz Rzymski,
- `roman_pl` — kalendarz polski,
- pozostałe kody — kalendarze diecezjalne lub zakonne.

Portal może nałożyć kalendarz powszechny na wybrany kalendarz lokalny. Ta sama
osoba występująca w obu kalendarzach jest zwracana tylko raz, z pierwszeństwem
danych lokalnych.

## Kolumny CSV

- `calendar_code` — stabilny kod kalendarza,
- `person_slug` — slug istniejącej i opublikowanej postaci,
- `month`, `day` — stała data wspomnienia,
- `rank` — `solemnity`, `feast`, `memorial`, `opt_memorial` albo `commemoration`,
- `liturgical_color` — opcjonalny kolor liturgiczny,
- `is_primary` — główna postać dnia w tym kalendarzu,
- `source_title`, `source_url` — dokument potwierdzający datę i rangę,
- `notes` — uwagi redakcyjne, w tym różnice regionalne.

## Import

Z katalogu `apps/backend`:

```bash
python -m src.infrastructure.db.import_liturgical_calendar \
  data/liturgical-calendar/feasts.csv --dry-run

python -m src.infrastructure.db.import_liturgical_calendar \
  data/liturgical-calendar/feasts.csv
```

Ponowny import aktualizuje istniejące przypisania i nie tworzy duplikatów.
Wiersze odwołujące się do nieistniejącej postaci lub kalendarza są raportowane
jako `skipped_missing_relations`.

## Dobór głównej postaci

API porządkuje wpisy według: ręcznego `is_primary`, wybranego kalendarza
lokalnego, wyróżnienia redakcyjnego postaci, rangi liturgicznej i nazwy. Pozwala
to później zastąpić wyróżnienie redakcyjne wynikiem analityki odwiedzin bez
zmiany kontraktu API.

Plik startowy zawiera wyłącznie zweryfikowane przypisania dla postaci obecnych
w projekcie. Pełny import Martyrologium Romanum powinien zostać dodany jako
oddzielny, licencjonowany zbiór z zachowaniem źródła przy każdym wierszu.
