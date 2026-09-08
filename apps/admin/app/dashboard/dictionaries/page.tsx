import type { Metadata } from "next";

import { DictionariesClient } from "./dictionaries-client";
import { DEFAULT_ADMIN_UI_LOCALE } from "@/lib/i18n/config";
import { getAdminDictionary } from "@/lib/i18n/dictionaries";

export async function generateMetadata(): Promise<Metadata> {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);
  return {
    title: dictionary.dictionariesWorkspace.metadataTitle,
    description: dictionary.dictionariesWorkspace.metadataDescription,
  };
}

export default async function DictionariesPage() {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);

  return (
    <DictionariesClient
      copy={dictionary.dictionariesWorkspace}
      locale={DEFAULT_ADMIN_UI_LOCALE}
    />
  );
}
