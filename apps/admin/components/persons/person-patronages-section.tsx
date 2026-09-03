import { useFieldArray, type Control, type FieldErrors, type UseFormRegister } from "react-hook-form";
import { HeartHandshake, Plus, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { PATRONAGE_TYPE_OPTIONS, type PersonFormData } from "./person-form-model";
import {
  PERSON_FORM_ERROR_CLASS,
  PERSON_FORM_INPUT_CLASS,
  PERSON_FORM_LABEL_CLASS,
} from "./person-form-styles";

interface PersonPatronagesSectionProps {
  control: Control<PersonFormData>;
  register: UseFormRegister<PersonFormData>;
  errors: FieldErrors<PersonFormData>;
}

const EMPTY_PATRONAGE: PersonFormData["patronages"][number] = {
  patronage_type: "other",
  name_pl: "",
  name_en: "",
  description: "",
  is_official: false,
};

export function PersonPatronagesSection({ control, register, errors }: PersonPatronagesSectionProps) {
  const { fields, append, remove } = useFieldArray({ control, name: "patronages" });
  const addPatronage = () => append({ ...EMPTY_PATRONAGE });

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <HeartHandshake className="h-4 w-4 text-primary" />
            Patronaty
          </h3>
          <p className="mt-1 max-w-3xl text-xs leading-5 text-muted-foreground">
            Dodaj informacje, komu lub czemu dana osoba patronuje. Typ patronatu
            pomaga później filtrować katalog publiczny, np. chorzy, rodzina,
            praca albo podróżni.
          </p>
        </div>
        <AddPatronageButton onClick={addPatronage} primary />
      </div>

      {fields.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border bg-muted/20 p-8 text-center">
          <HeartHandshake className="mx-auto h-7 w-7 text-primary" />
          <h3 className="mt-3 text-sm font-semibold text-foreground">Brak patronatów</h3>
          <p className="mx-auto mt-1 max-w-lg text-xs leading-5 text-muted-foreground">
            Dodaj pierwszy patronat, np. „chorych”, „spraw beznadziejnych”,
            „podróżnych” albo konkretny kraj, miasto czy zawód.
          </p>
          <AddPatronageButton onClick={addPatronage} />
        </div>
      ) : (
        <div className="space-y-4">
          {fields.map((field, index) => (
            <section key={field.id} className="rounded-xl border border-border bg-muted/15 p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h4 className="text-sm font-semibold text-foreground">Patronat #{index + 1}</h4>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Wpisz konkretną grupę, sprawę, miejsce lub zawód.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => remove(index)}
                  className="inline-flex h-8 items-center justify-center gap-1 rounded-md border border-border px-2.5 text-xs text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Usuń
                </button>
              </div>

              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <div>
                  <label className={PERSON_FORM_LABEL_CLASS}>Typ patronatu *</label>
                  <select
                    {...register(`patronages.${index}.patronage_type` as const)}
                    className={PERSON_FORM_INPUT_CLASS}
                  >
                    {PATRONAGE_TYPE_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                  {errors.patronages?.[index]?.patronage_type && (
                    <p className={PERSON_FORM_ERROR_CLASS}>{errors.patronages[index]?.patronage_type?.message}</p>
                  )}
                </div>

                <div>
                  <label className={PERSON_FORM_LABEL_CLASS}>Patron / patronka od *</label>
                  <input
                    {...register(`patronages.${index}.name_pl` as const)}
                    className={PERSON_FORM_INPUT_CLASS}
                    placeholder="np. spraw beznadziejnych, chorych, podróżnych"
                  />
                  {errors.patronages?.[index]?.name_pl && (
                    <p className={PERSON_FORM_ERROR_CLASS}>{errors.patronages[index]?.name_pl?.message}</p>
                  )}
                </div>

                <div>
                  <label className={PERSON_FORM_LABEL_CLASS}>Nazwa EN</label>
                  <input
                    {...register(`patronages.${index}.name_en` as const)}
                    className={PERSON_FORM_INPUT_CLASS}
                    placeholder="np. hopeless causes"
                  />
                </div>

                <div className="flex items-center gap-2 pt-7">
                  <input
                    type="checkbox"
                    id={`patronage-official-${field.id}`}
                    {...register(`patronages.${index}.is_official` as const)}
                    className="h-4 w-4 rounded border-input accent-primary"
                  />
                  <label htmlFor={`patronage-official-${field.id}`} className="text-sm text-foreground">
                    Patronat oficjalnie potwierdzony
                  </label>
                </div>

                <div className="sm:col-span-2">
                  <label className={PERSON_FORM_LABEL_CLASS}>Opis / notatka redakcyjna</label>
                  <textarea
                    {...register(`patronages.${index}.description` as const)}
                    rows={3}
                    className={cn(PERSON_FORM_INPUT_CLASS, "resize-y")}
                    placeholder="Np. zakres patronatu, lokalna tradycja, źródło informacji lub uwagi do weryfikacji…"
                  />
                </div>
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}

function AddPatronageButton({ onClick, primary = false }: { onClick: () => void; primary?: boolean }) {
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
      Dodaj patronat
    </button>
  );
}
