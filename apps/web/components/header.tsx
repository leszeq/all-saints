"use client";

import Link from "next/link";
import { useState } from "react";
import { BookOpen, Calendar, Crown, MapPin, Search, Shield, Menu, X } from "lucide-react";
import { useRouter } from "next/navigation";

export function Header() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (search.trim()) {
      router.push(`/swieci?search=${encodeURIComponent(search.trim())}`);
    }
  };

  return (
    <header className="sticky top-0 z-50 glass border-b border-gold-500/20 shadow-sm">
      <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand Logo */}
        <Link href="/" className="flex items-center gap-3 group">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-gold-400 via-gold-500 to-gold-700 text-burgundy-900 shadow-md group-hover:scale-105 transition-transform">
            <Crown className="h-6 w-6" />
          </div>
          <div>
            <span className="font-serif text-lg font-bold text-burgundy-900 block leading-tight tracking-tight">
              Encyklopedia Świętych
            </span>
            <span className="text-[11px] font-sans font-medium tracking-widest text-gold-700 uppercase block">
              Kościoła Katolickiego
            </span>
          </div>
        </Link>

        {/* Live Search Bar */}
        <form onSubmit={handleSearchSubmit} className="hidden md:flex flex-1 max-w-md mx-8">
          <div className="relative w-full">
            <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gold-600" />
            <input
              type="text"
              placeholder="Szukaj świętych, błogosławionych, patronów..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-full border border-gold-500/30 bg-white/80 py-2 pl-10 pr-4 text-sm text-gray-800 placeholder-gray-400 focus:border-gold-500 focus:outline-none focus:ring-2 focus:ring-gold-400/20 shadow-inner transition-all"
            />
          </div>
        </form>

        {/* Navigation Links */}
        <nav className="hidden lg:flex items-center gap-6 text-sm font-medium text-gray-700">
          <Link href="/swieci" className="flex items-center gap-1.5 hover:text-burgundy-600 transition-colors">
            <BookOpen className="h-4 w-4 text-gold-600" />
            Katalog
          </Link>
          <Link href="/kalendarz" className="flex items-center gap-1.5 hover:text-burgundy-600 transition-colors">
            <Calendar className="h-4 w-4 text-gold-600" />
            Kalendarz
          </Link>
          <Link href="/mapa" className="flex items-center gap-1.5 hover:text-burgundy-600 transition-colors">
            <MapPin className="h-4 w-4 text-gold-600" />
            Sanktuaria
          </Link>
          <a
            href="http://localhost:3001"
            target="_blank"
            rel="noreferrer"
            className="rounded-full bg-burgundy-500 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-burgundy-600 transition-all"
          >
            Panel Admina
          </a>
        </nav>

        {/* Mobile menu trigger */}
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="lg:hidden p-2 text-gray-700 hover:text-burgundy-600"
        >
          {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-t border-gold-500/20 bg-white px-4 py-4 space-y-3">
          <form onSubmit={handleSearchSubmit}>
            <input
              type="text"
              placeholder="Szukaj..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg border border-gold-500/30 p-2 text-sm"
            />
          </form>
          <Link href="/swieci" className="block text-sm font-medium py-1">Katalog Świętych</Link>
          <Link href="/kalendarz" className="block text-sm font-medium py-1">Kalendarz Liturgiczny</Link>
          <Link href="/mapa" className="block text-sm font-medium py-1">Sanktuaria i Miejsca</Link>
        </div>
      )}
    </header>
  );
}
