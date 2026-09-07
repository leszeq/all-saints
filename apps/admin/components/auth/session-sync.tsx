"use client";

import { useEffect, useState } from "react";
import { Loader2, ShieldCheck } from "lucide-react";
import { useAdminSystemCopy } from "@/components/admin-system-copy-context";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store/auth";

export function SessionSync({ children }: { children: React.ReactNode }) {
  const copy = useAdminSystemCopy().loading;
  const setAuth = useAuthStore((state) => state.setAuth);
  const [sessionReady, setSessionReady] = useState(false);

  useEffect(() => {
    let active = true;

    const syncSession = async () => {
      try {
        const accessToken = await authApi.refresh();
        if (!active) return;
        const { data } = await authApi.me();
        if (!active) return;
        setAuth(data, accessToken);
        setSessionReady(true);
      } catch {
        if (!active) return;
        useAuthStore.getState().logout();
        window.location.replace("/login");
      }
    };

    void syncSession();

    return () => {
      active = false;
    };
  }, [setAuth]);

  if (!sessionReady) {
    return (
      <div
        className="flex min-h-screen items-center justify-center bg-background p-6"
        aria-live="polite"
      >
        <div className="admin-card flex items-center gap-3 px-5 py-4 text-sm text-muted-foreground">
          <span className="relative flex h-8 w-8 items-center justify-center text-primary">
            <ShieldCheck className="h-5 w-5" />
            <Loader2 className="absolute h-8 w-8 animate-spin opacity-35" />
          </span>
          {copy.sessionVerification}
        </div>
      </div>
    );
  }

  return children;
}
