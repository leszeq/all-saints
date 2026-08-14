"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpen,
  Building2,
  Church,
  Crown,
  FileText,
  Globe,
  Home,
  Image,
  LayoutDashboard,
  Library,
  ShieldCheck,
  Tag,
  Users,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navSections = [
  {
    title: "Główne",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    ],
  },
  {
    title: "Hagiografia",
    items: [
      { href: "/dashboard/persons", label: "Osoby & Święci", icon: BookOpen },
    ],
  },
  {
    title: "Geografia",
    items: [
      { href: "/dashboard/geography/countries", label: "Państwa", icon: Globe },
      { href: "/dashboard/geography/dioceses", label: "Diecezje", icon: Building2 },
      { href: "/dashboard/geography/places", label: "Miejsca", icon: Home },
      { href: "/dashboard/geography/churches", label: "Kościoły", icon: Church },
    ],
  },
  {
    title: "Kościół",
    items: [
      { href: "/dashboard/orders", label: "Zakony", icon: ShieldCheck },
      { href: "/dashboard/popes", label: "Papieże", icon: Crown },
    ],
  },
  {
    title: "Źródła",
    items: [
      { href: "/dashboard/sources/bibliography", label: "Bibliografia", icon: Library },
      { href: "/dashboard/sources/historical", label: "Źródła hist.", icon: FileText },
      { href: "/dashboard/sources/images", label: "Obrazy", icon: Image },
    ],
  },
  {
    title: "Taksonomia",
    items: [
      { href: "/dashboard/taxonomy/categories", label: "Kategorie", icon: LayoutDashboard },
      { href: "/dashboard/taxonomy/tags", label: "Tagi", icon: Tag },
    ],
  },
  {
    title: "Administracja",
    items: [
      { href: "/dashboard/users", label: "Użytkownicy", icon: Users },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-60 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground">
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 border-b border-sidebar-border px-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
          <Crown className="h-4 w-4 text-white" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-white">
            Encyklopedia
          </p>
          <p className="truncate text-[10px] text-sidebar-foreground/50">
            Świętych Kościoła
          </p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-3">
        {navSections.map((section) => (
          <div key={section.title} className="mb-5">
            <p className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-widest text-sidebar-foreground/40">
              {section.title}
            </p>
            <ul className="space-y-0.5">
              {section.items.map((item) => {
                const active =
                  pathname === item.href ||
                  (item.href !== "/dashboard" && pathname.startsWith(item.href));
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={cn(
                        "flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-[13px] font-medium transition-all",
                        active
                          ? "bg-sidebar-accent text-sidebar-accent-foreground"
                          : "text-sidebar-foreground/70 hover:bg-sidebar-border hover:text-sidebar-foreground"
                      )}
                    >
                      <item.icon className="h-3.5 w-3.5 flex-shrink-0" />
                      {item.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-sidebar-border px-4 py-3">
        <p className="text-[10px] text-sidebar-foreground/30">v1.0.0 · Admin Panel</p>
      </div>
    </aside>
  );
}
