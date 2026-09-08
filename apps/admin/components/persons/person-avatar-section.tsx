import { useWatch, type Control, type FieldErrors, type UseFormRegister } from "react-hook-form";
import { FileImage, ImagePlus, Info, Upload, X } from "lucide-react";
import type {
  AdminAvatarLicenseKey,
  AdminDomainDictionary,
  AdminPersonEditorDictionary,
} from "@/lib/i18n/types";
import { cn } from "@/lib/utils";
import { SaintAvatar } from "./saint-avatar";
import type { PersonFormData } from "./person-form-model";
import {
  PERSON_FORM_ERROR_CLASS,
  PERSON_FORM_INPUT_CLASS,
  PERSON_FORM_LABEL_CLASS,
} from "./person-form-styles";

interface PersonAvatarSectionProps {
  copy: AdminPersonEditorDictionary["avatar"];
  domainCopy: AdminDomainDictionary;
  locale: string;
  control: Control<PersonFormData>;
  register: UseFormRegister<PersonFormData>;
  errors: FieldErrors<PersonFormData>;
  avatarFile: File | null;
  avatarPreview: string | null;
  avatarFileError: string | null;
  selectAvatarFile: (file?: File) => void;
  clearAvatarFile: () => void;
}

export function PersonAvatarSection({
  copy,
  domainCopy,
  locale,
  control,
  register,
  errors,
  avatarFile,
  avatarPreview,
  avatarFileError,
  selectAvatarFile,
  clearAvatarFile,
}: PersonAvatarSectionProps) {
  const avatarUrl = useWatch({ control, name: "avatar_url" });
  const canonicalName = useWatch({ control, name: "canonical_name" }) || copy.newPersonFallback;
  const avatarDisplayUrl = avatarPreview || avatarUrl || null;
  const fileSizeFormatter = new Intl.NumberFormat(locale, { maximumFractionDigits: 2 });

  return (
    <div className="grid gap-6 lg:grid-cols-[13rem_1fr]">
      <div className="rounded-xl border border-border bg-muted/25 p-5 text-center">
        <SaintAvatar
          name={canonicalName}
          avatar={avatarDisplayUrl ? { url: avatarDisplayUrl } : null}
          className="mx-auto h-32 w-32 text-3xl"
        />
        <p className="mt-4 text-sm font-semibold text-foreground">{copy.previewTitle}</p>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">
          {copy.previewDescription}
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <span className={PERSON_FORM_LABEL_CLASS}>{copy.diskFile}</span>
          <label
            htmlFor="avatar-file"
            className="flex cursor-pointer items-center justify-center gap-3 rounded-xl border border-dashed border-primary/35 bg-primary/5 px-5 py-6 text-sm text-foreground transition-colors hover:border-primary/60 hover:bg-primary/10"
          >
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Upload className="h-5 w-5" />
            </span>
            <span>
              <strong className="block font-semibold">{copy.chooseFile}</strong>
              <span className="mt-0.5 block text-xs text-muted-foreground">{copy.fileHint}</span>
            </span>
            <input
              key={avatarFile?.name ?? "empty-avatar-file"}
              id="avatar-file"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="sr-only"
              onChange={(event) => selectAvatarFile(event.target.files?.[0])}
            />
          </label>
          {avatarFileError && <p className={PERSON_FORM_ERROR_CLASS}>{avatarFileError}</p>}
          {avatarFile && (
            <div className="mt-2 flex items-center justify-between gap-3 rounded-lg border border-border bg-background px-3 py-2">
              <div className="flex min-w-0 items-center gap-2">
                <FileImage className="h-4 w-4 shrink-0 text-primary" />
                <span className="truncate text-xs font-medium text-foreground">{avatarFile.name}</span>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {fileSizeFormatter.format(avatarFile.size / 1024 / 1024)} MB
                </span>
              </div>
              <button
                type="button"
                onClick={clearAvatarFile}
                className="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                aria-label={copy.removeFileAriaLabel}
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>

        <div className="sm:col-span-2 flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
          <span className="h-px flex-1 bg-border" />
          {copy.orUseAddress}
          <span className="h-px flex-1 bg-border" />
        </div>

        <div className="sm:col-span-2">
          <label className={PERSON_FORM_LABEL_CLASS}>{copy.imageUrl}</label>
          <div className="relative">
            <ImagePlus className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              {...register("avatar_url")}
              className={cn(PERSON_FORM_INPUT_CLASS, "pl-9")}
              placeholder={copy.imageUrlPlaceholder}
            />
          </div>
          {errors.avatar_url && <p className={PERSON_FORM_ERROR_CLASS}>{errors.avatar_url.message}</p>}
          {avatarFile && (
            <p className="mt-1 text-xs text-muted-foreground">{copy.fileOverridesUrl}</p>
          )}
        </div>

        <div>
          <label className={PERSON_FORM_LABEL_CLASS}>{copy.thumbnailUrl}</label>
          <input {...register("avatar_thumbnail_url")} className={PERSON_FORM_INPUT_CLASS} placeholder={copy.thumbnailUrlPlaceholder} />
          {errors.avatar_thumbnail_url && <p className={PERSON_FORM_ERROR_CLASS}>{errors.avatar_thumbnail_url.message}</p>}
        </div>

        <div>
          <label className={PERSON_FORM_LABEL_CLASS}>{copy.altText}</label>
          <input {...register("avatar_title")} className={PERSON_FORM_INPUT_CLASS} placeholder={`${copy.altTextPrefix} ${canonicalName}`} />
        </div>

        <div>
          <label className={PERSON_FORM_LABEL_CLASS}>{copy.license}</label>
          <select {...register("avatar_license")} className={PERSON_FORM_INPUT_CLASS}>
            {Object.entries(domainCopy.avatarLicenseLabels).map(([value, label]) => (
              <option key={value} value={value as AdminAvatarLicenseKey}>{label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className={PERSON_FORM_LABEL_CLASS}>{copy.photographer}</label>
          <input {...register("avatar_photographer")} className={PERSON_FORM_INPUT_CLASS} placeholder={copy.photographerPlaceholder} />
        </div>

        <div className="sm:col-span-2">
          <label className={PERSON_FORM_LABEL_CLASS}>{copy.sourceUrl}</label>
          <input {...register("avatar_source_url")} className={PERSON_FORM_INPUT_CLASS} placeholder={copy.sourceUrlPlaceholder} />
          {errors.avatar_source_url && <p className={PERSON_FORM_ERROR_CLASS}>{errors.avatar_source_url.message}</p>}
        </div>

        <div className="sm:col-span-2 flex gap-2 rounded-lg border border-primary/15 bg-primary/5 p-3 text-xs leading-5 text-muted-foreground">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
          {copy.processingHint}
        </div>
      </div>
    </div>
  );
}
