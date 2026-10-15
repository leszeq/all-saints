import type { Metadata } from "next";
import Link from "next/link";
import { notFound, permanentRedirect } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  CalendarClock,
  ExternalLink,
  HeartHandshake,
  Quote,
  Users,
} from "lucide-react";

import { SaintAvatar } from "@/components/saint-avatar";
import { fetchOrderDetail, fetchOrders, isApiNotFound } from "@/lib/api";
import {
  orderMonogram,
  type ReligiousOrder,
  type ReligiousOrderDetail,
} from "@/lib/orders";
import { DEFAULT_WEB_UI_LOCALE } from "@/lib/i18n/config";
import { getWebDictionary } from "@/lib/i18n/dictionaries";
import { resolveDictionaryLabel, resolveDictionaryValue } from "@/lib/i18n/labels";
import { serializeJsonLd } from "@/lib/json-ld";

export const revalidate = 300;

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const [{ slug }, dictionary] = await Promise.all([
    params,
    getWebDictionary(DEFAULT_WEB_UI_LOCALE),
  ]);
  const copy = dictionary.orderProfile;
  try {
    const order = (await fetchOrderDetail(slug)) as ReligiousOrderDetail;
    return {
      title: `${order.name}${copy.metadataTitleSuffix}`,
      alternates: { canonical: `/zakony/${encodeURIComponent(order.slug)}` },
      description:
        order.description ||
        order.mission ||
        `${copy.metadataDescriptionPrefix}${order.name}.`,
      openGraph: {
        title: order.name,
        url: `/zakony/${encodeURIComponent(order.slug)}`,
        description:
          order.description ||
          order.mission ||
          `${copy.metadataDescriptionPrefix}${order.name}.`,
      },
    };
  } catch (error) {
    if (isApiNotFound(error)) return { title: copy.notFoundTitle };
    throw error;
  }
}

