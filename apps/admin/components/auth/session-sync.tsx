"use client";

import { useEffect } from "react";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store/auth";

export function SessionSync() {
  const updateUser = useAuthStore((state) => state.updateUser);

  useEffect(() => {
    if (!window.localStorage.getItem("access_token")) return;

    let active = true;
    void authApi.me().then(({ data }) => {
      if (active) updateUser(data);
    }).catch(() => {
      // The shared API interceptor handles expired sessions and redirects to login.
    });

    return () => {
      active = false;
    };
  }, [updateUser]);

  return null;
}
