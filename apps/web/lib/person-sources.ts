export interface PublicBibliography {
  title: string;
  subtitle?: string | null;
  authors?: string | null;
  editor?: string | null;
  publisher?: string | null;
  place_of_publication?: string | null;
  year?: number | null;
  edition?: string | null;
  volume?: string | null;
  pages?: string | null;
  isbn?: string | null;
  issn?: string | null;
  doi?: string | null;
  url?: string | null;
  url_access_date?: string | null;
}

export interface PublicPersonSource {
  id: string;
  page_reference?: string | null;
  is_primary: boolean;
  bibliography?: PublicBibliography | null;
  historical_source?: {
    title: string;
    original_title?: string | null;
    repository?: string | null;
    call_number?: string | null;
    date_range?: string | null;
    digitization_url?: string | null;
  } | null;
}

export function sourceHttpUrl(value?: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value.trim());
    return ["http:", "https:"].includes(url.protocol) && !url.username && !url.password
      ? url.href : null;
  } catch {
    return null;
  }
}

export function sourceDoiUrl(value?: string | null): string | null {
  if (!value) return null;
  const doi = value.trim().replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, "").replace(/^doi:\s*/i, "");
  if (!/^10\.\d{4,9}\/\S+$/i.test(doi)) return null;
  try {
    return `https://doi.org/${encodeURI(doi).replace(/#/g, "%23").replace(/\?/g, "%3F")}`;
  } catch {
    return null;
  }
}
