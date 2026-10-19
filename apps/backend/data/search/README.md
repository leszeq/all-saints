# Benchmark wyszukiwania osób

`search_gold_v1.json` jest wersjonowanym fixture jakości wyszukiwania. Zawiera
100 pytań i publiczne slugi oczekiwanych osób. Dane pochodzą wyłącznie z
opublikowanych rekordów katalogu; fixture nie jest tabelą produkcyjną i nie
zawiera treści nieopublikowanych.

Wersja `starter` obejmuje nazwy kanoniczne, angielskie, łacińskie, zapis bez
znaków diakrytycznych, wariant częściowy oraz pięć kontrolowanych literówek.
Przed użyciem jako release gate warianty literówek i klasy pytań powinny zostać
ocenione ręcznie przez redakcję. Progi w fixture są początkowym kontraktem
jakości, a nie wynikiem takiej oceny.

Evaluator przyjmuje zapis wyników adaptera w formacie:

```json
{
  "canonical_exact-001": ["sw-bartlomiej-apostol", "sw-benedykt-z-nursji"]
}
```

Uruchomienie z katalogu `apps/backend`:

```bash
PYTHONPATH=. python -m src.application.search_benchmark \
  --fixture data/search/search_gold_v1.json \
  --results /tmp/search-results.json \
  --check
```

W środowisku Compose ten sam check można wywołać z katalogu repozytorium:

```bash
make search-benchmark SEARCH_RESULTS=data/search/results.json
```

Plik wynikowy jest generowany przez adapter benchmarku i nie powinien być
dodawany do repozytorium.

Polecenie wypisuje `top_k_success`, `mrr_at_cutoff`, `ndcg_at_cutoff` i
`zero_results_rate`; z `--check` kończy się kodem 1 po spadku poniżej progów.
Adapter pobierający wyniki z API lub lokalnej bazy pozostaje poza evaluator'em,
więc benchmark można uruchamiać offline w CI lub podczas release check bez
nowej usługi.
