import type { Metadata } from "next";

import { QualityClient, type QualityTab } from "../quality-client";
import { DEFAULT_ADMIN_UI_LOCALE } from "@/lib/i18n/config";
import { getAdminDictionary } from "@/lib/i18n/dictionaries";

type Params = Promise<{
  tab: string;
}>;

const tabs = new Set(["issues", "duplicates", "sources"]);

function parseQualityTab(tab: string): QualityTab {
  return tabs.has(tab) ? (tab as QualityTab) : "issues";
}

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { tab } = await params;
  const activeTab = parseQualityTab(tab);
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);
  return {
    title: dictionary.quality.tabs[activeTab],
    description: dictionary.quality.metadataDescription,
  };
}

export default async function QualityTabPage({ params }: { params: Params }) {
  const { tab } = await params;
  const activeTab = parseQualityTab(tab);
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);

  return (
    <QualityClient
      activeTab={activeTab}
      copy={dictionary.quality}
      domainCopy={dictionary.domain}
      locale={DEFAULT_ADMIN_UI_LOCALE}
    />
  );
}
