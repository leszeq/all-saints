import Link from "next/link";
import { Crown, Heart } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-gold-500/20 bg-burgundy-900 text-burgundy-50">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gold-500 text-burgundy-900">
                <Crown className="h-5 w-5" />
              </div>
              <span className="font-serif text-lg font-bold text-gold-300">
                Encyklopedia Świętych
              </span>
            </div>
            <p className="text-xs text-burgundy-200 leading-relaxed">
              Kompletny cyfrowy leksykon hagiograficzny Kościoła Katolickiego. Ponad 20 000 postaci, życiorysy, patronaty, modlitwy oraz źródła.
            </p>
          </div>

          {/* Quick links */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gold-400 mb-3">
              Nawigacja
            </h3>
            <ul className="space-y-2 text-sm text-burgundy-200">
              <li><Link href="/swieci" className="hover:text-gold-300 transition-colors">Katalog Świętych</Link></li>
              <li><Link href="/kalendarz" className="hover:text-gold-300 transition-colors">Kalendarz Liturgiczny</Link></li>
              <li><Link href="/sanktuaria" className="hover:text-gold-300 transition-colors">Sanktuaria</Link></li>
              <li><Link href="/zakony" className="hover:text-gold-300 transition-colors">Zakony</Link></li>
            </ul>
          </div>

          {/* Categories */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gold-400 mb-3">
              Kategorie
            </h3>
            <ul className="space-y-2 text-sm text-burgundy-200">
              <li><Link href="/swieci?type=saint" className="hover:text-gold-300 transition-colors">Święci</Link></li>
              <li><Link href="/swieci?type=blessed" className="hover:text-gold-300 transition-colors">Błogosławieni</Link></li>
              <li><Link href="/swieci?type=servant_of_god" className="hover:text-gold-300 transition-colors">Słudzy Boży</Link></li>
              <li><Link href="/swieci?type=venerable" className="hover:text-gold-300 transition-colors">Czcigodni Boży</Link></li>
            </ul>
          </div>

          {/* Info */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gold-400 mb-3">
              Informacje
            </h3>
            <p className="text-xs text-burgundy-200 leading-relaxed mb-3">
              Wszelkie materiały udostępniane są w celach edukacyjnych i modlitewnych.
            </p>
            <p className="text-[11px] text-burgundy-300 flex items-center gap-1">
              Stworzone z <Heart className="h-3 w-3 text-red-400 fill-red-400" /> dla Kościoła
            </p>
          </div>
        </div>

        <div className="mt-8 border-t border-burgundy-800 pt-6 text-center text-xs text-burgundy-300">
          © {new Date().getFullYear()} Encyklopedia Świętych Kościoła Katolickiego. Wszelkie prawa zastrzeżone.
        </div>
      </div>
    </footer>
  );
}
