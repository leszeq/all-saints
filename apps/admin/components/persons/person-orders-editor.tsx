"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Plus, ShieldCheck, Trash2 } from "lucide-react";
import { getApiErrorMessage, ordersApi, personsApi } from "@/lib/api";
import type {
  AdminCommunityTypeKey,
  AdminDomainDictionary,
  AdminOrderMembershipTypeKey,
  AdminPersonEditorDictionary,
} from "@/lib/i18n/types";
import type {
  OrderMembershipType,
  PersonOrderMembership,
  ReligiousOrder,
} from "@/lib/orders";
interface PersonOrdersEditorProps {
  copy: AdminPersonEditorDictionary["orders"];
  domainCopy: AdminDomainDictionary;
  locale: string;
  personId: string;
}

export function PersonOrdersEditor({
  copy,
  domainCopy,
  locale,
  personId,
}: PersonOrdersEditorProps) {
  const queryClient = useQueryClient();
  const [orderId, setOrderId] = useState("");
  const [membershipType, setMembershipType] = useState<OrderMembershipType>("member");
  const [entryDate, setEntryDate] = useState("");
  const [exitDate, setExitDate] = useState("");
  const [notes, setNotes] = useState("");
  const [isFounder, setIsFounder] = useState(false);

  const personQuery = useQuery({
    queryKey: ["person", personId],
    queryFn: () => personsApi.get(personId),
  });
  const ordersQuery = useQuery({
    queryKey: ["orders", "management"],
    queryFn: () => ordersApi.management(),
  });
  const memberships = useMemo(
    () => (personQuery.data?.data.orders ?? []) as PersonOrderMembership[],
    [personQuery.data?.data.orders],
  );
  const availableOrders = useMemo(() => {
    const linked = new Set(memberships.map((membership) => membership.order.id));
    return (ordersQuery.data?.data ?? []).filter(
      (order: ReligiousOrder) => !order.is_suppressed && !linked.has(order.id),
    );
  }, [memberships, ordersQuery.data?.data]);

  const invalidateRelations = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["person", personId] }),
      queryClient.invalidateQueries({ queryKey: ["persons"] }),
      queryClient.invalidateQueries({ queryKey: ["orders"] }),
      queryClient.invalidateQueries({ queryKey: ["person-versions", personId] }),
      queryClient.invalidateQueries({ queryKey: ["editorial"] }),
    ]);
  };
  const addMutation = useMutation({
    mutationFn: () => {
      const order = availableOrders.find((item) => item.id === orderId);
      if (!order) throw new Error(copy.selectRequired);
      return ordersApi.addMember(order.id, {
        person_id: personId,
        entry_date: entryDate.trim() || null,
        exit_date: exitDate.trim() || null,
        is_founder: isFounder || membershipType === "founder",
        membership_type: membershipType,
        notes: notes.trim() || null,
      });
    },
    onSuccess: async () => {
      setOrderId("");
      setMembershipType("member");
      setEntryDate("");
      setExitDate("");
      setNotes("");
      setIsFounder(false);
      await invalidateRelations();
    },
  });
  const removeMutation = useMutation({
    mutationFn: (membership: PersonOrderMembership) =>
      ordersApi.removeMember(membership.order.id, personId),
    onSuccess: invalidateRelations,
  });

  if (personQuery.isLoading || ordersQuery.isLoading) {
    return <div className="flex min-h-40 items-center justify-center"><Loader2 className="h-5 w-5 animate-spin text-primary" /></div>;
  }

  const numberFormatter = new Intl.NumberFormat(locale);

  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-border bg-muted/20 p-5">
        <div className="flex items-start gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"><ShieldCheck className="h-4 w-4" /></span>
          <div>
            <h3 className="text-sm font-semibold">{copy.title}</h3>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">{copy.description}</p>
          </div>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <label className="space-y-1.5 text-xs font-medium xl:col-span-2">
            <span>{copy.community}</span>
            <select value={orderId} onChange={(event) => setOrderId(event.target.value)} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm">
              <option value="">{copy.selectCommunity}</option>
              {availableOrders.map((order) => <option key={order.id} value={order.id}>{order.name}{order.abbreviation ? ` (${order.abbreviation})` : ""}</option>)}
            </select>
          </label>
          <label className="space-y-1.5 text-xs font-medium">
            <span>{copy.membershipType}</span>
            <select value={membershipType} onChange={(event) => setMembershipType(event.target.value as OrderMembershipType)} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm">
              {Object.entries(domainCopy.orderMembershipTypeLabels).map(([value, label]) => (
                <option key={value} value={value as AdminOrderMembershipTypeKey}>{label}</option>
              ))}
            </select>
          </label>
          <label className="flex items-end gap-2 pb-2 text-sm"><input type="checkbox" checked={isFounder} onChange={(event) => setIsFounder(event.target.checked)} /> {copy.founder}</label>
          <label className="space-y-1.5 text-xs font-medium"><span>{copy.entry}</span><input value={entryDate} onChange={(event) => setEntryDate(event.target.value)} placeholder={copy.entryPlaceholder} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm" /></label>
          <label className="space-y-1.5 text-xs font-medium"><span>{copy.exit}</span><input value={exitDate} onChange={(event) => setExitDate(event.target.value)} placeholder={copy.exitPlaceholder} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm" /></label>
          <label className="space-y-1.5 text-xs font-medium xl:col-span-2"><span>{copy.notes}</span><input value={notes} onChange={(event) => setNotes(event.target.value)} placeholder={copy.notesPlaceholder} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm" /></label>
        </div>
        <div className="mt-4 flex items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">{copy.catalogueHint}</p>
          <button type="button" disabled={!orderId || addMutation.isPending} onClick={() => addMutation.mutate()} className="inline-flex h-9 shrink-0 items-center gap-2 rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground disabled:opacity-50">
            {addMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />} {copy.assignAction}
          </button>
        </div>
        {addMutation.isError && <p role="alert" className="mt-3 text-xs text-rose-600">{getApiErrorMessage(addMutation.error)}</p>}
      </div>

      <div className="space-y-2">
        <h3 className="text-sm font-semibold">{copy.assignedPrefix} ({numberFormatter.format(memberships.length)})</h3>
        {memberships.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border p-7 text-center text-sm text-muted-foreground">{copy.empty}</div>
        ) : memberships.map((membership) => (
          <article key={membership.order.id} className="flex flex-col gap-3 rounded-lg border border-border p-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-medium">{membership.order.name}{membership.order.abbreviation ? <span className="ml-2 text-xs font-semibold text-primary">{membership.order.abbreviation}</span> : null}</p>
              <p className="mt-1 text-xs text-muted-foreground">{domainCopy.communityTypeLabels[membership.order.community_type as AdminCommunityTypeKey] ?? membership.order.community_type} · {domainCopy.orderMembershipTypeLabels[membership.membership_type as AdminOrderMembershipTypeKey] ?? membership.membership_type}{membership.entry_date ? ` · ${copy.fromPrefix} ${membership.entry_date}` : ""}{membership.exit_date ? ` ${copy.toPrefix} ${membership.exit_date}` : ""}</p>
              {membership.notes && <p className="mt-1 text-xs text-muted-foreground">{membership.notes}</p>}
            </div>
            <button type="button" disabled={removeMutation.isPending} onClick={() => {
              if (window.confirm(`${copy.removeConfirmPrefix}${membership.order.name}${copy.removeConfirmSuffix}`)) removeMutation.mutate(membership);
            }} className="inline-flex h-8 items-center gap-1 self-start rounded-md border border-rose-200 px-2.5 text-xs text-rose-700 hover:bg-rose-50 disabled:opacity-50 dark:border-rose-900/60 dark:text-rose-300 dark:hover:bg-rose-950/30"><Trash2 className="h-3.5 w-3.5" /> {copy.removeAction}</button>
          </article>
        ))}
        {removeMutation.isError && <p role="alert" className="text-xs text-rose-600">{getApiErrorMessage(removeMutation.error)}</p>}
      </div>
    </div>
  );
}
