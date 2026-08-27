import { SourcesClient, type SourcesInitialLicenseFilter } from "./sources-client";

type SearchParams = Promise<{
  license?: string | string[];
}>;

function firstParam(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
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

  return <SourcesClient key={filterKey} initialLicenseFilter={initialLicenseFilter} />;
}
