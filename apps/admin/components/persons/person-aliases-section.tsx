import { useFieldArray, type Control, type FieldErrors, type UseFormRegister } from "react-hook-form";
import { Languages, Plus, Trash2 } from "lucide-react";
import type {
  AdminDomainDictionary,
  AdminPersonAliasKindKey,
  AdminPersonEditorDictionary,
} from "@/lib/i18n/types";
import { cn } from "@/lib/utils";
import type { PersonFormData } from "./person-form-model";
import {
  PERSON_FORM_ERROR_CLASS,
  PERSON_FORM_INPUT_CLASS,
  PERSON_FORM_LABEL_CLASS,
} from "./person-form-styles";

interface PersonAliasesSectionProps {
  copy: AdminPersonEditorDictionary["aliases"];
  domainCopy: AdminDomainDictionary;
  control: Control<PersonFormData>;
  register: UseFormRegister<PersonFormData>;
  errors: FieldErrors<PersonFormData>;
}

const EMPTY_ALIAS: PersonFormData["aliases"][number] = {
  value: "",
  language_code: "pl",
  kind: "alias",
};

export function PersonAliasesSection({
  copy,
  domainCopy,
  control,
  register,
  errors,
}: PersonAliasesSectionProps) {
  const { fields, append, remove } = useFieldArray({ control, name: "aliases" });
  const addAlias = () => append({ ...EMPTY_ALIAS });

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <Languages className="h-4 w-4 text-primary" />
            {copy.title}
          </h3>
          <p className="mt-1 max-w-3xl text-xs leading-5 text-muted-foreground">
            {copy.description}
          </p>
        </div>
        <AliasButton label={copy.addAction} onClick={addAlias} primary />
      </div>

      {fields.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border bg-muted/20 p-8 text-center">
          <Languages className="mx-auto h-7 w-7 text-primary" />
          <h3 className="mt-3 text-sm font-semibold text-foreground">{copy.emptyTitle}</h3>
          <p className="mx-auto mt-1 max-w-lg text-xs leading-5 text-muted-foreground">
            {copy.emptyDescription}
          </p>
          <AliasButton label={copy.addAction} onClick={addAlias} />
        </div>
      ) : (
        <div className="space-y-4">
          {fields.map((field, index) => (
            <section key={field.id} className="rounded-xl border border-border bg-muted/15 p-4">
              <div className="flex items-start justify-between gap-3">
                <h4 className="text-sm font-semibold text-foreground">{copy.itemPrefix} #{index + 1}</h4>
                <button
                  type="button"
                  onClick={() => remove(index)}
                  className="inline-flex h-8 items-center gap-1 rounded-md border border-border px-2.5 text-xs text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  {copy.removeAction}
                </button>
              </div>

              <div className="mt-4 grid gap-4 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_7rem]">
                <div>
                  <label className={PERSON_FORM_LABEL_CLASS}>{copy.name}</label>
                  <input
                    {...register(`aliases.${index}.value` as const)}
                    className={PERSON_FORM_INPUT_CLASS}
                    placeholder={copy.namePlaceholder}
                  />
                  {errors.aliases?.[index]?.value && (
                    <p className={PERSON_FORM_ERROR_CLASS}>{errors.aliases[index]?.value?.message}</p>
                  )}
                </div>

                <div>
                  <label className={PERSON_FORM_LABEL_CLASS}>{copy.kind}</label>
                  <select
                    {...register(`aliases.${index}.kind` as const)}
                    className={PERSON_FORM_INPUT_CLASS}
                  >
                    {Object.entries(domainCopy.personAliasKindLabels).map(([value, label]) => (
                      <option key={value} value={value as AdminPersonAliasKindKey}>{label}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className={PERSON_FORM_LABEL_CLASS}>{copy.language}</label>
                  <input
                    {...register(`aliases.${index}.language_code` as const)}
                    className={PERSON_FORM_INPUT_CLASS}
                    placeholder={copy.languagePlaceholder}
                  />
                  {errors.aliases?.[index]?.language_code && (
                    <p className={PERSON_FORM_ERROR_CLASS}>{errors.aliases[index]?.language_code?.message}</p>
                  )}
                </div>
              </div>
            </section>
          ))}
          {errors.aliases?.root?.message && (
            <p className={PERSON_FORM_ERROR_CLASS}>{errors.aliases.root.message}</p>
          )}
        </div>
      )}
    </div>
  );
}

function AliasButton({
  label,
  onClick,
  primary = false,
}: {
  label: string;
  onClick: () => void;
  primary?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex h-9 items-center justify-center gap-2 rounded-lg px-3 text-xs font-semibold",
        primary
          ? "bg-primary text-primary-foreground hover:bg-primary/90"
          : "mt-4 border border-border hover:bg-accent",
      )}
    >
      <Plus className="h-3.5 w-3.5" />
      {label}
    </button>
  );
}
