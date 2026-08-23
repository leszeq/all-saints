"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

export interface SaintAvatarData {
  url: string;
  thumbnail_url?: string | null;
  title?: string | null;
}

interface SaintAvatarProps {
  name: string;
  avatar?: SaintAvatarData | null;
  className?: string;
  eager?: boolean;
}

function getInitials(name: string) {
  const words = name
    .replace(/^(św\.|bł\.|czcigodny|sługa boży)\s+/i, "")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (!words.length) return "†";
  return `${words[0]?.[0] ?? ""}${words.length > 1 ? words.at(-1)?.[0] ?? "" : ""}`.toUpperCase();
}

export function SaintAvatar({ name, avatar, className, eager = false }: SaintAvatarProps) {
  const source = avatar?.thumbnail_url || avatar?.url;
  const [failedSource, setFailedSource] = useState<string | null>(null);
  const failed = Boolean(source && failedSource === source);

  return (
    <span
      className={cn(
        "relative flex shrink-0 items-center justify-center overflow-hidden rounded-full border border-gold-300/70 bg-gradient-to-br from-gold-100 via-[#fffdf8] to-burgundy-50 font-serif font-semibold tracking-wide text-burgundy-800 shadow-sm",
        className,
      )}
      aria-label={!source || failed ? `Avatar zastępczy: ${name}` : undefined}
    >
      {source && !failed ? (
        // Editorial images can come from many documented archives, so a native image is used instead of a broad Next.js remote allowlist.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={source}
          alt={avatar?.title || `Portret: ${name}`}
          className="h-full w-full object-cover"
          loading={eager ? "eager" : "lazy"}
          fetchPriority={eager ? "high" : "auto"}
          referrerPolicy="no-referrer"
          onError={() => setFailedSource(source || null)}
        />
      ) : (
        <span aria-hidden="true">{getInitials(name)}</span>
      )}
    </span>
  );
}
