"use client";

import Link from "next/link";
import { AlertTriangle, Home, RefreshCw } from "lucide-react";

import { useWebSystemCopy } from "@/components/web-system-copy-context";

interface RouteErrorProps {
  error: Error & { digest?: string };
  retry: () => void;
}

export function RouteError({ error, retry }: RouteErrorProps) {
  const copy = useWebSystemCopy().error;

  return (
    <section className="mx-auto flex min-h-[62vh] max-w-3xl items-center px-4 py-16 sm:px-6">
      <div className="surface-card w-full p-8 text-center sm:p-12">
        <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full border border-gold-300 bg-gold-50 text-burgundy-700">
          <AlertTriangle className="h-6 w-6" strokeWidth={1.6} />
        </span>
        <p className="editorial-label mt-7">{copy.kicker}</p>
        <h1 className="mt-3 font-serif text-3xl font-semibold text-charcoal sm:text-4xl">
          {copy.title}
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-sm leading-7 text-stone-600">
          {copy.description}
        </p>
        {error.digest && (
          <p className="mt-4 font-mono text-xs text-stone-500">
            {copy.digestPrefix} {error.digest}
          </p>
        )}
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <button
            type="button"
            onClick={retry}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-burgundy-700 px-5 text-sm font-semibold text-white transition-colors hover:bg-burgundy-600"
          >
            <RefreshCw className="h-4 w-4" /> {copy.retryAction}
          </button>
          <Link
            href="/"
            className="inline-flex h-11 items-center justify-center gap-2 rounded-lg border border-[#ded8cd] bg-white px-5 text-sm font-semibold text-burgundy-700 hover:bg-gold-50"
          >
            <Home className="h-4 w-4" /> {copy.homeAction}
          </Link>
        </div>
      </div>
    </section>
  );
}
