import type { Metadata } from "next";
import Link from "next/link";
import { notFound, permanentRedirect } from "next/navigation";
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
import { fetchPersonCommemorations, fetchPersonDetail, isApiNotFound } from "@/lib/api";
import { SaintAvatar, type SaintAvatarData } from "@/components/saint-avatar";
import { PersonCitationButton } from "@/components/person-citation-button";
import { PersonCommemorations } from "@/components/person-commemorations";
import { PersonFacts } from "@/components/person-facts";
import { PersonTableOfContents, type PersonTableOfContentsItem } from "@/components/person-table-of-contents";
import { DEFAULT_WEB_UI_LOCALE } from "@/lib/i18n/config";
import { getWebDictionary } from "@/lib/i18n/dictionaries";
import { resolveDictionaryLabel, resolveDictionaryValue } from "@/lib/i18n/labels";
import { readPublicPersonContent } from "@/lib/person-content";
import { serializeJsonLd } from "@/lib/json-ld";
import { PersonSources } from "@/components/person-sources";
import { PersonFeedback } from "@/components/person-feedback";
import type { PublicPersonSource } from "@/lib/person-sources";
import type { PersonCommemoration } from "@/lib/calendar";

interface PageProps {
  params: Promise<{
    slug: string;
  }>;
}

function formatRecognitionDate(
  value?: string | null,
  year?: number | null,
  locale = DEFAULT_WEB_UI_LOCALE,
) {
  if (value && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return new Intl.DateTimeFormat(locale, {
      day: "numeric",
      month: "long",
      year: "numeric",
      timeZone: "UTC",
    }).format(new Date(`${value}T00:00:00Z`));
  }
  return value || (year ? String(year) : null);
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const [{ slug }, dictionary] = await Promise.all([
    params,
    getWebDictionary(DEFAULT_WEB_UI_LOCALE),
  ]);
  const copy = dictionary.personProfile;
  try {
    const person = await fetchPersonDetail(slug, DEFAULT_WEB_UI_LOCALE);
    if (!person) return { title: copy.notFoundTitle };
    const content = readPublicPersonContent(person);
    return {
      title: `${content.canonicalName}${copy.metadataTitleSuffix}`,
      alternates: { canonical: `/swieci/${encodeURIComponent(String(person.slug))}` },
      description:
        content.summary || `${copy.metadataDescriptionPrefix}${content.canonicalName}.`,
      openGraph: {
        title: content.canonicalName,
        url: `/swieci/${encodeURIComponent(String(person.slug))}`,
        description:
          content.summary || `${copy.metadataBiographyPrefix}${content.canonicalName}`,
        images: person.avatar?.url
          ? [
              {
                url: person.avatar.url,
                alt:
                  person.avatar.title ||
                  `${copy.portraitPrefix}${content.canonicalName}`,
              },
            ]
          : undefined,
      },
    };
  } catch (error) {
    if (isApiNotFound(error)) return { title: copy.notFoundTitle };
    throw error;
  }
}

