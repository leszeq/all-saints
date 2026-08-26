# Dane zakonów i zgromadzeń

Katalog rozdziela konkretny instytut od szerszej rodziny duchowej. Dzięki temu
`OFM` i `OFMConv` są osobnymi rekordami, ale można je wspólnie filtrować przez
`spiritual_family=franciszkanska`.

## Pliki

- `orders.csv` — historia, misja, typ wspólnoty, charyzmat i źródło,
- `persons.csv` — brakujące osoby wymagane przez zestaw startowy,
- `memberships.csv` — udokumentowane relacje osoba–wspólnota.

Relacja rozróżnia m.in. założyciela, mnicha, brata, mniszkę, siostrę,
członka świeckiego i patrona duchowego. To istotne np. dla św. Augustyna,
który jest ojcem duchowym OSA, ale nie członkiem zakonu powstałego w XIII w.

## Import

Z katalogu `apps/backend`:

```bash
python -m src.infrastructure.db.import_religious_orders \
  data/religious-orders --dry-run

python -m src.infrastructure.db.import_religious_orders \
  data/religious-orders
```

Import jest idempotentny: aktualizuje treść wspólnot, nie nadpisuje
istniejących rekordów osób i aktualizuje istniejące powiązania.
