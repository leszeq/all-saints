import type { Metadata } from "next";

import { SourcesClient, type SourcesInitialLicenseFilter } from "./sources-client";
import { DEFAULT_ADMIN_UI_LOCALE } from "@/lib/i18n/config";
import { getAdminDictionary } from "@/lib/i18n/dictionaries";

type SearchParams = Promise<{
  license?: string | string[];
}>;

function firstParam(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export async function generateMetadata(): Promise<Metadata> {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);
  return {
    title: dictionary.sourcesHub.metadataTitle,
    description: dictionary.sourcesHub.metadataDescription,
  };
}

export default async function SourcesPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const params = await searchParams;
  const license = firstParam(params.license);
  const initialLicenseFilter: SourcesInitialLicenseFilter =
    license === "unknown" ? "unknown" : "";
  const filterKey = initialLicenseFilter || "all";
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);

  return (
    <SourcesClient
      key={filterKey}
      initialLicenseFilter={initialLicenseFilter}
      copy={dictionary.sourcesHub}
      domainCopy={dictionary.domain}
      locale={DEFAULT_ADMIN_UI_LOCALE}
    />
  );
}
