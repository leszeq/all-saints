"use client";

import { createContext, useContext } from "react";

import type { AdminSystemDictionary } from "@/lib/i18n/types";

const AdminSystemCopyContext = createContext<AdminSystemDictionary | null>(null);

export function AdminSystemCopyProvider({
  children,
  value,
}: {
  children: React.ReactNode;
  value: AdminSystemDictionary;
}) {
  return (
    <AdminSystemCopyContext.Provider value={value}>
      {children}
    </AdminSystemCopyContext.Provider>
  );
}

export function useAdminSystemCopy(): AdminSystemDictionary {
  const value = useContext(AdminSystemCopyContext);
  if (!value) {
    throw new Error("AdminSystemCopyProvider is missing from the admin application shell.");
  }
  return value;
}
