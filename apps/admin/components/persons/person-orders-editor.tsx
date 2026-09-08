"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Plus, ShieldCheck, Trash2 } from "lucide-react";
import { getApiErrorMessage, ordersApi, personsApi } from "@/lib/api";
import type {
  OrderMembershipType,
  PersonOrderMembership,
  ReligiousOrder,
} from "@/lib/orders";
import { COMMUNITY_TYPE_LABELS } from "@/lib/utils";

const MEMBERSHIP_TYPES: Array<{ value: OrderMembershipType; label: string }> = [
  { value: "member", label: "Członek / członkini" },
  { value: "founder", label: "Założyciel / założycielka" },
  { value: "monk", label: "Mnich" },
  { value: "friar", label: "Zakonnik" },
  { value: "nun", label: "Mniszka" },
  { value: "sister", label: "Siostra zakonna" },
  { value: "lay_member", label: "Członek świecki" },
  { value: "spiritual_patron", label: "Patron duchowy" },
];

const MEMBERSHIP_LABELS = Object.fromEntries(
  MEMBERSHIP_TYPES.map((item) => [item.value, item.label]),
) as Record<OrderMembershipType, string>;

export function PersonOrdersEditor({ personId }: { personId: string }) {
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
      if (!order) throw new Error("Wybierz wspólnotę z listy.");
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

  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-border bg-muted/20 p-5">
        <div className="flex items-start gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"><ShieldCheck className="h-4 w-4" /></span>
          <div>
            <h3 className="text-sm font-semibold">Przynależność do zakonów i zgromadzeń</h3>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">Jedna osoba może należeć do kilku wspólnot. Każda zmiana zostanie zapisana w historii wersji profilu.</p>
          </div>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <label className="space-y-1.5 text-xs font-medium xl:col-span-2">
            <span>Wspólnota</span>
            <select value={orderId} onChange={(event) => setOrderId(event.target.value)} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm">
              <option value="">Wybierz zakon lub zgromadzenie</option>
              {availableOrders.map((order) => <option key={order.id} value={order.id}>{order.name}{order.abbreviation ? ` (${order.abbreviation})` : ""}</option>)}
            </select>
          </label>
          <label className="space-y-1.5 text-xs font-medium">
            <span>Rodzaj przynależności</span>
            <select value={membershipType} onChange={(event) => setMembershipType(event.target.value as OrderMembershipType)} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm">
              {MEMBERSHIP_TYPES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
          </label>
          <label className="flex items-end gap-2 pb-2 text-sm"><input type="checkbox" checked={isFounder} onChange={(event) => setIsFounder(event.target.checked)} /> Założyciel / założycielka</label>
          <label className="space-y-1.5 text-xs font-medium"><span>Wstąpienie</span><input value={entryDate} onChange={(event) => setEntryDate(event.target.value)} placeholder="np. 1894" className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm" /></label>
          <label className="space-y-1.5 text-xs font-medium"><span>Wystąpienie / koniec</span><input value={exitDate} onChange={(event) => setExitDate(event.target.value)} placeholder="np. 1910" className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm" /></label>
          <label className="space-y-1.5 text-xs font-medium xl:col-span-2"><span>Uwagi</span><input value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Funkcja we wspólnocie, gałąź zakonu, uwagi źródłowe…" className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm" /></label>
        </div>
        <div className="mt-4 flex items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">Nie widzisz właściwej wspólnoty? Dodaj ją najpierw w sekcji „Zakony”.</p>
          <button type="button" disabled={!orderId || addMutation.isPending} onClick={() => addMutation.mutate()} className="inline-flex h-9 shrink-0 items-center gap-2 rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground disabled:opacity-50">
            {addMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />} Przypisz
          </button>
        </div>
        {addMutation.isError && <p role="alert" className="mt-3 text-xs text-rose-600">{getApiErrorMessage(addMutation.error)}</p>}
      </div>

      <div className="space-y-2">
        <h3 className="text-sm font-semibold">Przypisane wspólnoty ({memberships.length})</h3>
        {memberships.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border p-7 text-center text-sm text-muted-foreground">Ta osoba nie ma jeszcze udokumentowanej przynależności zakonnej.</div>
        ) : memberships.map((membership) => (
          <article key={membership.order.id} className="flex flex-col gap-3 rounded-lg border border-border p-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-medium">{membership.order.name}{membership.order.abbreviation ? <span className="ml-2 text-xs font-semibold text-primary">{membership.order.abbreviation}</span> : null}</p>
              <p className="mt-1 text-xs text-muted-foreground">{COMMUNITY_TYPE_LABELS[membership.order.community_type] ?? membership.order.community_type} · {MEMBERSHIP_LABELS[membership.membership_type] ?? membership.membership_type}{membership.entry_date ? ` · od ${membership.entry_date}` : ""}{membership.exit_date ? ` do ${membership.exit_date}` : ""}</p>
              {membership.notes && <p className="mt-1 text-xs text-muted-foreground">{membership.notes}</p>}
            </div>
            <button type="button" disabled={removeMutation.isPending} onClick={() => {
              if (window.confirm(`Usunąć powiązanie z „${membership.order.name}”?`)) removeMutation.mutate(membership);
            }} className="inline-flex h-8 items-center gap-1 self-start rounded-md border border-rose-200 px-2.5 text-xs text-rose-700 hover:bg-rose-50 disabled:opacity-50 dark:border-rose-900/60 dark:text-rose-300 dark:hover:bg-rose-950/30"><Trash2 className="h-3.5 w-3.5" /> Usuń powiązanie</button>
          </article>
        ))}
        {removeMutation.isError && <p role="alert" className="text-xs text-rose-600">{getApiErrorMessage(removeMutation.error)}</p>}
      </div>
    </div>
  );
}
