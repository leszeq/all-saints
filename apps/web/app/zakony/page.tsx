import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  Filter,
  LibraryBig,
  Search,
  Sparkles,
  Users,
} from "lucide-react";

import { fetchOrders } from "@/lib/api";
import {
  formatOrderMemberCount,
  orderMonogram,
  type ReligiousOrder,
} from "@/lib/orders";
import { DEFAULT_WEB_UI_LOCALE } from "@/lib/i18n/config";
import { getWebDictionary } from "@/lib/i18n/dictionaries";
import { resolveDictionaryLabel } from "@/lib/i18n/labels";
import type { WebDictionary } from "@/lib/i18n/types";

export const metadata: Metadata = {
  title: "Zakony i zgromadzenia | Encyklopedia Świętych",
  description:
    "Historia, duchowość i misja zakonów oraz zgromadzeń wraz ze świętymi należącymi do poszczególnych wspólnot.",
};

export const revalidate = 300;

interface PageProps {
  searchParams: Promise<{
    search?: string;
    charism?: string;
    family?: string;
    type?: string;
  }>;
}

function OrderCard({
  order,
  labels,
  compact = false,
}: {
  order: ReligiousOrder;
  labels: WebDictionary["domain"]["religiousCommunities"];
  compact?: boolean;
}) {
  return (
    <Link
      href={`/zakony/${order.slug}`}
      className={`group flex h-full flex-col border border-[#ded8cd] bg-[#fffdf8] transition-all hover:-translate-y-1 hover:border-gold-400 hover:shadow-lg ${compact ? "rounded-xl p-5" : "rounded-2xl p-7"}`}
    >
      <div className="flex items-start justify-between gap-5">
        <span className={`flex shrink-0 items-center justify-center rounded-xl border border-gold-300 bg-gold-50 font-serif font-semibold text-burgundy-800 ${compact ? "h-12 min-w-12 px-2 text-sm" : "h-16 min-w-16 px-3 text-lg"}`}>
          {orderMonogram(order)}
        </span>
        <span className="rounded-full border border-[#ded8cd] px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-stone-500">
          {resolveDictionaryLabel(labels.communityTypes, order.community_type) ??
            order.community_type}
        </span>
      </div>
      <div className={compact ? "mt-5" : "mt-8"}>
        <p className="text-[10px] font-bold uppercase tracking-[0.13em] text-gold-800">
          {order.spiritual_family
            ? `Rodzina ${labels.spiritualFamilies[order.spiritual_family] ?? order.spiritual_family}`
            : resolveDictionaryLabel(labels.charisms, order.charism) ?? "Wspólnota zakonna"}
        </p>
        <h2 className={`${compact ? "mt-2 text-xl" : "mt-3 text-3xl"} font-serif font-semibold leading-tight text-charcoal group-hover:text-burgundy-700`}>
          {order.name}
        </h2>
        {order.name_la && !compact && (
          <p className="mt-2 font-serif text-sm italic text-stone-500">{order.name_la}</p>
        )}
        <p className={`mt-4 text-sm leading-6 text-stone-600 ${compact ? "line-clamp-3" : "line-clamp-4"}`}>
          {order.description || order.mission || "Opis wspólnoty jest opracowywany."}
        </p>
      </div>
      <div className="mt-auto flex items-center justify-between gap-3 border-t border-[#ded8cd] pt-5 text-xs">
        <span className="text-stone-500">
          {formatOrderMemberCount(order.member_count, labels.memberCount)}
        </span>
        <span className="inline-flex items-center gap-1 font-semibold text-burgundy-700">
          Poznaj <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-1" />
        </span>
      </div>
    </Link>
  );
}

