"""Render the authored feature catalogue; no dependencies or network access."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parent
FEATURES = json.loads((ROOT / 'features.json').read_text())
KEYS = ('V', 'R', 'S', 'T', 'D', 'M', 'X', 'O', 'U')
BACKLOG_IDS = (5, 1, 2, 3, 4, 6, 9, 7, 8, 10, 12, 13, 25, 37, 38, 16)


def score(f):
    s = f['scores']
    benefit = .25*s['V'] + .15*s['R'] + .20*s['S'] + .15*s['X'] + .15*s['O'] + .10*s['U']
    cost = .45*s['T'] + .35*s['D'] + .20*s['M']
    return 10 * benefit / (1 + cost/5)


def checklist(value):
    return '\n'.join('- [ ] ' + part.strip().rstrip('.') + '.' for part in value.split(';') if part.strip())


def story(f):
    return f"**As a** {f['user']}  \n**I want** {f['want']}  \n**So that** {f['value']}"


def costs(f):
    s = f['scores']
    level = 'niska' if s['T'] <= 3 else 'średnia' if s['T'] <= 6 else 'wysoka'
    return f"Techniczna: **{s['T']}/10 ({level})**; dane: **{s['D']}/10**; utrzymanie: **{s['M']}/10**. Są to koszty względne, nie obietnica liczby dni."


assert len(FEATURES) == 40
assert len({f['id'] for f in FEATURES}) == 40
for f in FEATURES:
    assert tuple(f['scores']) == KEYS
    assert all(type(v) is int and 1 <= v <= 10 for v in f['scores'].values())

impl = ['# Szczegółowy plan implementacji — 40 funkcji', '',
        'Uzupełnienie sekcji 12 i 31 raportu. Wszystkie endpointy/tabele opisane jako „dodać” są propozycjami. Zachować obecne kontrakty i migracje, a nazwy finalizować przy implementacji. Faza jest docelowym horyzontem; w fazie 0 wdrażamy minimalne zabezpieczenia dużych epików.', '',
        'Dla każdej funkcji podano konkretne acceptance criteria i zakres wszystkich warstw. Po discovery duże epiki należy rozbić na pionowe przyrosty. Reach i wartość są hipotezami; nie są wynikami analityki produkcyjnej.', '']
for f in FEATURES:
    impl += [f"## {f['id']} — {f['name']}", '',
             f"**Grupa:** {f['group']}. **Faza:** {f['phase']}. **Priorytet:** {f['priority']}. **Priority Score:** {score(f):.2f}.", '',
             '**Product — problem**', '', f['problem'], '', '**User Story**', '', story(f), '',
             '**Wartość i złożoność**', '', f['value'], '', costs(f), '',
             '**Acceptance Criteria**', '', checklist(f['acceptance']), '',
             '**Backend — endpointy, serwisy, schemas, permissions**', '', f['backend'], '',
             '**Database — tabele, relacje, indeksy, migracje**', '', f['database'], '',
             '**Frontend — strony, komponenty, stan, integracja API**', '', f['frontend'], '',
             '**Tests — backend, frontend, E2E**', '', f['tests'], '',
             '**Infrastructure**', '', f['infrastructure'], '',
             '**Dependencies**', '', f['dependencies'], '', '**Risk**', '', f['risk'], '']
(ROOT / 'implementation.md').write_text('\n'.join(impl)+'\n')

priorities = ['# Macierz priorytetów — 40 rekomendacji', '',
              'Skala 1–10. V: wartość, R: reach, S: strategic fit, T: koszt techniczny, D: koszt danych, M: utrzymanie, X: wyróżnienie, O: SEO, U: retencja. W T/D/M większa ocena oznacza większy koszt. W pozostałych większą korzyść.', '',
              '`Benefit = 0.25V + 0.15R + 0.20S + 0.15X + 0.15O + 0.10U`', '',
              '`Cost = 0.45T + 0.35D + 0.20M`', '',
              '`Priority Score = 10 × Benefit / (1 + Cost/5)`', '',
              'Oceny eksperckie, bez danych o zasięgu i retencji. Nie są RICE ani procentem pewności. Kolejność liczbowa nie zastępuje P0 i zależności. Faza 0 dla dużych funkcji oznacza wykonanie minimum bezpieczeństwa, nie całego epika.', '',
              '| Miejsce | FEATURE | Funkcja | V | R | S | T | D | M | X | O | U | Score | Priorytet / faza |',
              '|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
for pos, f in enumerate(sorted(FEATURES,key=score,reverse=True),1):
    priorities.append('| '+ ' | '.join([str(pos),f['id'],f['name'],*[str(f['scores'][k]) for k in KEYS],f'{score(f):.2f}',f"{f['priority']} / {f['phase']}"])+ ' |')
priorities += ['', '## Przykład obliczenia', '']
f = FEATURES[0]
s = f['scores']
b = .25*s['V']+.15*s['R']+.20*s['S']+.15*s['X']+.15*s['O']+.10*s['U']
c = .45*s['T']+.35*s['D']+.20*s['M']
priorities += [f"FEATURE-001: Benefit={b:.2f}, Cost={c:.2f}, Score=10×{b:.2f}/(1+{c:.2f}/5)={score(f):.2f}.", '',
              '## Interpretacja i wrażliwość', '',
              'Quick wins z niskim kosztem naturalnie wypadają wysoko. Rewizje, źródła twierdzeń i resolver są trudniejsze, ale odblokowują inne funkcje; nie można ich uszeregować tylko według ilorazu. P0 renderer i granica publikacji są obowiązkowe przed rozszerzeniem uprawnień/redakcji. Koszt danych dla map i kalendarza musi być oszacowany osobno przez redakcję.', '',
              'Po pierwszych 4–8 tygodniach: zastąpić Reach szacunkami z eventów i badań; zweryfikować koszt danych na próbce 20 rekordów; sprawdzić ranking przy ±2 punktach T/D i ±2 R. Nie przestawiać programu strategicznego dla różnicy mniejszej niż kilka punktów score bez dowodu użytkowego.', '',
              'Zależności krytyczne: 004→016→017→020; 008→027; 007+014+015→028; 016+026+027→029; 004+037→036; 010+016+022→021. Część funkcji ma mniejszy MVP możliwy wcześniej, co opisano w planie.']
(ROOT/'priorities.md').write_text('\n'.join(priorities)+'\n')

backlog = ['# Backlog — 16 priorytetowych epików', '',
           'Gotowe do przeniesienia do issue trackera. Kolejność odpowiada zależnościom i ryzyku, nie samemu Priority Score. Przy FEATURE-004/037/038 faza 0 obejmuje minimum opisane w planie; późniejsze zakresy nie blokują małych poprawek. Nie utworzono zewnętrznych zgłoszeń.', '']
by_id={int(f['id'][-3:]): f for f in FEATURES}
for i in BACKLOG_IDS:
    f=by_id[i]
    backlog += [f"## {f['id']} — {f['name']}", '', '**Goal**', '', f['value'], '',
                '**Why**', '', f['problem'], '', '**User Story**', '', story(f), '',
                '**Backend**', '', checklist(f['backend']), '',
                '**Database**', '', checklist(f['database']), '',
                '**Frontend**', '', checklist(f['frontend']), '',
                '**Tests**', '', checklist(f['tests']), '',
                '**Infrastructure**', '', checklist(f['infrastructure']), '',
                '**Definition of Done**', '', checklist(f['acceptance']), '',
                '**Dependencies**', '', f['dependencies'], '', '**Risk**', '', f['risk'], '',
                '**Priority**', '', f"{f['priority']}; faza {f['phase']}; Priority Score {score(f):.2f}. {costs(f)}", '']
(ROOT/'backlog.md').write_text('\n'.join(backlog)+'\n')

# Final delivery uses absolute local links, as required by the desktop renderer.
for name in ('report.md','implementation.md','priorities.md','backlog.md','evidence.md'):
    p=ROOT/name
    text=p.read_text()
    text=re.sub(r'\]\(([^:/#][^)]*\.(?:md|json|py))\)',lambda m: ']('+str(ROOT/m.group(1))+')',text)
    p.write_text(text)
print(json.dumps({'features':len(FEATURES),'backlog':len(BACKLOG_IDS),'top_scores':[(f['id'],round(score(f),2)) for f in sorted(FEATURES,key=score,reverse=True)[:5]]},ensure_ascii=False))
