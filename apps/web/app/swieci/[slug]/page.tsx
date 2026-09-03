import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  ArrowLeft,
  BadgeCheck,
  BookOpen,
  CalendarDays,
  Crown,
  Heart,
  HeartHandshake,
  Landmark,
  Sparkles,
} from "lucide-react";
import { fetchPersonDetail, isApiNotFound } from "@/lib/api";
import { ERA_LABELS, PERSON_TYPE_LABELS } from "@/lib/utils";
import { SaintAvatar, type SaintAvatarData } from "@/components/saint-avatar";
import { MEMBERSHIP_TYPE_LABELS } from "@/lib/orders";

interface PageProps {
  params: Promise<{
    slug: string;
  }>;
}

function formatRecognitionDate(value?: string | null, year?: number | null) {
  if (value && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return new Intl.DateTimeFormat("pl-PL", {
      day: "numeric",
      month: "long",
      year: "numeric",
      timeZone: "UTC",
    }).format(new Date(`${value}T00:00:00Z`));
  }
  return value || (year ? String(year) : null);
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  try {
    const person = await fetchPersonDetail(slug);
    if (!person) return { title: "Nie znaleziono" };
    return {
      title: `${person.canonical_name} – Życiorys, modlitwy i patronaty`,
      description: person.summary_pl || `Życiorys i informacje o ${person.canonical_name}.`,
      openGraph: {
        title: person.canonical_name,
        description: person.summary_pl || `Życiorys ${person.canonical_name}`,
        images: person.avatar?.url
          ? [{ url: person.avatar.url, alt: person.avatar.title || `Portret: ${person.canonical_name}` }]
          : undefined,
      },
    };
  } catch (error) {
    if (isApiNotFound(error)) return { title: "Nie znaleziono" };
    throw error;
  }
}

