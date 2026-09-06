/** Resolve an API key through a complete dictionary without trusting unknown values. */
export function resolveDictionaryValue<Key extends string, Value>(
  dictionary: Record<Key, Value>,
  value: unknown,
): Value | undefined {
  const key = typeof value === "string" ? value : "";
  return Object.prototype.hasOwnProperty.call(dictionary, key)
    ? dictionary[key as Key]
    : undefined;
}

export function resolveDictionaryLabel<Key extends string>(
  labels: Record<Key, string>,
  value: unknown,
): string | undefined {
  return resolveDictionaryValue(labels, value);
}
