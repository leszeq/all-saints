"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  Download,
  FileJson,
  Loader2,
  Upload,
  X,
} from "lucide-react";
import { useRef, useState } from "react";
import { useAdminSystemCopy } from "@/components/admin-system-copy-context";
import { ordersApi } from "@/lib/api";
import { formatAdminApiError } from "@/lib/i18n/api-errors";
import type { AdminOrdersDictionary } from "@/lib/i18n/types";
import type {
  ReligiousOrderImportDocument,
  ReligiousOrderImportValidationResult,
} from "@/lib/orders";

const TEMPLATE: ReligiousOrderImportDocument = {
  schema_version: 1,
  orders: [
    {
      slug: "wspolnota-testowa-import-json",
      name: "Wspólnota testowa importu JSON",
      name_la: "Communitas Probatoria Importationis JSON",
      abbreviation: "TEST",
      community_type: "other",
      spiritual_family: "testowa",
      founded_year: 2026,
      suppressed_year: 2026,
      charism: "other",
      description: "Fikcyjny rekord przeznaczony wyłącznie do sprawdzenia importu.",
      history: "Wspólnota nie istnieje i nie powinna być publikowana jako dane merytoryczne.",
      mission: "Weryfikacja wersjonowanego kontraktu importu zakonów.",
      source_title: "Dokumentacja testowa projektu all-saints",
      source_url: "https://example.org/all-saints/orders-import-test",
      is_featured: false,
      is_suppressed: true,
      sort_order: 0,
    },
  ],
};

