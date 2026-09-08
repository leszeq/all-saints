import { useWatch, type Control, type FieldErrors, type UseFormRegister, type UseFormSetValue } from "react-hook-form";
import { CalendarDays } from "lucide-react";
import type {
  AdminDomainDictionary,
  AdminFeastRankKey,
  AdminGenderKey,
  AdminLiturgicalColorKey,
  AdminPersonEditorDictionary,
  AdminPersonTypeKey,
  AdminPublicationStatusKey,
} from "@/lib/i18n/types";
import { cn } from "@/lib/utils";
import {
  FEAST_RANK_VALUES,
  LITURGICAL_COLOR_VALUES,
  type PersonFormData,
} from "./person-form-model";
import {
  PERSON_FORM_ERROR_CLASS,
  PERSON_FORM_INPUT_CLASS,
  PERSON_FORM_LABEL_CLASS,
} from "./person-form-styles";

interface StateOfLifeOption {
  id: string;
  name_pl: string;
}

interface CalendarOption {
  code: string;
  name: string;
}

interface PersonBasicSectionProps {
  copy: AdminPersonEditorDictionary["basic"];
  domainCopy: AdminDomainDictionary;
  locale: string;
  control: Control<PersonFormData>;
  register: UseFormRegister<PersonFormData>;
  setValue: UseFormSetValue<PersonFormData>;
  errors: FieldErrors<PersonFormData>;
  statesOfLife: StateOfLifeOption[];
  statesLoading: boolean;
  statesError: boolean;
  retryStates: () => void;
  calendars: CalendarOption[];
  calendarsError: boolean;
  retryCalendars: () => void;
  isEdit: boolean;
  feastLoading: boolean;
  feastEntryCount: number;
  hasActiveFeastEntry: boolean;
}

const numberOrNull = (value: string) => value === "" ? null : Number(value);

