import type { UseFormRegister } from "react-hook-form";
import type { AdminPersonEditorDictionary } from "@/lib/i18n/types";
import { cn } from "@/lib/utils";
import type { PersonFormData } from "./person-form-model";
import { PERSON_FORM_INPUT_CLASS, PERSON_FORM_LABEL_CLASS } from "./person-form-styles";

interface PersonBiographySectionProps {
  copy: AdminPersonEditorDictionary["biography"];
  register: UseFormRegister<PersonFormData>;
  isEdit: boolean;
}

export function PersonBiographySection({ copy, register, isEdit }: PersonBiographySectionProps) {
  return (
    <div className="space-y-4">
      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>{copy.summary}</label>
        <textarea
          {...register("summary_pl")}
          rows={3}
          className={cn(PERSON_FORM_INPUT_CLASS, "resize-none")}
          placeholder={copy.summaryPlaceholder}
        />
      </div>
      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>{copy.biography}</label>
        <textarea
          {...register("biography_pl")}
          rows={10}
          className={cn(PERSON_FORM_INPUT_CLASS, "resize-y")}
          placeholder={copy.biographyPlaceholder}
        />
      </div>
      {isEdit && (
        <div>
          <label className={PERSON_FORM_LABEL_CLASS}>{copy.changeSummary}</label>
          <input
            {...register("change_summary")}
            className={PERSON_FORM_INPUT_CLASS}
            placeholder={copy.changeSummaryPlaceholder}
          />
        </div>
      )}
    </div>
  );
}