export default async function PersonDetailPage({ params }: PageProps) {
  const [{ slug }, dictionary] = await Promise.all([
    params,
    getWebDictionary(DEFAULT_WEB_UI_LOCALE),
  ]);
  const copy = dictionary.personProfile;
  const domain = dictionary.domain;
  let person: Record<string, unknown> | null = null;

  try {
    person = await fetchPersonDetail(slug, DEFAULT_WEB_UI_LOCALE);
  } catch (error) {
    if (isApiNotFound(error)) notFound();
    throw error;
  }

  if (!person) {
    notFound();
  }

  if (slug !== String(person.slug)) {
    permanentRedirect(`/swieci/${encodeURIComponent(String(person.slug))}`);
  }

  const content = readPublicPersonContent(person);
  let commemorations: PersonCommemoration[] = [];
  let commemorationsLoaded = false;
  try {
    commemorations = (await fetchPersonCommemorations(String(person.slug))) as PersonCommemoration[];
    commemorationsLoaded = true;
  } catch {
    // The profile remains usable when calendar data is temporarily unavailable.
  }

  const aliases = (Array.isArray(person.aliases) ? person.aliases : [])
    .map((alias) => String((alias as Record<string, unknown>).value ?? "").trim())
    .filter(Boolean);
  const alternateNames = Array.from(
    new Set([
      person.latin_name ? String(person.latin_name) : "",
      ...aliases,
    ].filter(Boolean)),
  );

  // Schema.org Person JSON-LD for Google SEO
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Person",
    name: content.canonicalName,
    alternateName: alternateNames.length > 0 ? alternateNames : undefined,
    description: content.summary,
    birthDate: person.birth_year ? String(person.birth_year) : undefined,
    deathDate: person.death_year ? String(person.death_year) : undefined,
    image: (person.avatar as SaintAvatarData | null)?.url || undefined,
  };
  const beatification = person.beatification as Record<string, unknown> | null;
  const canonization = person.canonization as Record<string, unknown> | null;
  const beatificationLabel = formatRecognitionDate(
    beatification?.beatification_date as string | null,
    beatification?.beatification_year as number | null,
    DEFAULT_WEB_UI_LOCALE,
  );
  const canonizationLabel = formatRecognitionDate(
    canonization?.canonization_date as string | null,
    canonization?.canonization_year as number | null,
    DEFAULT_WEB_UI_LOCALE,
  );
  const hasSummary = Boolean(content.summary);
  const hasFacts = Boolean(
    person.birth_year ||
      person.death_year ||
      person.gender ||
      (person.state_of_life as Record<string, unknown> | null)?.name_pl,
  );
  const hasRecognition = Boolean(beatificationLabel || canonizationLabel);
  const hasBiography = Boolean(content.biography);
  const hasPatronages = Array.isArray(person.patronages) && person.patronages.length > 0;
  const hasOrders = Array.isArray(person.orders) && person.orders.length > 0;
  const hasPrayer = Boolean(content.prayers);
  const hasIconography = Boolean(content.iconographicAttributes);
  const publicSources = Array.isArray(person.sources) ? person.sources : [];
  const tocItems: PersonTableOfContentsItem[] = [
    ...(hasFacts ? [{ id: "fakty", label: copy.factsTitle }] : []),
    ...(hasSummary ? [{ id: "streszczenie", label: copy.summarySection }] : []),
    ...(hasRecognition ? [{ id: "uznanie", label: copy.recognitionSection }] : []),
    ...(hasBiography ? [{ id: "zyciorys", label: copy.biographySection }] : []),
    ...(hasPatronages ? [{ id: "patronaty", label: copy.patronagesSection }] : []),
    ...(hasOrders ? [{ id: "zakony", label: copy.ordersSection }] : []),
    ...(commemorationsLoaded ? [{ id: "wspomnienia", label: copy.commemorations.title }] : []),
    ...(hasPrayer ? [{ id: "modlitwa", label: copy.prayerSection }] : []),
    ...(hasIconography ? [{ id: "ikonografia", label: copy.iconographySection }] : []),
    ...(publicSources.length ? [{ id: "bibliografia", label: copy.sourcesSection }] : []),
  ];

  return (
    <article className="pb-16 space-y-12">
      {/* Inject JSON-LD */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: serializeJsonLd(jsonLd) }}
      />

      {/* ─── Hero Banner ──────────────────────────────────────────────────── */}
      <section className="bg-gradient-to-br from-burgundy-900 via-burgundy-800 to-burgundy-700 py-16 text-white">
        <div className="mx-auto max-w-5xl space-y-6 px-4 sm:px-6 lg:px-8">
          <Link
            href="/swieci"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-gold-400 hover:text-gold-300 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            {copy.backToDirectory}
          </Link>

          <div className="grid items-center gap-8 sm:grid-cols-[12rem_1fr]">
            <SaintAvatar
              name={content.canonicalName}
              avatar={person.avatar as SaintAvatarData | null}
              className="h-48 w-48 rounded-2xl border-gold-300/40 bg-burgundy-800 text-5xl text-gold-300 shadow-2xl shadow-black/20"
              eager
            />

            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full border border-gold-400/30 bg-gold-500/20 px-3 py-1 text-xs font-semibold text-gold-300 backdrop-blur-md">
                  {resolveDictionaryValue(domain.personTypes, person.person_type)?.label ??
                    String(person.person_type)}
                </span>
                {Boolean(person.era) && (
                  <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-burgundy-200">
                    {copy.eraPrefix}{" "}
                    {resolveDictionaryLabel(domain.eras, person.era) ?? String(person.era)}
                  </span>
                )}
              </div>

              <h1 className="font-serif text-3xl font-bold tracking-tight text-white sm:text-5xl">
                {content.canonicalName}
              </h1>

              {Boolean(person.latin_name) && (
                <p className="font-serif text-lg font-medium italic text-gold-100">
                  {String(person.latin_name)}
                </p>
              )}

              <PersonFacts
                title={copy.factsTitle}
                labels={{
                  birth: copy.birthYear,
                  death: copy.deathYear,
                  gender: copy.gender,
                  state: copy.stateOfLife,
                }}
                birthYear={person.birth_year ? String(person.birth_year) : null}
                deathYear={person.death_year ? String(person.death_year) : null}
                gender={person.gender ? String(person.gender) : null}
                genderLabel={resolveDictionaryLabel(copy.genderLabels, person.gender)}
                stateOfLife={String((person.state_of_life as Record<string, unknown> | null)?.name_pl ?? "") || null}
              />

              {aliases.length > 0 && (
                <details className="group max-w-2xl text-sm leading-6 text-burgundy-100">
                  <summary className="cursor-pointer list-none font-semibold text-gold-200 outline-offset-2 marker:hidden focus-visible:outline focus-visible:outline-2 focus-visible:outline-gold-300">
                    <span>{copy.aliasesPrefix}</span>
                    <span className="ml-2 text-xs font-normal text-burgundy-200 group-open:hidden">{copy.aliasesExpand}</span>
                    <span className="ml-2 hidden text-xs font-normal text-burgundy-200 group-open:inline">{copy.aliasesCollapse}</span>
                  </summary>
                  <p className="mt-2 text-burgundy-100">{aliases.join(", ")}</p>
                </details>
              )}

              <div className="flex flex-wrap items-center gap-3">
                <span id={`wersja-${Number(person.version) || 1}`} className="text-xs text-burgundy-200">
                  {copy.citationVersion} {Number(person.version) || 1}
                </span>
                <PersonCitationButton
                  label={copy.citeProfile}
                  copiedLabel={copy.citationCopied}
                  version={Number(person.version) || 1}
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── Content Body ─────────────────────────────────────────────────── */}
      <section className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 space-y-8">
        <PersonTableOfContents title={copy.tocTitle} items={tocItems} />
        {/* Summary Card */}
        {hasSummary && (
          <div id="streszczenie" className="scroll-mt-24 rounded-2xl border border-gold-500/30 bg-gold-50/50 p-6 sm:p-8 shadow-sm">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-gold-800 mb-2 flex items-center gap-1.5">
              <Sparkles className="h-4 w-4 text-gold-600" />
              {copy.summary}
            </h2>
            <p className="font-serif text-base sm:text-lg text-burgundy-950 leading-relaxed italic">
              {content.summary}
            </p>
          </div>
        )}

        {hasRecognition && (
          <section id="uznanie" className="scroll-mt-24 rounded-2xl border border-gold-500/25 bg-[#fffdf8] p-6 shadow-sm sm:p-8">
            <div className="flex items-start gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-gold-500/30 bg-gold-50 text-gold-700">
                <BadgeCheck className="h-5 w-5" />
              </span>
              <div>
                <h2 className="font-serif text-2xl font-bold text-burgundy-900">
                  {copy.recognitionTitle}
                </h2>
                <p className="mt-1 text-sm leading-6 text-stone-600">
                  {copy.recognitionDescription}
                </p>
              </div>
            </div>

            <dl className="mt-6 grid gap-3 sm:grid-cols-2">
              {beatificationLabel && (
                <div className="rounded-xl border border-[#ded8cd] bg-white px-4 py-4">
                  <dt className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.14em] text-gold-800">
                    <CalendarDays className="h-4 w-4" />
                    {copy.beatification}
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
                    {copy.canonization}
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
        {hasBiography && (
        <div id="zyciorys" className="scroll-mt-24 rounded-2xl border border-gold-500/20 bg-white p-6 sm:p-8 shadow-sm space-y-4">
          <h2 className="font-serif text-2xl font-bold text-burgundy-900 flex items-center gap-2 border-b border-gray-100 pb-3">
            <BookOpen className="h-5 w-5 text-gold-600" />
            {copy.biographyTitle}
          </h2>
          <div className="prose prose-burgundy max-w-none text-base text-gray-800 leading-relaxed whitespace-pre-line">
            {content.biography}
          </div>
        </div>
        )}

        {/* Patronages */}
        {hasPatronages && (
          <section id="patronaty" className="scroll-mt-24 rounded-2xl border border-gold-500/20 bg-white p-6 shadow-sm sm:p-8">
            <h2 className="flex items-center gap-2 font-serif text-2xl font-bold text-burgundy-900">
              <HeartHandshake className="h-5 w-5 text-gold-600" />
              {copy.patronages}
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
        {hasOrders && (
          <section id="zakony" className="scroll-mt-24 rounded-2xl border border-gold-500/20 bg-white p-6 shadow-sm sm:p-8">
            <h2 className="flex items-center gap-2 font-serif text-2xl font-bold text-burgundy-900">
              <Landmark className="h-5 w-5 text-gold-600" />
              {copy.orders}
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
                      {resolveDictionaryLabel(
                        domain.religiousCommunities.membershipTypes,
                        membership.membership_type,
                      ) ?? String(membership.membership_type)}
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

        {commemorationsLoaded && (
          <PersonCommemorations
            entries={commemorations}
            copy={copy.commemorations}
            rankLabels={dictionary.calendar.feastRanks}
          />
        )}

        {/* Prayers / Attributes Grid */}
        {(hasPrayer || hasIconography) && <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {/* Prayers */}
          {hasPrayer && <div id="modlitwa" className="scroll-mt-24 rounded-2xl border border-gold-500/20 bg-white p-6 shadow-sm space-y-3">
            <h3 className="font-serif text-lg font-bold text-burgundy-900 flex items-center gap-2">
              <Heart className="h-4 w-4 text-gold-600" />
              {copy.prayer}
            </h3>
            <p className="whitespace-pre-line text-sm leading-relaxed text-gray-700 italic">
              {content.prayers}
            </p>
          </div>
          }

          {/* Iconography */}
          {hasIconography && <div id="ikonografia" className="scroll-mt-24 rounded-2xl border border-gold-500/20 bg-white p-6 shadow-sm space-y-3">
            <h3 className="font-serif text-lg font-bold text-burgundy-900 flex items-center gap-2">
              <Crown className="h-4 w-4 text-gold-600" />
              {copy.iconographicAttributes}
            </h3>
            <ul className="flex flex-wrap gap-2">
              {String(content.iconographicAttributes)
                .split(/[;\n]+/)
                .map((attribute) => attribute.trim())
                .filter(Boolean)
                .map((attribute) => (
                  <li key={attribute} className="rounded-full border border-gold-500/25 bg-gold-50 px-3 py-1 text-xs text-burgundy-900">
                    {attribute}
                  </li>
                ))}
            </ul>
          </div>
          }
        </div>
        }
        {publicSources.length > 0 && (
          <PersonSources sources={publicSources as PublicPersonSource[]} copy={copy.sources} />
        )}
        <PersonFeedback
          title={copy.feedbackTitle}
          description={copy.feedbackDescription}
          helpfulLabel={copy.feedbackHelpful}
          notHelpfulLabel={copy.feedbackNotHelpful}
          thanksLabel={copy.feedbackThanks}
        />
      </section>
    </article>
  );
}
