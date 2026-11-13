"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm, type FieldErrors } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, BookOpenText, Loader2, Save, ShieldCheck } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAdminSystemCopy } from "@/components/admin-system-copy-context";
import {
  calendarApi,
  geographyApi,
  getApiConflictDetails,
  personsApi,
  publicationRevisionsApi,
  sourcesApi,
  taxonomyApi,
  type PublicationRevision,
} from "@/lib/api";
import type { ApiConflictDetails } from "@/lib/api";
import { formatAdminApiError } from "@/lib/i18n/api-errors";
import { personFieldId } from "./person-form-styles";
import type { AdminDomainDictionary, AdminPersonEditorDictionary } from "@/lib/i18n/types";
import { cn } from "@/lib/utils";
import { PersonAliasesSection } from "./person-aliases-section";
import { PersonAvatarSection } from "./person-avatar-section";
import { PersonBasicSection } from "./person-basic-section";
import { PersonBiographySection } from "./person-biography-section";
import { PersonDatesSection } from "./person-dates-section";
import { PersonDevotionSection } from "./person-devotion-section";
import {
  buildFeastPayload,
  createPersonSchema,
  normalizePersonPayload,
  optionalText,
  type FeastEntryResponse,
  type PersonFormData,
} from "./person-form-model";
import { PersonPatronagesSection } from "./person-patronages-section";
import { PersonOrdersEditor } from "./person-orders-editor";
import { PersonSourcesEditor } from "./person-sources-editor";

const TAB_IDS = [
  "basic",
  "aliases",
  "dates",
  "biography",
  "patronages",
  "devotion",
  "orders",
  "sources",
  "avatar",
] as const;

type PersonFormTabId = (typeof TAB_IDS)[number];

const TAB_BY_FIELD: Record<string, PersonFormTabId> = {
  canonical_name: "basic",
  canonical_name_en: "basic",
  latin_name: "basic",
  person_type: "basic",
  status: "basic",
  gender: "basic",
  era: "basic",
  state_of_life_id: "basic",
  is_featured: "basic",
  feast_calendar_code: "basic",
  feast_month: "basic",
  feast_day: "basic",
  feast_rank: "basic",
  feast_liturgical_color: "basic",
  feast_is_primary: "basic",
  feast_source_title: "basic",
  feast_source_url: "basic",
  feast_notes: "basic",
  aliases: "aliases",
  birth_year: "dates",
  death_year: "dates",
  birth_country_id: "dates",
  death_country_id: "dates",
  beatification_date: "dates",
  beatification_year: "dates",
  canonization_date: "dates",
  canonization_year: "dates",
  summary_pl: "biography",
  biography_pl: "biography",
  change_summary: "biography",
  patronages: "patronages",
  prayers: "devotion",
  iconographic_attributes: "devotion",
  avatar_url: "avatar",
  avatar_thumbnail_url: "avatar",
  avatar_title: "avatar",
  avatar_license: "avatar",
  avatar_photographer: "avatar",
  avatar_source_url: "avatar",
};

function firstErrorPath(value: unknown, prefix = ""): string | null {
  if (!value || typeof value !== "object") return null;
  if ("message" in value || "ref" in value) return prefix || null;

  for (const [key, child] of Object.entries(value)) {
    if (key === "root") continue;
    const path = firstErrorPath(child, prefix ? `${prefix}.${key}` : key);
    if (path) return path;
  }

  return null;
}

interface PersonFormProps {
  copy: AdminPersonEditorDictionary;
  domainCopy: AdminDomainDictionary;
  locale: string;
  personId?: string;
  defaultValues?: Partial<PersonFormData>;
  isEdit?: boolean;
  expectedVersion?: number;
  revisionMode?: boolean;
  activeRevision?: PublicationRevision | null;
}

async function preparePersonPayload(
  data: PersonFormData,
  isEdit: boolean,
  avatarFile: File | null,
) {
  const payload = normalizePersonPayload(data, isEdit);
  if (!avatarFile) return payload;

  const upload = await sourcesApi.uploadAvatar(avatarFile);
  return {
    ...payload,
    avatar: {
      url: upload.data.url,
      thumbnail_url: upload.data.thumbnail_url,
      title: optionalText(data.avatar_title),
      license: data.avatar_license,
      photographer: optionalText(data.avatar_photographer),
      source_url: optionalText(data.avatar_source_url),
      storage_key: upload.data.storage_key,
      width_px: upload.data.width_px,
      height_px: upload.data.height_px,
      file_size_bytes: upload.data.file_size_bytes,
      mime_type: upload.data.mime_type,
    },
  };
}

