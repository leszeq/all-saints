"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Globe, Plus, Search } from "lucide-react";
import { geographyApi } from "@/lib/api";

export default function CountriesPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["countries", search],
    queryFn: () => geographyApi.countries({ search: search || undefined }),
  });

  const countries = data?.data ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Państwa</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Słownik państw i regionów historycznych
          </p>
        </div>
      </div>

      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          type="text"
          placeholder="Szukaj państwa..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-lg border border-input bg-background py-2 pl-9 pr-3 text-sm focus:border-primary focus:outline-none"
        />
      </div>

      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold text-muted-foreground uppercase">
            <tr>
              <th className="px-4 py-3">Nazwa (PL)</th>
              <th className="px-4 py-3">Nazwa (EN)</th>
              <th className="px-4 py-3">ISO2 / ISO3</th>
              <th className="px-4 py-3">Kontynent</th>
              <th className="px-4 py-3">Typ</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {isLoading ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                  Ładowanie...
                </td>
              </tr>
            ) : countries.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                  Brak danych
                </td>
              </tr>
            ) : (
              countries.map((c: Record<string, unknown>) => (
                <tr key={c.id as string} className="hover:bg-muted/30">
                  <td className="px-4 py-3 font-medium text-foreground">
                    <span className="mr-2">{c.flag_emoji as string ?? "🌐"}</span>
                    {c.name_pl as string}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {c.name_en as string}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                    {c.iso_code_alpha2 as string ?? "—"} / {c.iso_code_alpha3 as string ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {c.continent as string ?? "—"}
                  </td>
                  <td className="px-4 py-3">
                    {c.is_historical ? (
                      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800 dark:bg-amber-900/30 dark:text-amber-400">
                        Historyczny
                      </span>
                    ) : (
                      <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-800 dark:bg-green-900/30 dark:text-green-400">
                        Współczesny
                      </span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
