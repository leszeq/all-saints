"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ExternalLink,
  History,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Star,
  UsersRound,
} from "lucide-react";
import { ordersApi } from "@/lib/api";
import {
  COMMUNITY_TYPE_LABELS,
  formatDateTime,
  ORDER_CHARISM_LABELS,
  cn,
} from "@/lib/utils";

type ApiRecord = Record<string, unknown>;
type OrderFilter = "all" | "featured" | "active" | "suppressed" | "members";

const filters: Array<{ key: OrderFilter; label: string }> = [
  { key: "all", label: "Wszystkie" },
  { key: "featured", label: "Wyróżnione" },
  { key: "active", label: "Aktywne" },
  { key: "suppressed", label: "Zniesione" },
  { key: "members", label: "Z osobami" },
];

function valueText(value: unknown, fallback = "—") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
}: {
  label: string;
  value: number;
  detail: string;
  icon: typeof ShieldCheck;
}) {
  return (
    <article className="admin-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-muted-foreground">{label}</p>
          <p className="mt-2 text-3xl font-semibold tracking-tight">{value.toLocaleString("pl-PL")}</p>
        </div>
        <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Icon className="h-4 w-4" />
        </span>
      </div>
      <p className="mt-3 text-[11px] text-muted-foreground">{detail}</p>
    </article>
  );
}

function EmptyRow({ colSpan, label }: { colSpan: number; label: string }) {
  return (
    <tr>
      <td colSpan={colSpan} className="px-4 py-8 text-center text-sm text-muted-foreground">
        {label}
      </td>
    </tr>
  );
}

