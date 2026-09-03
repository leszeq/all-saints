import type { UseFormRegister } from "react-hook-form";
import type { PersonFormData } from "./person-form-model";
import { PERSON_FORM_INPUT_CLASS, PERSON_FORM_LABEL_CLASS } from "./person-form-styles";

interface CountryOption {
  id: string;
  name_pl: string;
}

interface PersonDatesSectionProps {
  register: UseFormRegister<PersonFormData>;
  countries: CountryOption[];
  countriesLoading: boolean;
  countriesError: boolean;
  retryCountries: () => void;
}

const numberOrNull = (value: string) => value === "" ? null : Number(value);

export function PersonDatesSection({
  register,
  countries,
  countriesLoading,
  countriesError,
  retryCountries,
}: PersonDatesSectionProps) {
  const countriesUnavailable = countriesLoading || countriesError || countries.length === 0;

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>Rok urodzenia</label>
        <input
          type="number"
          {...register("birth_year", { setValueAs: numberOrNull })}
          className={PERSON_FORM_INPUT_CLASS}
          placeholder="np. 1181"
        />
      </div>

      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>Rok śmierci</label>
        <input
          type="number"
          {...register("death_year", { setValueAs: numberOrNull })}
          className={PERSON_FORM_INPUT_CLASS}
          placeholder="np. 1226"
        />
      </div>

      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>Kraj urodzenia</label>
        <select
          {...register("birth_country_id")}
          className={PERSON_FORM_INPUT_CLASS}
          disabled={countriesUnavailable}
        >
          <CountryOptions countries={countries} isLoading={countriesLoading} isError={countriesError} />
        </select>
      </div>

      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>Kraj śmierci</label>
        <select
          {...register("death_country_id")}
          className={PERSON_FORM_INPUT_CLASS}
          disabled={countriesUnavailable}
        >
          <CountryOptions countries={countries} isLoading={countriesLoading} isError={countriesError} />
        </select>
      </div>

      {countriesError && (
        <div className="sm:col-span-2">
          <button type="button" onClick={retryCountries} className="text-xs text-primary hover:underline">
            Spróbuj ponownie pobrać listę krajów
          </button>
        </div>
      )}

      <div className="border-t border-border pt-5 sm:col-span-2">
        <h3 className="text-sm font-semibold text-foreground">Droga do chwały ołtarzy</h3>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">
          Wpisz dokładną datę, gdy jest udokumentowana. Jeśli źródło podaje tylko rok, pozostaw datę pustą i uzupełnij pole roku.
        </p>
      </div>

      <MilestoneFields
        title="Beatyfikacja"
        dateField="beatification_date"
        yearField="beatification_year"
        yearPlaceholder="np. 1993"
        register={register}
      />
      <MilestoneFields
        title="Kanonizacja"
        dateField="canonization_date"
        yearField="canonization_year"
        yearPlaceholder="np. 2000"
        register={register}
      />
    </div>
  );
}

function CountryOptions({
  countries,
  isLoading,
  isError,
}: {
  countries: CountryOption[];
  isLoading: boolean;
  isError: boolean;
}) {
  return (
    <>
      <option value="">—</option>
      {isLoading && <option>Ładowanie krajów…</option>}
      {isError && <option>Nie udało się pobrać krajów</option>}
      {!isLoading && !isError && countries.length === 0 && <option>Brak krajów w bazie</option>}
      {countries.map((country) => (
        <option key={country.id} value={country.id}>{country.name_pl}</option>
      ))}
    </>
  );
}

interface MilestoneFieldsProps {
  title: string;
  dateField: "beatification_date" | "canonization_date";
  yearField: "beatification_year" | "canonization_year";
  yearPlaceholder: string;
  register: UseFormRegister<PersonFormData>;
}

function MilestoneFields({ title, dateField, yearField, yearPlaceholder, register }: MilestoneFieldsProps) {
  return (
    <section className="space-y-4 rounded-xl border border-border bg-muted/20 p-4">
      <h4 className="text-sm font-semibold text-foreground">{title}</h4>
      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>Dokładna data</label>
        <input type="date" {...register(dateField)} className={PERSON_FORM_INPUT_CLASS} />
      </div>
      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>Rok (gdy brak dokładnej daty)</label>
        <input
          type="number"
          {...register(yearField, { setValueAs: numberOrNull })}
          className={PERSON_FORM_INPUT_CLASS}
          placeholder={yearPlaceholder}
        />
      </div>
    </section>
  );
}
