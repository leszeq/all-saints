import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  ArrowLeft,
  BookOpen,
  Calendar,
  Crown,
  Globe,
  Heart,
  HelpCircle,
  MapPin,
  Shield,
  Sparkles,
} from "lucide-react";
import { fetchPersonDetail } from "@/lib/api";
import { PERSON_TYPE_LABELS } from "@/lib/utils";

interface PageProps {
  params: Promise<{
    slug: string;
  }>;
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
      },
    };
  } catch {
    return { title: "Święty" };
  }
}

export default async function PersonDetailPage({ params }: PageProps) {
  const { slug } = await params;
  let person: Record<string, unknown> | null = null;

  try {
    person = await fetchPersonDetail(slug);
  } catch {
    notFound();
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
  };

  return (
    <article className="pb-16 space-y-12">
      {/* Inject JSON-LD */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* ─── Hero Banner ──────────────────────────────────────────────────── */}
      <section className="bg-gradient-to-b from-burgundy-900 via-burgundy-850 to-burgundy-950 text-white py-16">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 space-y-6">
          <Link
            href="/swieci"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-gold-400 hover:text-gold-300 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Wróć do katalogu
          </Link>

          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-gold-500/20 border border-gold-400/30 px-3 py-1 text-xs font-semibold text-gold-300 backdrop-blur-md">
                {PERSON_TYPE_LABELS[person.person_type as string] ?? (person.person_type as string)}
              </span>
              {Boolean(person.era) && (
                <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-burgundy-200">
                  Era: {String(person.era)}
                </span>
              )}
            </div>

            <h1 className="font-serif text-3xl sm:text-5xl font-bold tracking-tight text-white">
              {String(person.canonical_name)}
            </h1>

            {Boolean(person.latin_name) && (
              <p className="text-lg text-gold-300 italic font-serif">
                {String(person.latin_name)}
              </p>
            )}
          </div>

          {/* Quick Stats Pill */}
          <div className="flex flex-wrap gap-6 border-t border-burgundy-800 pt-6 text-xs text-burgundy-200">
            {Boolean(person.birth_year) && (
              <div>
                <span className="text-gold-400 block uppercase font-semibold">Rok urodzenia</span>
                <span>{String(person.birth_year)}</span>
              </div>
            )}
            {Boolean(person.death_year) && (
              <div>
                <span className="text-gold-400 block uppercase font-semibold">Rok śmierci</span>
                <span>{String(person.death_year)}</span>
              </div>
            )}
            {Boolean(person.gender) && (
              <div>
                <span className="text-gold-400 block uppercase font-semibold">Płeć</span>
                <span>{person.gender === "male" ? "Mężczyzna" : person.gender === "female" ? "Kobieta" : "—"}</span>
              </div>
            )}
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

        {/* Prayers / Attributes Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Prayers */}
          <div className="rounded-2xl border border-gold-500/20 bg-white p-6 shadow-sm space-y-3">
            <h3 className="font-serif text-lg font-bold text-burgundy-900 flex items-center gap-2">
              <Heart className="h-4 w-4 text-gold-600" />
              Modlitwa
            </h3>
            {Boolean(person.prayers) ? (
              <p className="text-sm text-gray-700 leading-relaxed italic">
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
              <p className="text-sm text-gray-700 leading-relaxed">
                {String(person.iconographic_attributes)}
              </p>
            ) : (
              <p className="text-xs text-gray-400">Brak podanych atrybutów.</p>
            )}
          </div>
        </div>
      </section>
    </article>
  );
}