export function OrderImportDialog({
  open,
  onOpenChange,
  onImported,
  copy,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImported: (count: number) => void;
  copy: AdminOrdersDictionary["importDialog"];
}) {
  const queryClient = useQueryClient();
  const { apiErrors } = useAdminSystemCopy();
  const inputRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState("");
  const [document, setDocument] = useState<ReligiousOrderImportDocument | null>(null);
  const [validation, setValidation] =
    useState<ReligiousOrderImportValidationResult | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);

  const validateMutation = useMutation({
    mutationFn: (payload: ReligiousOrderImportDocument) =>
      ordersApi.validateImport(payload),
    onSuccess: ({ data }) => setValidation(data),
  });
  const importMutation = useMutation({
    mutationFn: () => ordersApi.importBatch(validation!.normalized_document),
    onSuccess: async ({ data }) => {
      await queryClient.invalidateQueries({ queryKey: ["orders"] });
      onImported(data.length);
      onOpenChange(false);
    },
  });

  const reset = () => {
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
    if (!file) return;
    setFileName(file.name);
    if (file.size > 5 * 1024 * 1024) {
      setFileError(copy.maxSizeError);
      return;
    }
    try {
      const parsed = JSON.parse(await file.text()) as ReligiousOrderImportDocument;
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        throw new Error(copy.invalidRootError);
      }
      setDocument(parsed);
      validateMutation.mutate(parsed);
    } catch (error) {
      setFileError(
        error instanceof Error
          ? `${copy.invalidJsonPrefix}: ${error.message}`
          : copy.readError,
      );
    }
  };

  const downloadTemplate = () => {
    const blob = new Blob([JSON.stringify(TEMPLATE, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = window.document.createElement("a");
    link.href = url;
    link.download = "wzor-importu-zakonow.json";
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(nextOpen) => {
        onOpenChange(nextOpen);
        if (!nextOpen) reset();
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-slate-950/55 backdrop-blur-[2px]" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 max-h-[90vh] w-[calc(100%-2rem)] max-w-2xl -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-xl border border-border bg-card p-6 shadow-2xl focus:outline-none">
          <Dialog.Title className="pr-12 text-xl font-semibold">
            {copy.title}
          </Dialog.Title>
          <Dialog.Description className="mt-1 text-sm leading-6 text-muted-foreground">
            {copy.description}
          </Dialog.Description>
          <Dialog.Close
            className="absolute right-4 top-4 flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-muted"
            aria-label={copy.closeAriaLabel}
          >
            <X className="h-4 w-4" />
          </Dialog.Close>

          <div className="mt-6 grid gap-3 sm:grid-cols-[1fr_auto]">
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="flex min-h-36 flex-col items-center justify-center rounded-xl border border-dashed border-primary/35 bg-primary/5 px-6 py-7 text-center hover:bg-primary/10"
            >
              <span className="flex h-11 w-11 items-center justify-center rounded-full bg-primary/10 text-primary">
                <Upload className="h-5 w-5" />
              </span>
              <span className="mt-3 text-sm font-semibold">
                {fileName || copy.chooseFile}
              </span>
              <span className="mt-1 text-xs text-muted-foreground">
                {copy.fileHint}
              </span>
            </button>
            <button
              type="button"
              onClick={downloadTemplate}
              className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl border border-border px-4 text-sm font-semibold hover:bg-muted sm:min-h-36 sm:max-w-40 sm:flex-col"
            >
              <Download className="h-5 w-5 text-primary" />
              {copy.downloadTemplate}
            </button>
          </div>
          <input
            ref={inputRef}
            type="file"
            accept="application/json,.json"
            className="sr-only"
            onChange={(event) => {
              void readFile(event.target.files?.[0]);
            }}
          />

          {validateMutation.isPending && (
            <div className="mt-5 flex items-center gap-2 rounded-lg border border-border bg-muted/30 p-4 text-sm">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              {copy.validating}
            </div>
          )}
          {(fileError || validateMutation.isError) && (
            <div
              role="alert"
              className="mt-5 flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                {fileError ??
                  formatAdminApiError(validateMutation.error, apiErrors, {
                    invalidData: copy.invalidFormat,
                  })}
              </span>
            </div>
          )}

          {validation && document && (
            <div className="mt-5 space-y-4">
              <div className="rounded-xl border border-border p-4">
                <div className="flex items-start gap-3">
                  <FileJson className="mt-0.5 h-5 w-5 text-primary" />
                  <div>
                    <p className="font-semibold">{copy.batchTitle}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {copy.schemaVersionPrefix}: {validation.normalized_document.schema_version}
                    </p>
                  </div>
                </div>
                <div className="mt-4 rounded-lg bg-muted/35 p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    {copy.communitiesCount}
                  </p>
                  <p className="mt-1 text-2xl font-semibold">
                    {validation.normalized_document.orders.length}
                  </p>
                  <ul className="mt-3 space-y-1 text-xs text-muted-foreground">
                    {validation.normalized_document.orders.slice(0, 5).map((order) => (
                      <li key={order.slug}>
                        <span className="font-medium text-foreground">{order.name}</span>
                        {" · "}{order.slug}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {validation.warnings.length > 0 && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
                  <p className="font-semibold">{copy.warningsTitle}</p>
                  <ul className="mt-2 list-disc space-y-1 pl-5">
                    {validation.warnings.map((warning) => (
                      <li key={warning}>{warning}</li>
                    ))}
                  </ul>
                </div>
              )}
              {validation.errors.length > 0 && (
                <div
                  role="alert"
                  className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200"
                >
                  <p className="font-semibold">{copy.errorsTitle}</p>
                  <ul className="mt-2 list-disc space-y-1 pl-5">
                    {validation.errors.map((error) => (
                      <li key={error}>{error}</li>
                    ))}
                  </ul>
                </div>
              )}
              {validation.can_import && (
                <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-200">
                  <CheckCircle2 className="h-4 w-4" /> {copy.ready}
                </div>
              )}
            </div>
          )}

          {importMutation.isError && (
            <p
              role="alert"
              className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200"
            >
              {formatAdminApiError(importMutation.error, apiErrors)}
            </p>
          )}
          <div className="mt-6 flex justify-end gap-3 border-t border-border pt-4">
            <Dialog.Close className="h-10 rounded-lg border border-border px-4 text-sm font-medium hover:bg-muted">
              {copy.cancelAction}
            </Dialog.Close>
            <button
              type="button"
              disabled={!validation?.can_import || importMutation.isPending}
              onClick={() => importMutation.mutate()}
              className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50"
            >
              {importMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <FileJson className="h-4 w-4" />
              )}
              {importMutation.isPending ? copy.importingAction : copy.importAction}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
