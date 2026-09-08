import type { Metadata } from "next";

import { OrdersClient } from "./orders-client";
import { DEFAULT_ADMIN_UI_LOCALE } from "@/lib/i18n/config";
import { getAdminDictionary } from "@/lib/i18n/dictionaries";

export async function generateMetadata(): Promise<Metadata> {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);
  return {
    title: dictionary.ordersWorkspace.metadataTitle,
    description: dictionary.ordersWorkspace.metadataDescription,
  };
}

export default async function OrdersPage() {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);

  return (
    <OrdersClient
      copy={dictionary.ordersWorkspace}
      domainCopy={dictionary.domain}
      locale={DEFAULT_ADMIN_UI_LOCALE}
    />
  );
}
