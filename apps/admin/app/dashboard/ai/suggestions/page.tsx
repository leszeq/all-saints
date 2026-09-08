import type { Metadata } from "next";

import { AiSuggestionsClient } from "./suggestions-client";
import { DEFAULT_ADMIN_UI_LOCALE } from "@/lib/i18n/config";
import { getAdminDictionary } from "@/lib/i18n/dictionaries";

export async function generateMetadata(): Promise<Metadata> {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);
  return {
    title: dictionary.aiSuggestions.metadataTitle,
    description: dictionary.aiSuggestions.metadataDescription,
  };
}

export default async function AiSuggestionsPage() {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);

  return (
    <AiSuggestionsClient
      copy={dictionary.aiSuggestions}
      domainCopy={dictionary.domain}
      locale={DEFAULT_ADMIN_UI_LOCALE}
    />
  );
}
