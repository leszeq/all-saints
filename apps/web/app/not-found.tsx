import Link from "next/link";
import { ArrowRight, BookOpen } from "lucide-react";

export default function NotFound() {
  return (
    <section className="mx-auto flex min-h-[62vh] max-w-3xl items-center px-4 py-16 sm:px-6">
      <div className="surface-card w-full p-8 text-center sm:p-12">
        <BookOpen className="mx-auto h-10 w-10 text-gold-700" strokeWidth={1.4} />
        <p className="editorial-label mt-7">Błąd 404</p>
        <h1 className="mt-3 font-serif text-4xl font-semibold text-charcoal">
          Nie znaleziono strony
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-sm leading-7 text-stone-600">
          Adres mógł się zmienić albo wskazany profil nie jest opublikowany. Możesz wrócić
          do katalogu i odszukać właściwy wpis.
        </p>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Link
            href="/swieci"
            className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-burgundy-700 px-5 text-sm font-semibold text-white hover:bg-burgundy-600"
          >
            Otwórz katalog <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/"
            className="inline-flex h-11 items-center justify-center rounded-lg border border-[#ded8cd] bg-white px-5 text-sm font-semibold text-burgundy-700 hover:bg-gold-50"
          >
            Strona główna
          </Link>
        </div>
      </div>
    </section>
  );
}
