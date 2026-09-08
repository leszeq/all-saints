import type { UseFormRegister } from "react-hook-form";
import type { AdminPersonEditorDictionary } from "@/lib/i18n/types";
import type { PersonFormData } from "./person-form-model";
import { PERSON_FORM_INPUT_CLASS, PERSON_FORM_LABEL_CLASS } from "./person-form-styles";

interface CountryOption {
  id: string;
  name_pl: string;
}

interface PersonDatesSectionProps {
  copy: AdminPersonEditorDictionary["dates"];
  register: UseFormRegister<PersonFormData>;
  countries: CountryOption[];
  countriesLoading: boolean;
  countriesError: boolean;
  retryCountries: () => void;
}

const numberOrNull = (value: string) => value === "" ? null : Number(value);

export function PersonDatesSection({
  copy,
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
        <label className={PERSON_FORM_LABEL_CLASS}>{copy.birthYear}</label>
        <input
          type="number"
          {...register("birth_year", { setValueAs: numberOrNull })}
          className={PERSON_FORM_INPUT_CLASS}
          placeholder={copy.birthYearPlaceholder}
        />
      </div>

      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>{copy.deathYear}</label>
        <input
          type="number"
          {...register("death_year", { setValueAs: numberOrNull })}
          className={PERSON_FORM_INPUT_CLASS}
          placeholder={copy.deathYearPlaceholder}
        />
      </div>

      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>{copy.birthCountry}</label>
        <select
          {...register("birth_country_id")}
          className={PERSON_FORM_INPUT_CLASS}
          disabled={countriesUnavailable}
        >
          <CountryOptions copy={copy} countries={countries} isLoading={countriesLoading} isError={countriesError} />
        </select>
      </div>

      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>{copy.deathCountry}</label>
        <select
          {...register("death_country_id")}
          className={PERSON_FORM_INPUT_CLASS}
          disabled={countriesUnavailable}
        >
          <CountryOptions copy={copy} countries={countries} isLoading={countriesLoading} isError={countriesError} />
        </select>
      </div>

      {countriesError && (
        <div className="sm:col-span-2">
          <button type="button" onClick={retryCountries} className="text-xs text-primary hover:underline">
            {copy.retryCountries}
          </button>
        </div>
      )}

      <div className="border-t border-border pt-5 sm:col-span-2">
        <h3 className="text-sm font-semibold text-foreground">{copy.recognitionTitle}</h3>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">
          {copy.recognitionDescription}
        </p>
      </div>

      <MilestoneFields
        title={copy.beatification}
        dateField="beatification_date"
        yearField="beatification_year"
        yearPlaceholder={copy.beatificationYearPlaceholder}
        exactDateLabel={copy.exactDate}
        yearOnlyLabel={copy.yearOnly}
        register={register}
      />
      <MilestoneFields
        title={copy.canonization}
        dateField="canonization_date"
        yearField="canonization_year"
        yearPlaceholder={copy.canonizationYearPlaceholder}
        exactDateLabel={copy.exactDate}
        yearOnlyLabel={copy.yearOnly}
        register={register}
      />
    </div>
  );
}

function CountryOptions({
  copy,
  countries,
  isLoading,
  isError,
}: {
  copy: AdminPersonEditorDictionary["dates"];
  countries: CountryOption[];
  isLoading: boolean;
  isError: boolean;
}) {
  return (
    <>
      <option value="">—</option>
      {isLoading && <option>{copy.loadingCountries}</option>}
      {isError && <option>{copy.countriesLoadError}</option>}
      {!isLoading && !isError && countries.length === 0 && <option>{copy.noCountries}</option>}
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
  exactDateLabel: string;
  yearOnlyLabel: string;
  register: UseFormRegister<PersonFormData>;
}

function MilestoneFields({
  title,
  dateField,
  yearField,
  yearPlaceholder,
  exactDateLabel,
  yearOnlyLabel,
  register,
}: MilestoneFieldsProps) {
  return (
    <section className="space-y-4 rounded-xl border border-border bg-muted/20 p-4">
      <h4 className="text-sm font-semibold text-foreground">{title}</h4>
      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>{exactDateLabel}</label>
        <input type="date" {...register(dateField)} className={PERSON_FORM_INPUT_CLASS} />
      </div>
      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>{yearOnlyLabel}</label>
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
