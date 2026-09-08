import type { UseFormRegister } from "react-hook-form";
import type { AdminPersonEditorDictionary } from "@/lib/i18n/types";
import { cn } from "@/lib/utils";
import type { PersonFormData } from "./person-form-model";
import { PERSON_FORM_INPUT_CLASS, PERSON_FORM_LABEL_CLASS } from "./person-form-styles";

interface PersonDevotionSectionProps {
  copy: AdminPersonEditorDictionary["devotion"];
  register: UseFormRegister<PersonFormData>;
}

export function PersonDevotionSection({ copy, register }: PersonDevotionSectionProps) {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>{copy.prayer}</label>
        <textarea
          {...register("prayers")}
          rows={10}
          className={cn(PERSON_FORM_INPUT_CLASS, "resize-y leading-6")}
          placeholder={copy.prayerPlaceholder}
        />
        <p className="mt-1.5 text-xs leading-5 text-muted-foreground">
          {copy.prayerHint}
        </p>
      </div>

      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>{copy.iconography}</label>
        <textarea
          {...register("iconographic_attributes")}
          rows={10}
          className={cn(PERSON_FORM_INPUT_CLASS, "resize-y leading-6")}
          placeholder={copy.iconographyPlaceholder}
        />
        <p className="mt-1.5 text-xs leading-5 text-muted-foreground">
          {copy.iconographyHint}
        </p>
      </div>
    </div>
  );
}
