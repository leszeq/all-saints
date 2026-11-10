/**
 * Serialize structured data for an inline JSON-LD script safely.
 *
 * JSON.stringify alone can emit a literal `</script>` when editorial content
 * contains a less-than sign. Browsers terminate the script element before the
 * JSON parser gets a chance to read it. Escaping the HTML-sensitive characters
 * keeps the payload valid JSON while preventing the markup parser from closing
 * the element early.
 */
export function serializeJsonLd(value: unknown): string {
  const serialized = JSON.stringify(value) ?? "null";
  return serialized
    .replace(/</g, "\\u003c")
    .replace(/>/g, "\\u003e")
    .replace(/&/g, "\\u0026")
    .replace(/\u2028/g, "\\u2028")
    .replace(/\u2029/g, "\\u2029");
}

export interface JsonLdBreadcrumbItem {
  name: string;
  url: string;
}

/**
 * Build a Schema.org breadcrumb list from the same canonical URLs rendered by
 * the page. Keeping this shape in one place prevents pages from drifting into
 * different structured-data contracts as more public sections are added.
 */
export function createBreadcrumbListJsonLd(
  items: readonly JsonLdBreadcrumbItem[],
  id: string,
) {
  return {
    "@type": "BreadcrumbList",
    "@id": id,
    itemListElement: items.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.name,
      item: item.url,
    })),
  };
}
