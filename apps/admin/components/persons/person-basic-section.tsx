import { useWatch, type Control, type FieldErrors, type UseFormRegister, type UseFormSetValue } from "react-hook-form";
import { CalendarDays } from "lucide-react";
import { ERA_LABELS, FEAST_RANK_LABELS, LITURGICAL_COLOR_LABELS, PERSON_STATUS_LABELS, cn } from "@/lib/utils";
import {
  FEAST_RANK_VALUES,
  LITURGICAL_COLOR_VALUES,
  MONTH_OPTIONS,
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
        <label className={PERSON_FORM_LABEL_CLASS}>Imię kanoniczne (PL) *</label>
        <input {...register("canonical_name")} className={PERSON_FORM_INPUT_CLASS} placeholder="np. Św. Franciszek z Asyżu" />
        {errors.canonical_name && <p className={PERSON_FORM_ERROR_CLASS}>{errors.canonical_name.message}</p>}
      </div>

      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>Imię kanoniczne (EN)</label>
        <input {...register("canonical_name_en")} className={PERSON_FORM_INPUT_CLASS} placeholder="St. Francis of Assisi" />
      </div>

      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>Imię łacińskie</label>
        <input {...register("latin_name")} className={PERSON_FORM_INPUT_CLASS} placeholder="Franciscus Assisiensis" />
      </div>

      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>Typ osoby *</label>
        <select {...register("person_type")} className={PERSON_FORM_INPUT_CLASS}>
          <option value="saint">Święty/a</option>
          <option value="blessed">Błogosławiony/a</option>
          <option value="venerable">Czcigodny/a</option>
          <option value="servant_of_god">Sługa Boży/a</option>
          <option value="candidate">Kandydat/ka (status redakcyjny)</option>
        </select>
      </div>

      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>Status publikacji *</label>
        <input type="hidden" {...register("status")} />
        <div className="rounded-lg border border-input bg-muted/45 px-3 py-2">
          <p className="text-sm font-medium">{PERSON_STATUS_LABELS[publicationStatus] ?? publicationStatus}</p>
          <p className="mt-1 text-[11px] leading-4 text-muted-foreground">
            Status zmienisz wyłącznie przez akcje w kolejce redakcyjnej.
          </p>
        </div>
      </div>

      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>Płeć *</label>
        <select {...register("gender")} className={PERSON_FORM_INPUT_CLASS}>
          <option value="unknown">Nieznana</option>
          <option value="male">Mężczyzna</option>
          <option value="female">Kobieta</option>
        </select>
      </div>

      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>Era</label>
        <select {...register("era")} className={PERSON_FORM_INPUT_CLASS}>
          <option value="">—</option>
          {Object.entries(ERA_LABELS).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </div>

      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>Stan życia</label>
        <select
          {...register("state_of_life_id")}
          className={PERSON_FORM_INPUT_CLASS}
          disabled={statesUnavailable}
        >
          <option value="">—</option>
          {statesLoading && <option>Ładowanie danych…</option>}
          {statesError && <option>Nie udało się pobrać danych</option>}
          {!statesLoading && !statesError && statesOfLife.length === 0 && <option>Brak danych słownikowych</option>}
          {statesOfLife.map((state) => <option key={state.id} value={state.id}>{state.name_pl}</option>)}
        </select>
        {statesError && (
          <button type="button" onClick={retryStates} className="mt-1 text-xs text-primary hover:underline">
            Spróbuj pobrać ponownie
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
          Wyróżnij na stronie głównej (featured)
        </label>
      </div>

      <section className="space-y-4 border-t border-border pt-5 sm:col-span-2">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <CalendarDays className="h-4 w-4 text-primary" />
              Wspomnienie liturgiczne
            </h3>
            <p className="mt-1 max-w-2xl text-xs leading-5 text-muted-foreground">
              To pole tworzy powiązanie z kalendarzem liturgicznym. Publiczny portal pokaże wpis dopiero wtedy, gdy sama osoba ma status „Opublikowany”.
            </p>
          </div>
          {(hasActiveFeastEntry || feastMonth || feastDay) && (
            <button
              type="button"
              onClick={clearFeastDate}
              className="self-start rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            >
              Wyczyść wspomnienie
            </button>
          )}
        </div>

        {feastLoading && isEdit && (
          <p className="rounded-lg border border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
            Ładowanie aktualnych powiązań kalendarza…
          </p>
        )}

        {feastEntryCount > 1 && (
          <p className="rounded-lg border border-primary/15 bg-primary/5 px-3 py-2 text-xs leading-5 text-muted-foreground">
            Ta osoba ma {feastEntryCount} aktywne wpisy w kalendarzach. Formularz edytuje domyślnie wpis z Kalendarza Polskiego albo główny wpis dnia.
          </p>
        )}

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="lg:col-span-2">
            <label className={PERSON_FORM_LABEL_CLASS}>Kalendarz</label>
            <select {...register("feast_calendar_code")} className={PERSON_FORM_INPUT_CLASS}>
              {calendars.length === 0 && (
                <>
                  <option value="roman_pl">Kalendarz Polski</option>
                  <option value="roman_universal">Ogólny Kalendarz Rzymski</option>
                  <option value="roman_martyrology">Martyrologium Rzymskie</option>
                </>
              )}
              {calendars.map((calendar) => (
                <option key={calendar.code} value={calendar.code}>{calendar.name}</option>
              ))}
            </select>
            {errors.feast_calendar_code && <p className={PERSON_FORM_ERROR_CLASS}>{errors.feast_calendar_code.message}</p>}
            {calendarsError && (
              <button type="button" onClick={retryCalendars} className="mt-1 text-xs text-primary hover:underline">
                Spróbuj pobrać listę kalendarzy ponownie
              </button>
            )}
          </div>

          <div>
            <label className={PERSON_FORM_LABEL_CLASS}>Miesiąc</label>
            <select {...register("feast_month", { setValueAs: numberOrNull })} className={PERSON_FORM_INPUT_CLASS}>
              <option value="">—</option>
              {MONTH_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
            {errors.feast_month && <p className={PERSON_FORM_ERROR_CLASS}>{errors.feast_month.message}</p>}
          </div>

          <div>
            <label className={PERSON_FORM_LABEL_CLASS}>Dzień</label>
            <input
              type="number"
              min={1}
              max={31}
              {...register("feast_day", { setValueAs: numberOrNull })}
              className={PERSON_FORM_INPUT_CLASS}
              placeholder="np. 22"
            />
            {errors.feast_day && <p className={PERSON_FORM_ERROR_CLASS}>{errors.feast_day.message}</p>}
          </div>

          <div className="lg:col-span-2">
            <label className={PERSON_FORM_LABEL_CLASS}>Ranga liturgiczna</label>
            <select {...register("feast_rank")} className={PERSON_FORM_INPUT_CLASS}>
              {FEAST_RANK_VALUES.map((rank) => <option key={rank} value={rank}>{FEAST_RANK_LABELS[rank]}</option>)}
            </select>
          </div>

          <div>
            <label className={PERSON_FORM_LABEL_CLASS}>Kolor liturgiczny</label>
            <select {...register("feast_liturgical_color")} className={PERSON_FORM_INPUT_CLASS}>
              <option value="">—</option>
              {LITURGICAL_COLOR_VALUES.map((color) => (
                <option key={color} value={color}>{LITURGICAL_COLOR_LABELS[color]}</option>
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
            <label htmlFor="feast_is_primary" className="text-sm text-foreground">Główne wspomnienie dnia</label>
          </div>

          <div className="lg:col-span-2">
            <label className={PERSON_FORM_LABEL_CLASS}>Tytuł źródła kalendarzowego</label>
            <input
              {...register("feast_source_title")}
              className={PERSON_FORM_INPUT_CLASS}
              placeholder="np. Kalendarz liturgiczny diecezji / Martyrologium Romanum"
            />
          </div>

          <div className="lg:col-span-2">
            <label className={PERSON_FORM_LABEL_CLASS}>Link do źródła kalendarzowego</label>
            <input {...register("feast_source_url")} className={PERSON_FORM_INPUT_CLASS} placeholder="https://…" />
            {errors.feast_source_url && <p className={PERSON_FORM_ERROR_CLASS}>{errors.feast_source_url.message}</p>}
          </div>

          <div className="sm:col-span-2 lg:col-span-4">
            <label className={PERSON_FORM_LABEL_CLASS}>Notatka redakcyjna</label>
            <textarea
              {...register("feast_notes")}
              rows={3}
              className={cn(PERSON_FORM_INPUT_CLASS, "resize-y")}
              placeholder="Np. wspomnienie w kalendarzu polskim, obchód lokalny, różnice względem Martyrologium…"
            />
          </div>
        </div>
      </section>
    </div>
  );
}
