"use client";

import { useEffect } from "react";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store/auth";

export function SessionSync() {
  const updateUser = useAuthStore((state) => state.updateUser);

  useEffect(() => {
    let active = true;

    const syncSession = async () => {
      await useAuthStore.persist.rehydrate();
      if (!window.localStorage.getItem("access_token")) {
        useAuthStore.getState().logout();
        return;
      }

      try {
        const { data } = await authApi.me();
        if (active) updateUser(data);
      } catch {
        // The shared API interceptor handles expired sessions and redirects to login.
        if (active) useAuthStore.getState().logout();
      }
    };

    void syncSession();

    return () => {
      active = false;
    };
  }, [updateUser]);

  return null;
}
