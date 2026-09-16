# Import i nadpisywanie profilu JSON

W panelu na liście osób wybierz import JSON i wczytaj plik profilu w wersji 1.
Nowa osoba zostanie zapisana jako szkic.

Jeśli istnieje dokładnie jeden aktywny profil o tej samej nazwie kanonicznej
(porównanie bez rozróżniania wielkości liter), formularz pokaże jego nazwę,
adres i status. Zaznacz „Chcę nadpisać istniejący profil danymi z pliku”.
Po ponownej walidacji kliknij „Nadpisz istniejący profil”. Inne błędy pliku
nadal blokują zapis. Kilka dopasowanych osób blokuje automatyczne nadpisanie.

## Zakres nadpisania

- Zastępowane są dane edytowalne obsługiwane przez format, aliasy, patronaty,
  obraz główny, dane beatyfikacji i kanonizacji oraz przypisania zakonów,
  wspomnień i źródeł. Puste lub pominięte pola formatu przyjmują jego wartości
  domyślne; puste listy usuwają dotychczasowe przypisania.
- Zachowywane są ID, nazwa kanoniczna, slug, status oraz historia profilu.
  Pozostałe materiały spoza formatu JSON nie są zastępowane. Wspólne katalogi
  zakonów i bibliografii nie są usuwane.
- Zmiany tworzą wersje i wpisy audytu. Audyt nadpisania przechowuje również
  poprzedni dokument eksportu oraz dokument importowany. Cała operacja działa
  w jednej transakcji; błąd zapisu wycofuje wszystkie jej zmiany.
- Własne główne wspomnienie osoby nie jest konfliktem przy nadpisywaniu.
  Główny wpis innej osoby lub obchodu pozostaje główny; importowany wpis
  w tym dniu zostaje dodatkowy.
- Opublikowana osoba pozostaje opublikowana, więc zmiany są od razu widoczne.
  Formularz pokazuje ostrzeżenie przed zapisem.

## Uprawnienia i kontrakt API

Import wymaga `import:create`, nadpisanie dodatkowo `persons:update`,
a nadpisanie opublikowanej osoby także `persons:publish`.

Oba endpointy POST (`/api/v1/persons/import/validate` i `/api/v1/persons/import`)
przyjmują dotychczasowy dokument JSON bez zmiany formatu. Przy nadpisywaniu
dodaj parametry zapytania `overwrite_person_id` oraz `expected_version`
z pola `existing_person` otrzymanego podczas walidacji. Identyfikatory
`source_person_id` i `source_slug` w samym pliku nie wyrażają zgody na nadpisanie.

Zapis ponownie sprawdza dopasowanie, wersję i powiązania pod blokadą rekordu.
Nieaktualna wersja zwraca `409`: należy ponownie wczytać plik, sprawdzić
rekord i potwierdzić nadpisanie. Utworzenie zwraca `201`, nadpisanie `200`.
