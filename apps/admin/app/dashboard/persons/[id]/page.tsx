"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Calendar, Edit, Globe, History, Shield, Trash } from "lucide-react";
import { personsApi } from "@/lib/api";
import { cn, formatDateTime, PERSON_STATUS_COLORS, PERSON_STATUS_LABELS, PERSON_TYPE_COLORS, PERSON_TYPE_LABELS } from "@/lib/utils";

export default function PersonDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const { data: personData, isLoading } = useQuery({
    queryKey: ["person", id],
    queryFn: () => personsApi.get(id),
  });

  const { data: versionsData } = useQuery({
    queryKey: ["person-versions", id],
    queryFn: () => personsApi.versions(id),
  });

  const person = personData?.data;
  const versions = versionsData?.data ?? [];

  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 w-64 rounded bg-muted" />
        <div className="h-4 w-96 rounded bg-muted" />
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/dashboard/persons")}
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-border text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-foreground">
                {person.canonical_name}
              </h1>
              <span
                className={cn(
                  "rounded-full px-2.5 py-0.5 text-xs font-medium",
                  PERSON_TYPE_COLORS[person.person_type]
                )}
              >
                {PERSON_TYPE_LABELS[person.person_type] ?? person.person_type}
              </span>
              <span
                className={cn(
                  "rounded-full px-2.5 py-0.5 text-xs font-medium",
                  PERSON_STATUS_COLORS[person.status]
                )}
              >
                {PERSON_STATUS_LABELS[person.status] ?? person.status}
              </span>
            </div>
            {person.latin_name && (
              <p className="text-sm text-muted-foreground italic">
                {person.latin_name}
              </p>
            )}
          </div>
        </div>

        <button
          onClick={() => router.push(`/dashboard/persons/${id}/edit`)}
          className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 transition-colors"
        >
          <Edit className="h-4 w-4" />
          Edytuj
        </button>
      </div>

      {/* Main Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Detail Specs */}
        <div className="col-span-2 space-y-6">
          {/* Summary & Bio */}
          <div className="rounded-xl border border-border bg-card p-6 space-y-4">
            <h2 className="text-base font-semibold text-foreground">
              Biografia & Streszczenie
            </h2>
            {person.summary_pl ? (
              <div className="rounded-lg bg-muted/40 p-4 text-sm text-foreground/90 italic">
                {person.summary_pl}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Brak streszczenia.</p>
            )}

            {person.biography_pl ? (
              <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-line text-sm text-foreground/80">
                {person.biography_pl}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Brak biogramu.</p>
            )}
          </div>

          {/* Dates & Details */}
          <div className="rounded-xl border border-border bg-card p-6 space-y-4">
            <h2 className="text-base font-semibold text-foreground">
              Metadane Hagiograficzne
            </h2>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-xs text-muted-foreground block">Płeć</span>
                <span className="font-medium text-foreground">{person.gender}</span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">Era</span>
                <span className="font-medium text-foreground">{person.era ?? "—"}</span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">Rok urodzenia</span>
                <span className="font-medium text-foreground">{person.birth_year ?? "—"}</span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">Rok śmierci</span>
                <span className="font-medium text-foreground">{person.death_year ?? "—"}</span>
              </div>
            </div>
          </div>
        </div>

        {/* History Snapshots Sidebar */}
        <div className="space-y-6">
          <div className="rounded-xl border border-border bg-card p-6">
            <h2 className="flex items-center gap-2 text-base font-semibold text-foreground mb-4">
              <History className="h-4 w-4 text-primary" />
              Historia zmian (v{person.version})
            </h2>

            {versions.length === 0 ? (
              <p className="text-xs text-muted-foreground">Brak zarejestrowanych wersji.</p>
            ) : (
              <ol className="relative border-l border-border ml-2 space-y-4">
                {versions.map((v: Record<string, unknown>) => (
                  <li key={v.id as string} className="ml-4 text-xs">
                    <div className="absolute -left-1.5 mt-1 h-3 w-3 rounded-full border border-background bg-primary" />
                    <time className="font-mono text-[10px] text-muted-foreground">
                      v{v.version_number as number} · {formatDateTime(v.changed_at as string)}
                    </time>
                    <p className="font-medium text-foreground mt-0.5">
                      {(v.change_summary as string) || "Modyfikacja danych"}
                    </p>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
