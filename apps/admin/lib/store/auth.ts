"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { useSyncExternalStore } from "react";

export interface User {
  id: string;
  email: string;
  full_name: string;
  roles: string[];
  permissions: string[];
  preferred_language: string;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  setAuth: (user: User, token: string) => void;
  updateUser: (user: Partial<User>) => void;
  logout: () => void;
  hasRole: (role: string) => boolean;
  hasPermission: (permission: string) => boolean;
  isAdmin: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,

      setAuth: (user, token) => {
        localStorage.setItem("access_token", token);
        set({ user, accessToken: token, isAuthenticated: true });
      },

      updateUser: (user) => {
        const currentUser = get().user;
        if (currentUser) set({ user: { ...currentUser, ...user } });
      },

      logout: () => {
        localStorage.removeItem("access_token");
        set({ user: null, accessToken: null, isAuthenticated: false });
      },

      hasRole: (role) => {
        const { user } = get();
        return user?.roles.includes(role) ?? false;
      },

      hasPermission: (permission) => {
        const { user } = get();
        return user?.permissions?.includes(permission) ?? false;
      },

      isAdmin: () => {
        const { user } = get();
        return (
          user?.roles.includes("super_admin") ||
          user?.roles.includes("admin") ||
          false
        );
      },
    }),
    {
      name: "saints-auth",
      skipHydration: true,
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

export function useAuthHydrated(): boolean {
  return useSyncExternalStore(
    (onStoreChange) => useAuthStore.persist.onFinishHydration(onStoreChange),
    () => useAuthStore.persist.hasHydrated(),
    () => false,
  );
}
