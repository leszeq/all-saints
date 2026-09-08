"use client";

import { PersonForm } from "@/components/persons/person-form";
import type { AdminDomainDictionary, AdminPersonEditorDictionary } from "@/lib/i18n/types";
import { useAuthStore } from "@/lib/store/auth";

interface NewPersonClientProps {
  copy: AdminPersonEditorDictionary;
  domainCopy: AdminDomainDictionary;
  locale: string;
}

export function NewPersonClient({ copy, domainCopy, locale }: NewPersonClientProps) {
  const canCreate = useAuthStore((state) => state.hasPermission("persons:create"));

  if (!canCreate) {
    return (
      <div className="mx-auto mt-20 max-w-xl rounded-xl border border-border bg-card p-8 text-center">
        <h1 className="text-xl font-semibold">{copy.permissions.createTitle}</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          {copy.permissions.createDescription}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">{copy.header.newTitle}</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          {copy.header.newDescription}
        </p>
      </div>

      <div className="rounded-xl border border-border bg-card p-6">
        <PersonForm copy={copy} domainCopy={domainCopy} locale={locale} />
      </div>
    </div>
  );
}
