import Link from "next/link";
import { ArrowRight, BookOpen } from "lucide-react";

import { DEFAULT_WEB_UI_LOCALE } from "@/lib/i18n/config";
import { getWebDictionary } from "@/lib/i18n/dictionaries";

export default async function NotFound() {
  const dictionary = await getWebDictionary(DEFAULT_WEB_UI_LOCALE);
  const copy = dictionary.system.notFound;

  return (
    <section className="mx-auto flex min-h-[62vh] max-w-3xl items-center px-4 py-16 sm:px-6">
      <div className="surface-card w-full p-8 text-center sm:p-12">
        <BookOpen className="mx-auto h-10 w-10 text-gold-700" strokeWidth={1.4} />
        <p className="editorial-label mt-7">{copy.kicker}</p>
        <h1 className="mt-3 font-serif text-4xl font-semibold text-charcoal">
          {copy.title}
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-sm leading-7 text-stone-600">
          {copy.description}
        </p>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Link
            href="/swieci"
            className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-burgundy-700 px-5 text-sm font-semibold text-white hover:bg-burgundy-600"
          >
            {copy.catalogueAction} <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/"
            className="inline-flex h-11 items-center justify-center rounded-lg border border-[#ded8cd] bg-white px-5 text-sm font-semibold text-burgundy-700 hover:bg-gold-50"
          >
            {copy.homeAction}
          </Link>
        </div>
      </div>
    </section>
  );
}
