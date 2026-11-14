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
  const [sessionError, setSessionError] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

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
        setSessionError(true);
      }
    };

    void syncSession();

    return () => {
      active = false;
    };
  }, [retryCount, setAuth]);

  if (sessionError) {
    return (
      <div
        className="flex min-h-screen items-center justify-center bg-background p-6"
        aria-live="assertive"
      >
        <div className="admin-card w-full max-w-md space-y-4 px-5 py-5 text-sm">
          <p className="font-semibold text-foreground">{copy.sessionError}</p>
          <p className="text-muted-foreground">{copy.sessionErrorDescription}</p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => {
                setSessionError(false);
                setRetryCount((count) => count + 1);
              }}
              className="rounded-lg bg-primary px-4 py-2 font-semibold text-primary-foreground hover:bg-primary/90"
            >
              {copy.retrySession}
            </button>
            <button
              type="button"
              onClick={() => window.location.replace("/login")}
              className="rounded-lg border border-border px-4 py-2 font-semibold hover:bg-muted"
            >
              {copy.loginAction}
            </button>
          </div>
        </div>
      </div>
    );
  }

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
