"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Check, Loader2, Sparkles, X } from "lucide-react";

import { useAdminSystemCopy } from "@/components/admin-system-copy-context";
import { aiApi } from "@/lib/api";
import type { AiSuggestionItem } from "@/lib/ai";
import { formatAdminApiError } from "@/lib/i18n/api-errors";
import type { AdminAiSuggestionsDictionary } from "@/lib/i18n/types";
import { cn } from "@/lib/utils";

function suggestedTags(item: AiSuggestionItem) {
  if (item.kind !== "tags") return [];
  return (item.suggested_value ?? "")
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

interface DecisionDialogProps {
  item: AiSuggestionItem;
  copy: AdminAiSuggestionsDictionary["decisionDialog"];
  onOpenChange: (open: boolean) => void;
  onComplete: (message: string) => void;
}

export function AiSuggestionDecisionDialog({
  item,
  copy,
  onOpenChange,
  onComplete,
}: DecisionDialogProps) {
  const queryClient = useQueryClient();
  const { apiErrors } = useAdminSystemCopy();
  const availableTags = suggestedTags(item);
  const [summary, setSummary] = useState(
    item.kind === "summary" ? item.suggested_value ?? "" : "",
  );
  const [selectedTags, setSelectedTags] = useState<string[]>(availableTags);
  const [rejectionNote, setRejectionNote] = useState("");
  const [validationError, setValidationError] = useState("");

  const mutation = useMutation({
    mutationFn: (action: "accept" | "reject") => {
      if (item.kind !== "summary" && item.kind !== "tags") {
        throw new Error("Unsupported AI suggestion");
      }
      return aiApi.decideSuggestion(item.kind, item.person_id, {
        action,
        expected_version: item.person_version,
        ...(action === "accept" && item.kind === "summary"
          ? { value: summary.trim() }
          : {}),
        ...(action === "accept" && item.kind === "tags"
          ? { selected_tags: selectedTags }
          : {}),
        ...(action === "reject" ? { note: rejectionNote.trim() } : {}),
      });
    },
    onSuccess: async (_response, action) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["ai"] }),
        queryClient.invalidateQueries({ queryKey: ["persons"] }),
        queryClient.invalidateQueries({ queryKey: ["person", item?.person_id] }),
        queryClient.invalidateQueries({ queryKey: ["person-versions", item?.person_id] }),
        queryClient.invalidateQueries({ queryKey: ["taxonomy", "tags"] }),
      ]);
      onComplete(action === "accept" ? copy.acceptedMessage : copy.rejectedMessage);
      onOpenChange(false);
    },
  });

  const decide = (action: "accept" | "reject") => {
    setValidationError("");
    if (action === "accept" && item?.kind === "summary" && !summary.trim()) {
      setValidationError(copy.summaryRequired);
      return;
    }
    if (action === "accept" && item?.kind === "tags" && selectedTags.length === 0) {
      setValidationError(copy.tagsRequired);
      return;
    }
    if (action === "reject" && !rejectionNote.trim()) {
      setValidationError(copy.rejectionRequired);
      return;
    }
    mutation.mutate(action);
  };

  const apiError = mutation.error ? formatAdminApiError(mutation.error, apiErrors) : "";
  const busyAction = mutation.isPending ? mutation.variables : null;

  return (
    <Dialog.Root
      open
      onOpenChange={(open) => {
        if (!mutation.isPending) onOpenChange(open);
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-[2px]" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 max-h-[92vh] w-[calc(100%-2rem)] max-w-5xl -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-2xl border border-border bg-card p-6 shadow-2xl focus:outline-none">
          <div className="pr-12">
            <p className="admin-label">AI · {item.person_name}</p>
            <Dialog.Title className="mt-1 text-xl font-semibold">
              {item.kind === "tags" ? copy.tagsTitle : copy.summaryTitle}
            </Dialog.Title>
            <Dialog.Description className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
              {copy.description}
            </Dialog.Description>
          </div>
          <Dialog.Close
            className="absolute right-4 top-4 flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label={copy.closeAriaLabel}
          >
            <X className="h-4 w-4" />
          </Dialog.Close>

          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <section className="rounded-xl border border-border bg-muted/30 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                {copy.currentLabel}
              </p>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-foreground/80">
                {item.current_value || copy.currentEmpty}
              </p>
            </section>

            <section className="rounded-xl border border-primary/25 bg-primary/[0.035] p-4">
              {item.kind === "tags" ? (
                <>
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-primary">
                    {copy.tagsLabel}
                  </p>
                  <p className="mt-2 text-xs leading-5 text-muted-foreground">{copy.tagsHelp}</p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {availableTags.map((tag) => {
                      const checked = selectedTags.includes(tag);
                      return (
                        <button
                          key={tag}
                          type="button"
                          aria-pressed={checked}
                          onClick={() =>
                            setSelectedTags((current) =>
                              checked
                                ? current.filter((itemValue) => itemValue !== tag)
                                : [...current, tag],
                            )
                          }
                          className={cn(
                            "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
                            checked
                              ? "border-primary bg-primary text-primary-foreground"
                              : "border-border bg-background hover:border-primary/50",
                          )}
                        >
                          {checked && <Check className="h-3 w-3" />} {tag}
                        </button>
                      );
                    })}
                  </div>
                </>
              ) : (
                <>
                  <label
                    htmlFor="ai-summary-decision"
                    className="text-[11px] font-semibold uppercase tracking-wider text-primary"
                  >
                    {copy.summaryLabel}
                  </label>
                  <p className="mt-2 text-xs leading-5 text-muted-foreground">{copy.summaryHelp}</p>
                  <textarea
                    id="ai-summary-decision"
                    value={summary}
                    onChange={(event) => setSummary(event.target.value)}
                    rows={9}
                    className="mt-4 w-full resize-y rounded-lg border border-input bg-background p-3 text-sm leading-6 outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                  />
                </>
              )}
            </section>
          </div>

          <section className="mt-4 rounded-xl border border-border p-4">
            <label htmlFor="ai-rejection-note" className="text-xs font-semibold">
              {copy.rejectionLabel}
            </label>
            <textarea
              id="ai-rejection-note"
              value={rejectionNote}
              onChange={(event) => setRejectionNote(event.target.value)}
              placeholder={copy.rejectionPlaceholder}
              rows={2}
              className="mt-2 w-full resize-y rounded-lg border border-input bg-background p-3 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
            <p className="mt-2 text-[11px] text-muted-foreground">{copy.rejectionHelp}</p>
          </section>

          {(validationError || apiError) && (
            <div className="mt-4 flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              {validationError || apiError}
            </div>
          )}

          <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <button
              type="button"
              disabled={mutation.isPending}
              onClick={() => onOpenChange(false)}
              className="h-10 rounded-lg border border-border px-4 text-sm font-medium hover:bg-muted disabled:opacity-50"
            >
              {copy.cancelAction}
            </button>
            <button
              type="button"
              disabled={mutation.isPending}
              onClick={() => decide("reject")}
              className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-rose-300 px-4 text-sm font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-50 dark:border-rose-900 dark:text-rose-300 dark:hover:bg-rose-950/30"
            >
              {busyAction === "reject" && <Loader2 className="h-4 w-4 animate-spin" />}
              {busyAction === "reject" ? copy.savingAction : copy.rejectAction}
            </button>
            <button
              type="button"
              disabled={mutation.isPending}
              onClick={() => decide("accept")}
              className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {busyAction === "accept" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              {busyAction === "accept" ? copy.savingAction : copy.acceptAction}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