export default function OrdersPage() {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<OrderFilter>("all");

  const ordersQuery = useQuery({
    queryKey: ["orders", search],
    queryFn: () => ordersApi.list({ search: search || undefined }),
  });

  const orders = useMemo(
    () => (ordersQuery.data?.data ?? []) as ApiRecord[],
    [ordersQuery.data?.data],
  );
  const filteredOrders = useMemo(
    () =>
      orders.filter((order) => {
        if (filter === "featured") return Boolean(order.is_featured);
        if (filter === "active") return !order.is_suppressed;
        if (filter === "suppressed") return Boolean(order.is_suppressed);
        if (filter === "members") return Number(order.member_count ?? 0) > 0;
        return true;
      }),
    [orders, filter],
  );
  const activeCount = orders.filter((order) => !order.is_suppressed).length;
  const featuredCount = orders.filter((order) => order.is_featured).length;
  const memberCount = orders.reduce((sum, order) => sum + Number(order.member_count ?? 0), 0);
  const documentedCount = orders.filter((order) => order.history || order.mission || order.description).length;

  return (
    <div className="mx-auto max-w-[1500px] space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="admin-label">Źródła i dane</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Zakony i zgromadzenia</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Wspólnoty religijne, rodziny duchowe i powiązania ze świętymi.
          </p>
        </div>
        <button
          type="button"
          onClick={() => ordersQuery.refetch()}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-border px-4 text-sm font-semibold hover:bg-accent"
        >
          <RefreshCw className="h-4 w-4" /> Odśwież dane
        </button>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Podsumowanie zakonów">
        <MetricCard
          label="Wspólnoty"
          value={orders.length}
          detail={`${activeCount.toLocaleString("pl-PL")} aktywnych w katalogu`}
          icon={ShieldCheck}
        />
        <MetricCard
          label="Wyróżnione"
          value={featuredCount}
          detail="Widoczne jako ważne rodziny duchowe"
          icon={Star}
        />
        <MetricCard
          label="Powiązane osoby"
          value={memberCount}
          detail="Święci i błogosławieni przypisani do wspólnot"
          icon={UsersRound}
        />
        <MetricCard
          label="Opracowane opisy"
          value={documentedCount}
          detail="Wspólnoty z historią, misją lub opisem"
          icon={History}
        />
      </section>

      <section className="admin-card overflow-hidden">
        <div className="flex flex-col gap-4 border-b border-border px-5 py-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-wrap gap-1 rounded-lg border border-border bg-background p-1">
            {filters.map((item) => (
              <button
                key={item.key}
                type="button"
                onClick={() => setFilter(item.key)}
                className={cn(
                  "h-9 rounded-md px-3 text-sm font-medium transition-colors",
                  filter === item.key
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {item.label}
              </button>
            ))}
          </div>
          <div className="relative w-full xl:max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Szukaj po nazwie, skrócie lub duchowości..."
              className="w-full rounded-lg border border-input bg-background py-2 pl-9 pr-3 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-[1180px] w-full text-sm">
            <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold uppercase text-muted-foreground">
              <tr>
                <th className="px-4 py-3">Wspólnota</th>
                <th className="px-4 py-3">Typ</th>
                <th className="px-4 py-3">Charyzmat</th>
                <th className="px-4 py-3">Założenie</th>
                <th className="px-4 py-3">Misja / historia</th>
                <th className="px-4 py-3">Osoby</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Aktualizacja</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {ordersQuery.isLoading ? (
                <EmptyRow colSpan={8} label="Ładowanie wspólnot..." />
              ) : filteredOrders.length === 0 ? (
                <EmptyRow colSpan={8} label="Brak wspólnot dla tych kryteriów" />
              ) : (
                filteredOrders.map((order) => (
                  <tr key={String(order.id)} className="hover:bg-muted/30">
                    <td className="px-4 py-3">
                      <div className="flex items-start gap-3">
                        <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                          <ShieldCheck className="h-4 w-4" />
                        </span>
                        <div className="min-w-0">
                          <p className="font-medium text-foreground">
                            {valueText(order.name)}
                            {order.is_featured ? (
                              <Sparkles className="ml-1.5 inline h-3.5 w-3.5 text-primary" />
                            ) : null}
                          </p>
                          <p className="mt-1 text-xs italic text-muted-foreground">{valueText(order.name_la)}</p>
                          <p className="mt-1 text-xs font-semibold text-primary">{valueText(order.abbreviation)}</p>
                          {Boolean(order.website_url) && (
                            <a
                              href={String(order.website_url)}
                              target="_blank"
                              rel="noreferrer"
                              className="mt-1 inline-flex max-w-80 items-center gap-1 text-xs text-primary hover:underline"
                            >
                              <ExternalLink className="h-3 w-3 shrink-0" />
                              <span className="truncate">{String(order.website_url)}</span>
                            </a>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      <p>{COMMUNITY_TYPE_LABELS[String(order.community_type)] ?? valueText(order.community_type)}</p>
                      <p className="mt-1 text-xs">{valueText(order.spiritual_family)}</p>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {ORDER_CHARISM_LABELS[String(order.charism)] ?? valueText(order.charism)}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      <p>{valueText(order.founded_year)}</p>
                      <p className="mt-1 text-xs">{valueText(order.founder_name)}</p>
                    </td>
                    <td className="max-w-md px-4 py-3 text-muted-foreground">
                      <p className="line-clamp-2 text-xs leading-5">
                        {valueText(order.mission || order.history || order.description, "Opis nieuzupełniony")}
                      </p>
                      {Boolean(order.source_url) && (
                        <a
                          href={String(order.source_url)}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-1 inline-flex items-center gap-1 text-xs text-primary hover:underline"
                        >
                          <ExternalLink className="h-3 w-3" /> źródło
                        </a>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-semibold text-primary">
                        {Number(order.member_count ?? 0).toLocaleString("pl-PL")}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {order.is_suppressed ? (
                        <span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-medium text-rose-800 dark:bg-rose-900/30 dark:text-rose-300">
                          Zniesiony
                        </span>
                      ) : (
                        <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300">
                          Aktywny
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">
                      {formatDateTime(order.updated_at as string)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
