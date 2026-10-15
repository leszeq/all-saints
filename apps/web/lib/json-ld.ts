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
