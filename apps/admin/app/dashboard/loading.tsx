"use client";

import { useAdminSystemCopy } from "@/components/admin-system-copy-context";

export default function DashboardLoading() {
  const copy = useAdminSystemCopy().loading;

  return (
    <div className="animate-pulse space-y-6" aria-live="polite">
      <div className="space-y-2">
        <div className="h-7 w-64 rounded bg-muted" />
        <div className="h-4 w-96 max-w-full rounded bg-muted" />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }, (_, index) => (
          <div key={index} className="admin-card h-28 bg-card" />
        ))}
      </div>
      <div className="grid gap-5 xl:grid-cols-[1.4fr_1fr]">
        <div className="admin-card h-80 bg-card" />
        <div className="admin-card h-80 bg-card" />
      </div>
      <span className="sr-only">{copy.dashboard}</span>
    </div>
  );
}