async function syncPersonFeast(
  personId: string,
  data: PersonFormData,
  existingEntryId: string | null,
) {
  const createPayload = buildFeastPayload(personId, data, true);
  if (createPayload) {
    if (existingEntryId) {
      return calendarApi.updateEntry(existingEntryId, buildFeastPayload(personId, data, false));
    }
    return calendarApi.createEntry(createPayload);
  }

  if (existingEntryId) {
    return calendarApi.deleteEntry(existingEntryId);
  }

  return null;
}

const CONFLICT_FIELDS = [
  "canonical_name",
  "canonical_name_en",
  "latin_name",
  "person_type",
  "gender",
  "era",
  "birth_year",
  "death_year",
  "birth_country_id",
  "death_country_id",
  "state_of_life_id",
  "summary_pl",
  "biography_pl",
  "prayers",
  "iconographic_attributes",
  "aliases",
  "patronages",
  "avatar",
  "beatification",
  "canonization",
] as const;

type ConflictSnapshot = Record<string, unknown>;

interface ConflictState {
  expectedVersion?: number;
  currentVersion?: number;
  localSnapshot: ConflictSnapshot;
  serverSnapshot: ConflictSnapshot | null;
  isLoading: boolean;
  showDetails: boolean;
}

function conflictValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function conflictDiff(local: ConflictSnapshot, server: ConflictSnapshot): Array<{
  field: string;
  local: string;
  server: string;
}> {
  return CONFLICT_FIELDS.flatMap((field) => {
    const localValue = conflictValue(local[field]);
    const serverValue = conflictValue(server[field]);
    return localValue === serverValue ? [] : [{ field, local: localValue, server: serverValue }];
  });
}

