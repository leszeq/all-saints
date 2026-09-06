import { PageLoading } from "@/components/page-loading";
import { DEFAULT_WEB_UI_LOCALE } from "@/lib/i18n/config";
import { getWebDictionary } from "@/lib/i18n/dictionaries";

export default async function Loading() {
  const dictionary = await getWebDictionary(DEFAULT_WEB_UI_LOCALE);
  return <PageLoading label={dictionary.ordersDirectory.loadingLabel} />;
}
