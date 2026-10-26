import type { Metadata } from "next";

import { AnalyticsDashboardClient } from "@/components/dashboard/analytics-dashboard-client";
import { DEFAULT_ADMIN_UI_LOCALE } from "@/lib/i18n/config";
import { getAdminDictionary } from "@/lib/i18n/dictionaries";

export async function generateMetadata(): Promise<Metadata> {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);
  return {
    title: dictionary.analytics.metadataTitle,
    description: dictionary.analytics.metadataDescription,
  };
}

export default async function AnalyticsPage() {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);
  return (
    <AnalyticsDashboardClient
      copy={dictionary.analytics}
      locale={DEFAULT_ADMIN_UI_LOCALE}
    />
  );
}
