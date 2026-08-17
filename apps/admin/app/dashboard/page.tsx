"use client";

import Link from "next/link";
import type { ElementType } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  BookOpenText,
  CheckCircle2,
  Clock3,
  Copy,
  FileWarning,
  ImageOff,
  Plus,
  ShieldCheck,
  Users,
} from "lucide-react";
import { geographyApi, ordersApi, personsApi, sourcesApi, usersApi } from "@/lib/api";

const issues: Array<{ label: string; value: number; trend: string; icon: ElementType; tone: string }> = [
  { label: "Do recenzji", value: 84, trend: "+10 od wczoraj", icon: Clock3, tone: "text-blue-700 bg-blue-50 dark:bg-blue-950/30 dark:text-blue-300" },
  { label: "Braki krytyczne", value: 126, trend: "+7 od wczoraj", icon: FileWarning, tone: "text-amber-700 bg-amber-50 dark:bg-amber-950/30 dark:text-amber-300" },
  { label: "Duplikaty", value: 17, trend: "3 nowe sugestie", icon: Copy, tone: "text-rose-700 bg-rose-50 dark:bg-rose-950/30 dark:text-rose-300" },
  { label: "Licencje do sprawdzenia", value: 31, trend: "5 pilnych", icon: ImageOff, tone: "text-orange-700 bg-orange-50 dark:bg-orange-950/30 dark:text-orange-300" },
];

const taskRows = [
  ["Recenzja biogramu: św. Rita z Cascii", "Recenzja", "2 h"],
  ["Brak źródeł: św. Eustachy", "Kompletność", "5 h"],
  ["Duplikat: bł. Walenty", "Duplikaty", "1 d"],
  ["Licencja obrazu: św. Jan Bosko", "Media", "2 d"],
];

const chart = [42, 47, 45, 55, 51, 62, 59, 66, 70, 68, 76, 82];

