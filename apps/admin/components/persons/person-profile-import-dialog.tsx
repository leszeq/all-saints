"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, CheckCircle2, FileJson, Loader2, Upload, X } from "lucide-react";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAdminSystemCopy } from "@/components/admin-system-copy-context";
import { personsApi } from "@/lib/api";
import { formatAdminApiError } from "@/lib/i18n/api-errors";
import type {
  AdminDomainDictionary,
  AdminPersonsDictionary,
} from "@/lib/i18n/types";

interface ProfileDocument {
  schema_version: number;
  profile: {
    canonical_name?: string;
    person_type?: string;
    status?: string;
  };
  orders?: unknown[];
  feasts?: unknown[];
  sources?: unknown[];
}

interface ValidationResult {
  can_import: boolean;
  errors: string[];
  warnings: string[];
  normalized_document: ProfileDocument;
  existing_person: {
    id: string;
    canonical_name: string;
    slug: string;
    status: string;
    version: number;
  } | null;
}

type OverwriteTarget = { overwrite_person_id: string; expected_version: number };

export function PersonProfileImportDialog({
  open,
  onOpenChange,
  copy,
  domainCopy,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  copy: AdminPersonsDictionary["importDialog"];
  domainCopy: AdminDomainDictionary;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { apiErrors } = useAdminSystemCopy();
  const inputRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState("");
  const [document, setDocument] = useState<ProfileDocument | null>(null);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [overwriteTarget, setOverwriteTarget] = useState<OverwriteTarget | undefined>();
  const requestGeneration = useRef(0);

  const validateMutation = useMutation({
    mutationFn: async ({ payload, target, generation }: {
      payload: ProfileDocument; target?: OverwriteTarget; generation: number;
    }) => ({ ...(await personsApi.validateProfileImport(payload, target)), generation }),
    onSuccess: ({ data, generation }) => {
      if (generation === requestGeneration.current) setValidation(data as ValidationResult);
    },
  });
  const importMutation = useMutation({
    mutationFn: () => personsApi.importProfile(document!, overwriteTarget),
    onSuccess: async ({ data }) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["persons"] }),
        queryClient.invalidateQueries({ queryKey: ["editorial"] }),
        queryClient.invalidateQueries({ queryKey: ["orders"] }),
        queryClient.invalidateQueries({ queryKey: ["calendar"] }),
        queryClient.invalidateQueries({ queryKey: ["person", data.id] }),
        queryClient.invalidateQueries({ queryKey: ["person-versions", data.id] }),
        queryClient.invalidateQueries({ queryKey: ["person-sources", data.id] }),
      ]);
      onOpenChange(false);
      router.push(`/dashboard/persons/${data.id}`);
    },
  });

  const reset = () => {
    requestGeneration.current += 1;
    setOverwriteTarget(undefined);
    setFileName("");
    setDocument(null);
    setValidation(null);
    setFileError(null);
    validateMutation.reset();
    importMutation.reset();
    if (inputRef.current) inputRef.current.value = "";
  };

  const readFile = async (file?: File) => {
    reset();
    const generation = requestGeneration.current;
    if (!file) return;
    setFileName(file.name);
    if (file.size > 5 * 1024 * 1024) {
      setFileError(copy.maxSizeError);
      return;
    }
    try {
      const parsed = JSON.parse(await file.text()) as ProfileDocument;
      if (generation !== requestGeneration.current) return;
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        throw new Error(copy.invalidRootError);
      }
      setDocument(parsed);
      validateMutation.mutate({ payload: parsed, generation });
    } catch (error) {
      setFileError(
        error instanceof Error
          ? `${copy.invalidJsonPrefix}: ${error.message}`
          : copy.readError,
      );
    }
  };

  const changeOverwrite = (checked: boolean) => {
    if (!document || !validation?.existing_person) return;
    const target = checked ? {
      overwrite_person_id: validation.existing_person.id,
      expected_version: validation.existing_person.version,
    } : undefined;
    setOverwriteTarget(target);
    importMutation.reset();
    validateMutation.mutate({ payload: document, target, generation: ++requestGeneration.current });
  };

  return (
    <Dialog.Root open={open} onOpenChange={(nextOpen) => { if (importMutation.isPending) return; onOpenChange(nextOpen); if (!nextOpen) reset(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-slate-950/55 backdrop-blur-[2px]" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 max-h-[90vh] w-[calc(100%-2rem)] max-w-2xl -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-xl border border-border bg-card p-6 shadow-2xl focus:outline-none">
          <Dialog.Title className="pr-12 text-xl font-semibold">{copy.title}</Dialog.Title>
          <Dialog.Description className="mt-1 text-sm leading-6 text-muted-foreground">
            {copy.description}
          </Dialog.Description>
          <Dialog.Close className="absolute right-4 top-4 flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-muted" aria-label={copy.closeAriaLabel}><X className="h-4 w-4" /></Dialog.Close>

          <button type="button" disabled={validateMutation.isPending || importMutation.isPending} onClick={() => inputRef.current?.click()} className="mt-6 flex w-full flex-col items-center justify-center rounded-xl border border-dashed border-primary/35 bg-primary/5 px-6 py-10 text-center hover:bg-primary/10 disabled:opacity-50">
            <span className="flex h-11 w-11 items-center justify-center rounded-full bg-primary/10 text-primary"><Upload className="h-5 w-5" /></span>
            <span className="mt-3 text-sm font-semibold">{fileName || copy.chooseFile}</span>
            <span className="mt-1 text-xs text-muted-foreground">{copy.fileHint}</span>
          </button>
          <input ref={inputRef} type="file" accept="application/json,.json" className="sr-only" onChange={(event) => { void readFile(event.target.files?.[0]); }} />

          {(validateMutation.isPending) && <div className="mt-5 flex items-center gap-2 rounded-lg border border-border bg-muted/30 p-4 text-sm"><Loader2 className="h-4 w-4 animate-spin text-primary" /> {copy.validating}</div>}
          {(fileError || validateMutation.isError) && <div role="alert" className="mt-5 flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /><span>{fileError ?? formatAdminApiError(validateMutation.error, apiErrors, { invalidData: copy.invalidFormat })}</span></div>}

          {validation && document && (
            <div className="mt-5 space-y-4">
              <div className="rounded-xl border border-border p-4">
                <div className="flex items-start gap-3">
                  <FileJson className="mt-0.5 h-5 w-5 text-primary" />
                  <div>
                    <p className="font-semibold">{validation.normalized_document.profile.canonical_name ?? copy.profileWithoutName}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {copy.typePrefix}{" "}
                      {domainCopy.personTypeLabels[
                        validation.normalized_document.profile.person_type as keyof typeof domainCopy.personTypeLabels
                      ] ?? validation.normalized_document.profile.person_type ?? "—"}{" "}
                      · {copy.schemaVersionPrefix} {validation.normalized_document.schema_version}
                    </p>
                  </div>
                </div>
                <dl className="mt-4 grid grid-cols-3 gap-3 text-center">
                  <div className="rounded-lg bg-muted/35 p-3"><dt className="text-[10px] uppercase text-muted-foreground">{copy.counts.orders}</dt><dd className="mt-1 text-lg font-semibold">{validation.normalized_document.orders?.length ?? 0}</dd></div>
                  <div className="rounded-lg bg-muted/35 p-3"><dt className="text-[10px] uppercase text-muted-foreground">{copy.counts.feasts}</dt><dd className="mt-1 text-lg font-semibold">{validation.normalized_document.feasts?.length ?? 0}</dd></div>
                  <div className="rounded-lg bg-muted/35 p-3"><dt className="text-[10px] uppercase text-muted-foreground">{copy.counts.sources}</dt><dd className="mt-1 text-lg font-semibold">{validation.normalized_document.sources?.length ?? 0}</dd></div>
                </dl>
              </div>

              {validation.warnings.length > 0 && <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200"><p className="font-semibold">{copy.warningsTitle}</p><ul className="mt-2 list-disc space-y-1 pl-5">{validation.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>}
              {validation.errors.length > 0 && <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200"><p className="font-semibold">{copy.errorsTitle}</p><ul className="mt-2 list-disc space-y-1 pl-5">{validation.errors.map((error) => <li key={error}>{error}</li>)}</ul></div>}
              {validation.existing_person && (
                <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-100">
                  <p className="font-semibold">{validation.existing_person.canonical_name}</p>
                  <p className="mt-1 text-xs">/{validation.existing_person.slug} · {domainCopy.personStatusLabels[validation.existing_person.status as keyof typeof domainCopy.personStatusLabels] ?? validation.existing_person.status}</p>
                  <p className="mt-2">{copy.overwriteDescription}</p>
                  {validation.existing_person.status === "published" && <p className="mt-2 font-semibold">{copy.overwritePublishedWarning}</p>}
                  <label className="mt-3 flex items-start gap-2 font-semibold">
                    <input type="checkbox" className="mt-1" checked={!!overwriteTarget} disabled={validateMutation.isPending || importMutation.isPending} onChange={(event) => changeOverwrite(event.target.checked)} />
                    {copy.overwriteConfirm}
                  </label>
                </div>
              )}
              {validation.can_import && !validateMutation.isPending && !validateMutation.isError && <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-200"><CheckCircle2 className="h-4 w-4" /> {overwriteTarget ? copy.overwriteReady : copy.ready}</div>}
            </div>
          )}

          {importMutation.isError && <p role="alert" className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">{formatAdminApiError(importMutation.error, apiErrors)}</p>}
          <div className="mt-6 flex justify-end gap-3 border-t border-border pt-4">
            <Dialog.Close className="h-10 rounded-lg border border-border px-4 text-sm font-medium hover:bg-muted">{copy.cancelAction}</Dialog.Close>
            <button type="button" disabled={!validation?.can_import || validateMutation.isPending || validateMutation.isError || importMutation.isPending} onClick={() => importMutation.mutate()} className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50">
              {importMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileJson className="h-4 w-4" />} {overwriteTarget ? copy.overwriteAction : copy.importAction}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
