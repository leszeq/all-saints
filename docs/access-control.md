# Macierz ról i uprawnień

Polityka dostępu jest definiowana w kodzie w `src/domain/identity/rbac.py` i
materializowana w bazie przez Alembic oraz idempotentny seed. Panel nie jest
źródłem autoryzacji — ukrywa niedostępne akcje, ale każdą decyzję egzekwuje API.

## Role systemowe

| Obszar | Superadministrator | Administrator | Redaktor | Recenzent | Tłumacz |
| --- | :---: | :---: | :---: | :---: | :---: |
| Odczyt rekordów redakcyjnych | ✓ | ✓ | ✓ | ✓ | ✓ |
| Tworzenie osoby | ✓ | ✓ | ✓ | — | — |
| Edycja danych osoby | ✓ | ✓ | ✓ | — | — |
| Przekazanie szkicu do recenzji | ✓ | ✓ | ✓ | — | — |
| Zwrot z obowiązkowym komentarzem | ✓ | ✓ | — | ✓ | — |
| Akceptacja i publikacja po recenzji | ✓ | ✓ | — | ✓ | — |
| Wycofanie lub archiwizacja publikacji | ✓ | ✓ | — | — | — |
| Usuwanie i przywracanie osoby | ✓ | ✓ | — | — | — |
| Odczyt tłumaczeń | ✓ | ✓ | ✓ | ✓ | ✓ |
| Tworzenie, edycja i usuwanie tłumaczeń szkicu | ✓ | ✓ | — | — | ✓ |
| Pełne zarządzanie źródłami i mediami | ✓ | ✓ | — | — | — |
| Dodawanie i edycja źródeł/obrazów | ✓ | ✓ | ✓ | — | — |
| Odczyt źródeł, geografii i kalendarza | ✓ | ✓ | ✓ | ✓ | częściowo |
| Pełne zarządzanie geografią, zakonami i kalendarzem | ✓ | ✓ | — | — | — |
| Import, eksport i dziennik audytu | ✓ | ✓ | częściowo | odczyt eksportów | — |
| Zarządzanie użytkownikami | ✓ | — | — | — | — |
| Zarządzanie rolami i macierzą | ✓ | — | — | — | — |

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

Tłumaczenie jest częścią wersji osoby, a nie niezależną ścieżką publikacji.
Tłumacz może je zmieniać wyłącznie, gdy osoba ma status `draft`. Każda taka
operacja zwiększa wersję osoby, zapisuje snapshot i trafia do dziennika audytu.
Redaktor przekazuje cały rekord do recenzji, a recenzent widzi tłumaczenia i
akceptuje albo zwraca osobę w istniejącym workflow.

## Role niestandardowe

Superadministrator może tworzyć dodatkowe role z granularnych uprawnień
treściowych. Uprawnienia `users:*` i `roles:*` są zarezerwowane i nie mogą być
nadane roli niestandardowej. Role systemowe są niemodyfikowalne.

## Konta demonstracyjne

Seed może opcjonalnie utworzyć po jednym koncie dla każdej niewłaścicielskiej
roli systemowej po włączeniu `SEED_DEMO_USERS`:

| Rola | Konto lokalne |
| --- | --- |
| Administrator | `admin.test@encyklopedia.pl` |
| Redaktor | `redaktor.test@encyklopedia.pl` |
| Recenzent | `recenzent.test@encyklopedia.pl` |
| Tłumacz | `tlumacz.test@encyklopedia.pl` |
| Czytelnik wewnętrzny | `czytelnik.test@encyklopedia.pl` |
| Gość | `gosc.test@encyklopedia.pl` |

Istniejący właściciel stanowi test roli superadministratora, ponieważ system
celowo nie pozwala utworzyć drugiego takiego konta. Wszystkie konta demonstracyjne
korzystają z hasła `DEMO_USER_PASSWORD` z lokalnego, niecommitowanego pliku `.env`.
Flaga jest akceptowana wyłącznie w środowisku development lub testing;
konfiguracja produkcyjna z tą flagą kończy start błędem.
