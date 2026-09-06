import { SessionSync } from "@/components/auth/session-sync";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { DEFAULT_ADMIN_UI_LOCALE } from "@/lib/i18n/config";
import { getAdminDictionary } from "@/lib/i18n/dictionaries";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);

  return (
    <SessionSync>
      <div className="flex h-screen overflow-hidden bg-background">
        <Sidebar dictionary={{ brand: dictionary.brand, sidebar: dictionary.sidebar }} />
        <div className="flex flex-1 flex-col overflow-hidden">
          <Topbar dictionary={dictionary.topbar} />
          <main className="flex-1 overflow-y-auto p-5 lg:p-7">{children}</main>
        </div>
      </div>
    </SessionSync>
  );
}
