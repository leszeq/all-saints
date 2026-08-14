"use client";

import { PersonForm } from "@/components/persons/person-form";

export default function NewPersonPage() {
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
