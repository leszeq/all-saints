"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Check, Loader2, Plus, Save, Send, X } from "lucide-react";
import { useState, type FormEvent, type InputHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { focusFirstDialogControl } from "@/lib/focus";
import type { AdminDictionariesDictionary } from "@/lib/i18n/types";
import type {
  ConceptAliasKind,
  ConceptAliasPayload,
  PatronageConcept,
  PatronageConceptPayload,
  PatronageConceptReviewPayload,
} from "@/lib/taxonomy";

type ConceptCopy = AdminDictionariesDictionary["conceptEditor"];

type ConceptDraft = {
  patronage_type: string;
  name_pl: string;
  name_en: string;
  description: string;
};

type AliasDraft = {
  value: string;
  language_code: string;
  alias_kind: ConceptAliasKind;
  source_reference: string;
};

const EMPTY_DRAFT: ConceptDraft = {
  patronage_type: "",
  name_pl: "",
  name_en: "",
  description: "",
};

const EMPTY_ALIAS: AliasDraft = {
  value: "",
  language_code: "pl",
  alias_kind: "common",
  source_reference: "",
};

const ALIAS_KINDS: ConceptAliasKind[] = ["official", "common", "historical", "local"];

function inputClassName() {
  return "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/15";
}

function Input({ label, ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  return (
    <label className="space-y-1.5 text-sm font-medium text-foreground">
      <span>{label}</span>
      <input {...props} className={inputClassName()} />
    </label>
  );
}

function Textarea({ label, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string }) {
  return (
    <label className="space-y-1.5 text-sm font-medium text-foreground">
      <span>{label}</span>
      <textarea {...props} className={`${inputClassName()} resize-y leading-6`} />
    </label>
  );
}

function draftFromConcept(concept: PatronageConcept | null): ConceptDraft {
  if (!concept) return { ...EMPTY_DRAFT };
  return {
    patronage_type: concept.patronage_type,
    name_pl: concept.name_pl,
    name_en: concept.name_en ?? "",
    description: concept.description ?? "",
  };
}

export function PatronageConceptDialog({
  open,
  concept,
  pending,
  aliasPending,
  workflowPending,
  error,
  copy,
  canCreateAlias,
  canSubmit,
  canReview,
  onOpenChange,
  onSubmit,
  onAddAlias,
  onTransition,
}: {
  open: boolean;
  concept: PatronageConcept | null;
  pending: boolean;
  aliasPending: boolean;
  workflowPending: boolean;
  error: string | null;
  copy: ConceptCopy;
  canCreateAlias: boolean;
  canSubmit: boolean;
  canReview: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (payload: PatronageConceptPayload) => void;
  onAddAlias: (payload: ConceptAliasPayload) => void;
  onTransition: (payload: PatronageConceptReviewPayload) => void;
}) {
  const [draft, setDraft] = useState<ConceptDraft>(() => draftFromConcept(concept));
  const [aliasDraft, setAliasDraft] = useState<AliasDraft>({ ...EMPTY_ALIAS });
  const [reviewNote, setReviewNote] = useState("");

  const updateDraft = <Key extends keyof ConceptDraft>(key: Key, value: ConceptDraft[Key]) => {
    setDraft((current) => ({ ...current, [key]: value }));
  };

  const updateAlias = <Key extends keyof AliasDraft>(key: Key, value: AliasDraft[Key]) => {
    setAliasDraft((current) => ({ ...current, [key]: value }));
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit({
      patronage_type: draft.patronage_type.trim(),
      name_pl: draft.name_pl.trim(),
      name_en: draft.name_en.trim() || null,
      description: draft.description.trim() || null,
    });
  };

  const addAlias = () => {
    onAddAlias({
      value: aliasDraft.value.trim(),
      language_code: aliasDraft.language_code.trim().toLowerCase(),
      alias_kind: aliasDraft.alias_kind,
      source_reference: aliasDraft.source_reference.trim() || null,
    });
  };

  const rejectDisabled = workflowPending || !reviewNote.trim();

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-slate-950/55 backdrop-blur-[2px]" />
        <Dialog.Content
          onOpenAutoFocus={focusFirstDialogControl}
          className="fixed left-1/2 top-1/2 z-50 max-h-[92vh] w-[calc(100%-2rem)] max-w-3xl -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-xl border border-border bg-card p-6 shadow-2xl focus:outline-none"
        >
          <Dialog.Title className="pr-12 text-xl font-semibold">
            {concept ? copy.editTitle : copy.createTitle}
          </Dialog.Title>
          <Dialog.Description className="mt-1 text-sm text-muted-foreground">
            {copy.description}
          </Dialog.Description>
          <Dialog.Close className="absolute right-4 top-4 flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-muted" aria-label={copy.closeAriaLabel}>
            <X className="h-4 w-4" />
          </Dialog.Close>

          <form onSubmit={submit} className="mt-6 space-y-6">
            <fieldset className="grid gap-4 md:grid-cols-2">
              <legend className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground md:col-span-2">{copy.sections.identity}</legend>
              <Input required minLength={2} maxLength={50} label={copy.fields.patronageType} placeholder={copy.placeholders.patronageType} value={draft.patronage_type} onChange={(event) => updateDraft("patronage_type", event.target.value)} />
              <Input required minLength={2} maxLength={500} label={copy.fields.namePl} placeholder={copy.placeholders.namePl} value={draft.name_pl} onChange={(event) => updateDraft("name_pl", event.target.value)} />
              <Input maxLength={500} label={copy.fields.nameEn} placeholder={copy.placeholders.nameEn} value={draft.name_en} onChange={(event) => updateDraft("name_en", event.target.value)} />
              <Textarea label={copy.fields.description} placeholder={copy.placeholders.description} rows={3} value={draft.description} onChange={(event) => updateDraft("description", event.target.value)} />
            </fieldset>

            {concept && (
              <section className="space-y-4 border-t border-border pt-5">
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{copy.sections.aliases}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">{concept.aliases.length ? concept.aliases.map((alias) => `${alias.value} (${copy.aliasKinds[alias.alias_kind]})`).join(" · ") : copy.noAliases}</p>
                </div>
                {canCreateAlias && (
                  <div className="grid gap-3 rounded-lg border border-border bg-muted/20 p-4 md:grid-cols-2">
                    <Input required minLength={2} maxLength={500} label={copy.fields.aliasValue} placeholder={copy.placeholders.aliasValue} value={aliasDraft.value} onChange={(event) => updateAlias("value", event.target.value)} />
                    <Input required minLength={2} maxLength={10} label={copy.fields.aliasLanguage} placeholder={copy.placeholders.aliasLanguage} value={aliasDraft.language_code} onChange={(event) => updateAlias("language_code", event.target.value)} />
                    <label className="space-y-1.5 text-sm font-medium text-foreground">
                      <span>{copy.fields.aliasKind}</span>
                      <select value={aliasDraft.alias_kind} onChange={(event) => updateAlias("alias_kind", event.target.value as ConceptAliasKind)} className={inputClassName()}>
                        {ALIAS_KINDS.map((kind) => <option key={kind} value={kind}>{copy.aliasKinds[kind]}</option>)}
                      </select>
                    </label>
                    <Input label={copy.fields.aliasSource} placeholder={copy.placeholders.aliasSource} value={aliasDraft.source_reference} onChange={(event) => updateAlias("source_reference", event.target.value)} />
                    <div className="md:col-span-2">
                      <button disabled={aliasPending} type="button" onClick={addAlias} className="inline-flex h-9 items-center gap-2 rounded-lg border border-border px-3 text-sm font-semibold hover:bg-muted disabled:opacity-60">
                        {aliasPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                        {copy.addAliasAction}
                      </button>
                    </div>
                  </div>
                )}
              </section>
            )}

            {concept && (
              <section className="space-y-3 border-t border-border pt-5">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{copy.sections.workflow}</h3>
                <p className="text-sm text-muted-foreground">{copy.statusPrefix} <strong className="text-foreground">{concept.status}</strong> · {copy.assignmentsPrefix} {concept.assignment_count}</p>
                {concept.status === "review" && canReview && (
                  <Textarea label={copy.fields.reviewNote} placeholder={copy.placeholders.reviewNote} rows={3} value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} />
                )}
                <div className="flex flex-wrap gap-2">
                  {concept.status === "draft" && canSubmit && (
                    <button type="button" disabled={workflowPending} onClick={() => onTransition({ target_status: "review" })} className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground disabled:opacity-60">
                      {workflowPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                      {copy.submitAction}
                    </button>
                  )}
                  {concept.status === "review" && canReview && (
                    <>
                      <button type="button" disabled={workflowPending} onClick={() => onTransition({ target_status: "approved", note: reviewNote.trim() || null })} className="inline-flex h-10 items-center gap-2 rounded-lg bg-emerald-600 px-4 text-sm font-semibold text-white disabled:opacity-60">
                        {workflowPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                        {copy.approveAction}
                      </button>
                      <button type="button" disabled={rejectDisabled} onClick={() => onTransition({ target_status: "rejected", note: reviewNote.trim() })} className="inline-flex h-10 items-center gap-2 rounded-lg border border-rose-300 px-4 text-sm font-semibold text-rose-700 disabled:opacity-50 dark:border-rose-800 dark:text-rose-300">
                        <X className="h-4 w-4" /> {copy.rejectAction}
                      </button>
                    </>
                  )}
                </div>
              </section>
            )}

            {error && <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">{error}</p>}
            <div className="flex justify-end gap-3 border-t border-border pt-4">
              <Dialog.Close type="button" className="h-10 rounded-lg border border-border px-4 text-sm font-medium hover:bg-muted">{copy.cancelAction}</Dialog.Close>
              <button disabled={pending} type="submit" className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground disabled:opacity-60">
                {pending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                {concept ? copy.saveAction : copy.createAction}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
