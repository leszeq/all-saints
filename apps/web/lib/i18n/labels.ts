/** Resolve an API enum through a complete dictionary without trusting unknown keys. */
export function resolveDictionaryLabel<Key extends string>(
  labels: Record<Key, string>,
  value: unknown,
): string | undefined {
  const key = typeof value === "string" ? value : "";
  return Object.prototype.hasOwnProperty.call(labels, key)
    ? labels[key as Key]
    : undefined;
}
