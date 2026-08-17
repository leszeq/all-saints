import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/header";
import { Footer } from "@/components/footer";
import { Providers } from "@/components/providers";

export const metadata: Metadata = {
  title: {
    default: "Encyklopedia Świętych Kościoła Katolickiego",
    template: "%s | Encyklopedia Świętych",
  },
  description:
    "Kompletne cyfrowe leksykon hagiograficzny Kościoła Katolickiego. Wyszukuj świętych, błogosławionych, patronów, kalendarz liturgiczny i modlitwy.",
  keywords: [
    "święci",
    "błogosławieni",
    "Kościół Katolicki",
    "patroni",
    "hagiografia",
    "kalendarz liturgiczny",
    "modlitwy",
    "sanktuaria",
  ],
  authors: [{ name: "Encyklopedia Świętych Team" }],
  openGraph: {
    type: "website",
    locale: "pl_PL",
    url: "https://encyklopediaswietych.pl",
    siteName: "Encyklopedia Świętych",
    title: "Encyklopedia Świętych Kościoła Katolickiego",
    description:
      "Wyszukuj świętych, błogosławionych, patronów i kalendarz liturgiczny.",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pl" className="scroll-smooth" data-scroll-behavior="smooth">
      <body className="flex min-h-screen flex-col antialiased">
        <Providers>
          <Header />
          <main className="flex-1">{children}</main>
          <Footer />
        </Providers>
      </body>
    </html>
  );
}
