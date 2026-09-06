export interface PublicPersonContent {
  canonicalName: string;
  summary: string | null;
  biography: string | null;
  prayers: string | null;
  iconographicAttributes: string | null;
  requestedLocale: string | null;
  resolvedLocale: string | null;
  fallbackUsed: boolean;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function optionalText(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

/**
 * Read one language-coherent API projection. Legacy fields are used only when an
 * older backend does not return `localized_content`; they are never merged into
 * an existing, potentially incomplete translation.
 */
export function readPublicPersonContent(person: Record<string, unknown>): PublicPersonContent {
  const localized = asRecord(person.localized_content);

  if (localized) {
    return {
      // canonical_name is the stable public identity and remains the final display
      // fallback when an incomplete editorial translation has no localized name.
      canonicalName:
        optionalText(localized.canonical_name) ?? optionalText(person.canonical_name) ?? "",
      summary: optionalText(localized.summary),
      biography: optionalText(localized.biography),
      prayers: optionalText(localized.prayers),
      iconographicAttributes: optionalText(localized.iconographic_attributes),
      requestedLocale: optionalText(localized.requested_locale),
      resolvedLocale: optionalText(localized.resolved_locale),
      fallbackUsed: localized.fallback_used === true,
    };
  }

  return {
    canonicalName: optionalText(person.canonical_name) ?? "",
    summary: optionalText(person.summary_pl),
    biography: optionalText(person.biography_pl),
    prayers: optionalText(person.prayers),
    iconographicAttributes: optionalText(person.iconographic_attributes),
    requestedLocale: null,
    resolvedLocale: null,
    fallbackUsed: false,
  };
}
