"use client";

import { BookOpen } from "lucide-react";

import { useWebSystemCopy } from "@/components/web-system-copy-context";
import type { WebDictionary } from "@/lib/i18n/types";

type LoadingVariant = keyof WebDictionary["system"]["loading"]["labels"];

export function PageLoading({ variant = "default" }: { variant?: LoadingVariant }) {
  const copy = useWebSystemCopy().loading;

  return (
    <div className="mx-auto min-h-[62vh] max-w-7xl px-4 py-14 sm:px-6 lg:px-8" aria-live="polite">
      <div className="flex items-center gap-3 text-gold-700">
        <BookOpen className="h-5 w-5 animate-pulse" strokeWidth={1.5} />
        <p className="editorial-label">{copy.labels[variant]}</p>
      </div>
      <div className="mt-7 animate-pulse space-y-5">
        <div className="h-11 max-w-xl rounded-lg bg-stone-200/80" />
        <div className="h-5 max-w-2xl rounded bg-stone-200/60" />
        <div className="grid gap-5 pt-6 md:grid-cols-3">
          {Array.from({ length: 6 }, (_, index) => (
            <div key={index} className="surface-card h-56 bg-white/70" />
          ))}
        </div>
      </div>
      <span className="sr-only">{copy.screenReaderLabel}</span>
    </div>
  );
}
