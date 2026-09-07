export function formatAdminDateTime(
  value: string | Date | null | undefined,
  locale: string,
): string {
  if (!value) return "—";

  try {
    return new Intl.DateTimeFormat(locale, {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(typeof value === "string" ? new Date(value) : value);
  } catch {
    return String(value);
  }
}

export function formatAdminRelativeDays(days: number, locale: string): string {
  return new Intl.RelativeTimeFormat(locale, { numeric: "auto" }).format(
    -Math.max(0, days),
    "day",
  );
}
