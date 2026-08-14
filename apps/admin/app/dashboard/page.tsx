"use client";

import { useQuery } from "@tanstack/react-query";
import {
  BookOpen,
  Church,
  Globe,
  Library,
  ShieldCheck,
  TrendingUp,
  Users,
} from "lucide-react";
import { personsApi, usersApi, geographyApi, ordersApi, sourcesApi } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: number | string;
  icon: React.ElementType;
  trend?: string;
  color: string;
}

function StatCard({ label, value, icon: Icon, trend, color }: StatCardProps) {
  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-sm animate-fade-in">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            {label}
          </p>
          <p className="mt-1.5 text-3xl font-bold text-foreground">{value}</p>
          {trend && (
            <p className="mt-1 flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
              <TrendingUp className="h-3 w-3" />
              {trend}
            </p>
          )}
        </div>
        <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${color}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}

const PERSON_TYPE_COLORS: Record<string, string> = {
  saint: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  blessed: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400",
  venerable: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  servant_of_god: "bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400",
  candidate: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400",
};

const PERSON_TYPE_LABELS: Record<string, string> = {
  saint: "Święci",
  blessed: "Błogosławieni",
  venerable: "Czcigodni",
  servant_of_god: "Słudzy Boży",
  candidate: "Kandydaci",
};

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  review: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  published: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  archived: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400",
};

const STATUS_LABELS: Record<string, string> = {
  draft: "Szkice",
  review: "W recenzji",
  published: "Opublikowane",
  archived: "Zarchiwizowane",
};

export default function DashboardPage() {
  const { data: personsData } = useQuery({
    queryKey: ["persons", "dashboard"],
    queryFn: () => personsApi.list({ per_page: 10, page: 1 }),
  });
  const { data: usersData } = useQuery({
    queryKey: ["users", "dashboard"],
    queryFn: () => usersApi.list({ per_page: 1 }),
  });
  const { data: countriesData } = useQuery({
    queryKey: ["countries", "dashboard"],
    queryFn: () => geographyApi.countries(),
  });
  const { data: ordersData } = useQuery({
    queryKey: ["orders", "dashboard"],
    queryFn: () => ordersApi.list(),
  });
  const { data: bibData } = useQuery({
    queryKey: ["bibliography", "dashboard"],
    queryFn: () => sourcesApi.bibliography(),
  });

  const persons = personsData?.data;
  const recentPersons = persons?.items ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          Przegląd systemu Encyklopedii Świętych
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-5">
        <StatCard
          label="Wszystkie osoby"
          value={persons?.total ?? "—"}
          icon={BookOpen}
          color="bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400"
        />
        <StatCard
          label="Państwa"
          value={countriesData?.data?.length ?? "—"}
          icon={Globe}
          color="bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
        />
        <StatCard
          label="Zakony"
          value={ordersData?.data?.length ?? "—"}
          icon={ShieldCheck}
          color="bg-indigo-100 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400"
        />
        <StatCard
          label="Źródła bibl."
          value={bibData?.data?.length ?? "—"}
          icon={Library}
          color="bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400"
        />
        <StatCard
          label="Użytkownicy"
          value={usersData?.data?.total ?? "—"}
          icon={Users}
          color="bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400"
        />
      </div>

      {/* Bottom section */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Recent persons */}
        <div className="col-span-2 rounded-xl border border-border bg-card p-5">
          <h2 className="mb-4 text-sm font-semibold text-foreground">
            Ostatnio dodane osoby
          </h2>
          {recentPersons.length === 0 ? (
            <p className="text-sm text-muted-foreground">Brak danych</p>
          ) : (
            <ul className="divide-y divide-border">
              {recentPersons.map((p: Record<string, unknown>) => (
                <li
                  key={p.id as string}
                  className="flex items-center justify-between gap-4 py-2.5"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-foreground">
                      {p.canonical_name as string}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatDateTime(p.created_at as string)}
                    </p>
                  </div>
                  <div className="flex flex-shrink-0 gap-1.5">
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                        PERSON_TYPE_COLORS[p.person_type as string] ?? ""
                      }`}
                    >
                      {PERSON_TYPE_LABELS[p.person_type as string] ?? p.person_type as string}
                    </span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                        STATUS_COLORS[p.status as string] ?? ""
                      }`}
                    >
                      {STATUS_LABELS[p.status as string] ?? p.status as string}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Quick links */}
        <div className="rounded-xl border border-border bg-card p-5">
          <h2 className="mb-4 text-sm font-semibold text-foreground">
            Szybkie akcje
          </h2>
          <div className="space-y-2">
            {[
              { href: "/dashboard/persons/new", label: "➕ Dodaj nową osobę" },
              { href: "/dashboard/geography/countries", label: "🌍 Zarządzaj państwami" },
              { href: "/dashboard/orders", label: "⚜️ Zarządzaj zakonami" },
              { href: "/dashboard/sources/bibliography", label: "📚 Dodaj bibliografię" },
              { href: "/dashboard/users", label: "👥 Zarządzaj użytkownikami" },
            ].map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="flex items-center rounded-lg px-3 py-2 text-sm text-foreground/80 transition-colors hover:bg-accent hover:text-accent-foreground"
              >
                {link.label}
              </a>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
