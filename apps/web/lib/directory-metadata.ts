export type DirectorySearchParams = Record<string, string | readonly string[] | undefined>;

function hasValue(value: string | readonly string[] | undefined): boolean {
  if (typeof value !== "string") {
    return value?.some((item) => item.trim().length > 0) ?? false;
  }
  return value.trim().length > 0;
}

/**
 * Search, filters and pagination describe a catalogue state rather than a
 * standalone public landing page. Keep those URLs crawlable for navigation,
 * but prevent them from competing with the canonical catalogue URL.
 */
export function hasDirectoryState(params: DirectorySearchParams): boolean {
  return Object.values(params).some(hasValue);
}

export function directoryRobots(params: DirectorySearchParams): {
  index: boolean;
  follow: boolean;
} {
  return hasDirectoryState(params)
    ? { index: false, follow: true }
    : { index: true, follow: true };
}
