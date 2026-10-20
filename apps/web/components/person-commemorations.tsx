import Link from "next/link";
import { CalendarDays, ExternalLink } from "lucide-react";

import { currentWarsawDate, type PersonCommemoration } from "@/lib/calendar";
import { resolveDictionaryLabel } from "@/lib/i18n/labels";
import type { WebDictionary } from "@/lib/i18n/types";

export function PersonCommemorations({
  entries,
  copy,
  rankLabels,
}: {
  entries: PersonCommemoration[];
  copy: WebDictionary["personProfile"]["commemorations"];
  rankLabels: WebDictionary["calendar"]["feastRanks"];
}) {
  return (
    <section
      id="wspomnienia"
      aria-labelledby="person-commemorations-heading"
      className="scroll-mt-24 rounded-2xl border border-gold-500/20 bg-white p-6 shadow-sm sm:p-8"
    >
      <div className="flex items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-gold-500/30 bg-gold-50 text-gold-700">
          <CalendarDays aria-hidden="true" className="h-5 w-5" />
        </span>
        <div>
          <h2 id="person-commemorations-heading" className="font-serif text-2xl font-bold text-burgundy-900">
            {copy.title}
          </h2>
          <p className="mt-1 text-sm leading-6 text-stone-600">{copy.description}</p>
        </div>
      </div>

      {entries.length > 0 ? (
        <ol className="mt-6 divide-y divide-stone-100 border-y border-stone-100">
          {entries.map((entry) => {
            const date = new Intl.DateTimeFormat("pl-PL", {
              day: "numeric",
              month: "long",
              timeZone: "UTC",
            }).format(new Date(Date.UTC(2000, entry.month - 1, entry.day)));
            const calendarYear = currentWarsawDate().slice(0, 4);
            const dayHref = `/kalendarz/${calendarYear}-${String(entry.month).padStart(2, "0")}-${String(entry.day).padStart(2, "0")}?calendar=${encodeURIComponent(entry.calendar.code)}`;
            return (
              <li key={entry.id} className="flex flex-col gap-3 py-5 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-wide text-gold-800">
                    <span>{date}</span>
                    <span aria-hidden="true">·</span>
                    <span>{entry.calendar.name}</span>
                    {entry.calendar.coverage?.fixed_only && (
                      <span className="rounded-full bg-gold-50 px-2 py-0.5 text-[10px] normal-case tracking-normal text-gold-800">
                        {copy.fixedOnly}
                      </span>
                    )}
                  </div>
                  <p className="mt-1 font-serif text-lg font-semibold text-burgundy-950">
                    {resolveDictionaryLabel(rankLabels, entry.rank) ?? entry.rank}
                  </p>
                  {entry.source_title && (
                    <p className="mt-1 text-xs leading-5 text-stone-600">
                      {copy.sourcePrefix} {entry.source_title}
                    </p>
                  )}
                  {entry.calendar.coverage?.coverage_note && (
                    <p className="mt-1 text-xs leading-5 text-stone-500">{entry.calendar.coverage.coverage_note}</p>
                  )}
                </div>
                <Link
                  href={dayHref}
                  className="inline-flex min-h-9 shrink-0 items-center gap-1.5 self-start rounded-md px-2 py-1 text-sm font-semibold text-burgundy-700 underline decoration-gold-500/60 underline-offset-4 outline-offset-2 hover:text-burgundy-950 focus-visible:outline focus-visible:outline-2 focus-visible:outline-gold-600 sm:self-auto"
                >
                  {copy.viewDay}
                  <ExternalLink aria-hidden="true" className="h-3.5 w-3.5" />
                </Link>
              </li>
            );
          })}
        </ol>
      ) : (
        <p className="mt-6 rounded-xl border border-dashed border-[#ded8cd] bg-[#fffdf8] p-5 text-sm leading-6 text-stone-600">
          {copy.empty}
        </p>
      )}
    </section>
  );
}
