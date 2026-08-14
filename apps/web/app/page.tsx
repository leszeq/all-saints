import Link from "next/link";
import {
  BookOpen,
  Calendar,
  ChevronRight,
  Compass,
  Crown,
  Heart,
  MapPin,
  Search,
  Shield,
  Sparkles,
  Star,
} from "lucide-react";
import { fetchPersons } from "@/lib/api";
import { PERSON_TYPE_LABELS } from "@/lib/utils";

export const revalidate = 60; // SSR with 60s ISR

export default async function HomePage() {
  let persons: Array<Record<string, unknown>> = [];
  let totalPersons = 0;

  try {
    const res = await fetchPersons({ per_page: 6, is_featured: true });
    persons = res?.items ?? [];
    totalPersons = res?.total ?? 0;
  } catch {
    // Graceful fallback if backend is starting
    persons = [];
  }

  const todayDateStr = new Date().toLocaleDateString("pl-PL", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  return (
    <div className="space-y-16 pb-16">
      {/* ─── Hero Section ─────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden bg-gradient-to-b from-burgundy-900 via-burgundy-800 to-burgundy-950 py-24 text-white">
        {/* Decorative background aura */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden opacity-20">
          <div className="absolute top-10 left-1/2 -translate-x-1/2 h-96 w-96 rounded-full bg-gold-400 blur-3xl" />
        </div>

        <div className="relative mx-auto max-w-5xl px-4 text-center sm:px-6 lg:px-8">
          <div className="inline-flex items-center gap-2 rounded-full border border-gold-400/30 bg-gold-500/10 px-4 py-1.5 text-xs font-semibold text-gold-300 backdrop-blur-md mb-6">
            <Sparkles className="h-3.5 w-3.5" />
            Cyfrowy Leksykon Hagiograficzny
          </div>

          <h1 className="font-serif text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-tight">
            Poznaj Świętych i Błogosławionych{" "}
            <span className="text-gold-gradient block mt-1">Kościoła Katolickiego</span>
          </h1>

          <p className="mx-auto mt-6 max-w-2xl text-base sm:text-lg text-burgundy-100 font-light leading-relaxed">
            Przeszukuj historie życia, patronaty, modlitwy oraz atrybuty ponad 20 000 postaci kanonizowanych przez wieki.
          </p>

          {/* Large Hero Search Box */}
          <form
            action="/swieci"
            method="GET"
            className="mx-auto mt-10 max-w-2xl"
          >
            <div className="relative flex items-center rounded-2xl bg-white p-2 shadow-2xl shadow-black/40">
              <Search className="ml-3.5 h-5 w-5 flex-shrink-0 text-gold-600" />
              <input
                type="text"
                name="search"
                placeholder="Wpisz imię, patronat lub kraj (np. Franciszek, patron kierowców)..."
                className="w-full bg-transparent px-3 py-3 text-sm text-gray-900 placeholder-gray-400 focus:outline-none"
              />
              <button
                type="submit"
                className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-gold-500 to-gold-600 px-6 py-3 text-sm font-semibold text-burgundy-950 shadow-md hover:from-gold-400 hover:to-gold-500 transition-all flex-shrink-0"
              >
                Szukaj
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </form>
        </div>
      </section>

      {/* ─── Today's Saint Spotlight ──────────────────────────────────────── */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 -mt-10">
        <div className="rounded-2xl border border-gold-500/30 bg-white p-6 sm:p-8 shadow-xl relative overflow-hidden">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-gold-700">
                <Calendar className="h-4 w-4" />
                Kalendarz Liturgiczny na dziś ({todayDateStr})
              </div>
              <h2 className="font-serif text-2xl sm:text-3xl font-bold text-burgundy-900">
                Patron Dnia: Św. Maksymilian Maria Kolbe
              </h2>
              <p className="text-sm text-gray-600 max-w-3xl leading-relaxed">
                Prezbiter i męczennik, założyciel Rycerstwa Niepokalanej, franciszkanin. Oddał własne życie za współwięźnia w obozie koncentracyjnym Auschwitz-Birkenau w 1941 roku.
              </p>
            </div>

            <Link
              href="/swieci/sw-maksymilian-maria-kolbe"
              className="flex-shrink-0 flex items-center gap-2 rounded-xl border border-burgundy-500/20 bg-burgundy-50 px-5 py-3 text-sm font-semibold text-burgundy-800 hover:bg-burgundy-100 transition-colors"
            >
              Zobacz pełny biogram
              <ChevronRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* ─── Featured Saints Grid ─────────────────────────────────────────── */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="font-serif text-2xl font-bold text-burgundy-900">
              Wyróżnione postacie
            </h2>
            <p className="text-sm text-gray-500">
              Przeglądaj wybrane postacie z naszej encyklopedii
            </p>
          </div>
          <Link
            href="/swieci"
            className="flex items-center gap-1 text-sm font-semibold text-gold-700 hover:text-gold-800"
          >
            Zobacz wszystkich ({totalPersons})
            <ChevronRight className="h-4 w-4" />
          </Link>
        </div>

        {persons.length === 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                name: "Św. Franciszek z Asyżu",
                type: "saint",
                desc: "Założyciel Zakonu Braci Mniejszych, stygmatyk, patron ekologii.",
                slug: "sw-franciszek-z-asyzu",
              },
              {
                name: "Św. Faustyna Kowalska",
                type: "saint",
                desc: "Apostołka Miłosierdzia Bożego, mistyczka, autorka Dzienniczka.",
                slug: "sw-faustyna-kowalska",
              },
              {
                name: "Bł. Jerzy Popiełuszko",
                type: "blessed",
                desc: "Kapłan i męczennik, kapelan Solidarności.",
                slug: "bl-jerzy-popieluszko",
              },
            ].map((p) => (
              <div
                key={p.slug}
                className="group rounded-2xl border border-gold-500/20 bg-white p-6 shadow-sm hover:shadow-md transition-all flex flex-col justify-between"
              >
                <div>
                  <span className="rounded-full bg-gold-100 px-3 py-1 text-xs font-semibold text-gold-800 inline-block mb-3">
                    {PERSON_TYPE_LABELS[p.type] ?? p.type}
                  </span>
                  <h3 className="font-serif text-lg font-bold text-burgundy-900 group-hover:text-gold-700 transition-colors">
                    {p.name}
                  </h3>
                  <p className="mt-2 text-xs text-gray-600 line-clamp-3 leading-relaxed">
                    {p.desc}
                  </p>
                </div>
                <Link
                  href={`/swieci/${p.slug}`}
                  className="mt-4 flex items-center gap-1 text-xs font-semibold text-gold-700 hover:underline"
                >
                  Czytaj życiorys <ChevronRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {persons.map((p) => (
              <div
                key={p.id as string}
                className="group rounded-2xl border border-gold-500/20 bg-white p-6 shadow-sm hover:shadow-md transition-all flex flex-col justify-between"
              >
                <div>
                  <span className="rounded-full bg-gold-100 px-3 py-1 text-xs font-semibold text-gold-800 inline-block mb-3">
                    {PERSON_TYPE_LABELS[p.person_type as string] ?? (p.person_type as string)}
                  </span>
                  <h3 className="font-serif text-lg font-bold text-burgundy-900 group-hover:text-gold-700 transition-colors">
                    {p.canonical_name as string}
                  </h3>
                  <p className="mt-2 text-xs text-gray-600 line-clamp-3 leading-relaxed">
                    {(p.summary_pl as string) || "Brak krótkiego streszczenia."}
                  </p>
                </div>
                <Link
                  href={`/swieci/${p.slug as string}`}
                  className="mt-4 flex items-center gap-1 text-xs font-semibold text-gold-700 hover:underline"
                >
                  Czytaj życiorys <ChevronRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ─── Stats Banner ──────────────────────────────────────────────────── */}
      <section className="bg-burgundy-900 text-white py-12">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          <div>
            <p className="font-serif text-3xl sm:text-4xl font-bold text-gold-400">20 000+</p>
            <p className="text-xs text-burgundy-200 mt-1 uppercase tracking-wider">Postaci i Świętych</p>
          </div>
          <div>
            <p className="font-serif text-3xl sm:text-4xl font-bold text-gold-400">1 500+</p>
            <p className="text-xs text-burgundy-200 mt-1 uppercase tracking-wider">Zakonów i Zgromadzeń</p>
          </div>
          <div>
            <p className="font-serif text-3xl sm:text-4xl font-bold text-gold-400">800+</p>
            <p className="text-xs text-burgundy-200 mt-1 uppercase tracking-wider">Sanktuariów i Miejsc</p>
          </div>
          <div>
            <p className="font-serif text-3xl sm:text-4xl font-bold text-gold-400">50 000+</p>
            <p className="text-xs text-burgundy-200 mt-1 uppercase tracking-wider">Rekordów Źródłowych</p>
          </div>
        </div>
      </section>
    </div>
  );
}
