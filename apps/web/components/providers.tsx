"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

import { WebSystemCopyProvider } from "@/components/web-system-copy-context";
import type { WebDictionary } from "@/lib/i18n/types";

export function Providers({
  children,
  systemCopy,
}: {
  children: React.ReactNode;
  systemCopy: WebDictionary["system"];
}) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 60 * 1000,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <WebSystemCopyProvider value={systemCopy}>{children}</WebSystemCopyProvider>
    </QueryClientProvider>
  );
}
