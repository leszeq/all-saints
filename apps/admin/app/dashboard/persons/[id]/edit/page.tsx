import type { Metadata } from "next";

import { EditPersonClient } from "./edit-person-client";
import { DEFAULT_ADMIN_UI_LOCALE } from "@/lib/i18n/config";
import { getAdminDictionary } from "@/lib/i18n/dictionaries";

export async function generateMetadata(): Promise<Metadata> {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);
  return {
    title: dictionary.personEditor.metadata.editTitle,
    description: dictionary.personEditor.metadata.editDescription,
  };
}

export default async function EditPersonPage() {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);

  return <EditPersonClient copy={dictionary.personEditor} />;
}