export function PersonForm({
  copy,
  domainCopy,
  locale,
  personId,
  defaultValues,
  isEdit = false,
  expectedVersion,
  revisionMode = false,
  activeRevision = null,
}: PersonFormProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { apiErrors } = useAdminSystemCopy();
  const [activeTab, setActiveTab] = useState<PersonFormTabId>("basic");
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [avatarFileError, setAvatarFileError] = useState<string | null>(null);
  const [currentRevision, setCurrentRevision] = useState<PublicationRevision | null>(activeRevision);
  const [conflictState, setConflictState] = useState<ConflictState | null>(null);
  const hydratedFeastPersonIdRef = useRef<string | null>(null);
  const formSchema = useMemo(() => createPersonSchema(copy.validation), [copy.validation]);

  const countriesQuery = useQuery({
    queryKey: ["countries"],
    queryFn: () => geographyApi.countries(),
    staleTime: Infinity,
  });
  const statesQuery = useQuery({
    queryKey: ["states-of-life"],
    queryFn: () => taxonomyApi.statesOfLife(),
    staleTime: Infinity,
  });
  const calendarsQuery = useQuery({
    queryKey: ["liturgical-calendars"],
    queryFn: () => calendarApi.calendars(),
    staleTime: Infinity,
  });
  const feastEntriesQuery = useQuery({
    queryKey: ["calendar", "person-feasts", personId],
    queryFn: () => calendarApi.personEntries(personId!),
    enabled: Boolean(isEdit && personId),
  });

  const countries = countriesQuery.data?.data ?? [];
  const statesOfLife = statesQuery.data?.data ?? [];
  const calendars = calendarsQuery.data?.data ?? [];
  const feastEntries = useMemo(
    () => (feastEntriesQuery.data?.data ?? []) as FeastEntryResponse[],
    [feastEntriesQuery.data?.data],
  );
  const activeFeastEntry = useMemo(
    () =>
      feastEntries.find((entry) => entry.calendar?.code === "roman_pl") ??
      feastEntries.find((entry) => entry.is_primary) ??
      feastEntries[0] ??
      null,
    [feastEntries],
  );

  const {
    register,
    handleSubmit,
    control,
    getValues,
    setValue,
    formState: { errors, isDirty },
  } = useForm<PersonFormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      person_type: "saint",
      status: "draft",
      gender: "unknown",
      is_featured: false,
      avatar_license: "unknown",
      feast_calendar_code: "roman_pl",
      feast_month: null,
      feast_day: null,
      feast_rank: "memorial",
      feast_liturgical_color: "",
      feast_is_primary: false,
      feast_source_title: "",
      feast_source_url: "",
      feast_notes: "",
      aliases: [],
      patronages: [],
      ...defaultValues,
    },
  });

  const loadConflictSnapshot = async (details: ApiConflictDetails) => {
    const localSnapshot = normalizePersonPayload(getValues(), true) as ConflictSnapshot;
    setConflictState({
      expectedVersion: details.expectedVersion,
      currentVersion: details.currentVersion,
      localSnapshot,
      serverSnapshot: null,
      isLoading: true,
      showDetails: false,
    });

    if (!personId) return;

    try {
      const latestPersonResponse = await personsApi.get(personId);
      const latestPerson = latestPersonResponse.data as ConflictSnapshot & { version?: number };
      let latestRevision: PublicationRevision | null = null;
      if (revisionMode) {
        latestRevision = (await personsApi.activeRevision(personId)).data as PublicationRevision | null;
      }
      setConflictState((current) => current ? {
        ...current,
        currentVersion:
          current.currentVersion ?? (revisionMode ? latestRevision?.version : latestPerson.version),
        serverSnapshot: {
          ...latestPerson,
          ...(latestRevision?.payload ?? {}),
        },
        isLoading: false,
      } : null);
    } catch {
      setConflictState((current) => current ? { ...current, isLoading: false } : null);
    }
  };

  const handleMutationError = (error: unknown) => {
    const details = getApiConflictDetails(error);
    if (details) void loadConflictSnapshot(details);
  };

  const createMutation = useMutation({
    mutationFn: async (data: PersonFormData) => {
      const response = await personsApi.create(await preparePersonPayload(data, false, avatarFile));
      await syncPersonFeast(response.data.id, data, null);
      return response;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["persons"] }),
        queryClient.invalidateQueries({ queryKey: ["editorial"] }),
        queryClient.invalidateQueries({ queryKey: ["calendar"] }),
      ]);
      router.push("/dashboard/persons");
    },
  });

  const updateMutation = useMutation({
    mutationFn: async (data: PersonFormData) => {
      const payload = await preparePersonPayload(data, true, avatarFile);
      if (!revisionMode) {
        const response = await personsApi.update(personId!, {
          ...payload,
          expected_version: expectedVersion,
        });
        await syncPersonFeast(personId!, data, activeFeastEntry?.id ?? null);
        return { response, revision: null };
      }

      const changes = { ...(payload as Record<string, unknown>) };
      const changeSummary = changes.change_summary;
      delete changes.status;
      delete changes.change_summary;
      let revision = currentRevision;
      if (!revision) {
        revision = (
          await personsApi.createRevision(personId!, {
            expected_version: expectedVersion!,
            change_summary: typeof changeSummary === "string" ? changeSummary : null,
          })
        ).data;
        setCurrentRevision(revision);
      }

      const response = await publicationRevisionsApi.update(revision.id, {
        expected_version: revision.version,
        changes,
        change_summary: typeof changeSummary === "string" ? changeSummary : null,
      });
      return { response, revision: response.data };
    },
    onError: handleMutationError,
    onSuccess: async (result) => {
      setConflictState(null);
      if (result.revision) setCurrentRevision(result.revision);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["persons"] }),
        queryClient.invalidateQueries({ queryKey: ["person", personId] }),
        queryClient.invalidateQueries({ queryKey: ["person-versions", personId] }),
        queryClient.invalidateQueries({ queryKey: ["person-revision", personId] }),
        queryClient.invalidateQueries({ queryKey: ["editorial"] }),
        ...(revisionMode
          ? []
          : [
              queryClient.invalidateQueries({ queryKey: ["calendar"] }),
              queryClient.invalidateQueries({ queryKey: ["calendar", "person-feasts", personId] }),
            ]),
      ]);
      if (!revisionMode) router.push(`/dashboard/persons/${personId}`);
    },
  });

  const mutation = isEdit ? updateMutation : createMutation;

  useEffect(() => {
    if (!mutation.isError) return;
    window.requestAnimationFrame(() => document.getElementById("person-form-error")?.focus());
  }, [mutation.isError]);

  useEffect(() => {
    if (!avatarFileError) return;
    window.requestAnimationFrame(() => document.getElementById("avatar-file-error")?.focus());
  }, [avatarFileError]);

  useEffect(() => {
    const syncTabFromHash = () => {
      const hash = window.location.hash.replace("#", "");
      if (TAB_IDS.some((tabId) => tabId === hash)) {
        setActiveTab(hash as PersonFormTabId);
      }
    };

    syncTabFromHash();
    window.addEventListener("hashchange", syncTabFromHash);
    return () => window.removeEventListener("hashchange", syncTabFromHash);
  }, []);

  useEffect(() => {
    return () => {
      if (avatarPreview) URL.revokeObjectURL(avatarPreview);
    };
  }, [avatarPreview]);

  useEffect(() => {
    if (!isEdit || !personId || hydratedFeastPersonIdRef.current === personId || feastEntriesQuery.isLoading) {
      return;
    }

    if (activeFeastEntry) {
      setValue("feast_calendar_code", activeFeastEntry.calendar?.code ?? "roman_pl", { shouldDirty: false });
      setValue("feast_month", activeFeastEntry.month ?? null, { shouldDirty: false });
      setValue("feast_day", activeFeastEntry.day ?? null, { shouldDirty: false });
      setValue("feast_rank", (activeFeastEntry.rank as PersonFormData["feast_rank"]) ?? "memorial", { shouldDirty: false });
      setValue("feast_liturgical_color", (activeFeastEntry.liturgical_color as PersonFormData["feast_liturgical_color"]) ?? "", { shouldDirty: false });
      setValue("feast_is_primary", Boolean(activeFeastEntry.is_primary), { shouldDirty: false });
      setValue("feast_source_title", activeFeastEntry.source_title ?? "", { shouldDirty: false });
      setValue("feast_source_url", activeFeastEntry.source_url ?? "", { shouldDirty: false });
      setValue("feast_notes", activeFeastEntry.notes ?? "", { shouldDirty: false });
    }

    hydratedFeastPersonIdRef.current = personId;
  }, [activeFeastEntry, feastEntriesQuery.isLoading, isEdit, personId, setValue]);

  const selectAvatarFile = (file?: File) => {
    setAvatarFileError(null);
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setAvatarFileError(copy.avatarValidation.invalidType);
      return;
    }
    if (file.size > 8 * 1024 * 1024) {
      setAvatarFileError(copy.avatarValidation.maxSize);
      return;
    }
    setAvatarFile(file);
    setAvatarPreview(URL.createObjectURL(file));
  };

  const clearAvatarFile = () => {
    setAvatarFile(null);
    setAvatarPreview(null);
    setAvatarFileError(null);
  };

  const focusFirstInvalidField = (formErrors: FieldErrors<PersonFormData>) => {
    const path = firstErrorPath(formErrors);
    const firstField = path?.split(".")[0] ?? "";
    const tab = TAB_BY_FIELD[firstField];
    if (tab) selectTab(tab);

    window.requestAnimationFrame(() => {
      const field = path ? document.getElementById(personFieldId(path)) : null;
      const fallback = document.querySelector<HTMLElement>("[aria-invalid='true']");
      (field ?? fallback)?.focus();
    });
  };

  const selectTab = (tabId: PersonFormTabId) => {
    setActiveTab(tabId);
    window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}#${tabId}`);
  };

  return (
    <form onSubmit={handleSubmit((data) => mutation.mutate(data), focusFirstInvalidField)} className="space-y-6">
      {revisionMode && (
        <div className="rounded-lg border border-primary/25 bg-primary/5 px-4 py-3 text-sm text-primary" role="status">
          <p>{copy.workflow.draftNotice}</p>
          <p className="mt-1 text-xs text-primary/80">
            {copy.workflow.baseVersionNotice.replace(
              "{version}",
              String(activeRevision?.base_version ?? expectedVersion ?? "—"),
            )}
          </p>
        </div>
      )}

      {conflictState && (
        <section
          className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-4 text-sm text-amber-950 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-100"
          aria-labelledby="person-form-conflict-title"
        >
          <h2 id="person-form-conflict-title" className="font-semibold">{copy.workflow.conflictTitle}</h2>
          <p className="mt-1 leading-6">{copy.workflow.conflictDescription}</p>
          {(conflictState.expectedVersion || conflictState.currentVersion) && (
            <p className="mt-2 text-xs font-medium text-amber-800 dark:text-amber-200">
              {copy.workflow.conflictVersionNotice
                .replace("{expected}", String(conflictState.expectedVersion ?? "—"))
                .replace("{current}", String(conflictState.currentVersion ?? "—"))}
            </p>
          )}
          <button
            type="button"
            className="mt-3 rounded-md border border-amber-400 px-3 py-1.5 text-xs font-semibold hover:bg-amber-100 dark:border-amber-700 dark:hover:bg-amber-900/40"
            onClick={() => setConflictState((current) => current ? { ...current, showDetails: !current.showDetails } : null)}
          >
            {conflictState.showDetails ? copy.workflow.conflictHideDetails : copy.workflow.conflictDetailsAction}
          </button>
          {conflictState.showDetails && (
            <div className="mt-4 space-y-3 border-t border-amber-300/70 pt-4 dark:border-amber-800/70">
              {conflictState.isLoading && <p>{copy.workflow.conflictLoading}</p>}
              {!conflictState.isLoading && !conflictState.serverSnapshot && <p>{copy.workflow.conflictUnavailable}</p>}
              {!conflictState.isLoading && conflictState.serverSnapshot && (() => {
                const differences = conflictDiff(conflictState.localSnapshot, conflictState.serverSnapshot);
                return differences.length > 0 ? differences.map((difference) => (
                  <div key={difference.field} className="rounded-lg border border-amber-200 bg-white/60 p-3 dark:border-amber-900/70 dark:bg-black/10">
                    <code className="text-xs font-semibold">{difference.field}</code>
                    <div className="mt-2 grid gap-2 md:grid-cols-2">
                      <div>
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-800 dark:text-amber-200">{copy.workflow.conflictLocalValue}</p>
                        <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap break-words rounded bg-amber-100/70 p-2 text-xs dark:bg-amber-900/30">{difference.local}</pre>
                      </div>
                      <div>
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-800 dark:text-amber-200">{copy.workflow.conflictServerValue}</p>
                        <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap break-words rounded bg-amber-100/70 p-2 text-xs dark:bg-amber-900/30">{difference.server}</pre>
                      </div>
                    </div>
                  </div>
                )) : <p>{copy.workflow.conflictNoChanges}</p>;
              })()}
            </div>
          )}
        </section>
      )}
      <div className="flex w-fit max-w-full flex-wrap gap-1 rounded-lg border border-border bg-muted/40 p-1">
        {TAB_IDS.map((tabId) => (
          <button
            key={tabId}
            type="button"
            onClick={() => selectTab(tabId)}
            className={cn(
              "rounded-md px-4 py-1.5 text-sm font-medium transition-all",
              activeTab === tabId
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {copy.tabs[tabId]}
          </button>
        ))}
      </div>

      {activeTab === "basic" && (
        <PersonBasicSection
          copy={copy.basic}
          domainCopy={domainCopy}
          locale={locale}
          control={control}
          register={register}
          setValue={setValue}
          errors={errors}
          statesOfLife={statesOfLife}
          statesLoading={statesQuery.isLoading}
          statesError={statesQuery.isError}
          retryStates={() => { void statesQuery.refetch(); }}
          calendars={calendars}
          calendarsError={calendarsQuery.isError}
          retryCalendars={() => { void calendarsQuery.refetch(); }}
          isEdit={isEdit}
          feastLoading={feastEntriesQuery.isLoading}
          feastEntryCount={feastEntries.length}
          hasActiveFeastEntry={Boolean(activeFeastEntry)}
        />
      )}

      {activeTab === "dates" && (
        <PersonDatesSection
          copy={copy.dates}
          register={register}
          countries={countries}
          countriesLoading={countriesQuery.isLoading}
          countriesError={countriesQuery.isError}
          retryCountries={() => { void countriesQuery.refetch(); }}
        />
      )}

      {activeTab === "aliases" && (
        <PersonAliasesSection
          copy={copy.aliases}
          domainCopy={domainCopy}
          control={control}
          register={register}
          errors={errors}
        />
      )}
      {activeTab === "biography" && <PersonBiographySection copy={copy.biography} register={register} isEdit={isEdit} />}
      {activeTab === "patronages" && (
        <PersonPatronagesSection
          copy={copy.patronages}
          domainCopy={domainCopy}
          control={control}
          register={register}
          errors={errors}
        />
      )}
      {activeTab === "devotion" && <PersonDevotionSection copy={copy.devotion} register={register} />}

      {activeTab === "orders" && (
        revisionMode ? (
          <div className="rounded-xl border border-dashed border-border bg-muted/20 p-8 text-center">
            <ShieldCheck className="mx-auto h-7 w-7 text-primary" />
            <p className="mx-auto mt-3 max-w-lg text-sm leading-6 text-muted-foreground">
              {copy.workflow.relationsNotice}
            </p>
          </div>
        ) : isEdit && personId ? (
          <PersonOrdersEditor
            copy={copy.orders}
            domainCopy={domainCopy}
            locale={locale}
            personId={personId}
          />
        ) : (
          <div className="rounded-xl border border-dashed border-border bg-muted/20 p-8 text-center">
            <ShieldCheck className="mx-auto h-7 w-7 text-primary" />
            <h3 className="mt-3 text-sm font-semibold text-foreground">{copy.prerequisites.ordersTitle}</h3>
            <p className="mx-auto mt-1 max-w-lg text-xs leading-5 text-muted-foreground">
              {copy.prerequisites.ordersDescription}
            </p>
          </div>
        )
      )}

      {activeTab === "sources" && (
        revisionMode ? (
          <div className="rounded-xl border border-dashed border-border bg-muted/20 p-8 text-center">
            <BookOpenText className="mx-auto h-7 w-7 text-primary" />
            <p className="mx-auto mt-3 max-w-lg text-sm leading-6 text-muted-foreground">
              {copy.workflow.relationsNotice}
            </p>
          </div>
        ) : isEdit && personId ? (
          <PersonSourcesEditor copy={copy.sources} locale={locale} personId={personId} />
        ) : (
          <div className="rounded-xl border border-dashed border-border bg-muted/20 p-8 text-center">
            <BookOpenText className="mx-auto h-7 w-7 text-primary" />
            <h3 className="mt-3 text-sm font-semibold text-foreground">{copy.prerequisites.sourcesTitle}</h3>
            <p className="mx-auto mt-1 max-w-lg text-xs leading-5 text-muted-foreground">
              {copy.prerequisites.sourcesDescription}
            </p>
          </div>
        )
      )}

      {activeTab === "avatar" && (
        <PersonAvatarSection
          copy={copy.avatar}
          domainCopy={domainCopy}
          locale={locale}
          control={control}
          register={register}
          errors={errors}
          avatarFile={avatarFile}
          avatarPreview={avatarPreview}
          avatarFileError={avatarFileError}
          selectAvatarFile={selectAvatarFile}
          clearAvatarFile={clearAvatarFile}
        />
      )}

      <div className="flex items-center justify-between border-t border-border pt-4">
        <button
          type="button"
          onClick={() => router.back()}
          className="flex items-center gap-1.5 rounded-lg border border-border px-4 py-2 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          {copy.actions.cancel}
        </button>

        <button
          type="submit"
          disabled={mutation.isPending || (!isDirty && isEdit)}
          className="flex items-center gap-2 rounded-lg bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground shadow-sm transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          {isEdit ? (revisionMode ? copy.workflow.saveDraft : copy.actions.saveChanges) : copy.actions.createPerson}
        </button>
      </div>

      {mutation.isError && (
        <p id="person-form-error" tabIndex={-1} role="alert" className="rounded-lg border border-destructive/25 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {formatAdminApiError(mutation.error, apiErrors)}
        </p>
      )}
    </form>
  );
}
