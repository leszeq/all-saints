"use client";

import Link from "next/link";
import { AlertTriangle, LayoutDashboard, RefreshCw } from "lucide-react";

interface RouteErrorProps {
  error: Error & { digest?: string };
  retry: () => void;
  fullScreen?: boolean;
}

export function RouteError({ error, retry, fullScreen = false }: RouteErrorProps) {
  return (
    <section className={`flex items-center justify-center ${fullScreen ? "min-h-screen p-6" : "min-h-[65vh]"}`}>
      <div className="admin-card w-full max-w-2xl p-8 text-center sm:p-10">
        <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-300">
          <AlertTriangle className="h-6 w-6" />
        </span>
        <p className="admin-label mt-6">Błąd aplikacji</p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">
          Nie udało się wczytać widoku
        </h1>
        <p className="mx-auto mt-3 max-w-lg text-sm leading-6 text-muted-foreground">
          Spróbuj ponownie. Jeżeli problem nadal występuje, przekaż administratorowi
          identyfikator błędu.
        </p>
        {error.digest && (
          <p className="mt-4 font-mono text-xs text-muted-foreground">
            Identyfikator błędu: {error.digest}
          </p>
        )}
        <div className="mt-7 flex flex-col justify-center gap-3 sm:flex-row">
          <button
            type="button"
            onClick={retry}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:opacity-90"
          >
            <RefreshCw className="h-4 w-4" /> Spróbuj ponownie
          </button>
          <Link
            href="/dashboard"
            className="inline-flex h-10 items-center justify-center gap-2 rounded-md border bg-card px-4 text-sm font-medium text-foreground hover:bg-muted"
          >
            <LayoutDashboard className="h-4 w-4" /> Pulpit
          </Link>
        </div>
      </div>
    </section>
  );
}
