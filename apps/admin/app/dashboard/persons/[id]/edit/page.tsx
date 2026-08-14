"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { PersonForm } from "@/components/persons/person-form";
import { personsApi } from "@/lib/api";

export default function EditPersonPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const { data: personData, isLoading } = useQuery({
    queryKey: ["person", id],
    queryFn: () => personsApi.get(id),
  });

  const person = personData?.data;

  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 w-64 rounded bg-muted" />
        <div className="h-96 w-full rounded-xl bg-muted" />
      </div>
    );
  }

  if (!person) {
    return (
      <div className="py-12 text-center">
        <p className="text-muted-foreground">Osoba nie została znaleziona.</p>
        <button
          onClick={() => router.push("/dashboard/persons")}
          className="mt-4 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
        >
          Wróć do listy
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">
          Edycja: {person.canonical_name}
        </h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          Wprowadź zmiany w informacjach o tej postaci
        </p>
      </div>

      <div className="rounded-xl border border-border bg-card p-6">
        <PersonForm
          personId={id}
          isEdit
          defaultValues={{
            canonical_name: person.canonical_name ?? "",
            canonical_name_en: person.canonical_name_en ?? "",
            latin_name: person.latin_name ?? "",
            person_type: person.person_type ?? "saint",
            status: person.status ?? "draft",
            gender: person.gender ?? "unknown",
            era: person.era ?? "",
            birth_year: person.birth_year ?? null,
            death_year: person.death_year ?? null,
            birth_country_id: person.birth_country_id ?? null,
            death_country_id: person.death_country_id ?? null,
            state_of_life_id: person.state_of_life_id ?? null,
            summary_pl: person.summary_pl ?? "",
            biography_pl: person.biography_pl ?? "",
            is_featured: person.is_featured ?? false,
          }}
        />
      </div>
    </div>
  );
}
