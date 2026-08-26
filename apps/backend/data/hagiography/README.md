# Dane hagiograficzne

`recognitions.csv` przechowuje wersjonowane, udokumentowane daty beatyfikacji i
kanonizacji. Osoba musi już istnieć w katalogu; importer nie tworzy pustych
rekordów zastępczych.

Dokładna data ma format `RRRR-MM-DD`. Jeśli źródło pozwala ustalić tylko rok,
pole daty pozostaje puste, a uzupełniamy odpowiednie pole `*_year`. Każdy wiersz
zawiera tytuł i adres źródła, zapisywane w wewnętrznych uwagach procesu.

Import z katalogu `apps/backend`:

```bash
python -m src.infrastructure.db.import_person_recognitions \
  data/hagiography/recognitions.csv
```

Polecenie jest idempotentne. Przełącznik `--dry-run` sprawdza plik i wykonuje
pełną transakcję bez utrwalania zmian.
