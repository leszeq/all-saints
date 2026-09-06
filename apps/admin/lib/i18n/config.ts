export const ADMIN_UI_LOCALES = ["pl"] as const;

export type AdminUiLocale = (typeof ADMIN_UI_LOCALES)[number];

export const DEFAULT_ADMIN_UI_LOCALE: AdminUiLocale = "pl";

export function resolveAdminUiLocale(value?: string | null): AdminUiLocale {
  const normalized = value?.trim().toLowerCase().replaceAll("_", "-");
  const exact = normalized && ADMIN_UI_LOCALES.find((locale) => locale === normalized);
  if (exact) return exact;

  const primaryLanguage = normalized?.split("-")[0];
  return (
    ADMIN_UI_LOCALES.find((locale) => locale === primaryLanguage) ?? DEFAULT_ADMIN_UI_LOCALE
  );
}
