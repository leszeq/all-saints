import "server-only";

import type { AdminUiLocale } from "@/lib/i18n/config";
import type { AdminDictionary } from "@/lib/i18n/types";

const dictionaries: Record<AdminUiLocale, () => Promise<AdminDictionary>> = {
  pl: () => import("@/lib/i18n/dictionaries/pl").then((module) => module.default),
};

export async function getAdminDictionary(locale: AdminUiLocale): Promise<AdminDictionary> {
  return dictionaries[locale]();
}
