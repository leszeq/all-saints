"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Loader2, Save, X } from "lucide-react";
import {
  useState,
  type FormEvent,
  type InputHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";
import type {
  CommunityType,
  OrderCharism,
  ReligiousOrder,
  ReligiousOrderPayload,
} from "@/lib/orders";

type OrderDraft = Omit<ReligiousOrderPayload, "founded_year" | "suppressed_year" | "papal_approval_year" | "sort_order"> & {
  founded_year: string;
  suppressed_year: string;
  papal_approval_year: string;
  sort_order: string;
};

const EMPTY_DRAFT: OrderDraft = {
  slug: "",
  name: "",
  name_la: "",
  name_local: "",
  abbreviation: "",
  community_type: "religious_order",
  spiritual_family: "",
  founded_year: "",
  founder_name: "",
  suppressed_year: "",
  charism: null,
  description: "",
  description_en: "",
  history: "",
  mission: "",
  motto: "",
  website_url: "",
  source_title: "",
  source_url: "",
  papal_approval_year: "",
  is_suppressed: false,
  is_featured: false,
  sort_order: "0",
};

const COMMUNITY_TYPES: Array<{ value: CommunityType; label: string }> = [
  { value: "religious_order", label: "Zakon" },
  { value: "congregation", label: "Zgromadzenie zakonne" },
  { value: "monastic_family", label: "Rodzina monastyczna" },
  { value: "society_apostolic_life", label: "Stowarzyszenie życia apostolskiego" },
  { value: "secular_institute", label: "Instytut świecki" },
  { value: "federation", label: "Federacja" },
  { value: "other", label: "Inna wspólnota" },
];

const CHARISMS: Array<{ value: OrderCharism; label: string }> = [
  { value: "contemplative", label: "Kontemplacyjny" },
  { value: "apostolic", label: "Apostolski" },
  { value: "mendicant", label: "Żebraczy" },
  { value: "monastic", label: "Monastyczny" },
  { value: "missionary", label: "Misyjny" },
  { value: "educational", label: "Edukacyjny" },
  { value: "charitable", label: "Charytatywny" },
  { value: "military", label: "Rycerski" },
  { value: "other", label: "Inny" },
];

function nullableText(value: string | null) {
  const normalized = value?.trim();
  return normalized ? normalized : null;
}

function nullableNumber(value: string) {
  if (!value.trim()) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function draftFromOrder(order: ReligiousOrder | null): OrderDraft {
  if (!order) return { ...EMPTY_DRAFT };
  return {
    slug: order.slug,
    name: order.name,
    name_la: order.name_la ?? "",
    name_local: order.name_local ?? "",
    abbreviation: order.abbreviation ?? "",
    community_type: order.community_type,
    spiritual_family: order.spiritual_family ?? "",
    founded_year: order.founded_year?.toString() ?? "",
    founder_name: order.founder_name ?? "",
    suppressed_year: order.suppressed_year?.toString() ?? "",
    charism: order.charism,
    description: order.description ?? "",
    description_en: order.description_en ?? "",
    history: order.history ?? "",
    mission: order.mission ?? "",
    motto: order.motto ?? "",
    website_url: order.website_url ?? "",
    source_title: order.source_title ?? "",
    source_url: order.source_url ?? "",
    papal_approval_year: order.papal_approval_year?.toString() ?? "",
    is_suppressed: order.is_suppressed,
    is_featured: order.is_featured,
    sort_order: order.sort_order.toString(),
  };
}

function slugify(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 500);
}

function Input({ label, ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  return (
    <label className="space-y-1.5 text-sm font-medium text-foreground">
      <span>{label}</span>
      <input {...props} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/15" />
    </label>
  );
}

function Textarea({ label, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string }) {
  return (
    <label className="space-y-1.5 text-sm font-medium text-foreground">
      <span>{label}</span>
      <textarea {...props} className="w-full resize-y rounded-lg border border-input bg-background px-3 py-2 text-sm leading-6 outline-none focus:border-primary focus:ring-2 focus:ring-primary/15" />
    </label>
  );
}

export function OrderDialog({
  open,
  order,
  pending,
  error,
  onOpenChange,
  onSubmit,
}: {
  open: boolean;
  order: ReligiousOrder | null;
  pending: boolean;
  error: string | null;
  onOpenChange: (open: boolean) => void;
  onSubmit: (payload: ReligiousOrderPayload) => void;
}) {
  const [draft, setDraft] = useState<OrderDraft>(() => draftFromOrder(order));
  const [slugWasEdited, setSlugWasEdited] = useState(Boolean(order));

  const update = <Key extends keyof OrderDraft>(key: Key, value: OrderDraft[Key]) => {
    setDraft((current) => ({ ...current, [key]: value }));
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit({
      ...draft,
      slug: draft.slug.trim(),
      name: draft.name.trim(),
      name_la: nullableText(draft.name_la),
      name_local: nullableText(draft.name_local),
      abbreviation: nullableText(draft.abbreviation),
      spiritual_family: nullableText(draft.spiritual_family),
      founded_year: nullableNumber(draft.founded_year),
      founder_name: nullableText(draft.founder_name),
      suppressed_year: nullableNumber(draft.suppressed_year),
      description: nullableText(draft.description),
      description_en: nullableText(draft.description_en),
      history: nullableText(draft.history),
      mission: nullableText(draft.mission),
      motto: nullableText(draft.motto),
      website_url: nullableText(draft.website_url),
      source_title: nullableText(draft.source_title),
      source_url: nullableText(draft.source_url),
      papal_approval_year: nullableNumber(draft.papal_approval_year),
      sort_order: nullableNumber(draft.sort_order) ?? 0,
    });
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-slate-950/55 backdrop-blur-[2px]" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 max-h-[92vh] w-[calc(100%-2rem)] max-w-5xl -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-xl border border-border bg-card p-6 shadow-2xl focus:outline-none">
          <Dialog.Title className="pr-12 text-xl font-semibold">
            {order ? "Edytuj wspólnotę" : "Dodaj zakon lub zgromadzenie"}
          </Dialog.Title>
          <Dialog.Description className="mt-1 text-sm text-muted-foreground">
            Uzupełnij dane identyfikacyjne, historię i misję wspólnoty. Pola oznaczone * są wymagane.
          </Dialog.Description>
          <Dialog.Close className="absolute right-4 top-4 flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-muted" aria-label="Zamknij">
            <X className="h-4 w-4" />
          </Dialog.Close>

          <form onSubmit={submit} className="mt-6 space-y-6">
            <fieldset className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              <legend className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Tożsamość wspólnoty</legend>
              <Input required label="Nazwa *" value={draft.name} onChange={(event) => {
                const name = event.target.value;
                update("name", name);
                if (!slugWasEdited) update("slug", slugify(name));
              }} />
              <Input required minLength={2} pattern="[a-z0-9-]+" label="Slug *" value={draft.slug} onChange={(event) => { setSlugWasEdited(true); update("slug", event.target.value); }} />
              <Input label="Skrót" maxLength={20} value={draft.abbreviation ?? ""} onChange={(event) => update("abbreviation", event.target.value)} />
              <Input label="Nazwa łacińska" value={draft.name_la ?? ""} onChange={(event) => update("name_la", event.target.value)} />
              <Input label="Nazwa lokalna" value={draft.name_local ?? ""} onChange={(event) => update("name_local", event.target.value)} />
              <label className="space-y-1.5 text-sm font-medium">
                <span>Typ wspólnoty</span>
                <select value={draft.community_type} onChange={(event) => update("community_type", event.target.value as CommunityType)} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm">
                  {COMMUNITY_TYPES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                </select>
              </label>
              <Input label="Rodzina duchowa" placeholder="np. franciszkańska" value={draft.spiritual_family ?? ""} onChange={(event) => update("spiritual_family", event.target.value)} />
              <label className="space-y-1.5 text-sm font-medium">
                <span>Charyzmat</span>
                <select value={draft.charism ?? ""} onChange={(event) => update("charism", (event.target.value || null) as OrderCharism | null)} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm">
                  <option value="">Nie określono</option>
                  {CHARISMS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                </select>
              </label>
              <Input label="Kolejność" type="number" value={draft.sort_order} onChange={(event) => update("sort_order", event.target.value)} />
            </fieldset>

            <fieldset className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <legend className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Historia instytucjonalna</legend>
              <Input label="Rok założenia" type="number" value={draft.founded_year} onChange={(event) => update("founded_year", event.target.value)} />
              <Input label="Założyciel / założycielka" value={draft.founder_name ?? ""} onChange={(event) => update("founder_name", event.target.value)} />
              <Input label="Rok zatwierdzenia papieskiego" type="number" value={draft.papal_approval_year} onChange={(event) => update("papal_approval_year", event.target.value)} />
              <Input label="Rok zniesienia" type="number" value={draft.suppressed_year} onChange={(event) => update("suppressed_year", event.target.value)} />
            </fieldset>

            <fieldset className="grid gap-4 md:grid-cols-2">
              <legend className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Opis redakcyjny</legend>
              <Textarea label="Krótki opis" rows={4} value={draft.description ?? ""} onChange={(event) => update("description", event.target.value)} />
              <Textarea label="Misja" rows={4} value={draft.mission ?? ""} onChange={(event) => update("mission", event.target.value)} />
              <Textarea label="Historia" rows={7} value={draft.history ?? ""} onChange={(event) => update("history", event.target.value)} />
              <div className="space-y-4">
                <Textarea label="Opis angielski" rows={3} value={draft.description_en ?? ""} onChange={(event) => update("description_en", event.target.value)} />
                <Input label="Dewiza" value={draft.motto ?? ""} onChange={(event) => update("motto", event.target.value)} />
              </div>
            </fieldset>

            <fieldset className="grid gap-4 md:grid-cols-2">
              <legend className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Źródła i publikacja</legend>
              <Input label="Strona internetowa" type="url" value={draft.website_url ?? ""} onChange={(event) => update("website_url", event.target.value)} />
              <Input label="Tytuł źródła" value={draft.source_title ?? ""} onChange={(event) => update("source_title", event.target.value)} />
              <Input label="Link do źródła" type="url" value={draft.source_url ?? ""} onChange={(event) => update("source_url", event.target.value)} />
              <div className="flex flex-wrap items-center gap-5 pt-7">
                <label className="inline-flex items-center gap-2 text-sm"><input type="checkbox" checked={draft.is_featured} onChange={(event) => update("is_featured", event.target.checked)} /> Wyróżniona</label>
                <label className="inline-flex items-center gap-2 text-sm"><input type="checkbox" checked={draft.is_suppressed} onChange={(event) => update("is_suppressed", event.target.checked)} /> Wspólnota zniesiona</label>
              </div>
            </fieldset>

            {error && <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">{error}</p>}
            <div className="flex justify-end gap-3 border-t border-border pt-4">
              <Dialog.Close type="button" className="h-10 rounded-lg border border-border px-4 text-sm font-medium hover:bg-muted">Anuluj</Dialog.Close>
              <button disabled={pending} type="submit" className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground disabled:opacity-60">
                {pending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                {order ? "Zapisz zmiany" : "Dodaj wspólnotę"}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
