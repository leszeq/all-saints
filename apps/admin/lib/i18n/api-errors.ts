import { getApiErrorMessage } from "@/lib/api";
import type { AdminApiErrorsDictionary } from "@/lib/i18n/types";

export function formatAdminApiError(
  error: unknown,
  copy: AdminApiErrorsDictionary,
  overrides: { invalidData?: string } = {},
): string {
  return getApiErrorMessage(error, {
    messagesByCode: {
      UNAUTHORIZED: copy.unauthorized,
      FORBIDDEN: copy.forbidden,
      NOT_FOUND: copy.notFound,
      CONFLICT: copy.conflict,
      BAD_REQUEST: copy.validation,
      VALIDATION_ERROR: copy.validation,
      RATE_LIMITED: copy.rateLimited,
      INTERNAL_SERVER_ERROR: copy.server,
    },
    unexpected: copy.unexpected,
    invalidValue: copy.invalidValue,
    invalidData: overrides.invalidData ?? copy.invalidData,
    network: copy.network,
    httpError: (status) =>
      `${copy.requestFailedPrefix}${status}${copy.requestFailedSuffix}`,
  });
}
