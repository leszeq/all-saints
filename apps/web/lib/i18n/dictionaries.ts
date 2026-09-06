import "server-only";

import type { WebDictionary } from "@/lib/i18n/types";
import type { WebUiLocale } from "@/lib/i18n/config";

const dictionaries: Record<WebUiLocale, () => Promise<WebDictionary>> = {
  pl: () => import("@/lib/i18n/dictionaries/pl").then((module) => module.default),
};

export async function getWebDictionary(locale: WebUiLocale): Promise<WebDictionary> {
  return dictionaries[locale]();
}
