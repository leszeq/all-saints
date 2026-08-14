"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import {
  ChevronLeft,
  ChevronRight,
  Filter,
  Plus,
  RefreshCw,
  Search,
} from "lucide-react";
import { personsApi } from "@/lib/api";
import { cn, formatDateTime, PERSON_STATUS_COLORS, PERSON_STATUS_LABELS, PERSON_TYPE_COLORS, PERSON_TYPE_LABELS } from "@/lib/utils";

const PER_PAGE = 20;

export default function PersonsPage() {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  // Debounce search
  const handleSearch = (val: string) => {
    setSearch(val);
    clearTimeout((window as unknown as { _st?: ReturnType<typeof setTimeout> })._st);
    (window as unknown as { _st?: ReturnType<typeof setTimeout> })._st = setTimeout(() => {
      setDebouncedSearch(val);
      setPage(1);
    }, 350);
  };

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["persons", page, debouncedSearch, typeFilter, statusFilter],
    queryFn: () =>
      personsApi.list({
        page,
        per_page: PER_PAGE,
        ...(debouncedSearch && { search: debouncedSearch }),
        ...(typeFilter && { person_type: typeFilter }),
        ...(statusFilter && { status: statusFilter }),
      }),
  });

  const persons = data?.data?.items ?? [];
  const total = data?.data?.total ?? 0;
  const pages = data?.data?.pages ?? 1;

  return (
    <div className="flex flex-col gap-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Osoby & Święci</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Zarządzaj hagiograficzną bazą osób
          </p>
        </div>
        <button
          onClick={() => router.push("/dashboard/persons/new")}
          className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Dodaj osobę
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        {/* Search */}
        <div className="relative flex-1 min-w-52">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Szukaj po imieniu..."
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-full rounded-lg border border-input bg-background py-2 pl-9 pr-3 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>

        {/* Person type */}
        <select
          value={typeFilter}
          onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
          className="rounded-lg border border-input bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
        >
          <option value="">Wszystkie typy</option>
          {Object.entries(PERSON_TYPE_LABELS).map(([v, l]) => (
            <option key={v} value={v}>{l}</option>
          ))}
        </select>

        {/* Status */}
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="rounded-lg border border-input bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
        >
          <option value="">Wszystkie statusy</option>
          {Object.entries(PERSON_STATUS_LABELS).map(([v, l]) => (
            <option key={v} value={v}>{l}</option>
          ))}
        </select>

        {/* Refresh */}
        <button
          onClick={() => refetch()}
          className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Odśwież
        </button>
      </div>

      {/* Summary */}
      <p className="text-xs text-muted-foreground">
        Znaleziono <strong>{total}</strong> rekordów
      </p>

      {/* Table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="border-b border-border bg-muted/40">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Imię / Nazwa
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Typ
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Status
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Era
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Dodano
              </th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {isLoading ? (
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: 6 }).map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-4 w-full animate-pulse rounded bg-muted" />
                    </td>
                  ))}
                </tr>
              ))
            ) : persons.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center text-sm text-muted-foreground">
                  Brak wyników
                </td>
              </tr>
            ) : (
              persons.map((p: Record<string, unknown>) => (
                <tr
                  key={p.id as string}
                  className="cursor-pointer transition-colors hover:bg-muted/40"
                  onClick={() => router.push(`/dashboard/persons/${p.id}`)}
                >
                  <td className="px-4 py-3">
                    <div>
                      <p className="font-medium text-foreground">
                        {p.canonical_name as string}
                      </p>
                      {Boolean(p.latin_name) && (
                        <p className="text-xs text-muted-foreground italic">
                          {String(p.latin_name)}
                        </p>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        "rounded-full px-2.5 py-0.5 text-xs font-medium",
                        PERSON_TYPE_COLORS[p.person_type as string]
                      )}
                    >
                      {PERSON_TYPE_LABELS[p.person_type as string] ?? (p.person_type as string)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        "rounded-full px-2.5 py-0.5 text-xs font-medium",
                        PERSON_STATUS_COLORS[p.status as string]
                      )}
                    >
                      {PERSON_STATUS_LABELS[p.status as string] ?? (p.status as string)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">
                    {(p.era as string) ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {formatDateTime(p.created_at as string)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        router.push(`/dashboard/persons/${p.id}/edit`);
                      }}
                      className="rounded-md px-3 py-1 text-xs font-medium text-primary hover:bg-accent"
                    >
                      Edytuj
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex items-center justify-between text-sm">
          <p className="text-muted-foreground">
            Strona {page} z {pages}
          </p>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 text-sm disabled:opacity-40 hover:bg-accent transition-colors"
            >
              <ChevronLeft className="h-4 w-4" /> Wstecz
            </button>
            <button
              disabled={page >= pages}
              onClick={() => setPage((p) => p + 1)}
              className="flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 text-sm disabled:opacity-40 hover:bg-accent transition-colors"
            >
              Dalej <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
