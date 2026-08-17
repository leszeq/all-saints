import Link from "next/link";
import { BookOpenText } from "lucide-react";

const groups = [
  { title: "Odkrywaj", links: [["Katalog świętych", "/swieci"], ["Patronaty", "/#odkrywaj"], ["Kalendarz", "/#kalendarz"], ["Epoki", "/#epoki"]] },
  { title: "Projekt", links: [["Metodologia", "/#metodologia"], ["Źródła i zasady", "/#zrodla"], ["Kontakt", "mailto:redakcja@encyklopediaswietych.pl"]] },
];

export function Footer() {
  return (
    <footer id="zrodla" className="border-t border-[#342d29] bg-[#1d1b19] text-stone-300">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-12 sm:px-6 md:grid-cols-[1.7fr_1fr_1fr] lg:px-8">
        <div className="max-w-lg">
          <div className="flex items-center gap-3 text-[#d2b977]"><BookOpenText className="h-5 w-5" strokeWidth={1.6} /><span className="font-serif text-xl font-semibold">Encyklopedia Świętych</span></div>
          <p className="mt-4 text-sm leading-6 text-stone-400">Redakcyjna baza wiedzy o życiu, kulcie i dziedzictwie świętych. Każdy profil powstaje na podstawie udokumentowanych źródeł.</p>
          <p className="mt-5 text-xs text-stone-500">Portal ma charakter informacyjno-edukacyjny.</p>
        </div>
        {groups.map((group) => (
          <div key={group.title}>
            <h2 className="text-xs font-bold uppercase tracking-[0.16em] text-[#d2b977]">{group.title}</h2>
            <ul className="mt-4 space-y-3 text-sm">
              {group.links.map(([label, href]) => <li key={label}><Link href={href} className="transition-colors hover:text-white">{label}</Link></li>)}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-white/10 px-4 py-5 text-center text-xs text-stone-500">© {new Date().getFullYear()} Encyklopedia Świętych. Wszelkie prawa zastrzeżone.</div>
    </footer>
  );
}
