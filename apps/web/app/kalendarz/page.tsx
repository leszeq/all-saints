import type { Metadata } from "next";
import Link from "next/link";
import { BookOpen, CalendarDays, ChevronLeft, ChevronRight, Layers3 } from "lucide-react";

import { fetchCalendarMonth, fetchLiturgicalCalendars } from "@/lib/api";
import {
  type CalendarDay,
  type CalendarMonth,
  currentWarsawDate,
  currentWarsawMonth,
  FEAST_RANK_SHORT_LABELS,
  type LiturgicalCalendarInfo,
  parseMonthKey,
  shiftMonth,
} from "@/lib/calendar";


export const metadata: Metadata = {
  title: "Kalendarz liturgiczny | Encyklopedia Świętych",
  description:
    "Święci i błogosławieni przypisani do kolejnych dni roku w kalendarzu powszechnym i polskim.",
};

export const revalidate = 300;

const WEEKDAYS = ["Pon", "Wt", "Śr", "Czw", "Pt", "Sob", "Nd"];


interface PageProps {
  searchParams: Promise<{ month?: string; calendar?: string }>;
}


function emptyMonth(year: number, month: number): CalendarMonth {
  const numberOfDays = new Date(Date.UTC(year, month, 0)).getUTCDate();
  const days = Array.from({ length: numberOfDays }, (_, index): CalendarDay => {
    const date = `${year}-${String(month).padStart(2, "0")}-${String(index + 1).padStart(2, "0")}`;
    return {
      date,
      calendar_code: "roman_pl",
      calendar_name: "Kalendarz Polski",
      includes_universal: true,
      includes_martyrology: true,
      primary: null,
      entries: [],
      total: 0,
    };
  });
  return {
    year,
    month,
    calendar_code: "roman_pl",
    calendar_name: "Kalendarz Polski",
    includes_universal: true,
    includes_martyrology: true,
    days,
  };
}


