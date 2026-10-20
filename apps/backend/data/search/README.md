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

Adapter dla lokalnej bazy development można uruchomić razem z evaluator'em:

```bash
make search-benchmark-db SEARCH_RESULTS=data/search/results.local.json
```

Adapter wykonuje wyłącznie odczyty `published_only=true` i zapisuje obok
rankingów także `reason` oraz `match` każdego zwróconego sluga.

Polecenie wypisuje `top_k_success`, `mrr_at_cutoff`, `ndcg_at_cutoff` i
`zero_results_rate`; z `--check` kończy się kodem 1 po spadku poniżej progów.
Adapter pobierający wyniki z API lub lokalnej bazy pozostaje poza evaluator'em,
więc benchmark można uruchamiać offline w CI lub podczas release check bez
nowej usługi.

## Baseline v1

Automatyczny odczyt z lokalnej bazy development z `published_only=true` został
zapisany w `search_gold_v1_baseline.json` (20 października 2026, commit
`6f78a03`): 100 zapytań, top-5 success `1.0`, MRR@10 `0.98`, nDCG@10
`0.9852371901428583`, zero-results `0.0`. Jest to punkt odniesienia dla
regresji rankingu; ręczna ocena pytań nie jest przez te metryki zastępowana.