export default async function OrdersPage({ searchParams }: PageProps) {
  const [params, dictionary] = await Promise.all([
    searchParams,
    getWebDictionary(DEFAULT_WEB_UI_LOCALE),
  ]);
  const labels = dictionary.domain.religiousCommunities;
  const query = {
    search: params.search?.trim() || undefined,
    charism: params.charism || undefined,
    spiritual_family: params.family || undefined,
    community_type: params.type || undefined,
  };
  const hasFilters = Object.values(query).some(Boolean);

  const catalogue = (await fetchOrders()) as ReligiousOrder[];
  const visibleOrders = hasFilters
    ? ((await fetchOrders(query)) as ReligiousOrder[])
    : catalogue;

  const featured = catalogue.filter((order) => order.is_featured).slice(0, 3);
  const remaining = hasFilters
    ? visibleOrders
    : visibleOrders.filter((order) => !order.is_featured);
  const families = new Set(catalogue.map((order) => order.spiritual_family).filter(Boolean)).size;
  const linkedPeople = catalogue.reduce((total, order) => total + order.member_count, 0);

  return (
    <main>
      <section className="relative overflow-hidden border-b border-[#ded8cd] bg-burgundy-900 text-white">
        <div className="pointer-events-none absolute -right-20 -top-28 h-96 w-96 rounded-full border border-white/10" />
        <div className="pointer-events-none absolute -right-4 -top-12 h-72 w-72 rounded-full border border-gold-300/20" />
        <div className="relative mx-auto grid max-w-7xl gap-10 px-4 py-20 sm:px-6 lg:grid-cols-[1fr_22rem] lg:px-8">
          <div className="max-w-3xl">
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-gold-300">Duchowe rodziny Kościoła</p>
            <h1 className="mt-5 font-serif text-5xl font-semibold tracking-tight sm:text-6xl">
              Zakony i zgromadzenia
            </h1>
            <p className="mt-6 max-w-2xl text-base leading-7 text-burgundy-100">
              Poznaj wspólnoty przez ich historię, misję i charyzmat — a następnie odkrywaj świętych, którzy tę duchowość przeżywali.
            </p>
          </div>
          <dl className="grid grid-cols-3 gap-px overflow-hidden rounded-xl border border-white/10 bg-white/10 lg:grid-cols-1">
            {[
              [catalogue.length, "wspólnot"],
              [families, "rodzin duchowych"],
              [linkedPeople, "powiązań ze świętymi"],
            ].map(([value, label]) => (
              <div key={String(label)} className="bg-burgundy-900/80 p-5">
                <dt className="text-[10px] uppercase tracking-wide text-burgundy-200">{label}</dt>
                <dd className="mt-1 font-serif text-3xl text-gold-200">{value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
        <form method="GET" className="grid gap-3 rounded-2xl border border-[#ded8cd] bg-white p-4 shadow-sm md:grid-cols-[1.4fr_repeat(3,1fr)_auto]">
          <label className="relative">
            <span className="sr-only">Szukaj wspólnoty</span>
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
            <input name="search" defaultValue={params.search} className="h-11 w-full rounded-lg border border-[#ded8cd] bg-[#fffdf8] pl-9 pr-3 text-sm outline-none focus:border-gold-500" placeholder="Nazwa, skrót lub misja…" />
          </label>
          <label>
            <span className="sr-only">Rodzina duchowa</span>
            <select name="family" defaultValue={params.family || ""} className="h-11 w-full rounded-lg border border-[#ded8cd] bg-[#fffdf8] px-3 text-sm outline-none focus:border-gold-500">
              <option value="">Wszystkie rodziny</option>
              {Object.entries(labels.spiritualFamilies).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <label>
            <span className="sr-only">Charyzmat</span>
            <select name="charism" defaultValue={params.charism || ""} className="h-11 w-full rounded-lg border border-[#ded8cd] bg-[#fffdf8] px-3 text-sm outline-none focus:border-gold-500">
              <option value="">Wszystkie charyzmaty</option>
              {Object.entries(labels.charisms).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <label>
            <span className="sr-only">Typ wspólnoty</span>
            <select name="type" defaultValue={params.type || ""} className="h-11 w-full rounded-lg border border-[#ded8cd] bg-[#fffdf8] px-3 text-sm outline-none focus:border-gold-500">
              <option value="">Wszystkie typy</option>
              {Object.entries(labels.communityTypes).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <button className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-burgundy-700 px-5 text-sm font-semibold text-white hover:bg-burgundy-600">
            <Filter className="h-4 w-4" /> Filtruj
          </button>
        </form>
        {hasFilters && (
          <div className="mt-3 flex items-center justify-between text-xs text-stone-500">
            <span>Znaleziono: {visibleOrders.length}</span>
            <Link href="/zakony" className="font-semibold text-burgundy-700 hover:underline">Wyczyść filtry</Link>
          </div>
        )}
      </section>

      {!hasFilters && featured.length > 0 && (
        <section className="mx-auto max-w-7xl px-4 pb-20 sm:px-6 lg:px-8">
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="editorial-label">Najbardziej znane tradycje</p>
              <h2 className="mt-3 font-serif text-4xl font-semibold text-charcoal">Trzy punkty wejścia</h2>
            </div>
            <Sparkles className="h-7 w-7 text-gold-700" strokeWidth={1.4} />
          </div>
          <div className="mt-8 grid gap-5 lg:grid-cols-3">
            {featured.map((order) => <OrderCard key={order.id} order={order} labels={labels} />)}
          </div>
        </section>
      )}

      <section className="border-y border-[#ded8cd] bg-[#fffdf8] py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl">
            <p className="editorial-label">{hasFilters ? "Wyniki katalogu" : "Poza głównym nurtem"}</p>
            <h2 className="mt-3 font-serif text-4xl font-semibold text-charcoal">
              {hasFilters ? "Wspólnoty spełniające kryteria" : "Pozostałe wspólnoty"}
            </h2>
            <p className="mt-4 text-sm leading-6 text-stone-600">
              Mniejsze instytuty pokazujemy według rodziny duchowej, typu i misji. Dzięki temu zgromadzenie apostolskie nie znika w alfabetycznej liście obok wielowiekowej rodziny monastycznej.
            </p>
          </div>
          {remaining.length > 0 ? (
            <div className="mt-9 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {remaining.map((order) => <OrderCard key={order.id} order={order} labels={labels} compact />)}
            </div>
          ) : (
            <div className="mt-9 rounded-2xl border border-dashed border-[#ded8cd] bg-white p-10 text-center">
              <Search className="mx-auto h-8 w-8 text-gold-700" />
              <h3 className="mt-4 font-serif text-2xl font-semibold">Brak wspólnot dla tych filtrów</h3>
              <p className="mt-2 text-sm text-stone-500">Zmień kryteria albo wróć do pełnego katalogu.</p>
            </div>
          )}
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-px overflow-hidden px-4 py-20 sm:px-6 md:grid-cols-3 lg:px-8">
        {[
          [LibraryBig, "Rodzina duchowa", "Łączy odrębne zakony i zgromadzenia czerpiące z tej samej tradycji."],
          [Users, "Różne formy przynależności", "Rozróżniamy braci, mniszki, siostry, świeckich członków i patronów duchowych."],
          [BookOpen, "Źródło przy historii", "Każdy profil wskazuje dokument lub oficjalną stronę użytą przez redakcję."],
        ].map(([Icon, title, description]) => {
          const FeatureIcon = Icon as typeof LibraryBig;
          return (
            <article key={String(title)} className="border border-[#ded8cd] bg-white p-7 md:border-r-0 last:md:border-r">
              <FeatureIcon className="h-6 w-6 text-gold-700" strokeWidth={1.5} />
              <h3 className="mt-6 font-serif text-xl font-semibold">{String(title)}</h3>
              <p className="mt-2 text-sm leading-6 text-stone-600">{String(description)}</p>
            </article>
          );
        })}
      </section>
    </main>
  );
}
