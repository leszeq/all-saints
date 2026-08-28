import { QualityClient, type QualityTab } from "../quality-client";

type Params = Promise<{
  tab: string;
}>;

const tabs = new Set(["issues", "duplicates", "sources"]);

export default async function QualityTabPage({ params }: { params: Params }) {
  const { tab } = await params;
  const activeTab: QualityTab = tabs.has(tab) ? (tab as QualityTab) : "issues";

  return <QualityClient activeTab={activeTab} />;
}