export function PersonBasicSection({
  copy,
  domainCopy,
  locale,
  control,
  register,
  setValue,
  errors,
  statesOfLife,
  statesLoading,
  statesError,
  retryStates,
  calendars,
  calendarsError,
  retryCalendars,
  isEdit,
  feastLoading,
  feastEntryCount,
  hasActiveFeastEntry,
}: PersonBasicSectionProps) {
  const publicationStatus = useWatch({ control, name: "status" });
  const feastMonth = useWatch({ control, name: "feast_month" });
  const feastDay = useWatch({ control, name: "feast_day" });
  const statesUnavailable = statesLoading || statesError || statesOfLife.length === 0;
  const monthOptions = Array.from({ length: 12 }, (_, index) => {
    const label = new Intl.DateTimeFormat(locale, {
      month: "long",
      timeZone: "UTC",
    }).format(new Date(Date.UTC(2000, index, 1)));
    return [index + 1, label.charAt(0).toLocaleUpperCase(locale) + label.slice(1)] as const;
  });
  const numberFormatter = new Intl.NumberFormat(locale);

  const clearFeastDate = () => {
    setValue("feast_month", null, { shouldDirty: true, shouldValidate: true });
    setValue("feast_day", null, { shouldDirty: true, shouldValidate: true });
    setValue("feast_is_primary", false, { shouldDirty: true });
    setValue("feast_source_title", "", { shouldDirty: true });
    setValue("feast_source_url", "", { shouldDirty: true, shouldValidate: true });
    setValue("feast_notes", "", { shouldDirty: true });
  };

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <div className="sm:col-span-2">
        <label className={PERSON_FORM_LABEL_CLASS}>{copy.canonicalName}</label>
        <input {...register("canonical_name")} className={PERSON_FORM_INPUT_CLASS} placeholder={copy.canonicalNamePlaceholder} />
        {errors.canonical_name && <p className={PERSON_FORM_ERROR_CLASS}>{errors.canonical_name.message}</p>}
      </div>

      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>{copy.canonicalNameEn}</label>
        <input {...register("canonical_name_en")} className={PERSON_FORM_INPUT_CLASS} placeholder={copy.canonicalNameEnPlaceholder} />
      </div>

      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>{copy.latinName}</label>
        <input {...register("latin_name")} className={PERSON_FORM_INPUT_CLASS} placeholder={copy.latinNamePlaceholder} />
      </div>

      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>{copy.personType}</label>
        <select {...register("person_type")} className={PERSON_FORM_INPUT_CLASS}>
          {Object.entries(domainCopy.personTypeLabels).map(([value, label]) => (
            <option key={value} value={value as AdminPersonTypeKey}>{label}</option>
          ))}
        </select>
      </div>

      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>{copy.publicationStatus}</label>
        <input type="hidden" {...register("status")} />
        <div className="rounded-lg border border-input bg-muted/45 px-3 py-2">
          <p className="text-sm font-medium">{domainCopy.personStatusLabels[publicationStatus as AdminPublicationStatusKey] ?? publicationStatus}</p>
          <p className="mt-1 text-[11px] leading-4 text-muted-foreground">
            {copy.publicationStatusHint}
          </p>
        </div>
      </div>

      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>{copy.gender}</label>
        <select {...register("gender")} className={PERSON_FORM_INPUT_CLASS}>
          {Object.entries(domainCopy.genderLabels).map(([value, label]) => (
            <option key={value} value={value as AdminGenderKey}>{label}</option>
          ))}
        </select>
      </div>

      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>{copy.era}</label>
        <select {...register("era")} className={PERSON_FORM_INPUT_CLASS}>
          <option value="">—</option>
          {Object.entries(domainCopy.eraLabels).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </div>

      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>{copy.stateOfLife}</label>
        <select
          {...register("state_of_life_id")}
          className={PERSON_FORM_INPUT_CLASS}
          disabled={statesUnavailable}
        >
          <option value="">—</option>
          {statesLoading && <option>{copy.loadingData}</option>}
          {statesError && <option>{copy.dataLoadError}</option>}
          {!statesLoading && !statesError && statesOfLife.length === 0 && <option>{copy.noDictionaryData}</option>}
          {statesOfLife.map((state) => <option key={state.id} value={state.id}>{state.name_pl}</option>)}
        </select>
        {statesError && (
          <button type="button" onClick={retryStates} className="mt-1 text-xs text-primary hover:underline">
            {copy.retryData}
          </button>
        )}
      </div>

      <div className="flex items-center gap-2 sm:col-span-2">
        <input
          type="checkbox"
          id="is_featured"
          {...register("is_featured")}
          className="h-4 w-4 rounded border-input accent-primary"
        />
        <label htmlFor="is_featured" className="text-sm text-foreground">
          {copy.featured}
        </label>
      </div>

      <section className="space-y-4 border-t border-border pt-5 sm:col-span-2">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <CalendarDays className="h-4 w-4 text-primary" />
              {copy.feast.title}
            </h3>
            <p className="mt-1 max-w-2xl text-xs leading-5 text-muted-foreground">
              {copy.feast.description}
            </p>
          </div>
          {(hasActiveFeastEntry || feastMonth || feastDay) && (
            <button
              type="button"
              onClick={clearFeastDate}
              className="self-start rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            >
              {copy.feast.clearAction}
            </button>
          )}
        </div>

        {feastLoading && isEdit && (
          <p className="rounded-lg border border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
            {copy.feast.loading}
          </p>
        )}

        {feastEntryCount > 1 && (
          <p className="rounded-lg border border-primary/15 bg-primary/5 px-3 py-2 text-xs leading-5 text-muted-foreground">
            {copy.feast.multipleEntriesPrefix} {numberFormatter.format(feastEntryCount)} {copy.feast.multipleEntriesSuffix}
          </p>
        )}

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="lg:col-span-2">
            <label className={PERSON_FORM_LABEL_CLASS}>{copy.feast.calendar}</label>
            <select {...register("feast_calendar_code")} className={PERSON_FORM_INPUT_CLASS}>
              {calendars.length === 0 && (
                <>
                  <option value="roman_pl">{copy.feast.fallbackCalendars.romanPl}</option>
                  <option value="roman_universal">{copy.feast.fallbackCalendars.romanUniversal}</option>
                  <option value="roman_martyrology">{copy.feast.fallbackCalendars.romanMartyrology}</option>
                </>
              )}
              {calendars.map((calendar) => (
                <option key={calendar.code} value={calendar.code}>{calendar.name}</option>
              ))}
            </select>
            {errors.feast_calendar_code && <p className={PERSON_FORM_ERROR_CLASS}>{errors.feast_calendar_code.message}</p>}
            {calendarsError && (
              <button type="button" onClick={retryCalendars} className="mt-1 text-xs text-primary hover:underline">
                {copy.feast.retryCalendars}
              </button>
            )}
          </div>

          <div>
            <label className={PERSON_FORM_LABEL_CLASS}>{copy.feast.month}</label>
            <select {...register("feast_month", { setValueAs: numberOrNull })} className={PERSON_FORM_INPUT_CLASS}>
              <option value="">—</option>
              {monthOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
            {errors.feast_month && <p className={PERSON_FORM_ERROR_CLASS}>{errors.feast_month.message}</p>}
          </div>

          <div>
            <label className={PERSON_FORM_LABEL_CLASS}>{copy.feast.day}</label>
            <input
              type="number"
              min={1}
              max={31}
              {...register("feast_day", { setValueAs: numberOrNull })}
              className={PERSON_FORM_INPUT_CLASS}
              placeholder={copy.feast.dayPlaceholder}
            />
            {errors.feast_day && <p className={PERSON_FORM_ERROR_CLASS}>{errors.feast_day.message}</p>}
          </div>

          <div className="lg:col-span-2">
            <label className={PERSON_FORM_LABEL_CLASS}>{copy.feast.rank}</label>
            <select {...register("feast_rank")} className={PERSON_FORM_INPUT_CLASS}>
              {FEAST_RANK_VALUES.map((rank) => <option key={rank} value={rank}>{domainCopy.feastRankLabels[rank as AdminFeastRankKey]}</option>)}
            </select>
          </div>

          <div>
            <label className={PERSON_FORM_LABEL_CLASS}>{copy.feast.color}</label>
            <select {...register("feast_liturgical_color")} className={PERSON_FORM_INPUT_CLASS}>
              <option value="">—</option>
              {LITURGICAL_COLOR_VALUES.map((color) => (
                <option key={color} value={color}>{domainCopy.liturgicalColorLabels[color as AdminLiturgicalColorKey]}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2 pt-7">
            <input
              type="checkbox"
              id="feast_is_primary"
              {...register("feast_is_primary")}
              className="h-4 w-4 rounded border-input accent-primary"
            />
            <label htmlFor="feast_is_primary" className="text-sm text-foreground">{copy.feast.primary}</label>
          </div>

          <div className="lg:col-span-2">
            <label className={PERSON_FORM_LABEL_CLASS}>{copy.feast.sourceTitle}</label>
            <input
              {...register("feast_source_title")}
              className={PERSON_FORM_INPUT_CLASS}
              placeholder={copy.feast.sourceTitlePlaceholder}
            />
          </div>

          <div className="lg:col-span-2">
            <label className={PERSON_FORM_LABEL_CLASS}>{copy.feast.sourceUrl}</label>
            <input {...register("feast_source_url")} className={PERSON_FORM_INPUT_CLASS} placeholder={copy.feast.sourceUrlPlaceholder} />
            {errors.feast_source_url && <p className={PERSON_FORM_ERROR_CLASS}>{errors.feast_source_url.message}</p>}
          </div>

          <div className="sm:col-span-2 lg:col-span-4">
            <label className={PERSON_FORM_LABEL_CLASS}>{copy.feast.notes}</label>
            <textarea
              {...register("feast_notes")}
              rows={3}
              className={cn(PERSON_FORM_INPUT_CLASS, "resize-y")}
              placeholder={copy.feast.notesPlaceholder}
            />
          </div>
        </div>
      </section>
    </div>
  );
}
