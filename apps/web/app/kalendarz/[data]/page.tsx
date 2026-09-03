import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowRight, BookOpen, CalendarDays, ChevronLeft, ChevronRight, Layers3 } from "lucide-react";

import { SaintAvatar } from "@/components/saint-avatar";
import { fetchCalendarDay } from "@/lib/api";
import {
  calendarEntryAvatar,
  calendarEntryHref,
  calendarEntrySummary,
  calendarEntryTitle,
  type CalendarEntry,
  type CalendarDay,
  currentWarsawDate,
  FEAST_RANK_LABELS,
  formatCalendarEntryCount,
  formatCalendarDate,
  isValidCalendarDate,
  OBSERVANCE_TYPE_LABELS,
  shiftDate,
} from "@/lib/calendar";
import { PERSON_TYPE_LABELS } from "@/lib/utils";


export const revalidate = 300;


interface PageProps {
  params: Promise<{ data: string }>;
  searchParams: Promise<{ calendar?: string }>;
}


function entryTypeLabel(entry: CalendarEntry): string {
  if (entry.person) {
    return PERSON_TYPE_LABELS[entry.person.person_type] ?? entry.person.person_type;
  }
  const type = entry.observance?.observance_type ?? "other";
  return OBSERVANCE_TYPE_LABELS[type] ?? type;
}


export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { data } = await params;
  if (!isValidCalendarDate(data)) return { title: "Nieprawidłowa data" };
  const label = formatCalendarDate(data);
  return {
    title: `Kalendarz na ${label} | Encyklopedia Świętych`,
    description: `Osoby i obchody przypisane do ${label} w kalendarzu powszechnym i polskim.`,
  };
}


