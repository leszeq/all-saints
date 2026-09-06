export const WEB_UI_LOCALES = ["pl"] as const;

export type WebUiLocale = (typeof WEB_UI_LOCALES)[number];

export const DEFAULT_WEB_UI_LOCALE: WebUiLocale = "pl";

export function isWebUiLocale(value: string): value is WebUiLocale {
  return WEB_UI_LOCALES.some((locale) => locale === value);
}

export function resolveWebUiLocale(value?: string | null): WebUiLocale {
  const normalized = value?.trim().toLowerCase().replaceAll("_", "-");
  const exact = normalized && WEB_UI_LOCALES.find((locale) => locale === normalized);
  if (exact) return exact;

  const primaryLanguage = normalized?.split("-")[0];
  return (
    WEB_UI_LOCALES.find((locale) => locale === primaryLanguage) ?? DEFAULT_WEB_UI_LOCALE
  );
}
