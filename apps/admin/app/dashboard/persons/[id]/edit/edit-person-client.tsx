"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { PersonForm } from "@/components/persons/person-form";
import { personsApi, type PublicationRevision } from "@/lib/api";
import type { AdminDomainDictionary, AdminPersonEditorDictionary } from "@/lib/i18n/types";
import { useAuthStore } from "@/lib/store/auth";

interface EditPersonClientProps {
  copy: AdminPersonEditorDictionary;
  domainCopy: AdminDomainDictionary;
  locale: string;
}

export function EditPersonClient({ copy, domainCopy, locale }: EditPersonClientProps) {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const canEdit = useAuthStore((state) => state.hasPermission("persons:update"));

  const { data: personData, isLoading } = useQuery({
    queryKey: ["person", id],
    queryFn: () => personsApi.get(id),
    enabled: canEdit,
  });

  const person = personData?.data;
  const { data: revisionData, isLoading: isRevisionLoading } = useQuery({
    queryKey: ["person-revision", id],
    queryFn: () => personsApi.activeRevision(id),
    enabled: canEdit && person?.status === "published",
  });
  const activeRevision = (revisionData?.data ?? null) as PublicationRevision | null;
  const recognitionYearOrNull = (value: unknown) => {
    const year = Number(value);
    return Number.isInteger(year) && year > 0 ? year : null;
  };

  if (!canEdit) {
    return (
      <div className="mx-auto mt-20 max-w-xl rounded-xl border border-border bg-card p-8 text-center">
        <h1 className="text-xl font-semibold">{copy.permissions.readOnlyTitle}</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          {copy.permissions.readOnlyDescription}
        </p>
      </div>
    );
  }

  if (isLoading || (person?.status === "published" && isRevisionLoading)) {
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
        <p className="text-muted-foreground">{copy.notFound}</p>
        <button
          type="button"
          onClick={() => router.push("/dashboard/persons")}
          className="mt-4 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
        >
          {copy.backToListAction}
        </button>
      </div>
    );
  }

  if (person.status === "published" && activeRevision?.status === "review") {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            {copy.header.editTitlePrefix} {person.canonical_name}
          </h1>
          <p className="mt-0.5 text-sm text-muted-foreground">{copy.header.editDescription}</p>
        </div>
        <div className="rounded-xl border border-primary/25 bg-primary/5 p-6 text-sm text-primary" role="status">
          {copy.workflow.reviewNotice}
        </div>
      </div>
    );
  }

  const draftPerson = activeRevision?.status === "draft"
    ? { ...person, ...activeRevision.payload }
    : person;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">
          {copy.header.editTitlePrefix} {person.canonical_name}
        </h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          {copy.header.editDescription}
        </p>
      </div>

      <div className="rounded-xl border border-border bg-card p-6">
        <PersonForm
          copy={copy}
          domainCopy={domainCopy}
          locale={locale}
          personId={id}
          isEdit
          expectedVersion={person.version}
          revisionMode={person.status === "published"}
          activeRevision={activeRevision?.status === "draft" ? activeRevision : null}
          defaultValues={{
            canonical_name: draftPerson.canonical_name ?? "",
            canonical_name_en: draftPerson.canonical_name_en ?? "",
            latin_name: draftPerson.latin_name ?? "",
            person_type: draftPerson.person_type ?? "saint",
            status: draftPerson.status ?? "draft",
            gender: draftPerson.gender ?? "unknown",
            era: draftPerson.era ?? "",
            birth_year: draftPerson.birth_year ?? null,
            death_year: draftPerson.death_year ?? null,
            beatification_date: draftPerson.beatification?.beatification_date ?? "",
            beatification_year: recognitionYearOrNull(draftPerson.beatification?.beatification_year),
            canonization_date: draftPerson.canonization?.canonization_date ?? "",
            canonization_year: recognitionYearOrNull(draftPerson.canonization?.canonization_year),
            canonization_authority: draftPerson.canonization?.authority ?? "",
            canonization_notes: draftPerson.canonization?.notes ?? "",
            birth_country_id: draftPerson.birth_country_id ?? null,
            death_country_id: draftPerson.death_country_id ?? null,
            state_of_life_id: draftPerson.state_of_life_id ?? null,
            summary_pl: draftPerson.summary_pl ?? "",
            biography_pl: draftPerson.biography_pl ?? "",
            prayers: draftPerson.prayers ?? "",
            iconographic_attributes: draftPerson.iconographic_attributes ?? "",
            aliases: Array.isArray(draftPerson.aliases)
              ? draftPerson.aliases.map((alias: Record<string, unknown>) => ({
                  value: String(alias.value ?? ""),
                  language_code: String(alias.language_code ?? "pl"),
                  kind: String(alias.kind ?? "alias") as
                    | "birth_name"
                    | "religious_name"
                    | "alias"
                    | "abbreviation"
                    | "transliteration",
                }))
              : [],
            patronages: Array.isArray(draftPerson.patronages)
              ? draftPerson.patronages.map((patronage: Record<string, unknown>) => ({
                  patronage_type: String(patronage.patronage_type ?? "other"),
                  name_pl: String(patronage.name_pl ?? ""),
                  name_en: String(patronage.name_en ?? ""),
                  description: String(patronage.description ?? ""),
                  is_official: Boolean(patronage.is_official),
                }))
              : [],
            is_featured: draftPerson.is_featured ?? false,
            avatar_url: draftPerson.avatar?.url ?? "",
            avatar_thumbnail_url: draftPerson.avatar?.thumbnail_url ?? "",
            avatar_title: draftPerson.avatar?.title ?? "",
            avatar_license: draftPerson.avatar?.license ?? "unknown",
            avatar_photographer: draftPerson.avatar?.photographer ?? "",
            avatar_source_url: draftPerson.avatar?.source_url ?? "",
          }}
        />
      </div>
    </div>
  );
}