export default function DashboardPage() {
  const { data: personsData } = useQuery({ queryKey: ["persons", "dashboard"], queryFn: () => personsApi.list({ per_page: 6, page: 1 }) });
  const { data: usersData } = useQuery({ queryKey: ["users", "dashboard"], queryFn: () => usersApi.list({ per_page: 1 }) });
  const { data: countriesData } = useQuery({ queryKey: ["countries", "dashboard"], queryFn: () => geographyApi.countries() });
  const { data: ordersData } = useQuery({ queryKey: ["orders", "dashboard"], queryFn: () => ordersApi.list() });
  const { data: bibliographyData } = useQuery({ queryKey: ["bibliography", "dashboard"], queryFn: () => sourcesApi.bibliography() });

  const recentPersons = personsData?.data?.items ?? [];
  const total = personsData?.data?.total ?? 0;

  return (
    <div className="mx-auto max-w-[1500px] space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div><p className="admin-label">Poniedziałek, 17 sierpnia</p><h1 className="mt-1 text-2xl font-semibold tracking-tight">Pulpit redakcyjny</h1><p className="mt-1 text-sm text-muted-foreground">Najważniejsze zadania i kondycja bazy wiedzy.</p></div>
        <Link href="/dashboard/persons/new" className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground shadow-sm hover:bg-primary/90"><Plus className="h-4 w-4" />Dodaj postać</Link>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Kolejki operacyjne">
        {issues.map(({ label, value, trend, icon: Icon, tone }) => (
          <div key={label} className="admin-card p-4"><div className="flex items-start justify-between"><div><p className="text-xs font-medium text-muted-foreground">{label}</p><p className="mt-2 text-3xl font-semibold tracking-tight">{value}</p></div><span className={`flex h-9 w-9 items-center justify-center rounded-lg ${tone}`}><Icon className="h-4 w-4" /></span></div><p className="mt-3 text-[11px] text-muted-foreground">{trend}</p></div>
        ))}
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.45fr_.85fr]">
        <article className="admin-card p-5">
          <div className="flex items-center justify-between"><div><h2 className="text-sm font-semibold">Zweryfikowane profile</h2><p className="mt-1 text-xs text-muted-foreground">Ostatnie 12 miesięcy</p></div><span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300"><CheckCircle2 className="h-3 w-3" />+18,6%</span></div>
          <div className="mt-8 flex h-44 items-end gap-2 border-b border-l border-border px-3 pt-4">
            {chart.map((height, index) => <div key={index} className="group relative flex h-full flex-1 items-end"><div className="w-full rounded-t-sm bg-primary/75 transition-colors group-hover:bg-primary" style={{ height: `${height}%` }} /><span className="pointer-events-none absolute -top-5 left-1/2 hidden -translate-x-1/2 rounded bg-foreground px-1.5 py-0.5 text-[9px] text-background group-hover:block">{height}</span></div>)}
          </div>
          <div className="mt-2 grid grid-cols-12 text-center text-[9px] text-muted-foreground">{["Wrz", "Paź", "Lis", "Gru", "Sty", "Lut", "Mar", "Kwi", "Maj", "Cze", "Lip", "Sie"].map((month) => <span key={month}>{month}</span>)}</div>
        </article>

        <article className="admin-card p-5">
          <div className="flex items-center justify-between"><div><h2 className="text-sm font-semibold">Moje zadania</h2><p className="mt-1 text-xs text-muted-foreground">4 wymagają uwagi</p></div><Link href="/dashboard/persons" className="text-xs font-semibold text-primary">Zobacz wszystkie</Link></div>
          <ul className="mt-4 divide-y divide-border">
            {taskRows.map(([title, type, age], index) => <li key={title} className="flex items-center gap-3 py-3"><span className={`h-2 w-2 shrink-0 rounded-full ${index === 0 ? "bg-blue-500" : index === 1 ? "bg-amber-500" : index === 2 ? "bg-rose-500" : "bg-orange-500"}`} /><div className="min-w-0 flex-1"><p className="truncate text-xs font-medium">{title}</p><p className="mt-1 text-[10px] text-muted-foreground">{type}</p></div><span className="text-[10px] text-muted-foreground">{age}</span></li>)}
          </ul>
        </article>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.2fr_.8fr_.8fr]">
        <article className="admin-card p-5">
          <div className="flex items-center justify-between"><div><h2 className="text-sm font-semibold">Ostatnio zmienione rekordy</h2><p className="mt-1 text-xs text-muted-foreground">{total || "12 456"} osób w bazie</p></div><Link href="/dashboard/persons" className="inline-flex items-center gap-1 text-xs font-semibold text-primary">Lista osób <ArrowRight className="h-3 w-3" /></Link></div>
          <div className="mt-4 divide-y divide-border">
            {(recentPersons.length ? recentPersons : [{ id: "1", canonical_name: "Św. Jan Paweł II", status: "verified" }, { id: "2", canonical_name: "Św. Maksymilian Maria Kolbe", status: "review" }, { id: "3", canonical_name: "Św. Teresa z Ávili", status: "published" }]).slice(0, 4).map((person: Record<string, unknown>, index: number) => <div key={String(person.id)} className="flex items-center gap-3 py-3"><span className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-[11px] font-semibold text-muted-foreground">{index + 1}</span><div className="min-w-0 flex-1"><p className="truncate text-xs font-medium">{String(person.canonical_name)}</p><p className="mt-1 text-[10px] text-muted-foreground">Edytowano dzisiaj</p></div><span className="rounded-full bg-blue-50 px-2 py-1 text-[9px] font-semibold text-blue-700 dark:bg-blue-950/30 dark:text-blue-300">{String(person.status || "review")}</span></div>)}
          </div>
        </article>

        <article className="admin-card p-5"><h2 className="text-sm font-semibold">Kompletność danych</h2><p className="mt-1 text-xs text-muted-foreground">Rozkład wszystkich profili</p><div className="mt-6 space-y-4">{[["Pełne", 54, "bg-emerald-500"], ["Częściowe", 28, "bg-blue-500"], ["Niskie", 13, "bg-amber-500"], ["Brak krytyczny", 5, "bg-rose-500"]].map(([label, value, color]) => <div key={label as string}><div className="flex justify-between text-[11px]"><span>{label}</span><span className="font-semibold">{value}%</span></div><div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-muted"><div className={`h-full rounded-full ${color}`} style={{ width: `${value}%` }} /></div></div>)}</div></article>

        <article className="admin-card p-5"><h2 className="text-sm font-semibold">Stan systemu</h2><p className="mt-1 text-xs text-muted-foreground">Zasoby dostępne przez API</p><dl className="mt-5 space-y-3 text-xs">{[["Użytkownicy", usersData?.data?.total], ["Państwa", countriesData?.data?.length], ["Zakony", ordersData?.data?.length], ["Bibliografia", bibliographyData?.data?.length]].map(([label, value]) => <div key={label as string} className="flex items-center justify-between border-b border-border pb-3"><dt className="flex items-center gap-2 text-muted-foreground">{label === "Użytkownicy" ? <Users className="h-3.5 w-3.5" /> : label === "Bibliografia" ? <BookOpenText className="h-3.5 w-3.5" /> : <ShieldCheck className="h-3.5 w-3.5" />}{label}</dt><dd className="font-semibold">{value ?? "—"}</dd></div>)}</dl><div className="mt-5 flex items-center gap-2 rounded-lg bg-emerald-50 px-3 py-2 text-[10px] font-medium text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300"><span className="status-dot bg-emerald-500" />Wszystkie usługi działają</div></article>
      </section>

      <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/20 dark:text-amber-200"><AlertTriangle className="h-4 w-4" /><span><strong>Wskazówka:</strong> 31 obrazów nie ma informacji o licencji. Uzupełnij je przed kolejną publikacją.</span></div>
    </div>
  );
}
