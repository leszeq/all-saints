import Link from "next/link";
import { ArrowLeft, SearchX } from "lucide-react";

import { DEFAULT_ADMIN_UI_LOCALE } from "@/lib/i18n/config";
import { getAdminDictionary } from "@/lib/i18n/dictionaries";

export default async function NotFound() {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);
  const copy = dictionary.system.notFound;

  return (
    <section className="flex min-h-screen items-center justify-center bg-background p-6">
      <div className="admin-card w-full max-w-xl p-8 text-center sm:p-10">
        <SearchX className="mx-auto h-10 w-10 text-muted-foreground" />
        <p className="admin-label mt-6">{copy.kicker}</p>
        <h1 className="mt-2 text-2xl font-semibold">{copy.title}</h1>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          {copy.description}
        </p>
        <Link
          href="/dashboard"
          className="mt-7 inline-flex h-10 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          <ArrowLeft className="h-4 w-4" /> {copy.dashboardAction}
        </Link>
      </div>
    </section>
  );
}
