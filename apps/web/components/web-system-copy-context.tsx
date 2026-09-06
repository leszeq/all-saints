"use client";

import { createContext, useContext } from "react";

import type { WebDictionary } from "@/lib/i18n/types";

type WebSystemCopy = WebDictionary["system"];

const WebSystemCopyContext = createContext<WebSystemCopy | null>(null);

export function WebSystemCopyProvider({
  children,
  value,
}: {
  children: React.ReactNode;
  value: WebSystemCopy;
}) {
  return (
    <WebSystemCopyContext.Provider value={value}>
      {children}
    </WebSystemCopyContext.Provider>
  );
}

export function useWebSystemCopy(): WebSystemCopy {
  const value = useContext(WebSystemCopyContext);
  if (!value) {
    throw new Error("WebSystemCopyProvider is missing from the public application shell.");
  }
  return value;
}
