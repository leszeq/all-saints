"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, BookOpenText, Loader2, Save, ShieldCheck } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { calendarApi, geographyApi, getApiErrorMessage, personsApi, sourcesApi, taxonomyApi } from "@/lib/api";
import type { AdminPersonEditorDictionary } from "@/lib/i18n/types";
import { cn } from "@/lib/utils";
import { PersonAliasesSection } from "./person-aliases-section";
import { PersonAvatarSection } from "./person-avatar-section";
import { PersonBasicSection } from "./person-basic-section";
import { PersonBiographySection } from "./person-biography-section";
import { PersonDatesSection } from "./person-dates-section";
import { PersonDevotionSection } from "./person-devotion-section";
import {
  buildFeastPayload,
  normalizePersonPayload,
  optionalText,
  personSchema,
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

interface PersonFormProps {
  copy: AdminPersonEditorDictionary;
  personId?: string;
  defaultValues?: Partial<PersonFormData>;
  isEdit?: boolean;
  expectedVersion?: number;
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

export function PersonForm({
  copy,
  personId,
  defaultValues,
  isEdit = false,
  expectedVersion,
}: PersonFormProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<PersonFormTabId>("basic");
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [avatarFileError, setAvatarFileError] = useState<string | null>(null);
  const hydratedFeastPersonIdRef = useRef<string | null>(null);

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
    setValue,
    formState: { errors, isDirty },
  } = useForm<PersonFormData>({
    resolver: zodResolver(personSchema),
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
      const response = await personsApi.update(personId!, {
        ...(await preparePersonPayload(data, true, avatarFile)),
        expected_version: expectedVersion,
      });
      await syncPersonFeast(personId!, data, activeFeastEntry?.id ?? null);
      return response;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["persons"] }),
        queryClient.invalidateQueries({ queryKey: ["person", personId] }),
        queryClient.invalidateQueries({ queryKey: ["person-versions", personId] }),
        queryClient.invalidateQueries({ queryKey: ["editorial"] }),
        queryClient.invalidateQueries({ queryKey: ["calendar"] }),
        queryClient.invalidateQueries({ queryKey: ["calendar", "person-feasts", personId] }),
      ]);
      router.push(`/dashboard/persons/${personId}`);
    },
  });

  const mutation = isEdit ? updateMutation : createMutation;

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

  const selectTab = (tabId: PersonFormTabId) => {
    setActiveTab(tabId);
    window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}#${tabId}`);
  };

  return (
    <form onSubmit={handleSubmit((data) => mutation.mutate(data))} className="space-y-6">
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
          register={register}
          countries={countries}
          countriesLoading={countriesQuery.isLoading}
          countriesError={countriesQuery.isError}
          retryCountries={() => { void countriesQuery.refetch(); }}
        />
      )}

      {activeTab === "aliases" && (
        <PersonAliasesSection control={control} register={register} errors={errors} />
      )}
      {activeTab === "biography" && <PersonBiographySection register={register} isEdit={isEdit} />}
      {activeTab === "patronages" && <PersonPatronagesSection control={control} register={register} errors={errors} />}
      {activeTab === "devotion" && <PersonDevotionSection register={register} />}

      {activeTab === "orders" && (
        isEdit && personId ? (
          <PersonOrdersEditor personId={personId} />
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
        isEdit && personId ? (
          <PersonSourcesEditor personId={personId} />
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
          {isEdit ? copy.actions.saveChanges : copy.actions.createPerson}
        </button>
      </div>

      {mutation.isError && (
        <p role="alert" className="rounded-lg border border-destructive/25 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {getApiErrorMessage(mutation.error)}
        </p>
      )}
    </form>
  );
}
