"use client";

import { useQuery } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { ordersApi } from "@/lib/api";

export default function OrdersPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["orders"],
    queryFn: () => ordersApi.list(),
  });

  const orders = data?.data ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Zakony i Zgromadzenia</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          Katalog zakonów męskich i żeńskich Kościoła Katolickiego
        </p>
      </div>

      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold text-muted-foreground uppercase">
            <tr>
              <th className="px-4 py-3">Nazwa</th>
              <th className="px-4 py-3">Skrót</th>
              <th className="px-4 py-3">Charyzmat</th>
              <th className="px-4 py-3">Rok założenia</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {isLoading ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                  Ładowanie...
                </td>
              </tr>
            ) : orders.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                  Brak danych
                </td>
              </tr>
            ) : (
              orders.map((o: Record<string, unknown>) => (
                <tr key={o.id as string} className="hover:bg-muted/30">
                  <td className="px-4 py-3 font-medium text-foreground">
                    {o.name as string}
                    {Boolean(o.name_la) && (
                      <span className="block text-xs text-muted-foreground italic">
                        {String(o.name_la)}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono font-bold text-primary">
                    {Boolean(o.abbreviation) ? String(o.abbreviation) : "—"}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {Boolean(o.charism) ? String(o.charism) : "—"}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {o.founded_year != null ? String(o.founded_year) : "—"}
                  </td>
                  <td className="px-4 py-3">
                    {o.is_suppressed ? (
                      <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-800 dark:bg-red-900/30 dark:text-red-400">
                        Znoszony
                      </span>
                    ) : (
                      <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-800 dark:bg-green-900/30 dark:text-green-400">
                        Aktywny
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
