"use client";

import { useAdminSystemCopy } from "@/components/admin-system-copy-context";

export default function Loading() {
  const copy = useAdminSystemCopy().loading;

  return (
    <div className="flex min-h-screen items-center justify-center bg-background" aria-live="polite">
      <div className="h-9 w-9 animate-spin rounded-full border-2 border-border border-t-primary" />
      <span className="sr-only">{copy.application}</span>
    </div>
  );
}
