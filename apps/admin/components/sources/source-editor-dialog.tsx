"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Loader2, Save, X } from "lucide-react";
import { useState, type FormEvent } from "react";
import type {
  AdminDomainDictionary,
  AdminSourceTypeKey,
  AdminSourcesHubDictionary,
} from "@/lib/i18n/types";

type SourceRecord = Record<string, unknown>;
type Draft = Record<string, string | boolean>;

const SOURCE_TYPES: AdminSourceTypeKey[] = [
  "book",
  "article",
  "encyclopedia",
  "website",
  "manuscript",
  "archive",
  "document",
  "hagiography",
  "vita",
  "other",
];

function text(value: unknown): string {
  return value == null ? "" : String(value);
}

function sourceDraft(source: SourceRecord, historical: boolean): Draft {
  const keys = historical
    ? [
        "title",
        "original_title",
        "source_type",
        "repository",
        "call_number",
        "date_range",
        "language",
        "description",
        "digitization_url",
      ]
    : [
        "title",
        "subtitle",
        "source_type",
        "authors",
        "editor",
        "publisher",
        "place_of_publication",
        "year",
        "edition",
        "volume",
        "pages",
        "isbn",
        "issn",
        "doi",
        "url",
        "url_access_date",
        "language",
        "abstract",
        "reliability_score",
        "notes",
      ];
  return {
    ...Object.fromEntries(keys.map((key) => [key, text(source[key])])),
    is_digitized: Boolean(source.is_digitized),
  };
}

function nullable(value: string) {
  const normalized = value.trim();
  return normalized || null;
}

