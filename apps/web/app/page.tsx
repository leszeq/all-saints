import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  CalendarDays,
  ChevronRight,
  Church,
  Clock3,
  Compass,
  HeartHandshake,
  Landmark,
  Search,
  Sparkles,
} from "lucide-react";
import { fetchPersons } from "@/lib/api";

export const revalidate = 60;

const patronages = [
  { title: "W chorobie", detail: "Patroni chorych, lekarzy i opiekunów", icon: HeartHandshake, query: "chorzy" },
  { title: "W rodzinie", detail: "Orędownicy małżeństw, dzieci i rodziców", icon: Church, query: "rodzina" },
  { title: "W pracy", detail: "Patroni zawodów i codziennych obowiązków", icon: Landmark, query: "praca" },
  { title: "W drodze", detail: "Patroni podróżnych, kierowców i pielgrzymów", icon: Compass, query: "podróżni" },
];

const eras = [
  ["I–V wiek", "Pierwsi świadkowie", "Starożytność"],
  ["VI–XV wiek", "Klasztory i średniowiecze", "Średniowiecze"],
  ["XVI–XVIII wiek", "Odnowa i misje", "Nowożytność"],
  ["XIX–XXI wiek", "Święci bliscy naszym czasom", "Współczesność"],
];

const fallbackPersons = [
  { id: "1", slug: "sw-franciszek-z-asyzu", name: "Św. Franciszek z Asyżu", years: "1181–1226", summary: "Założyciel Zakonu Braci Mniejszych, patron pokoju i troski o stworzenie." },
  { id: "2", slug: "sw-faustyna-kowalska", name: "Św. Faustyna Kowalska", years: "1905–1938", summary: "Apostołka Bożego Miłosierdzia i autorka Dzienniczka." },
  { id: "3", slug: "bl-jerzy-popieluszko", name: "Bł. Jerzy Popiełuszko", years: "1947–1984", summary: "Kapłan, męczennik i duszpasterz ludzi pracy." },
];

