import type { Metadata } from "next";

import { LoginPageClient } from "@/components/auth/login-page-client";
import { DEFAULT_ADMIN_UI_LOCALE } from "@/lib/i18n/config";
import { getAdminDictionary } from "@/lib/i18n/dictionaries";

export async function generateMetadata(): Promise<Metadata> {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);
  return {
    title: dictionary.login.metadataTitle,
    description: dictionary.login.metadataDescription,
  };
}

export default async function LoginPage() {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);
  return <LoginPageClient dictionary={{ brand: dictionary.brand, login: dictionary.login }} />;
}
