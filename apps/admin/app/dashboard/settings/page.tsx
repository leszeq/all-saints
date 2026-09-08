import type { Metadata } from "next";

import { SettingsClient } from "./settings-client";
import { DEFAULT_ADMIN_UI_LOCALE } from "@/lib/i18n/config";
import { getAdminDictionary } from "@/lib/i18n/dictionaries";

export async function generateMetadata(): Promise<Metadata> {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);
  return {
    title: dictionary.settings.metadataTitle,
    description: dictionary.settings.metadataDescription,
  };
}

export default async function SettingsPage() {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);

  return (
    <SettingsClient
      copy={dictionary.settings}
      domainCopy={dictionary.domain}
      roleLabels={dictionary.topbar.roleLabels}
      locale={DEFAULT_ADMIN_UI_LOCALE}
    />
  );
}