export default async function LiturgicalCalendarPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const selected = parseMonthKey(params.month) ?? parseMonthKey(currentWarsawMonth())!;
  let calendars: LiturgicalCalendarInfo[] = [];
  try {
    calendars = await fetchLiturgicalCalendars();
  } catch {
    calendars = [];
  }
  const requestedCalendar = params.calendar || "roman_pl";
  const calendarCode =
    calendars.length === 0 || calendars.some((calendar) => calendar.code === requestedCalendar)
      ? requestedCalendar
      : "roman_pl";

  let monthData = emptyMonth(selected.year, selected.month);
  try {
    monthData = await fetchCalendarMonth(selected.year, selected.month, calendarCode);
  } catch {
    monthData = emptyMonth(selected.year, selected.month);
  }

  const monthLabel = new Intl.DateTimeFormat("pl-PL", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(selected.year, selected.month - 1, 1)));
  const firstWeekday = new Date(Date.UTC(selected.year, selected.month - 1, 1)).getUTCDay();
  const leadingEmptyDays = (firstWeekday + 6) % 7;
  const today = currentWarsawDate();
  const populatedDays = monthData.days.filter((day) => day.total > 0).length;
  const commemorations = monthData.days.reduce((total, day) => total + day.total, 0);
  const previousMonth = shiftMonth(selected.year, selected.month, -1);
  const nextMonth = shiftMonth(selected.year, selected.month, 1);

  return (
    <main>
      <section className="border-b border-[#ded8cd] bg-[#fffdf8]">
        <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
          <p className="editorial-label">Ryt rzymski · {monthData.calendar_name}</p>
          <div className="mt-4 flex flex-col justify-between gap-6 md:flex-row md:items-end">
            <div className="max-w-3xl">
              <h1 className="font-serif text-4xl font-semibold tracking-tight text-charcoal sm:text-5xl">
                Kalendarz liturgiczny
              </h1>
              <p className="mt-4 max-w-2xl text-sm leading-6 text-stone-600">
                {monthData.includes_universal
                  ? "Wpisy wybranego kalendarza uzupełniamy obchodami Ogólnego Kalendarza Rzymskiego."
                  : "Wpisy pochodzą z wybranego kalendarza bez nakładania kalendarzy lokalnych."}
                {monthData.includes_martyrology
                  ? " Osobno dołączamy postacie z Martyrologium Rzymskiego."
                  : ""} Każdy dzień może prowadzić do wielu postaci.
              </p>
            </div>
            <div className="flex gap-6 text-sm">
              <div><strong className="block font-serif text-3xl text-burgundy-700">{populatedDays}</strong><span className="text-stone-500">dni z wpisami</span></div>
              <div><strong className="block font-serif text-3xl text-burgundy-700">{commemorations}</strong><span className="text-stone-500">wspomnień</span></div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <form method="GET" className="mb-6 flex flex-col gap-3 rounded-xl border border-[#ded8cd] bg-white p-4 sm:flex-row sm:items-end sm:justify-end">
          <input type="hidden" name="month" value={`${selected.year}-${String(selected.month).padStart(2, "0")}`} />
          <label className="w-full sm:w-80">
            <span className="mb-1.5 block text-[10px] font-bold uppercase tracking-[0.12em] text-stone-500">Kalendarz bazowy</span>
            <select name="calendar" defaultValue={calendarCode} className="h-11 w-full rounded-lg border border-[#ded8cd] bg-[#fffdf8] px-3 text-sm text-charcoal outline-none focus:border-gold-500">
              {calendars.length ? calendars.map((calendar) => <option key={calendar.code} value={calendar.code}>{calendar.name}</option>) : <><option value="roman_pl">Kalendarz Polski</option><option value="roman_universal">Ogólny Kalendarz Rzymski</option></>}
            </select>
          </label>
          <button type="submit" className="h-11 rounded-lg bg-burgundy-700 px-5 text-sm font-semibold text-white hover:bg-burgundy-600">Zastosuj</button>
        </form>

        <div className="flex items-center justify-between gap-4 border-b border-[#ded8cd] pb-6">
          <Link
            href={`/kalendarz?month=${previousMonth}&calendar=${calendarCode}`}
            aria-label="Poprzedni miesiąc"
            className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-[#ded8cd] bg-white text-burgundy-700 hover:bg-gold-50"
          >
            <ChevronLeft className="h-5 w-5" />
          </Link>
          <div className="text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-gold-800">{monthData.calendar_name}</p>
            <h2 className="mt-1 font-serif text-3xl font-semibold capitalize text-charcoal">{monthLabel}</h2>
          </div>
          <Link
            href={`/kalendarz?month=${nextMonth}&calendar=${calendarCode}`}
            aria-label="Następny miesiąc"
            className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-[#ded8cd] bg-white text-burgundy-700 hover:bg-gold-50"
          >
            <ChevronRight className="h-5 w-5" />
          </Link>
        </div>

        <div className="mt-6 overflow-x-auto pb-2">
          <div className="min-w-[760px]">
            <div className="grid grid-cols-7 border-x border-t border-[#ded8cd] bg-[#f8f4eb]">
              {WEEKDAYS.map((weekday) => (
                <div key={weekday} className="border-r border-[#ded8cd] px-3 py-3 text-center text-[11px] font-bold uppercase tracking-[0.12em] text-stone-500 last:border-r-0">
                  {weekday}
                </div>
              ))}
            </div>
            <div className="grid grid-cols-7 border-l border-t border-[#ded8cd] bg-[#ded8cd]">
              {Array.from({ length: leadingEmptyDays }, (_, index) => (
                <div key={`empty-${index}`} className="min-h-36 border-b border-r border-[#ded8cd] bg-stone-50/70" aria-hidden="true" />
              ))}
              {monthData.days.map((day) => {
                const primary = day.primary;
                const isToday = day.date === today;
                return (
                  <Link
                    key={day.date}
                    href={`/kalendarz/${day.date}?calendar=${calendarCode}`}
                    className={`group min-h-36 border-b border-r border-[#ded8cd] p-3 transition-colors ${
                      isToday ? "bg-gold-50 ring-2 ring-inset ring-gold-500" : "bg-white hover:bg-[#fffdf8]"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold ${isToday ? "bg-burgundy-700 text-white" : "text-stone-600"}`}>
                        {Number(day.date.slice(-2))}
                      </span>
                      {day.total > 1 && <span className="rounded-full bg-burgundy-50 px-2 py-1 text-[10px] font-bold text-burgundy-700">+{day.total - 1}</span>}
                    </div>
                    {primary ? (
                      <div className="mt-4">
                        <p className="line-clamp-2 font-serif text-base font-semibold leading-5 text-charcoal group-hover:text-burgundy-700">
                          {primary.person.canonical_name}
                        </p>
                        <p className="mt-2 text-[10px] font-semibold uppercase tracking-wide text-gold-800">
                          {FEAST_RANK_SHORT_LABELS[primary.rank] ?? primary.rank}
                        </p>
                      </div>
                    ) : (
                      <p className="mt-5 text-xs leading-5 text-stone-400">Brak opracowanych wpisów</p>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        </div>

        <div className="mt-10 grid gap-5 lg:grid-cols-3">
          <article className="surface-card p-6">
            <CalendarDays className="h-6 w-6 text-gold-700" strokeWidth={1.5} />
            <h3 className="mt-6 font-serif text-xl font-semibold">Pełne 366 dni</h3>
            <p className="mt-2 text-sm leading-6 text-stone-600">Widok obejmuje każdy dzień roku, w tym 29 lutego. Puste daty pozostają gotowe do dalszej pracy redakcyjnej.</p>
          </article>
          <article className="surface-card p-6">
            <Layers3 className="h-6 w-6 text-gold-700" strokeWidth={1.5} />
            <h3 className="mt-6 font-serif text-xl font-semibold">Kalendarze nakładają się</h3>
            <p className="mt-2 text-sm leading-6 text-stone-600">Najpierw stosujemy kalendarz polski, a następnie uzupełniamy go wspomnieniami powszechnymi bez dublowania osób.</p>
          </article>
          <article className="surface-card p-6">
            <BookOpen className="h-6 w-6 text-gold-700" strokeWidth={1.5} />
            <h3 className="mt-6 font-serif text-xl font-semibold">Źródło przy wpisie</h3>
            <p className="mt-2 text-sm leading-6 text-stone-600">Ranga i data są przechowywane razem z odnośnikiem do dokumentu liturgicznego użytego przez redakcję.</p>
          </article>
        </div>
      </section>
    </main>
  );
}