export default async function PersonDetailPage({ params }: PageProps) {
  const { slug } = await params;
  let person: Record<string, unknown> | null = null;

  try {
    person = await fetchPersonDetail(slug);
  } catch (error) {
    if (isApiNotFound(error)) notFound();
    throw error;
  }

  if (!person) {
    notFound();
  }

  // Schema.org Person JSON-LD for Google SEO
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Person",
    name: person.canonical_name,
    alternateName: person.latin_name,
    description: person.summary_pl,
    birthDate: person.birth_year ? String(person.birth_year) : undefined,
    deathDate: person.death_year ? String(person.death_year) : undefined,
    image: (person.avatar as SaintAvatarData | null)?.url || undefined,
  };
  const beatification = person.beatification as Record<string, unknown> | null;
  const canonization = person.canonization as Record<string, unknown> | null;
  const beatificationLabel = formatRecognitionDate(
    beatification?.beatification_date as string | null,
    beatification?.beatification_year as number | null,
  );
  const canonizationLabel = formatRecognitionDate(
    canonization?.canonization_date as string | null,
    canonization?.canonization_year as number | null,
  );

  return (
    <article className="pb-16 space-y-12">
      {/* Inject JSON-LD */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* ─── Hero Banner ──────────────────────────────────────────────────── */}
      <section className="bg-gradient-to-br from-burgundy-900 via-burgundy-800 to-burgundy-700 py-16 text-white">
        <div className="mx-auto max-w-5xl space-y-6 px-4 sm:px-6 lg:px-8">
          <Link
            href="/swieci"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-gold-400 hover:text-gold-300 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Wróć do katalogu
          </Link>

          <div className="grid items-center gap-8 sm:grid-cols-[12rem_1fr]">
            <SaintAvatar
              name={String(person.canonical_name)}
              avatar={person.avatar as SaintAvatarData | null}
              className="h-48 w-48 rounded-2xl border-gold-300/40 bg-burgundy-800 text-5xl text-gold-300 shadow-2xl shadow-black/20"
              eager
            />

            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full border border-gold-400/30 bg-gold-500/20 px-3 py-1 text-xs font-semibold text-gold-300 backdrop-blur-md">
                  {PERSON_TYPE_LABELS[person.person_type as string] ?? (person.person_type as string)}
                </span>
                {Boolean(person.era) && (
                  <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-burgundy-200">
                    Era: {ERA_LABELS[person.era as string] ?? String(person.era)}
                  </span>
                )}
              </div>

              <h1 className="font-serif text-3xl font-bold tracking-tight text-white sm:text-5xl">
                {String(person.canonical_name)}
              </h1>

              {Boolean(person.latin_name) && (
                <p className="font-serif text-lg font-medium italic text-gold-100">
                  {String(person.latin_name)}
                </p>
              )}

              {/* Quick Stats */}
              <dl className="grid grid-cols-2 overflow-hidden rounded-xl border border-white/15 bg-black/10 shadow-sm sm:grid-cols-4">
                {Boolean(person.birth_year) && (
                  <div className="border-b border-r border-white/10 bg-burgundy-900/55 px-4 py-3 sm:border-b-0">
                    <dt className="text-[10px] font-bold uppercase tracking-wider text-gold-300">Rok urodzenia</dt>
                    <dd className="mt-1 text-sm font-semibold text-white">{String(person.birth_year)}</dd>
                  </div>
                )}
                {Boolean(person.death_year) && (
                  <div className="border-b border-white/10 bg-burgundy-900/55 px-4 py-3 sm:border-b-0 sm:border-r">
                    <dt className="text-[10px] font-bold uppercase tracking-wider text-gold-300">Rok śmierci</dt>
                    <dd className="mt-1 text-sm font-semibold text-white">{String(person.death_year)}</dd>
                  </div>
                )}
                {Boolean(person.gender) && (
                  <div className="border-r border-white/10 bg-burgundy-900/55 px-4 py-3">
                    <dt className="text-[10px] font-bold uppercase tracking-wider text-gold-300">Płeć</dt>
                    <dd className="mt-1 text-sm font-semibold text-white">
                      {person.gender === "male" ? "Mężczyzna" : person.gender === "female" ? "Kobieta" : "—"}
                    </dd>
                  </div>
                )}
                {Boolean((person.state_of_life as Record<string, unknown> | null)?.name_pl) && (
                  <div className="bg-burgundy-900/55 px-4 py-3">
                    <dt className="text-[10px] font-bold uppercase tracking-wider text-gold-300">Stan życia</dt>
                    <dd className="mt-1 text-sm font-semibold text-white">
                      {String((person.state_of_life as Record<string, unknown>).name_pl)}
                    </dd>
                  </div>
                )}
              </dl>
            </div>
          </div>
        </div>
      </section>

      {/* ─── Content Body ─────────────────────────────────────────────────── */}
      <section className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 space-y-8">
        {/* Summary Card */}
        {Boolean(person.summary_pl) && (
          <div className="rounded-2xl border border-gold-500/30 bg-gold-50/50 p-6 sm:p-8 shadow-sm">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-gold-800 mb-2 flex items-center gap-1.5">
              <Sparkles className="h-4 w-4 text-gold-600" />
              Streszczenie
            </h2>
            <p className="font-serif text-base sm:text-lg text-burgundy-950 leading-relaxed italic">
              {String(person.summary_pl)}
            </p>
          </div>
        )}

        {(beatificationLabel || canonizationLabel) && (
          <section className="rounded-2xl border border-gold-500/25 bg-[#fffdf8] p-6 shadow-sm sm:p-8">
            <div className="flex items-start gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-gold-500/30 bg-gold-50 text-gold-700">
                <BadgeCheck className="h-5 w-5" />
              </span>
              <div>
                <h2 className="font-serif text-2xl font-bold text-burgundy-900">
                  Droga do chwały ołtarzy
                </h2>
                <p className="mt-1 text-sm leading-6 text-stone-600">
                  Udokumentowane daty oficjalnego ogłoszenia przez Kościół.
                </p>
              </div>
            </div>

            <dl className="mt-6 grid gap-3 sm:grid-cols-2">
              {beatificationLabel && (
                <div className="rounded-xl border border-[#ded8cd] bg-white px-4 py-4">
                  <dt className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.14em] text-gold-800">
                    <CalendarDays className="h-4 w-4" />
                    Beatyfikacja
                  </dt>
                  <dd className="mt-2 font-serif text-xl font-semibold text-burgundy-950">
                    {beatificationLabel}
                  </dd>
                </div>
              )}
              {canonizationLabel && (
                <div className="rounded-xl border border-[#ded8cd] bg-white px-4 py-4">
                  <dt className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.14em] text-gold-800">
                    <CalendarDays className="h-4 w-4" />
                    Kanonizacja
                  </dt>
                  <dd className="mt-2 font-serif text-xl font-semibold text-burgundy-950">
                    {canonizationLabel}
                  </dd>
                </div>
              )}
            </dl>
          </section>
        )}

        {/* Biography */}
        <div className="rounded-2xl border border-gold-500/20 bg-white p-6 sm:p-8 shadow-sm space-y-4">
          <h2 className="font-serif text-2xl font-bold text-burgundy-900 flex items-center gap-2 border-b border-gray-100 pb-3">
            <BookOpen className="h-5 w-5 text-gold-600" />
            Życiorys i Dzieło
          </h2>
          {Boolean(person.biography_pl) ? (
            <div className="prose prose-burgundy max-w-none text-base text-gray-800 leading-relaxed whitespace-pre-line">
              {String(person.biography_pl)}
            </div>
          ) : (
            <p className="text-sm text-gray-500">Brak pełnego biogramu w bazie danych.</p>
          )}
        </div>

        {/* Patronages */}
        {Array.isArray(person.patronages) && person.patronages.length > 0 && (
          <section className="rounded-2xl border border-gold-500/20 bg-white p-6 shadow-sm sm:p-8">
            <h2 className="flex items-center gap-2 font-serif text-2xl font-bold text-burgundy-900">
              <HeartHandshake className="h-5 w-5 text-gold-600" />
              Patronaty
            </h2>
            <ul className="mt-4 flex flex-wrap gap-2">
              {(person.patronages as Array<Record<string, unknown>>).map((patronage) => (
                <li
                  key={String(patronage.id)}
                  className="rounded-full border border-burgundy-500/15 bg-burgundy-50 px-3 py-1.5 text-xs font-medium text-burgundy-900"
                >
                  {String(patronage.name_pl)}
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Religious communities */}
        {Array.isArray(person.orders) && person.orders.length > 0 && (
          <section className="rounded-2xl border border-gold-500/20 bg-white p-6 shadow-sm sm:p-8">
            <h2 className="flex items-center gap-2 font-serif text-2xl font-bold text-burgundy-900">
              <Landmark className="h-5 w-5 text-gold-600" />
              Zakony i zgromadzenia
            </h2>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              {(person.orders as Array<Record<string, unknown>>).map((membership) => {
                const order = membership.order as Record<string, unknown>;
                return (
                  <Link
                    key={String(order.id)}
                    href={`/zakony/${String(order.slug)}`}
                    className="group rounded-xl border border-[#ded8cd] bg-[#fffdf8] p-4 transition-colors hover:border-gold-400 hover:bg-gold-50"
                  >
                    <p className="text-[10px] font-bold uppercase tracking-wide text-gold-800">
                      {MEMBERSHIP_TYPE_LABELS[String(membership.membership_type)] ?? String(membership.membership_type)}
                    </p>
                    <h3 className="mt-1 font-serif text-lg font-semibold text-charcoal group-hover:text-burgundy-700">
                      {String(order.name)}
                      {Boolean(order.abbreviation) && <span className="ml-2 text-sm text-stone-500">{String(order.abbreviation)}</span>}
                    </h3>
                    {Boolean(membership.notes) && <p className="mt-2 line-clamp-2 text-xs leading-5 text-stone-600">{String(membership.notes)}</p>}
                  </Link>
                );
              })}
            </div>
          </section>
        )}

        {/* Prayers / Attributes Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Prayers */}
          <div className="rounded-2xl border border-gold-500/20 bg-white p-6 shadow-sm space-y-3">
            <h3 className="font-serif text-lg font-bold text-burgundy-900 flex items-center gap-2">
              <Heart className="h-4 w-4 text-gold-600" />
              Modlitwa
            </h3>
            {Boolean(person.prayers) ? (
              <p className="whitespace-pre-line text-sm leading-relaxed text-gray-700 italic">
                {String(person.prayers)}
              </p>
            ) : (
              <p className="text-xs text-gray-400">Brak przypisanych modlitw.</p>
            )}
          </div>

          {/* Iconography */}
          <div className="rounded-2xl border border-gold-500/20 bg-white p-6 shadow-sm space-y-3">
            <h3 className="font-serif text-lg font-bold text-burgundy-900 flex items-center gap-2">
              <Crown className="h-4 w-4 text-gold-600" />
              Atrybuty Ikonograficzne
            </h3>
            {Boolean(person.iconographic_attributes) ? (
              <ul className="flex flex-wrap gap-2">
                {String(person.iconographic_attributes)
                  .split(/[;\n]+/)
                  .map((attribute) => attribute.trim())
                  .filter(Boolean)
                  .map((attribute) => (
                    <li key={attribute} className="rounded-full border border-gold-500/25 bg-gold-50 px-3 py-1 text-xs text-burgundy-900">
                      {attribute}
                    </li>
                  ))}
              </ul>
            ) : (
              <p className="text-xs text-gray-400">Brak podanych atrybutów.</p>
            )}
          </div>
        </div>
      </section>
    </article>
  );
}
