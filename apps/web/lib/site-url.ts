const DEFAULT_SITE_URL = "https://encyklopediaswietych.pl";

export function getSiteUrl(): URL {
  const configured = process.env.NEXT_PUBLIC_SITE_URL?.trim() || DEFAULT_SITE_URL;
  try {
    return new URL(configured.endsWith("/") ? configured : `${configured}/`);
  } catch {
    return new URL(`${DEFAULT_SITE_URL}/`);
  }
}

export function absoluteSiteUrl(path = "/"): string {
  return new URL(path, getSiteUrl()).toString();
}
