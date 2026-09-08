import type { Metadata } from "next";

import { AccessControlClient } from "@/components/access-control/access-control-client";
import { DEFAULT_ADMIN_UI_LOCALE } from "@/lib/i18n/config";
import { getAdminDictionary } from "@/lib/i18n/dictionaries";

export async function generateMetadata(): Promise<Metadata> {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);
  return {
    title: dictionary.accessControl.metadataTitle,
    description: dictionary.accessControl.metadataDescription,
  };
}

export default async function UsersPage() {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);

  return (
    <AccessControlClient
      copy={dictionary.accessControl}
      locale={DEFAULT_ADMIN_UI_LOCALE}
      roleLabels={dictionary.topbar.roleLabels}
    />
  );
}
