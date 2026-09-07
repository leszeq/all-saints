import type { Metadata } from "next";

import { EditorialDashboardClient } from "@/components/dashboard/editorial-dashboard-client";
import { DEFAULT_ADMIN_UI_LOCALE } from "@/lib/i18n/config";
import { getAdminDictionary } from "@/lib/i18n/dictionaries";

export async function generateMetadata(): Promise<Metadata> {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);
  return {
    title: dictionary.dashboard.metadataTitle,
    description: dictionary.dashboard.metadataDescription,
  };
}

export default async function DashboardPage() {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);
  return (
    <EditorialDashboardClient
      copy={dictionary.dashboard}
      domainCopy={dictionary.domain}
      locale={DEFAULT_ADMIN_UI_LOCALE}
    />
  );
}
