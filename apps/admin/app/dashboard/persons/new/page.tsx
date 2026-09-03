"use client";

import { PersonForm } from "@/components/persons/person-form";
import { useAuthStore } from "@/lib/store/auth";

export default function NewPersonPage() {
  const canCreate = useAuthStore((state) => state.hasPermission("persons:create"));
  if (!canCreate) {
    return <div className="mx-auto mt-20 max-w-xl rounded-xl border border-border bg-card p-8 text-center"><h1 className="text-xl font-semibold">Brak uprawnień do tworzenia</h1><p className="mt-2 text-sm text-muted-foreground">Twoja rola pozwala na podgląd lub recenzję, ale nie na dodawanie rekordów.</p></div>;
  }
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Dodaj nową osobę</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          Wprowadź dane nowej postaci w hagiograficznej bazie danych
        </p>
      </div>

      <div className="rounded-xl border border-border bg-card p-6">
        <PersonForm />
      </div>
    </div>
  );
}
