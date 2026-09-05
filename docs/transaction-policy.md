# Polityka transakcji backendu

Docelowo jedna warstwa jest właścicielem każdej transakcji. Metody aplikacyjne
wykonują operacje domenowe i `flush`, natomiast nie wykonują samodzielnie `commit`.
Dzięki temu kilka operacji serwisowych można połączyć atomowo bez ryzyka, że
wcześniejszy krok zostanie zapisany mimo błędu późniejszego kroku.

## Granice unit-of-work

- Request HTTP: dependency `get_db_session` wykonuje `commit` po poprawnej obsłudze
  requestu i `rollback` po wyjątku.
- Zadanie Celery: funkcja zadania jest właścicielem transakcji i jawnie kończy ją
  po pełnym przypadku użycia.
- Import, seed i migracja: skrypt używa jawnego bloku transakcyjnego albo pary
  `commit` / `rollback`, ponieważ nie działa wewnątrz requestu.
- Serwis aplikacyjny: może wykonywać `flush`, aby uzyskać identyfikator i wcześnie
  wykryć naruszenie constraintu, ale nie kończy transakcji, poza opisanym niżej
  izolowanym zapisem zdarzeń bezpieczeństwa.

Wyjątek wymaga komentarza uzasadniającego trwały zapis przed zgłoszeniem błędu.
Zdarzenia odmowy logowania muszą pozostać w audycie również wtedy, gdy endpoint
zwraca odpowiedź błędną. `AuthenticationSecurityRecorder` realizuje je w krótkiej,
jawnej transakcji `session.begin()`. Pod blokadą wiersza atomowo zwiększa licznik
nieudanych prób i zapisuje audit, po czym request może bezpiecznie wykonać rollback.

## Stan migracji

Z zasady korzysta obecnie osiem pionów:

- zakony i zgromadzenia — tworzenie, edycja, soft-delete oraz zmiana członkostwa;
- kalendarz liturgiczny — obchody nieosobowe, przypisania do dni, zmiana wpisu
  głównego i soft-delete;
- osoby i workflow redakcyjny — tworzenie, edycja, soft-delete, przywracanie,
  zmiany statusu, snapshot wersji i audit log są zatwierdzane atomowo;
- kontrola dostępu — konta użytkowników, przypisania ról, role niestandardowe
  oraz ich uprawnienia są zatwierdzane przez właściciela unit-of-work;
- źródła i media — wpisy bibliograficzne, źródła historyczne, dokumenty, obrazy,
  powiązania z osobą, snapshot wersji i audit log tworzą jeden atomowy zapis;
- dane referencyjne — geografia, kategorie, tagi i papieże czekają na commit
  granicy requestu, dzięki czemu można je bezpiecznie składać w większe operacje;
- AI — embeddingi, streszczenia i tagi generowane przez API czekają na commit
  requestu; zadania Celery jawnie commitują każdy udany rekord i rollbackują błąd;
- uwierzytelnianie — udane logowanie, rotacja tokenu, logout, profil i zmiana hasła
  czekają na commit requestu, a odmowy logowania używają izolowanego recordera.

Endpoint ustawień jest wyłącznie odczytowy i nie uczestniczy w transakcjach zapisu.

Migracja runtime jest zakończona. Jawne commity i rollbacki pozostają wyłącznie
u właścicieli transakcji: w providerze requestu, workerach, skryptach importu,
seedzie, inicjalizacji rozszerzeń bazy oraz izolowanym recorderze bezpieczeństwa.
