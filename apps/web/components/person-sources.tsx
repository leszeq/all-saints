import { BookOpen, ExternalLink } from "lucide-react";
import type { WebDictionary } from "@/lib/i18n/types";
import { sourceDoiUrl, sourceHttpUrl, type PublicPersonSource } from "@/lib/person-sources";

export function PersonSources({ sources, copy }: {
  sources: PublicPersonSource[];
  copy: WebDictionary["personProfile"]["sources"];
}) {
  return (
    <section id="bibliografia" aria-labelledby="person-sources-heading" className="scroll-mt-24 rounded-2xl border border-gold-500/20 bg-white p-6 shadow-sm sm:p-8">
      <h2 id="person-sources-heading" className="flex items-center gap-2 font-serif text-2xl font-bold text-burgundy-900">
        <BookOpen aria-hidden="true" className="h-5 w-5 text-gold-600" />
        {copy.title}
      </h2>
      <p className="mt-2 text-sm leading-6 text-stone-600">{sources.length ? copy.description : copy.empty}</p>
      {sources.length > 0 && (
        <ol className="mt-6 list-decimal space-y-5 pl-6 marker:font-serif marker:text-gold-800">
          {sources.map((source) => {
            const book = source.bibliography;
            const archive = source.historical_source;
            const url = sourceHttpUrl(book?.url ?? archive?.digitization_url);
            const doiUrl = sourceDoiUrl(book?.doi);
            const publication = book ? Array.from(new Set([book.authors, book.publisher, book.place_of_publication, book.year].filter((value) => value !== null && value !== undefined && value !== ""))).join(" · ") : null;
            return (
              <li id={`zrodlo-${source.id}`} key={source.id} className="break-words border-b border-stone-100 pb-5 pl-2 last:border-b-0 last:pb-0">
                <h3 className="font-serif text-lg font-semibold leading-7 text-burgundy-950">{book?.title ?? archive?.title}</h3>
                {(book?.subtitle || archive?.original_title) && <p className="text-sm italic text-stone-600">{book?.subtitle ?? archive?.original_title}</p>}
                {source.is_primary && <span className="mt-2 inline-block rounded-full bg-gold-50 px-2 py-0.5 text-xs font-medium text-gold-800">{copy.primary}</span>}
                {publication && <p className="mt-2 text-sm leading-6 text-stone-700">{publication}</p>}
                <dl className="mt-2 space-y-1 text-sm leading-6 text-stone-600">
                  {[
                    [copy.editor, book?.editor],
                    [copy.edition, book?.edition],
                    [copy.volume, book?.volume],
                    [copy.pages, book?.pages],
                    [copy.reference, source.page_reference],
                    ["ISBN", book?.isbn],
                    ["ISSN", book?.issn],
                    ["DOI", book?.doi],
                    [copy.accessed, book?.url_access_date],
                    [copy.repository, archive?.repository],
                    [copy.callNumber, archive?.call_number],
                    [copy.dateRange, archive?.date_range],
                  ].map(([label, value]) => value ? (
                    <div key={label}><dt className="inline font-medium">{label}: </dt><dd className="inline">{value}</dd></div>
                  ) : null)}
                </dl>
                <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-sm">
                  {url && <a href={url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 font-semibold text-burgundy-700 underline underline-offset-4 hover:text-burgundy-900">{archive ? copy.digitization : copy.open} · {new URL(url).hostname}<ExternalLink aria-hidden="true" className="h-3.5 w-3.5 shrink-0" /><span className="sr-only">{copy.newTab}</span></a>}
                  {doiUrl && doiUrl !== url && <a href={doiUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 font-semibold text-burgundy-700 underline underline-offset-4 hover:text-burgundy-900">{copy.openDoi}<ExternalLink aria-hidden="true" className="h-3.5 w-3.5" /><span className="sr-only">{copy.newTab}</span></a>}
                  {!url && !doiUrl && <p className="text-xs text-stone-500">{copy.offline}</p>}
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
