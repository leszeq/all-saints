"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { useEffect, useState } from "react";

import { AdminSystemCopyProvider } from "@/components/admin-system-copy-context";
import type { AdminSystemDictionary } from "@/lib/i18n/types";

export function Providers({
  children,
  systemCopy,
}: {
  children: React.ReactNode;
  systemCopy: AdminSystemDictionary;
}) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  useEffect(() => {
    // One-time migration from the former persisted JWT/session implementation.
    window.localStorage.removeItem("access_token");
    window.localStorage.removeItem("saints-auth");
  }, []);

  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
      <QueryClientProvider client={queryClient}>
        <AdminSystemCopyProvider value={systemCopy}>{children}</AdminSystemCopyProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
