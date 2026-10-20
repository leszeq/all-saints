"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";

export function PersonCitationButton({
  label,
  copiedLabel,
  version,
}: {
  label: string;
  copiedLabel: string;
  version: number;
}) {
  const [copied, setCopied] = useState(false);

  async function copyCitation() {
    const citationUrl = `${window.location.origin}${window.location.pathname}#wersja-${version}`;
    try {
      await navigator.clipboard.writeText(citationUrl);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2200);
    } catch {
      setCopied(false);
    }
  }

  return (
    <button
      type="button"
      onClick={copyCitation}
      className="inline-flex min-h-9 items-center gap-2 rounded-full border border-gold-300/40 bg-white/10 px-3 py-1.5 text-xs font-semibold text-gold-100 outline-offset-2 transition-colors hover:bg-white/20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-gold-300"
      aria-live="polite"
    >
      {copied ? <Check aria-hidden="true" className="h-3.5 w-3.5" /> : <Copy aria-hidden="true" className="h-3.5 w-3.5" />}
      {copied ? copiedLabel : label}
    </button>
  );
}