export default async function CalendarDayPage({ params, searchParams }: PageProps) {
  const { data } = await params;
  if (!isValidCalendarDate(data)) notFound();
  const query = await searchParams;
  const calendarCode = query.calendar || "roman_pl";

  const day: CalendarDay = await fetchCalendarDay(data, calendarCode);

  const formattedDate = formatCalendarDate(data);
  const isToday = data === currentWarsawDate();
  const monthKey = data.slice(0, 7);
  const primary = day.primary;
  const remaining = primary ? day.entries.filter((entry) => entry.id !== primary.id) : [];

  return (
    <main>
      <section className="border-b border-[#ded8cd] bg-[#fffdf8]">
        <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
          <Link href={`/kalendarz?month=${monthKey}&calendar=${calendarCode}`} className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.12em] text-burgundy-700 hover:underline">
            <ChevronLeft className="h-4 w-4" /> Wróć do miesiąca
          </Link>
          <div className="mt-8 flex flex-col justify-between gap-6 md:flex-row md:items-end">
            <div>
              <p className="editorial-label">Kalendarz liturgiczny</p>
              <h1 className="mt-3 font-serif text-4xl font-semibold tracking-tight text-charcoal sm:text-5xl">
                {isToday ? "Wspomnienia na dziś" : "Wspomnienia tego dnia"}
              </h1>
              <p className="mt-3 font-serif text-2xl capitalize text-burgundy-700">{formattedDate}</p>
            </div>
            <div className="flex items-center gap-2">
              <Link href={`/kalendarz/${shiftDate(data, -1)}?calendar=${calendarCode}`} aria-label="Poprzedni dzień" className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-[#ded8cd] bg-white text-burgundy-700 hover:bg-gold-50"><ChevronLeft className="h-5 w-5" /></Link>
              <Link href={`/kalendarz/${shiftDate(data, 1)}?calendar=${calendarCode}`} aria-label="Następny dzień" className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-[#ded8cd] bg-white text-burgundy-700 hover:bg-gold-50"><ChevronRight className="h-5 w-5" /></Link>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        {primary ? (
          <>
            <article className="surface-card overflow-hidden">
              <div className="grid lg:grid-cols-[18rem_1fr]">
                <div className="flex min-h-72 items-center justify-center bg-burgundy-800 p-8">
                  <SaintAvatar name={calendarEntryTitle(primary)} avatar={calendarEntryAvatar(primary)} className="h-44 w-44 border-4 border-white/20 text-4xl" />
                </div>
                <div className="p-7 sm:p-10">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-gold-100 px-3 py-1 text-xs font-bold text-gold-800">Główne wspomnienie</span>
                    <span className="rounded-full border border-[#ded8cd] px-3 py-1 text-xs font-semibold text-stone-600">{FEAST_RANK_LABELS[primary.rank] ?? primary.rank}</span>
                    <span className="rounded-full border border-[#ded8cd] px-3 py-1 text-xs font-semibold text-stone-600">{entryTypeLabel(primary)}</span>
                  </div>
                  <h2 className="mt-5 font-serif text-4xl font-semibold text-charcoal">{calendarEntryTitle(primary)}</h2>
                  <p className="mt-4 max-w-3xl text-sm leading-7 text-stone-600">{calendarEntrySummary(primary) || "Opis tego wpisu jest obecnie opracowywany przez redakcję."}</p>
                  {primary.person && primary.person.patronages.length > 0 && (
                    <div className="mt-5 flex flex-wrap gap-2">
                      {primary.person.patronages.slice(0, 4).map((patronage) => <span key={patronage.id} className="rounded-full border border-gold-200 bg-gold-50 px-3 py-1 text-xs text-gold-800">{patronage.name_pl}</span>)}
                    </div>
                  )}
                  <div className="mt-7 flex flex-wrap items-center gap-4">
                    <Link href={calendarEntryHref(primary)} className="inline-flex h-11 items-center gap-2 rounded-lg bg-burgundy-700 px-5 text-sm font-semibold text-white hover:bg-burgundy-600">{primary.person ? "Pełny profil" : "Poznaj obchód"} <ArrowRight className="h-4 w-4" /></Link>
                    <span className="text-xs text-stone-500">{primary.calendar.name}</span>
                  </div>
                </div>
              </div>
            </article>

            <div className="mt-12 grid gap-10 lg:grid-cols-[1fr_18rem]">
              <div>
                <div className="flex items-center justify-between gap-4">
                  <div><p className="editorial-label">Pełna lista dnia</p><h2 className="mt-2 font-serif text-3xl font-semibold">Pozostali wspominani</h2></div>
                  <span className="text-sm text-stone-500">{formatCalendarEntryCount(remaining.length)}</span>
                </div>
                {remaining.length > 0 ? (
                  <div className="mt-6 divide-y divide-[#ded8cd] border-y border-[#ded8cd]">
                    {remaining.map((entry) => (
                      <article key={entry.id} className="flex flex-col gap-5 py-6 sm:flex-row sm:items-center">
                        <SaintAvatar name={calendarEntryTitle(entry)} avatar={calendarEntryAvatar(entry)} className="h-16 w-16 shrink-0 text-lg" />
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2 text-[10px] font-bold uppercase tracking-wide text-gold-800"><span>{FEAST_RANK_LABELS[entry.rank] ?? entry.rank}</span><span>·</span><span>{entry.calendar.name}</span></div>
                          <h3 className="mt-1 font-serif text-2xl font-semibold text-charcoal">{calendarEntryTitle(entry)}</h3>
                          <p className="mt-2 line-clamp-2 text-sm leading-6 text-stone-600">{calendarEntrySummary(entry) || "Opis w opracowaniu."}</p>
                        </div>
                        <Link href={calendarEntryHref(entry)} className="inline-flex items-center gap-1 text-sm font-semibold text-burgundy-700">{entry.person ? "Profil" : "Obchód"} <ChevronRight className="h-4 w-4" /></Link>
                      </article>
                    ))}
                  </div>
                ) : (
                  <div className="mt-6 rounded-xl border border-[#ded8cd] bg-[#fffdf8] p-6 text-sm text-stone-600">To obecnie jedyny opracowany wpis przypisany do tej daty.</div>
                )}
              </div>

              <aside className="space-y-4">
                <div className="surface-card p-5">
                  <Layers3 className="h-5 w-5 text-gold-700" />
                  <h3 className="mt-4 font-serif text-lg font-semibold">Zakres kalendarza</h3>
                  <p className="mt-2 text-xs leading-5 text-stone-600">
                    {day.calendar_name}
                    {day.includes_universal ? " wraz z obchodami kalendarza powszechnego" : ""}
                    {day.includes_martyrology ? " oraz osobną warstwą Martyrologium Rzymskiego" : ""}.
                  </p>
                </div>
                {primary.source_url && (
                  <div className="surface-card p-5">
                    <BookOpen className="h-5 w-5 text-gold-700" />
                    <h3 className="mt-4 font-serif text-lg font-semibold">Źródło wpisu</h3>
                    <a href={primary.source_url} target="_blank" rel="noreferrer" className="mt-2 block text-xs font-semibold leading-5 text-burgundy-700 hover:underline">{primary.source_title || "Dokument liturgiczny"}</a>
                  </div>
                )}
              </aside>
            </div>
          </>
        ) : (
          <div className="surface-card mx-auto max-w-2xl p-10 text-center">
            <CalendarDays className="mx-auto h-10 w-10 text-gold-700" strokeWidth={1.4} />
            <h2 className="mt-5 font-serif text-3xl font-semibold text-charcoal">Dzień czeka na opracowanie</h2>
            <p className="mt-3 text-sm leading-6 text-stone-600">W bazie nie ma jeszcze zweryfikowanych wpisów przypisanych do tej daty. Sam dzień pozostaje częścią pełnego kalendarza 366 dni.</p>
            <Link href={`/kalendarz?month=${monthKey}&calendar=${calendarCode}`} className="mt-7 inline-flex h-11 items-center rounded-lg bg-burgundy-700 px-5 text-sm font-semibold text-white">Zobacz cały miesiąc</Link>
          </div>
        )}
      </section>
    </main>
  );
}
