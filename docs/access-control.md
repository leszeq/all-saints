# Macierz ról i uprawnień

Polityka dostępu jest definiowana w kodzie w `src/domain/identity/rbac.py` i
materializowana w bazie przez Alembic oraz idempotentny seed. Panel nie jest
źródłem autoryzacji — ukrywa niedostępne akcje, ale każdą decyzję egzekwuje API.

## Role systemowe

| Obszar | Superadministrator | Administrator | Redaktor | Recenzent |
| --- | :---: | :---: | :---: | :---: |
| Odczyt rekordów redakcyjnych | ✓ | ✓ | ✓ | ✓ |
| Tworzenie osoby | ✓ | ✓ | ✓ | — |
| Edycja danych osoby | ✓ | ✓ | ✓ | — |
| Przekazanie szkicu do recenzji | ✓ | ✓ | ✓ | — |
| Zwrot z obowiązkowym komentarzem | ✓ | ✓ | — | ✓ |
| Akceptacja i publikacja po recenzji | ✓ | ✓ | — | ✓ |
| Wycofanie lub archiwizacja publikacji | ✓ | ✓ | — | — |
| Usuwanie i przywracanie osoby | ✓ | ✓ | — | — |
| Pełne zarządzanie źródłami i mediami | ✓ | ✓ | — | — |
| Dodawanie i edycja źródeł/obrazów | ✓ | ✓ | ✓ | — |
| Odczyt źródeł, geografii i kalendarza | ✓ | ✓ | ✓ | ✓ |
| Pełne zarządzanie geografią, zakonami i kalendarzem | ✓ | ✓ | — | — |
| Import, eksport i dziennik audytu | ✓ | ✓ | częściowo | odczyt eksportów |
| Zarządzanie użytkownikami | ✓ | — | — | — |
| Zarządzanie rolami i macierzą | ✓ | — | — | — |

Superadministrator jest pojedynczym kontem właściciela. API nie pozwala
przypisać tej roli, seed zachowuje istniejącego właściciela, a trigger bazy
blokuje równoległe utworzenie drugiego aktywnego przypisania.

## Workflow redakcyjny

```text
Redaktor                 Recenzent
draft ── przekazuje ──> review ── akceptuje ──> published
                           │
                           └── zwraca z komentarzem ──> draft
```

Recenzent nie otrzymuje `persons:update`. Jego uprawnienie `persons:review`
działa wyłącznie w kontrolowanym endpoincie decyzji redakcyjnej. Dzięki temu
nie może zmienić biogramu tuż przed akceptacją.

## Role niestandardowe

Superadministrator może tworzyć dodatkowe role z granularnych uprawnień
treściowych. Uprawnienia `users:*` i `roles:*` są zarezerwowane i nie mogą być
nadane roli niestandardowej. Role systemowe są niemodyfikowalne.

## Konta demonstracyjne

Seed może opcjonalnie utworzyć konta `admin`, `editor` i `reviewer` po włączeniu
`SEED_DEMO_USERS`. Flaga jest akceptowana wyłącznie w środowisku development lub
testing; konfiguracja produkcyjna z tą flagą kończy start błędem.