export default async function HomePage() {
  let persons: Array<Record<string, unknown>> = [];
  let totalPersons = 0;

  try {
    const response = await fetchPersons({ per_page: 6, is_featured: true });
    persons = response?.items ?? [];
    totalPersons = response?.total ?? 0;
  } catch {
    persons = [];
  }

  const featured = persons.length
    ? persons.slice(0, 3).map((person) => ({
        id: String(person.id),
        slug: String(person.slug),
        name: String(person.canonical_name),
        years: person.birth_year || person.death_year ? `${person.birth_year ?? "?"}–${person.death_year ?? "?"}` : "Daty w opracowaniu",
        summary: String(person.summary_pl || "Profil jest obecnie opracowywany przez redakcję."),
      }))
    : fallbackPersons;

  const today = new Intl.DateTimeFormat("pl-PL", { day: "numeric", month: "long" }).format(new Date());

  return (
    <div className="overflow-hidden">
      <section className="relative border-b border-[#ded8cd]">
        <div className="pointer-events-none absolute inset-0 opacity-70" aria-hidden="true">
          <div className="absolute left-[-9rem] top-16 h-72 w-72 rounded-full border border-gold-200" />
          <div className="absolute left-[-6rem] top-28 h-60 w-60 rounded-full border border-gold-200" />
          <div className="absolute right-[-6rem] top-10 h-[28rem] w-64 rounded-t-full border border-gold-200 bg-gold-50/40" />
        </div>

        <div className="relative mx-auto grid max-w-7xl items-center gap-12 px-4 py-20 sm:px-6 lg:grid-cols-[1.25fr_.75fr] lg:px-8 lg:py-28">
          <div className="max-w-3xl">
            <p className="editorial-label ornament-rule max-w-[16rem]">Cyfrowe kompendium</p>
            <h1 className="mt-7 font-serif text-5xl font-semibold leading-[1.04] tracking-[-0.035em] text-charcoal sm:text-6xl lg:text-7xl">
              Poznaj historię <span className="text-burgundy-700">świętych</span>
            </h1>
            <p className="mt-7 max-w-2xl text-base leading-7 text-stone-600 sm:text-lg">
              Rzetelne biogramy, patronaty i źródła — uporządkowane tak, by prowadzić od prostego pytania do pogłębionej wiedzy.
            </p>

            <form action="/swieci" method="GET" className="glass-search mt-9 flex max-w-2xl flex-col gap-2 rounded-xl p-2 sm:flex-row">
              <label className="relative min-w-0 flex-1">
                <span className="sr-only">Zapytaj o świętych</span>
                <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-gold-700" />
                <input name="search" className="h-12 w-full rounded-lg bg-transparent pl-12 pr-4 text-sm text-charcoal outline-none placeholder:text-stone-400" placeholder="Np. patron osób chorych w średniowieczu…" />
              </label>
              <button className="h-12 rounded-lg bg-burgundy-700 px-6 text-sm font-semibold text-white transition-colors hover:bg-burgundy-600">
                Szukaj w encyklopedii
              </button>
            </form>
            <p className="mt-3 text-xs text-stone-500">Możesz wpisać imię, miejsce, patronat albo pytanie naturalnym językiem.</p>
          </div>

          <aside className="surface-card relative mx-auto w-full max-w-sm overflow-hidden p-7 lg:mr-0" aria-label="O projekcie">
            <div className="absolute right-0 top-0 h-32 w-24 rounded-bl-full bg-gold-100/70" />
            <BookOpen className="h-7 w-7 text-gold-700" strokeWidth={1.5} />
            <p className="mt-12 font-serif text-3xl font-semibold leading-tight text-charcoal">Wiedza budowana źródło po źródle.</p>
            <p className="mt-4 text-sm leading-6 text-stone-600">Profile przechodzą przez proces redakcyjny, weryfikację danych i kontrolę bibliografii.</p>
            <div className="mt-8 grid grid-cols-2 gap-6 border-t border-[#ded8cd] pt-6">
              <div><p className="font-serif text-2xl font-semibold text-burgundy-700">{totalPersons || "12 456"}</p><p className="mt-1 text-xs text-stone-500">opracowanych postaci</p></div>
              <div><p className="font-serif text-2xl font-semibold text-burgundy-700">1 248</p><p className="mt-1 text-xs text-stone-500">udokumentowanych źródeł</p></div>
            </div>
          </aside>
        </div>
      </section>

      <main>
        <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
          <article className="surface-card grid overflow-hidden md:grid-cols-[14rem_1fr_auto] md:items-center">
            <div className="flex min-h-52 items-center justify-center bg-burgundy-800 p-8 text-gold-200">
              <div className="text-center"><Sparkles className="mx-auto h-8 w-8" strokeWidth={1.25} /><p className="mt-4 font-serif text-2xl">22 maja</p></div>
            </div>
            <div className="p-7 md:p-9">
              <p className="editorial-label">Święta dnia · {today}</p>
              <h2 className="mt-3 font-serif text-3xl font-semibold text-charcoal">Św. Rita z Cascii</h2>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-600">Augustianka, mistyczka i orędowniczka w sprawach po ludzku trudnych. Poznaj historię jej życia oraz rozwój kultu.</p>
              <div className="mt-5 flex flex-wrap gap-2"><span className="rounded-full border border-gold-200 bg-gold-50 px-3 py-1 text-xs text-gold-800">sprawy trudne</span><span className="rounded-full border border-gold-200 bg-gold-50 px-3 py-1 text-xs text-gold-800">małżeństwa</span></div>
            </div>
            <div className="p-7 md:pr-9"><Link href="/swieci/sw-rita-z-cascii" className="inline-flex h-11 items-center gap-2 rounded-lg border border-burgundy-200 px-4 text-sm font-semibold text-burgundy-700 hover:bg-burgundy-50">Zobacz profil <ArrowRight className="h-4 w-4" /></Link></div>
          </article>
        </section>

        <section id="odkrywaj" className="border-y border-[#ded8cd] bg-[#fffdf8] py-20">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><p className="editorial-label">Punkty wyjścia</p><h2 className="mt-3 font-serif text-4xl font-semibold text-charcoal">Odkrywaj według patronatu</h2></div><Link href="/swieci" className="inline-flex items-center gap-1 text-sm font-semibold text-burgundy-700">Zobacz katalog <ChevronRight className="h-4 w-4" /></Link></div>
            <div className="mt-9 grid gap-px overflow-hidden rounded-xl border border-[#ded8cd] bg-[#ded8cd] sm:grid-cols-2 lg:grid-cols-4">
              {patronages.map(({ title, detail, icon: Icon, query }) => (
                <Link key={title} href={`/swieci?search=${encodeURIComponent(query)}`} className="group bg-[#fffdf8] p-6 transition-colors hover:bg-gold-50">
                  <Icon className="h-6 w-6 text-gold-700" strokeWidth={1.5} /><h3 className="mt-8 font-serif text-2xl font-semibold text-charcoal">{title}</h3><p className="mt-2 text-sm leading-6 text-stone-600">{detail}</p><span className="mt-7 inline-flex items-center gap-1 text-xs font-bold uppercase tracking-wider text-burgundy-700">Przeglądaj <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-1" /></span>
                </Link>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto grid max-w-7xl gap-12 px-4 py-20 sm:px-6 lg:grid-cols-2 lg:px-8">
          <div id="kalendarz">
            <div className="flex items-center justify-between"><div><p className="editorial-label">Kalendarz liturgiczny</p><h2 className="mt-3 font-serif text-3xl font-semibold">Dzisiaj wspominamy</h2></div><CalendarDays className="h-7 w-7 text-gold-700" strokeWidth={1.4} /></div>
            <div className="mt-7 divide-y divide-[#ded8cd] border-y border-[#ded8cd]">
              {["Św. Rita z Cascii", "Św. Emilia de Vialar", "Bł. Jan Forest"].map((name, index) => <Link key={name} href={`/swieci?search=${encodeURIComponent(name)}`} className="group flex items-center gap-5 py-5"><span className="flex h-11 w-11 items-center justify-center rounded-full border border-gold-200 bg-gold-50 font-serif text-lg text-gold-800">{index + 1}</span><span className="flex-1"><span className="block font-serif text-xl font-semibold">{name}</span><span className="mt-1 block text-xs text-stone-500">Wspomnienie dowolne · profil zweryfikowany</span></span><ChevronRight className="h-4 w-4 text-stone-400 group-hover:text-burgundy-700" /></Link>)}
            </div>
          </div>

          <div id="epoki">
            <div className="flex items-center justify-between"><div><p className="editorial-label">Oś czasu</p><h2 className="mt-3 font-serif text-3xl font-semibold">Święci przez wieki</h2></div><Clock3 className="h-7 w-7 text-gold-700" strokeWidth={1.4} /></div>
            <div className="relative mt-7 grid gap-3 before:absolute before:bottom-4 before:left-[6px] before:top-4 before:w-px before:bg-gold-300">
              {eras.map(([period, title, era]) => <Link key={period} href={`/swieci?era=${encodeURIComponent(era)}`} className="group relative grid grid-cols-[7.5rem_1fr] items-center gap-4 pl-7"><span className="absolute left-0 h-3 w-3 rounded-full border-2 border-[#fffdf8] bg-gold-500 ring-1 ring-gold-400" /><span className="text-xs font-semibold text-gold-800">{period}</span><span className="rounded-lg border border-transparent px-4 py-3 font-serif text-lg transition-colors group-hover:border-[#ded8cd] group-hover:bg-[#fffdf8]">{title}</span></Link>)}
            </div>
          </div>
        </section>

        <section id="zakony" className="bg-burgundy-800 py-16 text-white">
          <div className="mx-auto flex max-w-7xl flex-col gap-8 px-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8"><div className="max-w-2xl"><p className="text-xs font-bold uppercase tracking-[0.16em] text-gold-300">Zakony i zgromadzenia</p><h2 className="mt-3 font-serif text-4xl font-semibold">Wspólnoty, które kształtowały historię</h2><p className="mt-4 text-sm leading-6 text-burgundy-100">Odkrywaj postacie przez duchowość benedyktyńską, franciszkańską, dominikańską i wiele innych tradycji.</p></div><div className="grid grid-cols-3 gap-3 text-center text-xs"><span className="rounded-lg border border-white/15 bg-white/5 px-5 py-4">Benedyktyni</span><span className="rounded-lg border border-white/15 bg-white/5 px-5 py-4">Franciszkanie</span><span className="rounded-lg border border-white/15 bg-white/5 px-5 py-4">Dominikanie</span></div></div>
        </section>

        <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
          <div className="flex items-end justify-between gap-4"><div><p className="editorial-label">Praca redakcji</p><h2 className="mt-3 font-serif text-4xl font-semibold">Ostatnio opracowane</h2></div><Link href="/swieci" className="hidden items-center gap-1 text-sm font-semibold text-burgundy-700 sm:inline-flex">Wszystkie profile <ChevronRight className="h-4 w-4" /></Link></div>
          <div className="mt-9 grid gap-5 md:grid-cols-3">
            {featured.map((person, index) => (
              <Link key={person.id} href={`/swieci/${person.slug}`} className="surface-card group flex min-h-72 flex-col p-6 transition-transform hover:-translate-y-1">
                <div className="flex items-center justify-between"><span className="flex h-10 w-10 items-center justify-center rounded-full bg-gold-100 font-serif text-lg text-gold-800">{String(index + 1).padStart(2, "0")}</span><span className="text-[10px] font-bold uppercase tracking-[0.14em] text-emerald-700">Zweryfikowany</span></div>
                <div className="mt-auto pt-12"><p className="text-xs text-gold-800">{person.years}</p><h3 className="mt-2 font-serif text-2xl font-semibold text-charcoal group-hover:text-burgundy-700">{person.name}</h3><p className="mt-3 line-clamp-3 text-sm leading-6 text-stone-600">{person.summary}</p></div>
              </Link>
            ))}
          </div>
        </section>

        <section id="metodologia" className="border-t border-[#ded8cd] bg-[#fffdf8] py-12">
          <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8"><div><p className="editorial-label">Metodologia</p><p className="mt-2 max-w-3xl text-sm leading-6 text-stone-600">Oddzielamy tradycję hagiograficzną od ustaleń historycznych, oznaczamy rozbieżności i wskazujemy źródła przy konkretnych informacjach.</p></div><Link href="/swieci" className="inline-flex h-11 shrink-0 items-center gap-2 rounded-lg border border-[#ded8cd] px-4 text-sm font-semibold text-charcoal hover:bg-gold-50">Rozpocznij odkrywanie <ArrowRight className="h-4 w-4" /></Link></div>
        </section>
      </main>
    </div>
  );
}
