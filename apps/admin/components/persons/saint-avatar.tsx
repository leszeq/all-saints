"use client";

import * as Avatar from "@radix-ui/react-avatar";
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

export function SaintAvatar({ name, avatar, className }: SaintAvatarProps) {
  const source = avatar?.thumbnail_url || avatar?.url;

  return (
    <Avatar.Root
      className={cn(
        "relative flex shrink-0 items-center justify-center overflow-hidden rounded-full border border-primary/15 bg-gradient-to-br from-primary/15 via-primary/5 to-background shadow-sm",
        className,
      )}
    >
      {source && (
        <Avatar.Image
          src={source}
          alt={avatar?.title || `Portret: ${name}`}
          className="h-full w-full object-cover"
        />
      )}
      <Avatar.Fallback
        delayMs={source ? 250 : 0}
        className="flex h-full w-full items-center justify-center font-serif font-semibold tracking-wide text-primary"
      >
        {getInitials(name)}
      </Avatar.Fallback>
    </Avatar.Root>
  );
}
