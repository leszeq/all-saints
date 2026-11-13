import type { UseFormRegister } from "react-hook-form";
import type { AdminPersonEditorDictionary } from "@/lib/i18n/types";
import { cn } from "@/lib/utils";
import type { PersonFormData } from "./person-form-model";
import { PERSON_FORM_INPUT_CLASS, PERSON_FORM_LABEL_CLASS, personFieldId } from "./person-form-styles";

interface PersonBiographySectionProps {
  copy: AdminPersonEditorDictionary["biography"];
  register: UseFormRegister<PersonFormData>;
  isEdit: boolean;
}

export function PersonBiographySection({ copy, register, isEdit }: PersonBiographySectionProps) {
  return (
    <div className="space-y-4">
      <div>
        <label htmlFor={personFieldId("summary_pl")} className={PERSON_FORM_LABEL_CLASS}>{copy.summary}</label>
        <textarea
          id={personFieldId("summary_pl")}
          {...register("summary_pl")}
          rows={3}
          className={cn(PERSON_FORM_INPUT_CLASS, "resize-none")}
          placeholder={copy.summaryPlaceholder}
        />
        <p className="mt-1 text-xs leading-5 text-muted-foreground">{copy.summaryMarkdownHint}</p>
      </div>
      <div>
        <label htmlFor={personFieldId("biography_pl")} className={PERSON_FORM_LABEL_CLASS}>{copy.biography}</label>
        <textarea
          id={personFieldId("biography_pl")}
          {...register("biography_pl")}
          rows={10}
          className={cn(PERSON_FORM_INPUT_CLASS, "resize-y")}
          placeholder={copy.biographyPlaceholder}
        />
        <p className="mt-1 text-xs leading-5 text-muted-foreground">{copy.biographyMarkdownHint}</p>
      </div>
      {isEdit && (
        <div>
          <label htmlFor={personFieldId("change_summary")} className={PERSON_FORM_LABEL_CLASS}>{copy.changeSummary}</label>
          <input
            id={personFieldId("change_summary")}
            {...register("change_summary")}
            className={PERSON_FORM_INPUT_CLASS}
            placeholder={copy.changeSummaryPlaceholder}
          />
        </div>
      )}
    </div>
  );
}
