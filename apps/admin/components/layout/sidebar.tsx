"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  BookOpenText,
  Bot,
  Braces,
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
import { API_BASE_URL, aiApi, editorialApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useAuthHydrated, useAuthStore } from "@/lib/store/auth";

interface NavItem {
  href?: string;
  label: string;
  icon: LucideIcon;
  badge?: string;
  dynamicBadge?: "editorial-queue" | "quality-issues" | "quality-duplicates" | "quality-sources" | "ai-suggestions";
  exact?: boolean;
  external?: boolean;
  requiredPermission?: string;
}

const sections: Array<{ title: string; items: NavItem[] }> = [
  { title: "Redakcja", items: [
    { href: "/dashboard", label: "Pulpit", icon: CircleGauge },
    { href: "/dashboard/persons", label: "Osoby i święci", icon: BookOpenText },
    { href: "/dashboard/review", label: "Kolejka redakcyjna", icon: FileSearch, dynamicBadge: "editorial-queue" },
  ] },
  { title: "Jakość danych", items: [
    { href: "/dashboard/quality/issues", label: "Problemy jakości", icon: Database, dynamicBadge: "quality-issues" },
    { href: "/dashboard/quality/duplicates", label: "Duplikaty", icon: Network, dynamicBadge: "quality-duplicates" },
    { href: "/dashboard/quality/sources", label: "Weryfikacja źródeł", icon: ShieldCheck, dynamicBadge: "quality-sources" },
  ] },
  { title: "AI", items: [
    { href: "/dashboard/ai", label: "Centrum AI", icon: Bot, exact: true },
    { href: "/dashboard/ai/suggestions", label: "Sugestie", icon: Tags, dynamicBadge: "ai-suggestions" },
  ] },
  { title: "Źródła i dane", items: [
    { href: "/dashboard/sources", label: "Źródła i media", icon: Library },
    { href: "/dashboard/geography", label: "Geografia", icon: Globe2 },
    { href: "/dashboard/orders", label: "Zakony", icon: ShieldCheck },
    { href: "/dashboard/dictionaries", label: "Słowniki", icon: Tags },
  ] },
  { title: "Administracja", items: [
    { href: "/dashboard/users", label: "Użytkownicy i role", icon: Users, requiredPermission: "users:read" },
    { href: `${API_BASE_URL}/docs`, label: "Dokumentacja API", icon: Braces, external: true },
    { href: "/dashboard/settings", label: "Ustawienia", icon: Settings },
  ] },
];

export function Sidebar() {
  const pathname = usePathname();
  const hasPermission = useAuthStore((state) => state.hasPermission);
  const authHydrated = useAuthHydrated();
  const dashboardQuery = useQuery({
    queryKey: ["editorial", "dashboard"],
    queryFn: () => editorialApi.dashboard(),
  });
  const qualityQuery = useQuery({
    queryKey: ["editorial", "quality"],
    queryFn: () => editorialApi.quality(),
    staleTime: 60_000,
  });
  const aiSuggestionsQuery = useQuery({
    queryKey: ["ai", "suggestions", "sidebar"],
    queryFn: () => aiApi.suggestions({ limit: 1 }),
    staleTime: 60_000,
  });
  const queueCount = dashboardQuery.data?.data.queue_counts.total;
  const qualitySummary = qualityQuery.data?.data.summary;
  const aiSuggestionCount = aiSuggestionsQuery.data
    ? aiSuggestionsQuery.data.data.pending_review + aiSuggestionsQuery.data.data.ready_to_generate
    : undefined;

  const getDynamicBadge = (kind: NavItem["dynamicBadge"]) => {
    if (kind === "editorial-queue") return queueCount;
    if (kind === "quality-issues") return qualitySummary?.records_with_issues;
    if (kind === "quality-duplicates") return qualitySummary?.duplicate_groups;
    if (kind === "quality-sources") return qualitySummary?.source_items_to_review;
    if (kind === "ai-suggestions") return aiSuggestionCount;
    return undefined;
  };

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
              {section.items.filter((item) => !item.requiredPermission || (authHydrated && hasPermission(item.requiredPermission))).map((item) => {
                const active = item.href && !item.external
                  ? pathname === item.href || (!item.exact && item.href !== "/dashboard" && pathname.startsWith(`${item.href}/`))
                  : false;
                const badge = item.dynamicBadge ? getDynamicBadge(item.dynamicBadge) : item.badge;
                const content = <><item.icon className="h-4 w-4 shrink-0" strokeWidth={1.7} /><span className="min-w-0 flex-1 truncate">{item.label}</span>{badge !== undefined && <span className="rounded-full bg-white/8 px-2 py-0.5 text-[9px] text-sidebar-foreground/60">{badge}</span>}{!item.href && !item.badge && <ChevronRight className="h-3 w-3 text-sidebar-foreground/25" />}</>;
                const navClassName = cn("relative flex h-9 items-center gap-2.5 rounded-md px-2.5 text-[12px] font-medium transition-colors", active ? "bg-white/[0.07] text-white before:absolute before:-left-3 before:h-5 before:w-0.5 before:bg-sidebar-accent" : "text-sidebar-foreground/67 hover:bg-white/[0.04] hover:text-white");
                return <li key={item.label}>{item.href ? (item.external ? <a href={item.href} target="_blank" rel="noreferrer" className={navClassName}>{content}</a> : <Link href={item.href} className={navClassName}>{content}</Link>) : <span className="flex h-9 cursor-default items-center gap-2.5 rounded-md px-2.5 text-[12px] font-medium text-sidebar-foreground/48" title="Moduł przewidziany w kolejnym etapie">{content}</span>}</li>;
              })}
            </ul>
          </section>
        ))}
      </nav>

      <div className="border-t border-sidebar-border px-5 py-4"><div className="flex items-center gap-2 text-[10px] text-sidebar-foreground/45"><span className={cn("status-dot", dashboardQuery.isError ? "bg-rose-500" : dashboardQuery.data ? "bg-emerald-500" : "bg-amber-500")} />{dashboardQuery.isError ? "API niedostępne" : dashboardQuery.data ? "API połączone" : "Łączenie z API…"}</div><p className="mt-1 text-[9px] text-sidebar-foreground/25">v1.0 · środowisko lokalne</p></div>
    </aside>
  );
}
