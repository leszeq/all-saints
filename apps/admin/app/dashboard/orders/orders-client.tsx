"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ExternalLink,
  History,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Star,
  Pencil,
  Plus,
  Trash2,
  UsersRound,
} from "lucide-react";
import { OrderDialog } from "@/components/orders/order-dialog";
import { useAdminSystemCopy } from "@/components/admin-system-copy-context";
import { ordersApi } from "@/lib/api";
import { formatAdminApiError } from "@/lib/i18n/api-errors";
import { formatAdminDateTime } from "@/lib/i18n/format";
import type {
  AdminCommunityTypeKey,
  AdminDomainDictionary,
  AdminOrderCharismKey,
  AdminOrdersDictionary,
} from "@/lib/i18n/types";
import type { ReligiousOrder, ReligiousOrderPayload } from "@/lib/orders";
import { useAuthStore } from "@/lib/store/auth";
import { cn } from "@/lib/utils";

type OrderFilter = "all" | "featured" | "active" | "suppressed" | "members";

const FILTER_KEYS: OrderFilter[] = ["all", "featured", "active", "suppressed", "members"];

function valueText(value: unknown, fallback = "—") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
  locale,
}: {
  label: string;
  value: number;
  detail: string;
  icon: typeof ShieldCheck;
  locale: string;
}) {
  return (
    <article className="admin-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-muted-foreground">{label}</p>
          <p className="mt-2 text-3xl font-semibold tracking-tight">{new Intl.NumberFormat(locale).format(value)}</p>
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

interface OrdersClientProps {
  copy: AdminOrdersDictionary;
  domainCopy: AdminDomainDictionary;
  locale: string;
}

export function OrdersClient({ copy, domainCopy, locale }: OrdersClientProps) {
  const queryClient = useQueryClient();
  const { apiErrors } = useAdminSystemCopy();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<OrderFilter>("all");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editedOrder, setEditedOrder] = useState<ReligiousOrder | null>(null);
  const canCreate = useAuthStore((state) => state.hasPermission("orders:create"));
  const canUpdate = useAuthStore((state) => state.hasPermission("orders:update"));
  const canDelete = useAuthStore((state) => state.hasPermission("orders:delete"));

  const ordersQuery = useQuery({
    queryKey: ["orders", search],
    queryFn: () => ordersApi.management({ search: search || undefined }),
  });

  const orders = useMemo(
    () => ordersQuery.data?.data ?? [],
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

  const saveMutation = useMutation({
    mutationFn: (payload: ReligiousOrderPayload) =>
      editedOrder
        ? ordersApi.update(editedOrder.id, payload)
        : ordersApi.create(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["orders"] });
      setDialogOpen(false);
      setEditedOrder(null);
    },
  });
  const deleteMutation = useMutation({
    mutationFn: (order: ReligiousOrder) => ordersApi.delete(order.id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
  });

  const openCreate = () => {
    setEditedOrder(null);
    saveMutation.reset();
    setDialogOpen(true);
  };
  const openEdit = (order: ReligiousOrder) => {
    setEditedOrder(order);
    saveMutation.reset();
    setDialogOpen(true);
  };

  return (
    <div className="mx-auto max-w-[1500px] space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="admin-label">{copy.kicker}</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">{copy.title}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {copy.description}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => ordersQuery.refetch()}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-border px-4 text-sm font-semibold hover:bg-accent"
          >
            <RefreshCw className="h-4 w-4" /> {copy.refreshAction}
          </button>
          {canCreate && (
            <button type="button" onClick={openCreate} className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground">
              <Plus className="h-4 w-4" /> {copy.addAction}
            </button>
          )}
        </div>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label={copy.summaryAriaLabel}>
        <MetricCard
          label={copy.metrics.communities}
          value={orders.length}
          detail={`${new Intl.NumberFormat(locale).format(activeCount)} ${copy.metrics.activeSuffix}`}
          icon={ShieldCheck}
          locale={locale}
        />
        <MetricCard
          label={copy.metrics.featured}
          value={featuredCount}
          detail={copy.metrics.featuredDetail}
          icon={Star}
          locale={locale}
        />
        <MetricCard
          label={copy.metrics.members}
          value={memberCount}
          detail={copy.metrics.membersDetail}
          icon={UsersRound}
          locale={locale}
        />
        <MetricCard
          label={copy.metrics.documented}
          value={documentedCount}
          detail={copy.metrics.documentedDetail}
          icon={History}
          locale={locale}
        />
      </section>

      <section className="admin-card overflow-hidden">
        <div className="flex flex-col gap-4 border-b border-border px-5 py-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-wrap gap-1 rounded-lg border border-border bg-background p-1">
            {FILTER_KEYS.map((filterKey) => (
              <button
                key={filterKey}
                type="button"
                onClick={() => setFilter(filterKey)}
                className={cn(
                  "h-9 rounded-md px-3 text-sm font-medium transition-colors",
                  filter === filterKey
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {copy.filters[filterKey]}
              </button>
            ))}
          </div>
          <div className="relative w-full xl:max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              aria-label={copy.searchAriaLabel}
              placeholder={copy.searchPlaceholder}
              className="w-full rounded-lg border border-input bg-background py-2 pl-9 pr-3 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-[1180px] w-full text-sm">
            <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold uppercase text-muted-foreground">
              <tr>
                <th className="px-4 py-3">{copy.table.community}</th>
                <th className="px-4 py-3">{copy.table.type}</th>
                <th className="px-4 py-3">{copy.table.charism}</th>
                <th className="px-4 py-3">{copy.table.foundation}</th>
                <th className="px-4 py-3">{copy.table.missionHistory}</th>
                <th className="px-4 py-3">{copy.table.persons}</th>
                <th className="px-4 py-3">{copy.table.status}</th>
                <th className="px-4 py-3">{copy.table.updated}</th>
                {(canUpdate || canDelete) && <th className="px-4 py-3 text-right">{copy.table.actions}</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {ordersQuery.isLoading ? (
                <EmptyRow colSpan={canUpdate || canDelete ? 9 : 8} label={copy.states.loading} />
              ) : filteredOrders.length === 0 ? (
                <EmptyRow colSpan={canUpdate || canDelete ? 9 : 8} label={copy.states.empty} />
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
                      <p>{domainCopy.communityTypeLabels[order.community_type as AdminCommunityTypeKey] ?? valueText(order.community_type)}</p>
                      <p className="mt-1 text-xs">{valueText(order.spiritual_family)}</p>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {domainCopy.orderCharismLabels[order.charism as AdminOrderCharismKey] ?? valueText(order.charism)}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      <p>{valueText(order.founded_year)}</p>
                      <p className="mt-1 text-xs">{valueText(order.founder_name)}</p>
                    </td>
                    <td className="max-w-md px-4 py-3 text-muted-foreground">
                      <p className="line-clamp-2 text-xs leading-5">
                        {valueText(order.mission || order.history || order.description, copy.labels.descriptionMissing)}
                      </p>
                      {Boolean(order.source_url) && (
                        <a
                          href={String(order.source_url)}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-1 inline-flex items-center gap-1 text-xs text-primary hover:underline"
                        >
                          <ExternalLink className="h-3 w-3" /> {copy.labels.source}
                        </a>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-semibold text-primary">
                        {new Intl.NumberFormat(locale).format(Number(order.member_count ?? 0))}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {order.is_suppressed ? (
                        <span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-medium text-rose-800 dark:bg-rose-900/30 dark:text-rose-300">
                          {copy.labels.suppressed}
                        </span>
                      ) : (
                        <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300">
                          {copy.labels.active}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">
                      {formatAdminDateTime(order.updated_at as string, locale)}
                    </td>
                    {(canUpdate || canDelete) && (
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-1.5">
                          {canUpdate && (
                            <button type="button" onClick={() => openEdit(order)} className="inline-flex h-8 items-center gap-1 rounded-md border border-border px-2.5 text-xs font-medium hover:bg-muted">
                              <Pencil className="h-3.5 w-3.5" /> {copy.actions.edit}
                            </button>
                          )}
                          {canDelete && (
                            <button
                              type="button"
                              disabled={deleteMutation.isPending || order.member_count > 0}
                              onClick={() => {
                                if (window.confirm(`${copy.actions.deleteConfirmPrefix}${order.name}${copy.actions.deleteConfirmSuffix}`)) {
                                  deleteMutation.mutate(order);
                                }
                              }}
                              className="inline-flex h-8 items-center rounded-md border border-rose-200 px-2 text-rose-700 hover:bg-rose-50 disabled:opacity-50 dark:border-rose-900/60 dark:text-rose-300 dark:hover:bg-rose-950/30"
                              aria-label={`${copy.actions.deleteAriaPrefix} ${order.name}`}
                              title={order.member_count > 0 ? copy.actions.deleteBlockedTitle : copy.actions.deleteTitle}
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          )}
                        </div>
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {dialogOpen && (
        <OrderDialog
          open
          order={editedOrder}
          pending={saveMutation.isPending}
          error={saveMutation.isError ? formatAdminApiError(saveMutation.error, apiErrors) : null}
          copy={copy.dialog}
          domainCopy={domainCopy}
          onOpenChange={(open) => {
            setDialogOpen(open);
            if (!open) setEditedOrder(null);
          }}
          onSubmit={(payload) => saveMutation.mutate(payload)}
        />
      )}
    </div>
  );
}
