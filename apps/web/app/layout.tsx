import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/header";
import { Footer } from "@/components/footer";
import { Providers } from "@/components/providers";
import { DEFAULT_WEB_UI_LOCALE } from "@/lib/i18n/config";
import { getWebDictionary } from "@/lib/i18n/dictionaries";

export async function generateMetadata(): Promise<Metadata> {
  const dictionary = await getWebDictionary(DEFAULT_WEB_UI_LOCALE);
  return {
    title: {
      default: dictionary.metadata.defaultTitle,
      template: dictionary.metadata.titleTemplate,
    },
    description: dictionary.metadata.description,
    keywords: dictionary.metadata.keywords,
    authors: [{ name: dictionary.metadata.author }],
    openGraph: {
      type: "website",
      locale: dictionary.metadata.openGraphLocale,
      url: "https://encyklopediaswietych.pl",
      siteName: dictionary.brand.name,
      title: dictionary.metadata.openGraphTitle,
      description: dictionary.metadata.openGraphDescription,
    },
  };
}

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const dictionary = await getWebDictionary(DEFAULT_WEB_UI_LOCALE);

  return (
    <html
      lang={DEFAULT_WEB_UI_LOCALE}
      className="scroll-smooth"
      data-scroll-behavior="smooth"
    >
      <body className="flex min-h-screen flex-col antialiased">
        <Providers>
          <Header dictionary={{ brand: dictionary.brand, header: dictionary.header }} />
          <main className="flex-1">{children}</main>
          <Footer dictionary={{ brand: dictionary.brand, footer: dictionary.footer }} />
        </Providers>
      </body>
    </html>
  );
}
