import Link from "next/link";
import { BookOpenText } from "lucide-react";
import type { WebFooterDictionary } from "@/lib/i18n/types";

export function Footer({ dictionary }: { dictionary: WebFooterDictionary }) {
  return (
    <footer id="zrodla" className="border-t border-[#342d29] bg-[#1d1b19] text-stone-300">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-12 sm:px-6 md:grid-cols-[1.7fr_1fr_1fr] lg:px-8">
        <div className="max-w-lg">
          <div className="flex items-center gap-3 text-[#d2b977]"><BookOpenText className="h-5 w-5" strokeWidth={1.6} /><span className="font-serif text-xl font-semibold">{dictionary.brand.name}</span></div>
          <p className="mt-4 text-sm leading-6 text-stone-400">{dictionary.footer.description}</p>
          <p className="mt-5 text-xs text-stone-500">{dictionary.footer.disclaimer}</p>
        </div>
        {dictionary.footer.groups.map((group) => (
          <div key={group.title}>
            <h2 className="text-xs font-bold uppercase tracking-[0.16em] text-[#d2b977]">{group.title}</h2>
            <ul className="mt-4 space-y-3 text-sm">
              {group.links.map(({ label, href }) => <li key={label}><Link href={href} className="transition-colors hover:text-white">{label}</Link></li>)}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-white/10 px-4 py-5 text-center text-xs text-stone-500">© {new Date().getFullYear()} {dictionary.brand.name}. {dictionary.footer.rightsReserved}</div>
    </footer>
  );
}