export default async function OrderDetailPage({ params }: PageProps) {
  const [{ slug }, dictionary] = await Promise.all([
    params,
    getWebDictionary(DEFAULT_WEB_UI_LOCALE),
  ]);
  const domain = dictionary.domain;
  const labels = domain.religiousCommunities;
  const copy = dictionary.orderProfile;
  let order: ReligiousOrderDetail;
  try {
    order = (await fetchOrderDetail(slug)) as ReligiousOrderDetail;
  } catch (error) {
    if (isApiNotFound(error)) notFound();
    throw error;
  }

  if (slug !== order.slug) {
    permanentRedirect(`/zakony/${encodeURIComponent(order.slug)}`);
  }

  let related: ReligiousOrder[] = [];
  if (order.spiritual_family) {
    try {
      related = ((await fetchOrders({ spiritual_family: order.spiritual_family })) as ReligiousOrder[])
        .filter((item) => item.id !== order.id)
        .slice(0, 3);
    } catch {
      related = [];
    }
  }

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: order.name,
    alternateName: order.name_la || order.abbreviation,
    foundingDate: order.founded_year ? String(order.founded_year) : undefined,
    description: order.description,
    url: order.website_url,
  };

  return (
    <main>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: serializeJsonLd(jsonLd) }} />
      <section className="border-b border-[#ded8cd] bg-burgundy-900 text-white">
        <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
          <Link href="/zakony" className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.12em] text-gold-300 hover:text-gold-200">
            <ArrowLeft className="h-4 w-4" /> {copy.backToDirectory}
          </Link>
          <div className="mt-10 grid items-center gap-8 md:grid-cols-[9rem_1fr]">
            <div className="flex h-36 w-36 items-center justify-center rounded-2xl border border-gold-300/30 bg-white/5 px-4 text-center font-serif text-2xl font-semibold text-gold-200 shadow-2xl">
              {orderMonogram(order)}
            </div>
            <div>
              <div className="flex flex-wrap gap-2">
                <span className="rounded-full bg-gold-300 px-3 py-1 text-[10px] font-bold uppercase tracking-wide text-burgundy-950">
                  {resolveDictionaryLabel(labels.communityTypes, order.community_type) ??
                    order.community_type}
                </span>
                {order.charism && <span className="rounded-full border border-white/15 px-3 py-1 text-[10px] font-bold uppercase tracking-wide text-burgundy-100">{resolveDictionaryLabel(labels.charisms, order.charism) ?? order.charism}</span>}
                {order.spiritual_family && <span className="rounded-full border border-white/15 px-3 py-1 text-[10px] font-bold uppercase tracking-wide text-burgundy-100">{copy.familyPrefix} {labels.spiritualFamilies[order.spiritual_family] ?? order.spiritual_family}</span>}
              </div>
              <h1 className="mt-5 max-w-4xl font-serif text-4xl font-semibold leading-tight sm:text-6xl">{order.name}</h1>
              {order.name_la && <p className="mt-3 font-serif text-lg italic text-gold-100">{order.name_la}</p>}
              <p className="mt-5 max-w-3xl text-sm leading-7 text-burgundy-100">{order.description || copy.descriptionFallback}</p>
            </div>
          </div>
          <dl className="mt-10 grid overflow-hidden rounded-xl border border-white/10 bg-white/10 sm:grid-cols-3">
            <div className="bg-burgundy-900/80 p-5"><dt className="text-[10px] uppercase tracking-wide text-gold-300">{copy.origins}</dt><dd className="mt-1 font-serif text-xl">{order.founded_year || copy.originsFallback}</dd></div>
            <div className="border-t border-white/10 bg-burgundy-900/80 p-5 sm:border-l sm:border-t-0"><dt className="text-[10px] uppercase tracking-wide text-gold-300">{copy.founder}</dt><dd className="mt-1 font-serif text-xl">{order.founder_name || copy.founderFallback}</dd></div>
            <div className="border-t border-white/10 bg-burgundy-900/80 p-5 sm:border-l sm:border-t-0"><dt className="text-[10px] uppercase tracking-wide text-gold-300">{copy.linkedPeople}</dt><dd className="mt-1 font-serif text-xl">{order.member_count}</dd></div>
          </dl>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-12 px-4 py-16 sm:px-6 lg:grid-cols-[minmax(0,1fr)_20rem] lg:px-8">
        <article>
          <p className="editorial-label">{copy.legacyKicker}</p>
          <h2 className="mt-3 font-serif text-4xl font-semibold text-charcoal">{copy.history}</h2>
          <div className="mt-7 whitespace-pre-line font-serif text-lg leading-8 text-stone-700 first-letter:float-left first-letter:mr-2 first-letter:font-serif first-letter:text-6xl first-letter:leading-[0.85] first-letter:text-gold-700">
            {order.history || copy.historyFallback}
          </div>

          <div className="mt-12 rounded-2xl border border-gold-300 bg-gold-50 p-7 sm:p-9">
            <HeartHandshake className="h-7 w-7 text-gold-700" strokeWidth={1.5} />
            <p className="mt-6 text-xs font-bold uppercase tracking-[0.14em] text-gold-800">{copy.mission}</p>
            <p className="mt-3 font-serif text-2xl leading-9 text-burgundy-900">
              {order.mission || copy.missionFallback}
            </p>
          </div>
        </article>

        <aside className="space-y-4">
          {order.motto && (
            <div className="surface-card p-6">
              <Quote className="h-5 w-5 text-gold-700" />
              <p className="mt-5 font-serif text-xl italic text-charcoal">„{order.motto}”</p>
              <p className="mt-2 text-[10px] font-bold uppercase tracking-wide text-stone-500">{copy.motto}</p>
            </div>
          )}
          <div className="surface-card p-6">
            <CalendarClock className="h-5 w-5 text-gold-700" />
            <dl className="mt-5 space-y-4 text-sm">
              <div><dt className="text-xs text-stone-500">{copy.foundedYear}</dt><dd className="mt-1 font-semibold">{order.founded_year || "—"}</dd></div>
              <div><dt className="text-xs text-stone-500">{copy.papalApproval}</dt><dd className="mt-1 font-semibold">{order.papal_approval_year || "—"}</dd></div>
              <div><dt className="text-xs text-stone-500">{copy.abbreviation}</dt><dd className="mt-1 font-semibold">{order.abbreviation || "—"}</dd></div>
            </dl>
          </div>
          {(order.source_url || order.website_url) && (
            <div className="surface-card p-6">
              <BookOpen className="h-5 w-5 text-gold-700" />
              <h3 className="mt-5 font-serif text-lg font-semibold">{copy.sources}</h3>
              <div className="mt-3 grid gap-2 text-xs font-semibold text-burgundy-700">
                {order.source_url && <a href={order.source_url} target="_blank" rel="noreferrer" className="inline-flex items-start gap-1 hover:underline">{order.source_title || copy.historySource}<ExternalLink className="mt-0.5 h-3 w-3 shrink-0" /></a>}
                {order.website_url && <a href={order.website_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:underline">{copy.officialWebsite} <ExternalLink className="h-3 w-3" /></a>}
              </div>
            </div>
          )}
        </aside>
      </section>

      <section className="border-y border-[#ded8cd] bg-[#fffdf8] py-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex items-end justify-between gap-5">
            <div><p className="editorial-label">{copy.membersKicker}</p><h2 className="mt-3 font-serif text-4xl font-semibold">{copy.membersTitle}</h2></div>
            <Users className="h-7 w-7 text-gold-700" strokeWidth={1.4} />
          </div>
          {order.members.length > 0 ? (
            <div className="mt-8 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
              {order.members.map((membership) => (
                <Link key={membership.person.id} href={`/swieci/${membership.person.slug}`} className="group surface-card flex min-h-64 flex-col p-6 transition-transform hover:-translate-y-1">
                  <div className="flex items-start justify-between gap-4">
                    <SaintAvatar name={membership.person.canonical_name} avatar={membership.person.avatar ?? null} className="h-16 w-16 text-lg" />
                    <span className="rounded-full bg-gold-50 px-3 py-1 text-[10px] font-bold uppercase tracking-wide text-gold-800">{resolveDictionaryLabel(labels.membershipTypes, membership.membership_type) ?? membership.membership_type}</span>
                  </div>
                  <div className="mt-auto pt-10">
                    <p className="text-[10px] font-bold uppercase tracking-wide text-stone-500">{resolveDictionaryValue(domain.personTypes, membership.person.person_type)?.label ?? membership.person.person_type} · {membership.person.birth_year || "?"}–{membership.person.death_year || "?"}</p>
                    <h3 className="mt-2 font-serif text-2xl font-semibold text-charcoal group-hover:text-burgundy-700">{membership.person.canonical_name}</h3>
                    <p className="mt-3 line-clamp-2 text-sm leading-6 text-stone-600">{membership.notes || membership.person.summary_pl || copy.memberProfileFallback}</p>
                    <span className="mt-5 inline-flex items-center gap-1 text-sm font-semibold text-burgundy-700">{copy.fullProfile} <ArrowRight className="h-4 w-4" /></span>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="mt-8 rounded-2xl border border-dashed border-[#ded8cd] bg-white p-10 text-center text-sm text-stone-500">{copy.membersEmpty}</div>
          )}
        </div>
      </section>

      {related.length > 0 && (
        <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
          <p className="editorial-label">{copy.relatedKicker}</p>
          <h2 className="mt-3 font-serif text-3xl font-semibold">{copy.relatedTitle}</h2>
          <div className="mt-7 grid gap-4 md:grid-cols-3">
            {related.map((item) => (
              <Link key={item.id} href={`/zakony/${item.slug}`} className="group rounded-xl border border-[#ded8cd] bg-white p-5 hover:border-gold-400">
                <p className="text-xs font-bold text-gold-800">{item.abbreviation || resolveDictionaryLabel(labels.communityTypes, item.community_type)}</p>
                <h3 className="mt-2 font-serif text-xl font-semibold group-hover:text-burgundy-700">{item.name}</h3>
                <span className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-burgundy-700">{copy.viewProfile} <ArrowRight className="h-3.5 w-3.5" /></span>
              </Link>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