function numberOrNull(value: string) {
  if (!value.trim()) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function validHttpUrl(value: string) {
  if (!value.trim()) return true;
  try {
    const parsed = new URL(value);
    return (parsed.protocol === "http:" || parsed.protocol === "https:") && !parsed.username && !parsed.password;
  } catch {
    return false;
  }
}

function Input({
  label,
  value,
  onChange,
  type = "text",
  required = false,
  invalid = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: "text" | "url" | "number";
  required?: boolean;
  invalid?: boolean;
}) {
  return (
    <label className="space-y-1.5 text-sm font-medium text-foreground">
      <span>{label}{required ? " *" : ""}</span>
      <input
        type={type}
        value={value}
        required={required}
        aria-invalid={invalid}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"
      />
    </label>
  );
}

function Textarea({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="space-y-1.5 text-sm font-medium text-foreground">
      <span>{label}</span>
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="min-h-24 w-full resize-y rounded-lg border border-input bg-background px-3 py-2 text-sm leading-6 outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"
      />
    </label>
  );
}

export function SourceEditorDialog({
  open,
  source,
  historical,
  pending,
  error,
  copy,
  domainCopy,
  onOpenChange,
  onSubmit,
}: {
  open: boolean;
  source: SourceRecord | null;
  historical: boolean;
  pending: boolean;
  error: string | null;
  copy: AdminSourcesHubDictionary["editor"];
  domainCopy: AdminDomainDictionary;
  onOpenChange: (open: boolean) => void;
  onSubmit: (id: string, payload: Record<string, string | number | boolean | null>) => void;
}) {
  const [draft, setDraft] = useState<Draft>(() => sourceDraft(source ?? {}, historical));

  const urlField = historical ? "digitization_url" : "url";
  const urlIsValid = validHttpUrl(String(draft[urlField] ?? ""));
  const update = (key: string, value: string | boolean) => {
    setDraft((current) => ({ ...current, [key]: value }));
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!source?.id || !urlIsValid || !String(draft.title ?? "").trim()) return;

    if (historical) {
      onSubmit(String(source.id), {
        title: nullable(String(draft.title)),
        original_title: nullable(String(draft.original_title)),
        source_type: nullable(String(draft.source_type)),
        repository: nullable(String(draft.repository)),
        call_number: nullable(String(draft.call_number)),
        date_range: nullable(String(draft.date_range)),
        language: nullable(String(draft.language)),
        description: nullable(String(draft.description)),
        digitization_url: nullable(String(draft.digitization_url)),
        is_digitized: Boolean(draft.is_digitized),
      });
      return;
    }

    onSubmit(String(source.id), {
      title: nullable(String(draft.title)),
      subtitle: nullable(String(draft.subtitle)),
      source_type: nullable(String(draft.source_type)),
      authors: nullable(String(draft.authors)),
      editor: nullable(String(draft.editor)),
      publisher: nullable(String(draft.publisher)),
      place_of_publication: nullable(String(draft.place_of_publication)),
      year: numberOrNull(String(draft.year)),
      edition: nullable(String(draft.edition)),
      volume: nullable(String(draft.volume)),
      pages: nullable(String(draft.pages)),
      isbn: nullable(String(draft.isbn)),
      issn: nullable(String(draft.issn)),
      doi: nullable(String(draft.doi)),
      url: nullable(String(draft.url)),
      url_access_date: nullable(String(draft.url_access_date)),
      language: nullable(String(draft.language)),
      abstract: nullable(String(draft.abstract)),
      reliability_score: numberOrNull(String(draft.reliability_score)),
      notes: nullable(String(draft.notes)),
    });
  };

  const input = (key: string, label: string, options?: { type?: "url" | "number"; required?: boolean; invalid?: boolean }) => (
    <Input
      label={label}
      value={String(draft[key] ?? "")}
      onChange={(value) => update(key, value)}
      type={options?.type}
      required={options?.required}
      invalid={options?.invalid}
    />
  );

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/45" />
        <Dialog.Content className="fixed inset-x-4 top-1/2 z-50 max-h-[90vh] w-auto max-w-4xl -translate-y-1/2 overflow-y-auto rounded-2xl border border-border bg-card p-6 shadow-2xl md:left-1/2 md:right-auto md:w-[calc(100%-2rem)] md:-translate-x-1/2">
          <div className="flex items-start justify-between gap-4">
            <div>
              <Dialog.Title className="text-lg font-semibold text-foreground">
                {historical ? copy.editHistoricalTitle : copy.editBibliographyTitle}
              </Dialog.Title>
              <Dialog.Description className="mt-1 text-sm text-muted-foreground">
                {copy.description}
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <button type="button" className="rounded-md p-2 text-muted-foreground hover:bg-accent" aria-label={copy.cancelAction}>
                <X className="h-4 w-4" />
              </button>
            </Dialog.Close>
          </div>

          <form onSubmit={submit} className="mt-6 space-y-5">
            <div className="grid gap-4 md:grid-cols-2">
              {input("title", copy.title, { required: true })}
              <label className="space-y-1.5 text-sm font-medium text-foreground">
                <span>{copy.sourceType}</span>
                <select
                  value={String(draft.source_type ?? "other")}
                  onChange={(event) => update("source_type", event.target.value)}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"
                >
                  {SOURCE_TYPES.map((type) => (
                    <option key={type} value={type}>{domainCopy.sourceTypeLabels[type]}</option>
                  ))}
                </select>
              </label>
              {historical ? (
                <>
                  {input("original_title", copy.originalTitle)}
                  {input("repository", copy.repository)}
                  {input("call_number", copy.callNumber)}
                  {input("date_range", copy.dateRange)}
                  {input("language", copy.language)}
                  {input("digitization_url", copy.digitizationUrl, { type: "url", invalid: !urlIsValid })}
                  <label className="flex items-center gap-2 self-end pb-2 text-sm font-medium text-foreground">
                    <input type="checkbox" checked={Boolean(draft.is_digitized)} onChange={(event) => update("is_digitized", event.target.checked)} className="h-4 w-4 rounded border-input accent-primary" />
                    {copy.digitized}
                  </label>
                  <div className="md:col-span-2"><Textarea label={copy.descriptionField} value={String(draft.description ?? "")} onChange={(value) => update("description", value)} /></div>
                </>
              ) : (
                <>
                  {input("subtitle", copy.subtitle)}
                  {input("authors", copy.authors)}
                  {input("editor", copy.editor)}
                  {input("publisher", copy.publisher)}
                  {input("place_of_publication", copy.placeOfPublication)}
                  {input("year", copy.year, { type: "number" })}
                  {input("edition", copy.edition)}
                  {input("volume", copy.volume)}
                  {input("pages", copy.pages)}
                  {input("isbn", copy.isbn)}
                  {input("issn", copy.issn)}
                  {input("doi", copy.doi)}
                  {input("url", copy.url, { type: "url", invalid: !urlIsValid })}
                  {input("url_access_date", copy.accessDate)}
                  {input("language", copy.language)}
                  {input("reliability_score", copy.reliabilityScore, { type: "number" })}
                  <div className="md:col-span-2"><Textarea label={copy.abstract} value={String(draft.abstract ?? "")} onChange={(value) => update("abstract", value)} /></div>
                  <div className="md:col-span-2"><Textarea label={copy.notes} value={String(draft.notes ?? "")} onChange={(value) => update("notes", value)} /></div>
                </>
              )}
            </div>
            {!urlIsValid && <p role="alert" className="text-sm text-destructive">{copy.invalidUrl}</p>}
            {error && <p role="alert" className="rounded-lg border border-destructive/25 bg-destructive/5 px-4 py-3 text-sm text-destructive">{error}</p>}
            <div className="flex justify-end gap-3 border-t border-border pt-5">
              <Dialog.Close asChild><button type="button" className="rounded-lg border border-border px-4 py-2 text-sm font-semibold hover:bg-accent">{copy.cancelAction}</button></Dialog.Close>
              <button type="submit" disabled={pending || !urlIsValid} className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50">
                {pending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                {copy.saveAction}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
