"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpenText,
  Bot,
  ChevronRight,
  CircleGauge,
  Database,
  FileSearch,
  Globe2,
  Library,
  Network,
  Settings,
  ShieldCheck,
  Tags,
  Users,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItem {
  href?: string;
  label: string;
  icon: LucideIcon;
  badge?: string;
}

const sections: Array<{ title: string; items: NavItem[] }> = [
  { title: "Redakcja", items: [
    { href: "/dashboard", label: "Pulpit", icon: CircleGauge },
    { href: "/dashboard/persons", label: "Osoby i święci", icon: BookOpenText },
    { label: "Kolejka redakcyjna", icon: FileSearch, badge: "84" },
  ] },
  { title: "Jakość danych", items: [
    { label: "Problemy jakości", icon: Database, badge: "126" },
    { label: "Duplikaty", icon: Network, badge: "17" },
    { label: "Weryfikacja źródeł", icon: ShieldCheck },
  ] },
  { title: "AI", items: [
    { label: "Centrum AI", icon: Bot },
    { label: "Sugestie", icon: Tags, badge: "236" },
  ] },
  { title: "Źródła i dane", items: [
    { label: "Źródła i media", icon: Library },
    { href: "/dashboard/geography/countries", label: "Geografia", icon: Globe2 },
    { href: "/dashboard/orders", label: "Zakony", icon: ShieldCheck },
    { label: "Słowniki", icon: Tags },
  ] },
  { title: "Administracja", items: [
    { href: "/dashboard/users", label: "Użytkownicy", icon: Users },
    { label: "Ustawienia", icon: Settings },
  ] },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-[260px] shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground">
      <Link href="/dashboard" className="flex h-16 items-center gap-3 border-b border-sidebar-border px-5">
        <span className="flex h-9 w-9 items-center justify-center rounded-full border border-sidebar-accent/60 text-sidebar-accent"><BookOpenText className="h-4 w-4" strokeWidth={1.6} /></span>
        <span className="min-w-0"><span className="block truncate text-sm font-semibold text-white">Encyklopedia Świętych</span><span className="mt-0.5 block text-[9px] font-semibold uppercase tracking-[0.17em] text-sidebar-foreground/45">Panel redakcyjny</span></span>
      </Link>

      <nav className="flex-1 overflow-y-auto px-3 py-4" aria-label="Nawigacja panelu">
        {sections.map((section) => (
          <section key={section.title} className="mb-5">
            <h2 className="mb-1.5 px-2 text-[9px] font-bold uppercase tracking-[0.17em] text-sidebar-foreground/35">{section.title}</h2>
            <ul className="space-y-0.5">
              {section.items.map((item) => {
                const active = item.href ? pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href)) : false;
                const content = <><item.icon className="h-4 w-4 shrink-0" strokeWidth={1.7} /><span className="min-w-0 flex-1 truncate">{item.label}</span>{item.badge && <span className="rounded-full bg-white/8 px-2 py-0.5 text-[9px] text-sidebar-foreground/60">{item.badge}</span>}{!item.href && !item.badge && <ChevronRight className="h-3 w-3 text-sidebar-foreground/25" />}</>;
                return <li key={item.label}>{item.href ? <Link href={item.href} className={cn("relative flex h-9 items-center gap-2.5 rounded-md px-2.5 text-[12px] font-medium transition-colors", active ? "bg-white/[0.07] text-white before:absolute before:-left-3 before:h-5 before:w-0.5 before:bg-sidebar-accent" : "text-sidebar-foreground/67 hover:bg-white/[0.04] hover:text-white")}>{content}</Link> : <span className="flex h-9 cursor-default items-center gap-2.5 rounded-md px-2.5 text-[12px] font-medium text-sidebar-foreground/48" title="Moduł przewidziany w kolejnym etapie">{content}</span>}</li>;
              })}
            </ul>
          </section>
        ))}
      </nav>

      <div className="border-t border-sidebar-border px-5 py-4"><div className="flex items-center gap-2 text-[10px] text-sidebar-foreground/45"><span className="status-dot bg-emerald-500" />API połączone</div><p className="mt-1 text-[9px] text-sidebar-foreground/25">v1.0 · środowisko lokalne</p></div>
    </aside>
  );
}
