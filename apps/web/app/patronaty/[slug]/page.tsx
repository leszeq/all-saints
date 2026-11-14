import type { Metadata } from "next";
import Link from "next/link";
import { notFound, permanentRedirect } from "next/navigation";
import { ArrowLeft, ArrowRight, HeartHandshake, Users } from "lucide-react";

import { fetchPatronagePersons, isApiNotFound } from "@/lib/api";
import {
  type PatronageConceptPersonsResponse,
} from "@/lib/patronages";
import { DEFAULT_WEB_UI_LOCALE } from "@/lib/i18n/config";
import { getWebDictionary } from "@/lib/i18n/dictionaries";
import { resolveDictionaryLabel, resolveDictionaryValue } from "@/lib/i18n/labels";
import { stripMarkdown } from "@/components/markdown-content";
import { absoluteSiteUrl } from "@/lib/site-url";

export const revalidate = 300;

interface PageProps {
  params: Promise<{ slug: string }>;
}

async function loadConcept(slug: string): Promise<PatronageConceptPersonsResponse> {
  return (await fetchPatronagePersons(slug)) as PatronageConceptPersonsResponse;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const [{ slug }, dictionary] = await Promise.all([
    params,
    getWebDictionary(DEFAULT_WEB_UI_LOCALE),
  ]);
  const copy = dictionary.patronageDirectory;
  try {
    const data = await loadConcept(slug);
    return {
      title: `${data.concept.name_pl}${copy.metadataTitleSuffix}`,
      alternates: {
        canonical: absoluteSiteUrl(`/patronaty/${encodeURIComponent(data.concept.slug)}`),
      },
      description:
        data.concept.description || `${copy.metadataDescriptionPrefix}${data.concept.name_pl}.`,
    };
  } catch (error) {
    if (isApiNotFound(error)) return { title: copy.notFoundTitle };
    throw error;
  }
}

export default async function PatronageDetailPage({ params }: PageProps) {
  const [{ slug }, dictionary] = await Promise.all([
    params,
    getWebDictionary(DEFAULT_WEB_UI_LOCALE),
  ]);
  const copy = dictionary.patronageDirectory;
  let data: PatronageConceptPersonsResponse;
  try {
    data = await loadConcept(slug);
  } catch (error) {
    if (isApiNotFound(error)) notFound();
    throw error;
  }

  if (slug !== data.concept.slug) {
    permanentRedirect(`/patronaty/${encodeURIComponent(data.concept.slug)}`);
  }

  const typeLabel = resolveDictionaryLabel(
    dictionary.saintsDirectory.patronageTypeLabels,
    data.concept.patronage_type,
  ) ?? data.concept.patronage_type;

  return (
    <main>
      <section className="border-b border-[#ded8cd] bg-burgundy-900 text-white">
        <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
          <Link
            href="/swieci"
            className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.12em] text-gold-300 hover:text-gold-200"
          >
            <ArrowLeft className="h-4 w-4" /> {copy.backToDirectory}
          </Link>
          <div className="mt-10 grid items-start gap-8 md:grid-cols-[5rem_1fr]">
            <div className="flex h-20 w-20 items-center justify-center rounded-2xl border border-gold-300/30 bg-white/5 text-gold-200 shadow-2xl">
              <HeartHandshake className="h-9 w-9" strokeWidth={1.4} />
            </div>
            <div>
              <span className="rounded-full bg-gold-300 px-3 py-1 text-[10px] font-bold uppercase tracking-wide text-burgundy-950">
                {typeLabel}
              </span>
              <h1 className="mt-5 max-w-4xl font-serif text-4xl font-semibold leading-tight sm:text-6xl">
                {data.concept.name_pl}
              </h1>
              {data.concept.name_en && (
                <p className="mt-3 font-serif text-lg italic text-gold-100">{data.concept.name_en}</p>
              )}
              <p className="mt-5 max-w-3xl text-sm leading-7 text-burgundy-100">
                {data.concept.description || copy.descriptionFallback}
              </p>
            </div>
          </div>
          <dl className="mt-10 grid overflow-hidden rounded-xl border border-white/10 bg-white/10 sm:grid-cols-2">
            <div className="bg-burgundy-900/80 p-5">
              <dt className="text-[10px] uppercase tracking-wide text-gold-300">{copy.typeLabel}</dt>
              <dd className="mt-1 font-serif text-xl">{typeLabel}</dd>
            </div>
            <div className="border-t border-white/10 bg-burgundy-900/80 p-5 sm:border-l sm:border-t-0">
              <dt className="text-[10px] uppercase tracking-wide text-gold-300">{copy.peopleLabel}</dt>
              <dd className="mt-1 font-serif text-xl">{data.concept.person_count}</dd>
            </div>
          </dl>
        </div>
      </section>

      <section className="border-y border-[#ded8cd] bg-[#fffdf8] py-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex items-end justify-between gap-5">
            <div>
              <p className="editorial-label">{copy.peopleKicker}</p>
              <h2 className="mt-3 font-serif text-4xl font-semibold">{copy.peopleTitle}</h2>
            </div>
            <Users className="h-7 w-7 text-gold-700" strokeWidth={1.4} />
          </div>
          {data.items.length > 0 ? (
            <div className="mt-8 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
              {data.items.map((person) => (
                <Link
                  key={person.id}
                  href={`/swieci/${encodeURIComponent(person.slug)}`}
                  className="group surface-card flex min-h-52 flex-col p-6 transition-transform hover:-translate-y-1"
                >
                  <p className="text-[10px] font-bold uppercase tracking-wide text-stone-500">
                    {resolveDictionaryValue(dictionary.domain.personTypes, person.person_type)?.label ??
                      person.person_type}
                  </p>
                  <h3 className="mt-3 font-serif text-2xl font-semibold text-charcoal group-hover:text-burgundy-700">
                    {person.canonical_name}
                  </h3>
                  <p className="mt-3 line-clamp-3 text-sm leading-6 text-stone-600">
                    {person.summary_pl ? stripMarkdown(person.summary_pl) : copy.personSummaryFallback}
                  </p>
                  <span className="mt-auto inline-flex items-center gap-1 pt-5 text-sm font-semibold text-burgundy-700">
                    {copy.fullProfile} <ArrowRight className="h-4 w-4" />
                  </span>
                </Link>
              ))}
            </div>
          ) : (
            <div className="mt-8 rounded-2xl border border-dashed border-[#ded8cd] bg-white p-10 text-center text-sm text-stone-500">
              {copy.peopleEmpty}
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
