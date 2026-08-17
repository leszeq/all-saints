import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/providers";

export const metadata: Metadata = {
  title: {
    default: "Admin – Encyklopedia Świętych",
    template: "%s | Admin Encyklopedia Świętych",
  },
  description:
    "Panel administracyjny Encyklopedii Świętych Kościoła Katolickiego",
  robots: { index: false, follow: false },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pl" suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
