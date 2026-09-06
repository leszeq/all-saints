import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, BookOpen, CalendarDays, Church, Sparkles } from "lucide-react";

import { fetchLiturgicalObservance, isApiNotFound } from "@/lib/api";
import { type LiturgicalObservance } from "@/lib/calendar";
import { DEFAULT_WEB_UI_LOCALE } from "@/lib/i18n/config";
import { getWebDictionary } from "@/lib/i18n/dictionaries";
import { resolveDictionaryLabel } from "@/lib/i18n/labels";


export const revalidate = 300;


interface PageProps {
  params: Promise<{ slug: string }>;
}


async function loadObservance(slug: string): Promise<LiturgicalObservance | null> {
  try {
    return (await fetchLiturgicalObservance(slug)) as LiturgicalObservance;
  } catch (error) {
    if (isApiNotFound(error)) return null;
    throw error;
  }
}


export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const [{ slug }, dictionary] = await Promise.all([
    params,
    getWebDictionary(DEFAULT_WEB_UI_LOCALE),
  ]);
  const copy = dictionary.calendar.observance;
  const observance = await loadObservance(slug);
  if (!observance) return { title: copy.metadataFallbackTitle };
  return {
    title: `${observance.title_pl}${copy.metadataTitleSuffix}`,
    description:
      observance.summary_pl ?? `${copy.metadataDescriptionPrefix}${observance.title_pl}.`,
  };
}


export default async function LiturgicalObservancePage({ params }: PageProps) {
  const [{ slug }, dictionary] = await Promise.all([
    params,
    getWebDictionary(DEFAULT_WEB_UI_LOCALE),
  ]);
  const copy = dictionary.calendar.observance;
  const observance = await loadObservance(slug);
  if (!observance) notFound();

  const typeLabel =
    resolveDictionaryLabel(dictionary.calendar.observanceTypes, observance.observance_type) ??
    dictionary.calendar.observanceTypes.other;
  const attributes = observance.iconographic_attributes
    ?.split(";")
    .map((item) => item.trim())
    .filter(Boolean) ?? [];

  return (
    <main>
      <section className="border-b border-[#ded8cd] bg-[#fffdf8]">
        <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
          <Link
            href="/kalendarz"
            className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.12em] text-burgundy-700 hover:underline"
          >
            <ArrowLeft className="h-4 w-4" /> {copy.backToCalendar}
          </Link>
          <div className="mt-10 grid items-center gap-10 lg:grid-cols-[16rem_1fr]">
            <div className="flex aspect-square items-center justify-center rounded-full border border-gold-300 bg-burgundy-800 text-gold-200 shadow-sm">
              <Church className="h-20 w-20" strokeWidth={1} />
            </div>
            <div className="max-w-4xl">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-gold-100 px-3 py-1 text-xs font-bold text-gold-800">
                  {typeLabel}
                </span>
                <span className="rounded-full border border-[#ded8cd] px-3 py-1 text-xs font-semibold text-stone-600">
                  {copy.separateProfileNotice}
                </span>
              </div>
              <h1 className="mt-5 font-serif text-4xl font-semibold tracking-tight text-charcoal sm:text-6xl">
                {observance.title_pl}
              </h1>
              {observance.latin_title && (
                <p className="mt-3 font-serif text-xl italic text-stone-600">
                  {observance.latin_title}
                </p>
              )}
              <p className="mt-6 max-w-3xl text-base leading-7 text-stone-600">
                {observance.summary_pl ?? copy.summaryFallback}
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-10 px-4 py-14 sm:px-6 lg:grid-cols-[1fr_19rem] lg:px-8">
        <article className="surface-card p-7 sm:p-10">
          <div className="flex items-center gap-3 text-gold-700">
            <BookOpen className="h-5 w-5" />
            <p className="editorial-label">{copy.historyKicker}</p>
          </div>
          <div className="mt-7 whitespace-pre-line text-base leading-8 text-stone-700">
            {observance.description_pl ?? observance.summary_pl}
          </div>
        </article>

        <aside className="space-y-5">
          <div className="surface-card p-6">
            <Sparkles className="h-5 w-5 text-gold-700" />
            <h2 className="mt-4 font-serif text-xl font-semibold text-charcoal">
              {copy.iconographicAttributes}
            </h2>
            {attributes.length ? (
              <ul className="mt-4 space-y-2 text-sm leading-6 text-stone-600">
                {attributes.map((attribute) => (
                  <li key={attribute} className="border-b border-[#ded8cd] pb-2 last:border-0">
                    {attribute}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-sm leading-6 text-stone-500">{copy.pending}</p>
            )}
          </div>
          <Link
            href="/kalendarz"
            className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-burgundy-700 px-5 text-sm font-semibold text-white hover:bg-burgundy-600"
          >
            <CalendarDays className="h-4 w-4" /> {copy.viewCalendar}
          </Link>
        </aside>
      </section>
    </main>
  );
}
