import type { UseFormRegister } from "react-hook-form";
import { cn } from "@/lib/utils";
import type { PersonFormData } from "./person-form-model";
import { PERSON_FORM_INPUT_CLASS, PERSON_FORM_LABEL_CLASS } from "./person-form-styles";

interface PersonBiographySectionProps {
  register: UseFormRegister<PersonFormData>;
  isEdit: boolean;
}

export function PersonBiographySection({ register, isEdit }: PersonBiographySectionProps) {
  return (
    <div className="space-y-4">
      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>Streszczenie (PL)</label>
        <textarea
          {...register("summary_pl")}
          rows={3}
          className={cn(PERSON_FORM_INPUT_CLASS, "resize-none")}
          placeholder="Krótkie streszczenie..."
        />
      </div>
      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>Biografia (PL)</label>
        <textarea
          {...register("biography_pl")}
          rows={10}
          className={cn(PERSON_FORM_INPUT_CLASS, "resize-y")}
          placeholder="Pełny biogram..."
        />
      </div>
      {isEdit && (
        <div>
          <label className={PERSON_FORM_LABEL_CLASS}>Opis zmian (dla historii wersji)</label>
          <input
            {...register("change_summary")}
            className={PERSON_FORM_INPUT_CLASS}
            placeholder="np. Uzupełniono biogram..."
          />
        </div>
      )}
    </div>
  );
}
