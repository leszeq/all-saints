import type { Metadata } from "next";

import { QualityClient } from "./quality-client";
import { DEFAULT_ADMIN_UI_LOCALE } from "@/lib/i18n/config";
import { getAdminDictionary } from "@/lib/i18n/dictionaries";

export async function generateMetadata(): Promise<Metadata> {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);
  return {
    title: dictionary.quality.metadataTitle,
    description: dictionary.quality.metadataDescription,
  };
}

export default async function QualityPage() {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);
  return (
    <QualityClient
      activeTab="issues"
      copy={dictionary.quality}
      domainCopy={dictionary.domain}
      locale={DEFAULT_ADMIN_UI_LOCALE}
    />
  );
}
