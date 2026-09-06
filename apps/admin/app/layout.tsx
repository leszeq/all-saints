import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/providers";
import { DEFAULT_ADMIN_UI_LOCALE } from "@/lib/i18n/config";
import { getAdminDictionary } from "@/lib/i18n/dictionaries";

export async function generateMetadata(): Promise<Metadata> {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);
  return {
    title: {
      default: dictionary.metadata.defaultTitle,
      template: dictionary.metadata.titleTemplate,
    },
    description: dictionary.metadata.description,
    robots: { index: false, follow: false },
  };
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang={DEFAULT_ADMIN_UI_LOCALE} suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
