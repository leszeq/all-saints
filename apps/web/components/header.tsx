"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { BookOpenText, Menu, Search, X } from "lucide-react";

const navigation = [
  { href: "/swieci", label: "Katalog świętych" },
  { href: "/#odkrywaj", label: "Patronaty" },
  { href: "/#kalendarz", label: "Kalendarz" },
  { href: "/#zakony", label: "Zakony" },
  { href: "/#epoki", label: "Epoki" },
];

export function Header() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const submitSearch = (event: React.FormEvent) => {
    event.preventDefault();
    const query = search.trim();
    if (query) router.push(`/swieci?search=${encodeURIComponent(query)}`);
  };

  return (
    <header className="sticky top-0 z-50 border-b border-[#ded8cd] bg-[#f7f3ea]/95 backdrop-blur-md">
      <div className="mx-auto flex h-[72px] max-w-7xl items-center gap-8 px-4 sm:px-6 lg:px-8">
        <Link href="/" className="group flex shrink-0 items-center gap-3" aria-label="Encyklopedia Świętych — strona główna">
          <span className="flex h-10 w-10 items-center justify-center rounded-full border border-gold-300 bg-[#fffdf8] text-gold-700 transition-colors group-hover:border-gold-500">
            <BookOpenText className="h-[18px] w-[18px]" strokeWidth={1.6} />
          </span>
          <span>
            <span className="block font-serif text-[17px] font-semibold leading-none text-charcoal">Encyklopedia Świętych</span>
            <span className="mt-1 block text-[9px] font-semibold uppercase tracking-[0.2em] text-gold-700">Portal publiczny</span>
          </span>
        </Link>

        <nav className="ml-auto hidden items-center gap-6 lg:flex" aria-label="Nawigacja główna">
          {navigation.map((item) => <Link key={item.href} href={item.href} className="text-[13px] font-medium text-stone-600 transition-colors hover:text-burgundy-700">{item.label}</Link>)}
        </nav>

        <form onSubmit={submitSearch} className="hidden md:block">
          <label className="relative block">
            <span className="sr-only">Szukaj w encyklopedii</span>
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-500" />
            <input value={search} onChange={(event) => setSearch(event.target.value)} className="h-10 w-48 rounded-lg border border-[#ded8cd] bg-[#fffdf8] pl-9 pr-3 text-sm outline-none transition-all placeholder:text-stone-400 focus:w-60 focus:border-gold-500" placeholder="Szukaj…" />
          </label>
        </form>

        <button type="button" onClick={() => setMobileMenuOpen((open) => !open)} className="ml-auto flex h-10 w-10 items-center justify-center rounded-lg border border-[#ded8cd] bg-[#fffdf8] text-charcoal lg:hidden" aria-expanded={mobileMenuOpen} aria-label={mobileMenuOpen ? "Zamknij menu" : "Otwórz menu"}>
          {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {mobileMenuOpen && (
        <div className="border-t border-[#ded8cd] bg-[#fffdf8] px-4 py-5 lg:hidden">
          <form onSubmit={submitSearch} className="mb-4 flex gap-2">
            <input value={search} onChange={(event) => setSearch(event.target.value)} className="h-11 min-w-0 flex-1 rounded-lg border border-[#ded8cd] bg-white px-3 text-sm" placeholder="Szukaj świętego lub patronatu…" />
            <button className="h-11 rounded-lg bg-burgundy-700 px-4 text-sm font-semibold text-white">Szukaj</button>
          </form>
          <nav className="grid gap-1" aria-label="Nawigacja mobilna">
            {navigation.map((item) => <Link key={item.href} href={item.href} onClick={() => setMobileMenuOpen(false)} className="rounded-lg px-3 py-2.5 text-sm font-medium text-stone-700 hover:bg-gold-50">{item.label}</Link>)}
          </nav>
        </div>
      )}
    </header>
  );
}
