import type { UseFormRegister } from "react-hook-form";
import { cn } from "@/lib/utils";
import type { PersonFormData } from "./person-form-model";
import { PERSON_FORM_INPUT_CLASS, PERSON_FORM_LABEL_CLASS } from "./person-form-styles";

interface PersonDevotionSectionProps {
  register: UseFormRegister<PersonFormData>;
}

export function PersonDevotionSection({ register }: PersonDevotionSectionProps) {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>Modlitwa</label>
        <textarea
          {...register("prayers")}
          rows={10}
          className={cn(PERSON_FORM_INPUT_CLASS, "resize-y leading-6")}
          placeholder="Treść zatwierdzonej modlitwy związanej z postacią…"
        />
        <p className="mt-1.5 text-xs leading-5 text-muted-foreground">
          Podziały wierszy zostaną zachowane na profilu publicznym. Publikuj wyłącznie tekst o zweryfikowanym źródle i prawach do wykorzystania.
        </p>
      </div>

      <div>
        <label className={PERSON_FORM_LABEL_CLASS}>Atrybuty ikonograficzne</label>
        <textarea
          {...register("iconographic_attributes")}
          rows={10}
          className={cn(PERSON_FORM_INPUT_CLASS, "resize-y leading-6")}
          placeholder="Róże; cierń na czole; habit augustiański; krucyfiks"
        />
        <p className="mt-1.5 text-xs leading-5 text-muted-foreground">
          Oddziel atrybuty średnikiem lub nowym wierszem. Portal pokaże każdy element jako osobną etykietę.
        </p>
      </div>
    </div>
  );
}
