import type { Metadata } from "next";

import { PersonsClient } from "./persons-client";
import { DEFAULT_ADMIN_UI_LOCALE } from "@/lib/i18n/config";
import { getAdminDictionary } from "@/lib/i18n/dictionaries";

export async function generateMetadata(): Promise<Metadata> {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);
  return {
    title: dictionary.persons.metadataTitle,
    description: dictionary.persons.metadataDescription,
  };
}

export default async function PersonsPage() {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);

  return (
    <PersonsClient
      copy={dictionary.persons}
      domainCopy={dictionary.domain}
      locale={DEFAULT_ADMIN_UI_LOCALE}
    />
  );
}
